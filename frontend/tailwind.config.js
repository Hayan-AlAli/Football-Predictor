/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Instrument Sans', ...['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif']],
        mono: ['IBM Plex Mono', ...['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace']],
        display: ['Big Shoulders Display', ...['Impact', 'Arial Narrow', 'sans-serif']],
      },
      colors: {
        ground: {
          DEFAULT: '#0F1114',
          deep: '#0A0B0D',
        },
        panel: '#171A1F',
        raised: '#1D2127',
        line: {
          DEFAULT: '#262B33',
          strong: '#3A404A',
        },
        chalk: {
          DEFAULT: '#E9E6DF',
          soft: '#B5B8BE',
          faint: '#8C919A',
        },
        amber: {
          DEFAULT: '#FFB547',
          deep: '#E89A2C',
        },
        signal: {
          DEFAULT: '#6FA8FF',
          deep: '#4F8DEB',
          bright: '#9CC3FF',
        },
        draw: '#4B515C',
      },
      boxShadow: {
        'plate': '0 1px 0 rgba(255, 255, 255, 0.03) inset, 0 12px 32px -16px rgba(0, 0, 0, 0.6)',
        'press': '0 2px 0 rgba(0, 0, 0, 0.35)',
      },
      fontSize: {
        'micro': '0.6875rem',
      },
      letterSpacing: {
        'caps': '0.08em',
        'wider-caps': '0.14em',
      },
      transitionTimingFunction: {
        'print': 'cubic-bezier(0.22, 1, 0.36, 1)',
        'press': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}
