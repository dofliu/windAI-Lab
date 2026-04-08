import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 後端 port：優先讀 VITE_BACKEND_PORT 環境變數，預設 5800
const backendPort = process.env.VITE_BACKEND_PORT || '5800'
const backendUrl = `http://localhost:${backendPort}`

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/ws': {
        target: backendUrl,
        ws: true,
      },
    },
  },
})
