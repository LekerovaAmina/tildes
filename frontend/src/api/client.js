// Клиент API Django-бэкенда (backend/learning/urls.py).
// В разработке Vite проксирует /api на http://127.0.0.1:8000 (vite.config.js).
// Для продакшена укажите адрес бэкенда в VITE_API_URL (см. .env.example).

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

const DEVICE_KEY = 'tildes-device-id'

function deviceId() {
  try {
    let id = localStorage.getItem(DEVICE_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(DEVICE_KEY, id)
    }
    return id
  } catch {
    return 'anonymous'
  }
}

async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Device-Id': deviceId() },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`API ${method} ${path}: ${res.status}`)
  return res.json()
}

// Изменяющие запросы (ответы на карточки и т.п.) отправляем строго по очереди:
// порядок сохраняется, и бэкенд не получает пачку одновременных записей.
let writeQueue = Promise.resolve()
function write(path, body, method = 'POST') {
  const run = () => request(path, { method, body })
  const p = writeQueue.then(run, run)
  writeQueue = p.catch(() => {})
  return p
}

export const api = {
  levels: () => request('/levels/'),
  modules: (level = 'b2') => request(`/levels/${level}/modules/`),
  content: (level = 'b2') => request(`/levels/${level}/content/`),
  module: (id) => request(`/modules/${id}/`),
  submitQuiz: (id, answers) => write(`/modules/${id}/quiz/`, { answers }),
  reviewDeck: (size = 20) => request(`/cards/review/?size=${size}`),
  answerCard: (wordId, result) => write('/cards/answer/', { word_id: wordId, result }),
  completeTopic: (moduleId = null) => write('/cards/complete/', { module_id: moduleId }),
  markRead: (moduleId, section) => write('/topics/read/', { module_id: moduleId, section }),
  progress: () => request('/progress/'),
  updateProfile: (data) => write('/progress/', data, 'PATCH'),
  resetProgress: () => write('/progress/reset/'),
  leaderboard: () => request('/leaderboard/'),
}
