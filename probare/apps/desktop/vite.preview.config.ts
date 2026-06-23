import { resolve } from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Config Vite standalone pour le preview renderer (sans Electron)
export default defineConfig({
  root: 'src/renderer',
  plugins: [react()],
  resolve: {
    alias: {
      '@renderer': resolve(__dirname, 'src/renderer/src'),
      '@': resolve(__dirname, 'src/renderer/src'),
    },
  },
  server: {
    port: Number(process.env.PORT) || 5173,
  },
  css: {
    postcss: resolve(__dirname, 'postcss.config.js'),
  },
})
