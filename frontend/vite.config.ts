import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend runs on :5173. Backend Django/Daphne on :8000.
// Proxy API + WebSocket so relative paths just work in the app.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true, changeOrigin: true },
    },
  },
})
