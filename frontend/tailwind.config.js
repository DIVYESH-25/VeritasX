/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: '#020617',
          dark: '#020617',
          cyan: '#00E5FF',
          blue: '#0077FF',
          card: 'rgba(0, 0, 0, 0.2)',
          border: 'rgba(0, 229, 255, 0.6)',
        },
      },
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        space: ['"Space Grotesk"', 'sans-serif'],
        inter: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backgroundImage: {
        'radial-center-glow': 'radial-gradient(circle at center, rgba(0, 229, 255, 0.35) 0%, rgba(0, 119, 255, 0.15) 45%, transparent 70%)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 4s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)' },
          '50%': { opacity: '0.9', transform: 'scale(1.05)' },
        },
      },
    },
  },
  plugins: [],
};
