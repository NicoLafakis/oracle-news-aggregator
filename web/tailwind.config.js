/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        oracle: {
          dark: '#0a0a0f',
          darker: '#050508',
          gold: '#d4af37',
          glow: '#ffd700',
        }
      }
    },
  },
  plugins: [],
}
