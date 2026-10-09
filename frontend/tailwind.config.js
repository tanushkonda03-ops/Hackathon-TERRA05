/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gis: {
          bg: '#F5F7FA',
          panel: '#FFFFFF',
          border: '#DDE3EA',
          borderLight: '#EDF1F5',
          text: '#1A202C',
          muted: '#64748B',
          subtle: '#94A3B8',
          hover: '#F1F5F9',
        },
        flood: {
          safe: '#10B981',     // Green
          advisory: '#F59E0B', // Yellow
          warning: '#F97316',  // Orange
          severe: '#EF4444',   // Red
          water: '#0284C7',    // Vibrant GIS Cyan/Blue
          waterSurface: '#38BDF8',
          river: '#0369A1',
        },
        brand: {
          50: '#F0F9FF',
          100: '#E0F2FE',
          500: '#0EA5E9',
          600: '#0284C7',
          700: '#0369A1',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'monospace'],
        display: ['"Chakra Petch"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        gis: '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'gis-lg': '0 8px 24px -4px rgba(15, 23, 42, 0.08), 0 2px 6px -2px rgba(15, 23, 42, 0.04)',
        float: '0 12px 32px -4px rgba(15, 23, 42, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.06)',
      }
    },
  },
  plugins: [],
}
