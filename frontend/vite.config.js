import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const envDir = path.resolve(__dirname, '..')

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, '')
  const frontendPort = Number(env.FRONTEND_PORT || 5177)
  const backendPort = Number(env.APP_PORT || 8100)

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@assets': path.resolve(__dirname, '../assets'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: frontendPort,
      strictPort: true,
      allowedHosts: ['telecombot.darrov.uz', 'uztelecombot.darrov.uz', 'localhost', '127.0.0.1'],
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
        '/uploads': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
        '/ws': {
          target: `ws://localhost:${backendPort}`,
          ws: true,
        },
      },
    },
  }
})
