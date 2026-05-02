import { heroui } from '@heroui/react'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    './node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: 'var(--color-surface)',
          secondary: 'var(--color-surface-sec)',
          tertiary: 'var(--color-surface-ter)',
          border: 'var(--color-surface-border)',
        },
        brand: {
          DEFAULT: '#6366f1',
          hover: '#4f46e5',
          light: '#818cf8',
          glow: '#a5b4fc',
        },
      },
      fontFamily: {
        display: ['Nabla', 'system-ui', 'sans-serif'],
        sans: ['Average Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glass: '0 4px 24px -4px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)',
        indigo: '0 0 20px rgba(99,102,241,0.35)',
        'indigo-inset': 'inset 0 0 0 1px rgba(99,102,241,0.4)',
      },
    },
  },
  plugins: [heroui({ addCommonColors: true })],
}
