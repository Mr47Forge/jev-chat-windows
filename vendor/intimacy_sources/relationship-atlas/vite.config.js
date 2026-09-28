import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/fetlife-relationship-atlas/',
  plugins: [react()],
  build: {
    sourcemap: false,
    target: 'es2020',
    chunkSizeWarningLimit: 1100,
  },
  test: {
    exclude: ['tests/**', 'node_modules/**', 'dist/**'],
  },
})
