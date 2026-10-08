"""
Download public raster inputs for Mumbai Flood MVP.

Datasets:
1. ESA WorldCover 2021 v200
2. SRTM 1 arc-second DEM tiles

The downloader:
- uses project-root-relative paths
- downloads in chunks
- retries failed connections
- resumes partial downloads when the server supports HTTP Range
- does not restart completed files
"""

from pathlib import Path
import time
import requests


# ============================================================
# PROJECT PATH
# ============================================================

# .../mumbai_flood_data_ready_package/scripts/download_external_rasters.py
#                    ↑
# parents[1] = project root

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUT = PROJECT_ROOT / "data" / "raw" / "external"
OUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# SETTINGS
# ============================================================

CHUNK_SIZE = 1024 * 1024 * 4       # 4 MB
MAX_RETRIES = 10
TIMEOUT = (30, 300)                # connect, read


# ============================================================
# RESUMABLE DOWNLOADER
# ============================================================

def download_file(url: str, destination: Path):
    """
    Download a file with retry + resume support.
    """

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Temporary partial file
    partial = destination.with_suffix(destination.suffix + ".part")

    # Already completed
    if destination.exists() and destination.stat().st_size > 1000:
        print(f"[SKIP] {destination}")
        return

    existing_size = partial.stat().st_size if partial.exists() else 0

    print()
    print("=" * 70)
    print(f"[DOWNLOAD] {destination.name}")
    print(f"[URL]      {url}")

    if existing_size > 0:
        print(f"[RESUME]   {existing_size / (1024 * 1024):.2f} MB already downloaded")

    session = requests.Session()

    headers = {
        "User-Agent": "MumbaiFloodMVP/1.0"
    }

    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(f"[ATTEMPT] {attempt}/{MAX_RETRIES}")

            response = session.get(
                url,
                headers=headers,
                stream=True,
                timeout=TIMEOUT
            )

            response.raise_for_status()

            # ------------------------------------------------
            # Check whether server honored resume request
            # ------------------------------------------------

            if existing_size > 0 and response.status_code == 206:

                mode = "ab"

                print("[RESUME] Server supports HTTP Range requests.")

            elif existing_size > 0 and response.status_code == 200:

                # Server ignored Range.
                # Restart safely rather than corrupting the file.

                print(
                    "[INFO] Server did not honor Range request. "
                    "Restarting download."
                )

                existing_size = 0
                partial.unlink(missing_ok=True)

                mode = "wb"

            else:

                mode = "wb"

            # ------------------------------------------------
            # Calculate expected size
            # ------------------------------------------------

            content_length = response.headers.get("Content-Length")

            if content_length:
                content_length = int(content_length)

                total_size = (
                    existing_size + content_length
                    if response.status_code == 206
                    else content_length
                )
            else:
                total_size = None

            downloaded = existing_size if mode == "ab" else 0

            # ------------------------------------------------
            # Download chunks
            # ------------------------------------------------

            with open(partial, mode) as f:

                last_print = time.time()

                for chunk in response.iter_content(
                    chunk_size=CHUNK_SIZE
                ):

                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)

                    # Progress every ~1 second
                    now = time.time()

                    if now - last_print >= 1:

                        if total_size:

                            percent = (
                                downloaded / total_size * 100
                            )

                            print(
                                f"\r[PROGRESS] "
                                f"{downloaded / (1024 * 1024):.1f} / "
                                f"{total_size / (1024 * 1024):.1f} MB "
                                f"({percent:.1f}%)",
                                end="",
                                flush=True
                            )

                        else:

                            print(
                                f"\r[PROGRESS] "
                                f"{downloaded / (1024 * 1024):.1f} MB",
                                end="",
                                flush=True
                            )

                        last_print = now

            print()

            # ------------------------------------------------
            # Validate
            # ------------------------------------------------

            if partial.stat().st_size < 1000:

                raise RuntimeError(
                    "Downloaded file is suspiciously small."
                )

            # Move partial → final
            partial.replace(destination)

            print(
                f"[SAVED] {destination}"
            )

            return

        except Exception as e:

            print()
            print(
                f"[ERROR] Attempt {attempt}/{MAX_RETRIES}: {e}"
            )

            if attempt == MAX_RETRIES:

                print(
                    f"[FAILED] Could not download {url}"
                )

                print(
                    f"[PARTIAL] {partial}"
                )

                raise

            # Recalculate current partial size
            existing_size = (
                partial.stat().st_size
                if partial.exists()
                else 0
            )

            if existing_size > 0:

                headers["Range"] = f"bytes={existing_size}-"

                print(
                    f"[RETRY] Will resume from "
                    f"{existing_size / (1024 * 1024):.2f} MB"
                )

            else:

                headers.pop("Range", None)

            wait = min(attempt * 3, 20)

            print(
                f"[WAIT] Retrying in {wait} seconds..."
            )

            time.sleep(wait)


# ============================================================
# 1. ESA WORLDCOVER
# ============================================================

WORLD_COVER_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
    "v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_N18E072_Map.tif"
)

worldcover = OUT / "worldcover_N18E072.tif"

download_file(
    WORLD_COVER_URL,
    worldcover
)


# ============================================================
# 2. SRTM DEM
# ============================================================

SRTM_BASE = "https://terrain.ardupilot.org/SRTM1"

SRTM_TILES = [
    "N18E072",
    "N18E073",
    "N19E072",
    "N19E073",
]

for tile in SRTM_TILES:

    url = f"{SRTM_BASE}/{tile}.hgt.zip"

    output = OUT / f"{tile}.hgt.zip"

    download_file(
        url,
        output
    )


# ============================================================
# FINISHED
# ============================================================

print()
print("=" * 70)
print("EXTERNAL RASTER DOWNLOADS COMPLETE")
print("=" * 70)

print()
print("Files are located at:")
print(OUT)

print()
print("Next steps:")
print()
print("1. Mosaic SRTM HGT files into:")
print("   data/raw/external/dem_mumbai.tif")
print()
print("2. Prepare/copy WorldCover as:")
print("   data/raw/external/worldcover_mumbai.tif")
print()
print("3. Then run:")
print("   python compute_derived_features.py")