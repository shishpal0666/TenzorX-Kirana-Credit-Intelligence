/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#e6f2f2',
          100: '#c0dfdf',
          200: '#99cbcf',
          300: '#73b8b8',
          400: '#4da4a4',
          500: '#3B9797', // Teal primary
          600: '#2f7979',
          700: '#235a5a',
          800: '#173c3c',
          900: '#0c1e1e',
        },
        navy: {
          400: '#333399',
          500: '#000080', // Navy Blue
          600: '#000066',
          700: '#00004d',
        },
        surface: {
          0:   '#000000', // Black
          50:  '#030303',
          100: '#080808',
          200: '#121212',
          300: '#1c1c1c',
          400: '#262626',
        }
      },
      animation: {
        'fade-up'    : 'fadeUp 0.5s ease-out forwards',
        'gauge-fill' : 'gaugeFill 1.2s ease-out forwards',
        'pulse-slow' : 'pulse 3s ease-in-out infinite',
        'shimmer'    : 'shimmer 2s linear infinite',
        'count-up'   : 'countUp 0.8s ease-out forwards',
      },
      keyframes: {
        fadeUp: {
          '0%'  : { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%'  : { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'grid-pattern': "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%233B9797' fill-opacity='0.03'%3E%3Cpath d='M0 0h40v1H0zM0 0v40h1V0z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
      }
    },
  },
  plugins: [],
}
