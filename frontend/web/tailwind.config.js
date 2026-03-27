/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0f1117',
          card: '#161b27',
          elevated: '#1c2333',
          border: '#2a3448',
        },
        accent: {
          green: '#4ade80',
          amber: '#fbbf24',
          red: '#f87171',
          blue: '#60a5fa',
          muted: '#64748b',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
