/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        // Status colors
        status: {
          todo: '#f59e0b',          // amber-500
          'in-progress': '#3b82f6', // blue-500
          done: '#22c55e',          // green-500
          blocked: '#ef4444',       // red-500
        },
        // Priority/Release colors
        priority: {
          low: '#6b7280',         // gray-500
          medium: '#f59e0b',      // amber-500
          high: '#ef4444',        // red-500
          mvp: '#ef4444',         // backward compatibility
          release1: '#f97316',    // backward compatibility
          later: '#6b7280',       // backward compatibility
        },
        severity: {
          low: '#38bdf8',       // sky-400
          medium: '#f59e0b',    // amber-500
          high: '#f97316',      // orange-500
          critical: '#ef4444',  // red-500
        },
        // Surface colors
        surface: {
          DEFAULT: '#ffffff',
          muted: '#f9fafb',
          subtle: '#f3f4f6',
          border: '#e5e7eb',
          'border-strong': '#d1d5db',
        },
        // Text colors
        content: {
          DEFAULT: '#111827',
          secondary: '#4b5563',
          muted: '#6b7280',
          subtle: '#9ca3af',
          inverse: '#ffffff',
        },
      },
      spacing: {
        // Touch-friendly sizes
        'touch': '44px',
        'touch-sm': '36px',
      },
      fontSize: {
        // Typography scale
        'heading-xl': ['1.5rem', { lineHeight: '2rem', fontWeight: '700' }],
        'heading-lg': ['1.25rem', { lineHeight: '1.75rem', fontWeight: '600' }],
        'heading-md': ['1.125rem', { lineHeight: '1.5rem', fontWeight: '600' }],
        'heading-sm': ['1rem', { lineHeight: '1.5rem', fontWeight: '600' }],
        'body-lg': ['1rem', { lineHeight: '1.5rem', fontWeight: '400' }],
        'body-md': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '400' }],
        'body-sm': ['0.75rem', { lineHeight: '1rem', fontWeight: '400' }],
        'label': ['0.75rem', { lineHeight: '1rem', fontWeight: '500' }],
      },
      borderRadius: {
        'card': '0.75rem',
        'button': '0.5rem',
        'input': '0.5rem',
        'modal': '0.75rem',
        'badge': '9999px',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
        'card-drag': '0 12px 28px rgba(0, 0, 0, 0.2), 0 4px 10px rgba(0, 0, 0, 0.1)',
        'modal': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        'dropdown': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
      },
      animation: {
        'slide-in': 'slide-in 0.3s ease-out',
        'fade-in': 'fade-in 0.2s ease-out',
        'scale-in': 'scale-in 0.2s ease-out',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
      keyframes: {
        'slide-in': {
          from: { transform: 'translateX(100%)', opacity: '0' },
          to: { transform: 'translateX(0)', opacity: '1' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'scale-in': {
          from: { transform: 'scale(0.95)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
      transitionDuration: {
        'fast': '150ms',
        'normal': '200ms',
        'slow': '300ms',
      },
    },
  },
  plugins: [],
}

