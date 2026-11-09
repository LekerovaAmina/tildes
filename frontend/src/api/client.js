// Клиент API Django-бэкенда (backend/learning/urls.py).
// В разработке Vite проксирует /api на http://127.0.0.1:8000 (vite.config.js).
// Для продакшена укажите адрес бэкенда в VITE_API_URL (см. .env.example).

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

// Адрес страницы на бэкенде (например, админки /admin/)
export const serverUrl = (path) => `${BASE}${path}`

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

// Токен входа (POST /api/auth/login/ или /register/). Без него работает анонимный режим по X-Device-Id.
const TOKEN_KEY = 'tildes-auth-token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {}
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json', 'X-Device-Id': deviceId() }
  const token = getToken()
  if (token) headers.Authorization = `Token ${token}`
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = new Error(`API ${method} ${path}: ${res.status}`)
    err.status = res.status
    err.data = await res.json().catch(() => null)
    // Токен устарел или удалён — возвращаемся в анонимный режим
    if (token && (res.status === 401 || res.status === 403)) setToken(null)
    throw err
  }
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
  register: (data) => request('/auth/register/', { method: 'POST', body: data }).then((r) => (setToken(r.token), r)),
  login: (email, password) =>
    request('/auth/login/', { method: 'POST', body: { email, password } }).then((r) => (setToken(r.token), r)),
  logout: () => request('/auth/logout/', { method: 'POST' }).finally(() => setToken(null)),
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
