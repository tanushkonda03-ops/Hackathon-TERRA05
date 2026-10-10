import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const pabitraSwdPath = fileURLToPath(new URL('../data/processed/bmc_storm_water_drains_working.geojson', import.meta.url))
let drainageGeoJson: string | undefined

function getDrainageGeoJson() {
  if (drainageGeoJson) return drainageGeoJson
  const source = JSON.parse(readFileSync(pabitraSwdPath, 'utf8')) as {
    type: string
    features: Array<{ type: string; properties?: Record<string, unknown>; geometry: unknown }>
  }
  const existingCount = source.features.filter((feature) => String(feature.properties?.USER_TEXT2 ?? '').trim().toLowerCase() === 'existing').length
  const proposalCount = source.features.length - existingCount
  drainageGeoJson = JSON.stringify(source)
  console.info(`[TERRA05] Bundling ${source.features.length} SWD conduits from Pabitra's GIS file (${existingCount} existing, ${proposalCount} proposed)`)
  return drainageGeoJson
}

const pabitraSwdDataPlugin: Plugin = {
  name: 'pabitra-swd-data',
  configureServer(server) {
    server.middlewares.use((request, response, next) => {
      const pathname = new URL(request.url ?? '/', 'http://localhost').pathname
      if (pathname !== '/data/drainage-network.geojson') return next()
      response.statusCode = 200
      response.setHeader('Content-Type', 'application/geo+json; charset=utf-8')
      response.setHeader('Cache-Control', 'public, max-age=300')
      response.end(getDrainageGeoJson())
    })
  },
  generateBundle() {
    this.emitFile({
      type: 'asset',
      fileName: 'data/drainage-network.geojson',
      source: getDrainageGeoJson(),
    })
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), pabitraSwdDataPlugin],
})
