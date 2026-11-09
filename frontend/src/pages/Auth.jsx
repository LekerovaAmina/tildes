import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, getToken, serverUrl } from '../api/client.js'

// Страница входа и регистрации: /auth. Работает с /api/auth/* (backend/learning/auth.py).

function errorText(err) {
  const data = err?.data
  if (!data) return err?.status ? `Ошибка сервера (${err.status})` : 'Нет связи с сервером'
  if (typeof data.detail === 'string') return data.detail
  return Object.values(data).flat().join(' ')
}

export default function Auth() {
  const [params] = useSearchParams()
  const [mode, setMode] = useState(params.get('mode') === 'register' ? 'register' : 'login')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [user, setUser] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    api
      .me()
      .then((r) => setUser(r.user))
      .catch(() => {})
      .finally(() => setChecking(false))
  }, [])

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const r = mode === 'login' ? await api.login(form.email, form.password) : await api.register(form)
      // Администратор / редактор — сразу в админку (сессия уже открыта бэкендом)
      if (r.redirect) {
        window.location.href = serverUrl(r.redirect)
        return
      }
      setUser(r.user)
      setForm({ name: '', email: '', password: '' })
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  async function logout() {
    setBusy(true)
    await api.logout().catch(() => {})
    setUser(null)
    setBusy(false)
  }

  return (
    <div className="soon-page">
      <div className="card auth-card">
        <Link to="/" className="logo auth-logo">
          <span className="logo-mark">T</span> Tildes
        </Link>

        {checking ? (
          <div className="spinner" aria-label="Загрузка" />
        ) : user ? (
          <>
            <h1 className="auth-title">Вы вошли</h1>
            <dl className="auth-info">
              <dt>Имя</dt>
              <dd>{user.name || '—'}</dd>
              <dt>Email</dt>
              <dd>{user.email}</dd>
              <dt>Роль</dt>
              <dd>{user.role}</dd>
              <dt>Баллы</dt>
              <dd>{user.points}</dd>
              <dt>ID</dt>
              <dd>{user.id}</dd>
            </dl>
            {user.is_staff && (
              <a href={serverUrl('/admin/')} className="btn btn-primary btn-block">
                Админ-панель
              </a>
            )}
            {/* Полная перезагрузка — прогресс и баллы загрузятся уже от аккаунта */}
            <a href="/home" className={`btn btn-block ${user.is_staff ? 'btn-ghost' : 'btn-primary'}`}>
              К урокам
            </a>
            <button className="btn btn-ghost btn-block" onClick={logout} disabled={busy}>
              Выйти
            </button>
          </>
        ) : (
          <>
            <div className="auth-tabs" role="tablist">
              {[
                ['login', 'Вход'],
                ['register', 'Регистрация'],
              ].map(([key, label]) => (
                <button
                  key={key}
                  role="tab"
                  aria-selected={mode === key}
                  className={`auth-tab${mode === key ? ' active' : ''}`}
                  onClick={() => {
                    setMode(key)
                    setError('')
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            <form className="auth-form" onSubmit={submit}>
              {mode === 'register' && (
                <label>
                  Имя
                  <input value={form.name} onChange={set('name')} maxLength={80} autoComplete="name" />
                </label>
              )}
              <label>
                Email
                <input type="email" required value={form.email} onChange={set('email')} autoComplete="email" />
              </label>
              <label>
                Пароль
                <input
                  type="password"
                  required
                  value={form.password}
                  onChange={set('password')}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
              </label>
              {mode === 'register' && <p className="muted small">Минимум 8 символов, не только цифры.</p>}
              {error && <p className="auth-error">{error}</p>}
              <button className="btn btn-primary btn-lg btn-block" disabled={busy}>
                {busy ? '…' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
