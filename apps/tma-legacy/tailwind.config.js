/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0D0D0F',
          card: '#141418',
          border: '#1F1F24',
          hover: '#1A1A1F',
        },
        accent: {
          purple: '#8B5CF6',
          violet: '#A855F7',
          glow: 'rgba(139, 92, 246, 0.4)',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#6B7280',
          muted: '#4B5563',
        },
      },
      fontFamily: {
        sans: ['Manrope', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glow': '0 0 20px rgba(139, 92, 246, 0.3)',
        'glow-lg': '0 0 40px rgba(139, 92, 246, 0.4)',
        'glow-sm': '0 0 10px rgba(139, 92, 246, 0.25)',
      },
      backgroundImage: {
        'gradient-purple': 'linear-gradient(135deg, #8B5CF6 0%, #A855F7 100%)',
        'gradient-dark': 'linear-gradient(180deg, #141418 0%, #0D0D0F 100%)',
      },
    },
  },
  plugins: [],
}
