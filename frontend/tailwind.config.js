/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Archivo', ...['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']],
        mono: ['Fragment Mono', ...['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monospace']],
        serif: ['Spectral', ...['Georgia', 'Cambria', 'Times New Roman', 'serif']],
      },
      colors: {
        paper: {
          DEFAULT: '#F1E9D8',
          deep: '#E9DFC8',
          white: '#FFFFFF',
          line: '#C9BD9F',
        },
        ink: {
          DEFAULT: '#2A2A29',
          soft: '#4A463F',
          faint: '#6A6355',
        },
        rubric: {
          DEFAULT: '#B93B2F',
          deep: '#A0392D',
        },
        ledger: {
          DEFAULT: '#2F6E48',
          deep: '#316B4A',
          bright: '#3E9C6E',
        },
      },
      boxShadow: {
        'plate': '0 1px 0 rgba(42, 42, 41, 0.08), 0 8px 24px -12px rgba(42, 42, 41, 0.3)',
        'press': '0 2px 0 rgba(42, 42, 41, 0.16)',
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
