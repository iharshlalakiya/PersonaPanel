/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dde6ff',
          200: '#c3d0ff',
          300: '#9fb0fd',
          400: '#7a87fa',
          500: '#5c5ff5',
          600: '#4a41ea',
          700: '#3d33cf',
          800: '#322ba7',
          900: '#2d2984',
          950: '#1b184d',
        },
      },
    },
  },
  plugins: [],
}
