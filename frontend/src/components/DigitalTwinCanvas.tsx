import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RiskZone, DrainageNode, LayerState, SeverityLevel } from '../types';

interface DigitalTwinCanvasProps {
  rainfall: number;
  isSimulating: boolean;
  simulationProgress: number; // 0 to 1
  selectedZone: RiskZone | null;
  onSelectZone: (zone: RiskZone) => void;
  layers: LayerState;
  zones: RiskZone[];
  drains: DrainageNode[];
}

export const DigitalTwinCanvas: React.FC<DigitalTwinCanvasProps> = ({
  rainfall,
  isSimulating,
  simulationProgress,
  selectedZone,
  onSelectZone,
  layers,
  zones,
  drains,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const waterMeshRef = useRef<THREE.Mesh | null>(null);
  const buildingsGroupRef = useRef<THREE.Group | null>(null);
  const drainsGroupRef = useRef<THREE.Group | null>(null);
  const zonesGroupRef = useRef<THREE.Group | null>(null);
  const riverGroupRef = useRef<THREE.Group | null>(null);
  const uncertaintyGroupRef = useRef<THREE.Group | null>(null);
  const historicalGroupRef = useRef<THREE.Group | null>(null);

  // Mouse interaction state
  const isDraggingRef = useRef(false);
  const previousMousePosition = useRef({ x: 0, y: 0 });
  const cameraRotation = useRef({ theta: Math.PI / 4, phi: Math.PI / 3.2, radius: 68 });
  const cameraTarget = useRef(new THREE.Vector3(0, 0, 0));

  // Initialize Three.js scene
  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene & Background
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06090e);
    scene.fog = new THREE.FogExp2(0x06090e, 0.015);
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    cameraRef.current = camera;
    updateCameraPosition();

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0x1e293b, 1.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x93c5fd, 2.2);
    dirLight.position.set(40, 60, 40);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    scene.add(dirLight);

    const blueHemisphere = new THREE.HemisphereLight(0x0284c7, 0x0f172a, 0.8);
    scene.add(blueHemisphere);

    // 5. Build Terrain Mesh (Mumbai coastal & Mithi Basin depression)
    const terrainGeo = new THREE.PlaneGeometry(120, 120, 64, 64);
    terrainGeo.rotateX(-Math.PI / 2);
    const pos = terrainGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const vx = pos.getX(i);
      const vz = pos.getZ(i);
      // Create Mithi river channel running roughly from z = -40 to z = 40 with meanders
      const riverDist = Math.abs(vx - (-15 + Math.sin(vz * 0.08) * 8));
      let height = (Math.sin(vx * 0.08) + Math.cos(vz * 0.08)) * 1.5;
      if (riverDist < 7) {
        // carved riverbed
        height -= (7 - riverDist) * 0.6;
      }
      pos.setY(i, height);
    }
    terrainGeo.computeVertexNormals();

    const terrainMat = new THREE.MeshStandardMaterial({
      color: 0x0b1320,
      roughness: 0.9,
      metalness: 0.1,
      wireframe: false,
    });
    const terrainMesh = new THREE.Mesh(terrainGeo, terrainMat);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    // Grid Floor Overlay
    const grid = new THREE.GridHelper(120, 40, 0x1e3a5f, 0x0f1d33);
    grid.position.y = -0.1;
    scene.add(grid);

    // 6. Natural Mithi River watercourse
    const riverGroup = new THREE.Group();
    const riverCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-28, 0.05, -50),
      new THREE.Vector3(-22, 0.05, -28),
      new THREE.Vector3(-16, 0.05, -10),
      new THREE.Vector3(-14, 0.05, 5),
      new THREE.Vector3(-10, 0.05, 25),
      new THREE.Vector3(-8, 0.05, 50),
    ]);
    const riverGeo = new THREE.TubeGeometry(riverCurve, 64, 3.8, 8, false);
    const riverMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      roughness: 0.1,
      metalness: 0.8,
      transparent: true,
      opacity: 0.85,
    });
    const riverMesh = new THREE.Mesh(riverGeo, riverMat);
    riverGroup.add(riverMesh);
    scene.add(riverGroup);
    riverGroupRef.current = riverGroup;

    // 7. Dynamic Flood Water Surface Mesh
    const waterGeo = new THREE.PlaneGeometry(100, 100, 32, 32);
    waterGeo.rotateX(-Math.PI / 2);
    const waterMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      roughness: 0.05,
      metalness: 0.9,
      transparent: true,
      opacity: 0.65,
    });
    const waterMesh = new THREE.Mesh(waterGeo, waterMat);
    waterMesh.position.y = -0.5; // Starts hidden under ground
    scene.add(waterMesh);
    waterMeshRef.current = waterMesh;

    // 8. Synthesize Mumbai Urban Blocks & Extruded Buildings
    const buildingsGroup = new THREE.Group();
    const boxGeo = new THREE.BoxGeometry(1, 1, 1);

    // Seeded pseudo-random building generator around Mumbai coordinates
    for (let bx = -45; bx <= 45; bx += 3.8) {
      for (let bz = -45; bz <= 45; bz += 3.8) {
        // Skip riverbed corridor
        const riverDist = Math.abs(bx - (-15 + Math.sin(bz * 0.08) * 8));
        if (riverDist < 5.5) continue;

        // Skip random plots for streets/parks
        if ((bx * 17 + bz * 31) % 7 === 0) continue;

        const isBkcZone = bx > -10 && bx < 10 && bz > -15 && bz < 5;
        const isKurla = bx < -10 && bz > 0 && bz < 18;

        // Height variation
        let height = 2 + Math.abs(Math.sin(bx * 0.5 + bz * 0.3) * 6);
        if (isBkcZone) height = 12 + Math.abs(Math.sin(bx) * 14); // high-rise commercial BKC
        if (isKurla) height = 2.5 + Math.abs(Math.sin(bz) * 4); // dense mid-rise residential

        const buildingMat = new THREE.MeshStandardMaterial({
          color: isBkcZone ? 0x1e3a5f : 0x131f33,
          roughness: 0.4,
          metalness: 0.4,
        });

        const building = new THREE.Mesh(boxGeo, buildingMat);
        const w = 1.8 + Math.random() * 0.8;
        const d = 1.8 + Math.random() * 0.8;
        building.scale.set(w, height, d);
        building.position.set(bx + (Math.random() - 0.5) * 0.5, height / 2, bz + (Math.random() - 0.5) * 0.5);
        building.castShadow = true;
        building.receiveShadow = true;
        buildingsGroup.add(building);
      }
    }
    scene.add(buildingsGroup);
    buildingsGroupRef.current = buildingsGroup;

    // 9. Drainage Network Mesh
    const drainsGroup = new THREE.Group();
    drains.forEach((drain) => {
      const points = drain.points.map((p) => new THREE.Vector3(p[0], p[1] + 0.15, p[2]));
      const curve = new THREE.CatmullRomCurve3(points);
      const tubeGeo = new THREE.TubeGeometry(curve, 20, drain.type === 'PRIMARY_OUTFALL' ? 0.45 : 0.25, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: drain.type === 'PRIMARY_OUTFALL' ? 0x06b6d4 : 0x0ea5e9,
        wireframe: false,
      });
      const drainMesh = new THREE.Mesh(tubeGeo, tubeMat);
      drainsGroup.add(drainMesh);

      // Add Manhole pulse rings along points
      points.forEach((pt) => {
        const ringGeo = new THREE.RingGeometry(0.3, 0.5, 16);
        ringGeo.rotateX(-Math.PI / 2);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, side: THREE.DoubleSide });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.position.copy(pt);
        ring.position.y += 0.05;
        drainsGroup.add(ring);
      });
    });
    scene.add(drainsGroup);
    drainsGroupRef.current = drainsGroup;

    // 10. Risk Zone Pylons & Hotspot Markers
    const zonesGroup = new THREE.Group();
    zones.forEach((zone) => {
      const zGroup = new THREE.Group();
      zGroup.name = zone.id;

      // Vertical beacon cylinder
      const cylGeo = new THREE.CylinderGeometry(0.2, 0.2, 10, 8);
      const cylMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.6,
      });
      const beacon = new THREE.Mesh(cylGeo, cylMat);
      beacon.position.set(zone.coordinates.x, 5, zone.coordinates.z);
      zGroup.add(beacon);

      // Expanding radar floor disk
      const diskGeo = new THREE.RingGeometry(1.5, 4.5, 32);
      diskGeo.rotateX(-Math.PI / 2);
      const diskMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.45,
        side: THREE.DoubleSide,
      });
      const disk = new THREE.Mesh(diskGeo, diskMat);
      disk.position.set(zone.coordinates.x, 0.12, zone.coordinates.z);
      zGroup.add(disk);

      zonesGroup.add(zGroup);
    });
    scene.add(zonesGroup);
    zonesGroupRef.current = zonesGroup;

    // 11. Uncertainty Hashed Cloud Group
    const uncertaintyGroup = new THREE.Group();
    zones.forEach((zone) => {
      const uncertGeo = new THREE.RingGeometry(4.5, 7.5, 24);
      uncertGeo.rotateX(-Math.PI / 2);
      const uncertMat = new THREE.MeshBasicMaterial({
        color: 0xa855f7,
        transparent: true,
        opacity: 0.35,
        wireframe: true,
      });
      const uncertMesh = new THREE.Mesh(uncertGeo, uncertMat);
      uncertMesh.position.set(zone.coordinates.x, 0.14, zone.coordinates.z);
      uncertaintyGroup.add(uncertMesh);
    });
    scene.add(uncertaintyGroup);
    uncertaintyGroupRef.current = uncertaintyGroup;

    // 12. Historical 2005 Comparison Outline Group
    const historicalGroup = new THREE.Group();
    zones.forEach((zone) => {
      const histGeo = new THREE.RingGeometry(2, 6.2, 16);
      histGeo.rotateX(-Math.PI / 2);
      const histMat = new THREE.MeshBasicMaterial({
        color: 0x10b981,
        transparent: true,
        opacity: 0.5,
        wireframe: true,
      });
      const histMesh = new THREE.Mesh(histGeo, histMat);
      histMesh.position.set(zone.coordinates.x + 0.5, 0.15, zone.coordinates.z - 0.5);
      historicalGroup.add(histMesh);
    });
    scene.add(historicalGroup);
    historicalGroupRef.current = historicalGroup;

    // Animation Render Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Subtle water rippling oscillation
      if (waterMeshRef.current) {
        waterMeshRef.current.position.y += Math.sin(elapsedTime * 2) * 0.0008;
      }

      // Rotate zone beacons
      if (zonesGroupRef.current) {
        zonesGroupRef.current.children.forEach((child, idx) => {
          const ring = child.children[1] as THREE.Mesh;
          if (ring) {
            ring.rotation.z += 0.008 * (idx % 2 === 0 ? 1 : -1);
          }
        });
      }

      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const handleResize = () => {
      if (!mountRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      if (rendererRef.current && container.contains(rendererRef.current.domElement)) {
        container.removeChild(rendererRef.current.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update camera coordinates based on spherical rotation
  const updateCameraPosition = () => {
    if (!cameraRef.current) return;
    const { theta, phi, radius } = cameraRotation.current;
    const x = cameraTarget.current.x + radius * Math.sin(phi) * Math.sin(theta);
    const y = cameraTarget.current.y + radius * Math.cos(phi);
    const z = cameraTarget.current.z + radius * Math.sin(phi) * Math.cos(theta);
    cameraRef.current.position.set(x, y, z);
    cameraRef.current.lookAt(cameraTarget.current);
  };

  // Mouse drag Orbit Controls
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    previousMousePosition.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return;
    const deltaX = e.clientX - previousMousePosition.current.x;
    const deltaY = e.clientY - previousMousePosition.current.y;

    cameraRotation.current.theta -= deltaX * 0.008;
    cameraRotation.current.phi = Math.max(0.1, Math.min(Math.PI / 2.1, cameraRotation.current.phi + deltaY * 0.008));

    updateCameraPosition();
    previousMousePosition.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    cameraRotation.current.radius = Math.max(25, Math.min(130, cameraRotation.current.radius + e.deltaY * 0.05));
    updateCameraPosition();
  };

  // Handle Raycasting click for Zone Selection
  const handleClick = (e: React.MouseEvent) => {
    if (!mountRef.current || !cameraRef.current || !sceneRef.current) return;
    const rect = mountRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);

    // Check intersection with zone discs or beacons
    if (zonesGroupRef.current) {
      const intersects = raycaster.intersectObjects(zonesGroupRef.current.children, true);
      if (intersects.length > 0) {
        // Find top-level zone group
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && obj.parent !== zonesGroupRef.current) {
          obj = obj.parent;
        }
        if (obj) {
          const matchedZone = zones.find((z) => z.id === obj?.name);
          if (matchedZone) {
            onSelectZone(matchedZone);
          }
        }
      }
    }
  };

  // Reactively respond to Simulation & Water Height changes
  useEffect(() => {
    if (!waterMeshRef.current) return;

    // Calculate simulated water height based on rainfall and simulation animation progress
    let targetWaterY = -0.5;
    if (rainfall === 25) targetWaterY = 0.15;
    else if (rainfall === 50) targetWaterY = 0.45;
    else if (rainfall === 100) targetWaterY = 0.85;
    else if (rainfall === 150) targetWaterY = 1.45;

    // Interpolate water based on simulationProgress
    const actualWaterY = isSimulating 
      ? -0.5 + (targetWaterY - (-0.5)) * simulationProgress 
      : targetWaterY;

    waterMeshRef.current.position.y = actualWaterY;

    // Color and opacity shifts with severity
    const mat = waterMeshRef.current.material as THREE.MeshStandardMaterial;
    if (mat) {
      if (rainfall >= 100) {
        mat.color.setHex(0x0284c7);
        mat.opacity = 0.78;
      } else if (rainfall >= 50) {
        mat.color.setHex(0x38bdf8);
        mat.opacity = 0.65;
      } else {
        mat.color.setHex(0x7dd3fc);
        mat.opacity = 0.45;
      }
    }
  }, [rainfall, isSimulating, simulationProgress]);

  // Reactively respond to Layer Toggles
  useEffect(() => {
    if (buildingsGroupRef.current) buildingsGroupRef.current.visible = layers.buildings;
    if (drainsGroupRef.current) drainsGroupRef.current.visible = layers.stormwaterDrains;
    if (zonesGroupRef.current) zonesGroupRef.current.visible = layers.floodRisk;
    if (uncertaintyGroupRef.current) uncertaintyGroupRef.current.visible = layers.uncertainty;
    if (historicalGroupRef.current) historicalGroupRef.current.visible = layers.historicalFloodExtent;
    if (waterMeshRef.current) waterMeshRef.current.visible = layers.floodDepth;
  }, [layers]);

  // Center camera on selected zone if changed
  useEffect(() => {
    if (selectedZone) {
      cameraTarget.current.set(selectedZone.coordinates.x, 2, selectedZone.coordinates.z);
      cameraRotation.current.radius = 45;
      updateCameraPosition();
    }
  }, [selectedZone]);

  // Color zone disks by current rainfall scenario severity
  useEffect(() => {
    if (!zonesGroupRef.current) return;
    zones.forEach((zone) => {
      const zGroup = zonesGroupRef.current?.getObjectByName(zone.id);
      if (zGroup) {
        const scenario = zone.scenarioData[rainfall] || zone.scenarioData[100];
        const isSelected = selectedZone?.id === zone.id;
        
        let colorHex = 0x10b981; // SAFE
        if (scenario.severity === 'ADVISORY') colorHex = 0xf59e0b;
        if (scenario.severity === 'WARNING') colorHex = 0xf97316;
        if (scenario.severity === 'SEVERE') colorHex = 0xef4444;

        zGroup.children.forEach((mesh) => {
          const m = mesh as THREE.Mesh;
          if (m.material) {
            const mat = m.material as THREE.MeshBasicMaterial;
            mat.color.setHex(isSelected ? 0x06b6d4 : colorHex);
            if (m.geometry.type === 'CylinderGeometry') {
              mat.opacity = isSelected ? 0.9 : 0.5;
            }
          }
        });
      }
    });
  }, [rainfall, selectedZone, zones]);

  return (
    <div
      ref={mountRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      onClick={handleClick}
      className="w-full h-full cursor-grab active:cursor-grabbing relative overflow-hidden"
    >
      {/* Compass / Orientation HUD element */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none flex items-center space-x-2">
        <div className="px-2.5 py-1.5 rounded bg-command-900/80 backdrop-blur border border-command-700/80 text-[10px] font-mono text-slate-300 flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
          <span>MUMBAI ELEVATION GRID (MSL)</span>
          <span className="text-slate-500">|</span>
          <span className="text-cyan-400">LAT: 19.0760° N, LON: 72.8777° E</span>
        </div>
      </div>

      {/* 3D Zone Labels HUD floating in viewport */}
      <div className="absolute inset-0 pointer-events-none">
        {zones.map((zone) => {
          const scenario = zone.scenarioData[rainfall] || zone.scenarioData[100];
          const isSelected = selectedZone?.id === zone.id;

          // Simple static label positioning mapping for the key Mumbai areas
          const labelStyle: React.CSSProperties = {
            position: 'absolute',
            left: `${50 + zone.coordinates.x * 0.9}%`,
            top: `${50 + zone.coordinates.z * 0.8}%`,
            transform: 'translate(-50%, -50%)',
          };

          return (
            <div
              key={zone.id}
              style={labelStyle}
              onClick={(e) => {
                e.stopPropagation();
                onSelectZone(zone);
              }}
              className={`pointer-events-auto cursor-pointer transition-transform hover:scale-110 flex flex-col items-center ${
                isSelected ? 'scale-110 z-20' : 'z-10'
              }`}
            >
              <div
                className={`px-2 py-0.5 rounded text-[10px] font-tech font-bold uppercase tracking-wider flex items-center space-x-1 shadow-lg border ${
                  scenario.severity === 'SEVERE'
                    ? 'bg-rose-950/90 text-rose-300 border-rose-500/80'
                    : scenario.severity === 'WARNING'
                    ? 'bg-amber-950/90 text-amber-300 border-amber-500/80'
                    : scenario.severity === 'ADVISORY'
                    ? 'bg-yellow-950/90 text-yellow-300 border-yellow-500/80'
                    : 'bg-emerald-950/90 text-emerald-300 border-emerald-500/80'
                } ${isSelected ? 'ring-2 ring-cyan-400' : ''}`}
              >
                <span>{zone.name.split(' ')[0]}</span>
                <span className="font-mono text-[9px] opacity-90">
                  {scenario.expectedDepthM.toFixed(2)}m
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
