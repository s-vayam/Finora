/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Pro Finance Palette
        lime: {
          DEFAULT: '#D9F83F', // Neon lime
          neon: '#D9F83F',
          soft: '#ECF9A8',    // Soft lime
          hover: '#c8ea2e',
        },
        page: '#F5F5F2',      // Warm off-white
        card: '#FFFFFF',      // White
        black: {
          DEFAULT: '#111111',
          pure: '#000000',
          panel: '#161616',
        },
        grey: {
          secondary: '#8B8D86', // Secondary grey
          light: '#F0F0ED',
        },
        border: {
          DEFAULT: '#E7E7E2',
          light: '#EEEEEA',
        },
        // Semantic statuses
        semantic: {
          success: '#39765A',
          successBg: '#EDF7F2',
          successBorder: '#BDE3D1',
          warning: '#A87524',
          warningBg: '#FEF8EC',
          warningBorder: '#F5DCB2',
          critical: '#B94A48',
          criticalBg: '#FDF2F2',
          criticalBorder: '#F6CECE',
        }
      },
      borderRadius: {
        DEFAULT: '8px',
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '20px',
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'monospace',
        ],
      },
      boxShadow: {
        'subtle': '0 1px 3px rgba(0, 0, 0, 0.03), 0 1px 2px rgba(0, 0, 0, 0.02)',
        'card': '0 2px 6px rgba(0, 0, 0, 0.03)',
        'lime': '0 0 16px rgba(217, 248, 63, 0.4)',
      }
    },
  },
  plugins: [],
}
