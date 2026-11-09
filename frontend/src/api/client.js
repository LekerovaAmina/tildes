// Клиент API Django-бэкенда (backend/learning/urls.py).
// В разработке Vite проксирует /api на http://127.0.0.1:8000 (vite.config.js).
// Для продакшена укажите адрес бэкенда в VITE_API_URL (см. .env.example).

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

// Токен входа (POST /api/auth/login/) хранится в браузере и уходит в заголовке Authorization
const TOKEN_KEY = 'tildes-token'

export const tokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token)
      else localStorage.removeItem(TOKEN_KEY)
    } catch {
      /* приватный режим — токен живёт до перезагрузки */
    }
  },
}

// Ошибка API с текстом от сервера (для форм входа и регистрации)
export class ApiError extends Error {
  constructor(status, data) {
    super(firstMessage(data) || `Ошибка ${status}`)
    this.status = status
    this.data = data
  }
}

function firstMessage(data) {
  if (!data || typeof data !== 'object') return ''
  if (typeof data.detail === 'string') return data.detail
  const v = Object.values(data)[0]
  return Array.isArray(v) ? String(v[0]) : typeof v === 'string' ? v : ''
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = tokenStore.get()
  if (token) headers.Authorization = `Token ${token}`

  const res = await fetch(`${BASE}/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  const data = await res.json().catch(() => null)
  if (res.status === 401 && token) {
    // токен устарел или удалён — просим войти заново
    tokenStore.set(null)
    window.dispatchEvent(new Event('tildes:logout'))
  }
  if (!res.ok) throw new ApiError(res.status, data)
  return data
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
  register: (email, password, name) => request('/auth/register/', { method: 'POST', body: { email, password, name } }),
  login: (email, password) => request('/auth/login/', { method: 'POST', body: { email, password } }),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  me: () => request('/auth/me/'),

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
