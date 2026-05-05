/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-primary': '#12232e',
        'dark-secondary': '#0B0C10',
        'dark-card': '#1a3344',
        'dark-border': '#1e3a50',
        'accent': '#3a7bd5',
        'accent-light': '#00d2ff',
      },
      fontFamily: {
        lato: ['Lato', 'sans-serif'],
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(to right, #3a7bd5, #00d2ff)',
      },
    },
  },
  plugins: [],
}
