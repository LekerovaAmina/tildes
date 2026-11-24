import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Куда проксировать запросы к Django. Локально — 127.0.0.1:8000,
// в Docker — http://core:8000 (имя сервиса из infra/docker-compose.yml)
const API_TARGET = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // В Docker на Windows/macOS включаем опрос файлов, чтобы работала горячая перезагрузка
    watch: process.env.CHOKIDAR_USEPOLLING === 'true' ? { usePolling: true, interval: 300 } : undefined,
    // Запросы /api/* уходят на Django (backend, порт 8000)
    // /django-admin и /static — Django-админка на том же адресе, чтобы после входа сессия сразу работала.
    // /admin — это админ-панель самого сайта (React), её Vite отдаёт сам
    proxy: {
      '/api': API_TARGET,
      '/django-admin': API_TARGET,
      '/static': API_TARGET,
      // Загруженные картинки карточек (MEDIA_URL Django)
      '/media': API_TARGET,
    },
  },
})