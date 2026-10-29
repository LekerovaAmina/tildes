import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Запросы /api/* уходят на Django (backend, порт 8000)
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
