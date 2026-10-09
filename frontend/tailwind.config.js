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
          bg: '#F8FAFC',
          surface: '#FFFFFF',
          panel: '#FFFFFF',
          subtle: '#F1F5F9',
          border: '#E2E8F0',
          borderLight: '#EDF1F5',
          borderDark: '#CBD5E1',
          text: '#0F172A',
          secondary: '#334155',
          muted: '#64748B',
          faint: '#94A3B8',
          hover: '#F8FAFC',
          active: '#E0F2FE',
        },
        flood: {
          safe: '#059669',     // Emerald Green
          advisory: '#D97706', // Amber
          warning: '#EA580C',  // Orange
          severe: '#DC2626',   // Crimson Red
          water: '#0284C7',    // Vibrant GIS Cyan/Blue
          waterSurface: '#38BDF8',
          river: '#0369A1',
          deep: '#082F49',
        },
        brand: {
          50: '#F0F9FF',
          100: '#E0F2FE',
          200: '#BAE6FD',
          300: '#7DD3FC',
          400: '#38BDF8',
          500: '#0EA5E9',
          600: '#0284C7',
          700: '#0369A1',
          800: '#075985',
          900: '#0C4A6E',
          950: '#082F49',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'monospace'],
        display: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'gis-xs': '0 1px 2px 0 rgba(15, 23, 42, 0.05)',
        'gis-sm': '0 1px 3px 0 rgba(15, 23, 42, 0.08), 0 1px 2px -1px rgba(15, 23, 42, 0.04)',
        'gis': '0 2px 6px -1px rgba(15, 23, 42, 0.07), 0 1px 3px -1px rgba(15, 23, 42, 0.05)',
        'gis-md': '0 4px 12px -2px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)',
        'gis-lg': '0 8px 24px -4px rgba(15, 23, 42, 0.08), 0 2px 6px -2px rgba(15, 23, 42, 0.04)',
        'float': '0 14px 34px -4px rgba(15, 23, 42, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.06)',
      }
    },
  },
  plugins: [],
}
