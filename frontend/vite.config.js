import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@assets': path.resolve(__dirname, '../assets'),
    },
  },
  server: {
    port: 5173,
    allowedHosts: ['uztelecombot.darrov.uz', 'localhost', '127.0.0.1'],
    proxy: {
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://localhost:8100',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8100',
        ws: true
      }
    }
  }
})
