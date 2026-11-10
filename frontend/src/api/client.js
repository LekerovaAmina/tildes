// Клиент API Django-бэкенда (backend/learning/urls.py).
// В разработке Vite проксирует /api и /admin на http://127.0.0.1:8000 (vite.config.js).
// Для продакшена укажите адрес бэкенда в VITE_API_URL (см. .env.example).

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

// Адрес страницы на бэкенде (например, админки /admin/)
export const serverUrl = (path) => `${BASE}${path}`

const DEVICE_KEY = 'tildes-device-id'

// id устройства: бэкенд переносит анонимный прогресс устройства в аккаунт при регистрации
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

// Токен входа (POST /api/auth/login/ или /register/, backend/learning/auth.py)
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
  } catch {
    /* приватный режим — токен живёт до перезагрузки */
  }
}

// Понятный текст ошибки от сервера (для форм входа и регистрации)
export function errorText(err) {
  const data = err?.data
  if (!data) return err?.status ? `Ошибка сервера (${err.status})` : 'Нет связи с сервером. Запустите бэкенд (backend/run.bat).'
  if (typeof data.detail === 'string') return data.detail
  return Object.values(data).flat().join(' ')
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
    // Токен устарел или удалён — сайт просит войти заново (store/auth.jsx)
    if (token && (res.status === 401 || res.status === 403)) {
      setToken(null)
      window.dispatchEvent(new Event('tildes:logout'))
    }
    throw err
  }
  return res.json()
}

// Загрузка файла (картинка карточки) — multipart, поэтому без JSON-заголовка
async function upload(path, file) {
  const form = new FormData()
  form.append('file', file)
  const token = getToken()
  const res = await fetch(`${BASE}/api${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Token ${token}` } : {},
    body: form,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const err = new Error(`API POST ${path}: ${res.status}`)
    err.status = res.status
    err.data = data
    throw err
  }
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

// API админ-панели (backend/learning/panel_api.py) — только для admin / editor
const send = (path, method, body) => request(path, { method, body })
export const panelApi = {
  dashboard: (level = 'B2') => request(`/panel/dashboard/?level=${level}`),
  search: (q) => request(`/panel/search/?q=${encodeURIComponent(q)}`),
  levels: () => request('/panel/levels/'),
  createLevel: (data) => send('/panel/levels/', 'POST', data),
  updateLevel: (code, data) => send(`/panel/levels/${code}/`, 'PATCH', data),
  modules: (code) => request(`/panel/levels/${code}/modules/`),
  createModule: (code, data) => send(`/panel/levels/${code}/modules/`, 'POST', data),
  reorderModules: (code, ids) => send(`/panel/levels/${code}/modules/reorder/`, 'POST', { ids }),
  updateModule: (id, data) => send(`/panel/modules/${id}/`, 'PATCH', data),
  createLesson: (moduleId, data = {}) => send(`/panel/modules/${moduleId}/lessons/`, 'POST', data),
  lesson: (id) => request(`/panel/lessons/${id}/`),
  updateLesson: (id, data) => send(`/panel/lessons/${id}/`, 'PATCH', data),
  deleteLesson: (id) => send(`/panel/lessons/${id}/`, 'DELETE'),
  publishLesson: (id) => send(`/panel/lessons/${id}/publish/`, 'POST'),
  addBlock: (id, type) => send(`/panel/lessons/${id}/blocks/`, 'POST', { type }),
  deleteBlock: (id, type) => send(`/panel/lessons/${id}/blocks/${type}/`, 'DELETE'),
  reorderBlocks: (id, types) => send(`/panel/lessons/${id}/blocks/reorder/`, 'POST', { types }),
  words: (lessonId) => request(`/panel/lessons/${lessonId}/words/`),
  createWord: (lessonId, data) => send(`/panel/lessons/${lessonId}/words/`, 'POST', data),
  updateWord: (id, data) => send(`/panel/words/${id}/`, 'PATCH', data),
  deleteWord: (id) => send(`/panel/words/${id}/`, 'DELETE'),
  wordsBulk: (lessonId, ids, action) => send(`/panel/lessons/${lessonId}/words/bulk/`, 'POST', { ids, action }),
  importWords: (lessonId, csv) => send(`/panel/lessons/${lessonId}/words/import/`, 'POST', { csv }),
  uploadImage: (file) => upload('/panel/media/', file),
  grammar: (lessonId) => request(`/panel/lessons/${lessonId}/grammar/`),
  saveGrammar: (lessonId, data) => send(`/panel/lessons/${lessonId}/grammar/`, 'PUT', data),
  textQuiz: (lessonId) => request(`/panel/lessons/${lessonId}/text-quiz/`),
  saveTextQuiz: (lessonId, data) => send(`/panel/lessons/${lessonId}/text-quiz/`, 'PUT', data),
}
