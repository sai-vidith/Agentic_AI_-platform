/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: '#0a0a08',
        surface: '#111110',
        elevated: '#1a1a18',
        overlay: '#222220',
        border: '#2c2c2a',
        'border-strong': '#3d3d3a',
        primary: '#f5f5f0',
        secondary: '#a8a49e',
        muted: '#5c5a55',
        disabled: '#3d3b38',
        accent: '#c8f73a',
        'accent-dim': 'rgba(200, 247, 58, 0.12)',
        'accent-text': '#8fb825',
        success: '#4ade80',
        'success-dim': 'rgba(74, 222, 128, 0.10)',
        warning: '#f59e0b',
        'warning-dim': 'rgba(245, 158, 11, 0.10)',
        danger: '#f87171',
        'danger-dim': 'rgba(248, 113, 113, 0.10)',
        info: '#60a5fa',
        'info-dim': 'rgba(96, 165, 250, 0.10)',
      },
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}

