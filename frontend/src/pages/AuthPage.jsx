import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { errorText } from '../api/client.js'
import { Logo } from '../components/Layout.jsx'
import Icon from '../components/Icon.jsx'
import { useAuth } from '../store/auth.jsx'

// Страница входа и регистрации: /auth (вход) и /auth?mode=register. Работает с /api/auth/* (backend/learning/auth.py).
export default function AuthPage() {
  const [params] = useSearchParams()
  const isRegister = params.get('mode') === 'register'
  const { status, user, login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  // Переключили вкладку — старая ошибка больше не к месту
  useEffect(() => setError(''), [isRegister])

  // Куда вести после входа: на страницу, с которой отправили на вход, иначе — к выбору уровня или на главную
  // Сотрудник (admin / editor) — в админ-панель (или на ту её страницу, с которой отправили на вход)
  const after = (u) => {
    const from = location.state?.from
    if (u.is_staff) return from?.startsWith('/panel') ? from : '/panel'
    return from || (u.level ? '/home' : '/')
  }

  if (status === 'user') return <Navigate to={after(user)} replace />

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setSending(true)
    try {
      const res = isRegister
        ? await register(form.email.trim(), form.password, form.name.trim())
        : await login(form.email.trim(), form.password)
      // Сессию Django-админки для сотрудника бэкенд тоже открыл — ссылка на неё есть в меню панели
      navigate(after(res.user), { replace: true })
    } catch (err) {
      setError(errorText(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="auth-page">
      <aside className="auth-side" aria-hidden="true">
        <Logo />
        <div className="auth-side-text">
          <h2>Қазақ тілін қуанышпен үйреніңіз</h2>
          <p>Карточки, темы из учебника, тесты и рейтинг — прогресс сохраняется в вашем аккаунте.</p>
        </div>
        <div className="auth-side-card">
          <span className="demo-word">Қош келдіңіз!</span>
          <span>Добро пожаловать!</span>
        </div>
      </aside>

      <main className="auth-main">
        <div className="auth-mobile-logo">
          <Logo />
        </div>
        <form className="auth-card card" onSubmit={submit} noValidate>
          <div className="auth-tabs" role="tablist">
            <Link to="/auth" state={location.state} replace role="tab" aria-selected={!isRegister} className={!isRegister ? 'active' : ''}>
              Вход
            </Link>
            <Link to="/auth?mode=register" state={location.state} replace role="tab" aria-selected={isRegister} className={isRegister ? 'active' : ''}>
              Регистрация
            </Link>
          </div>

          <h1 className="h1">{isRegister ? 'Создайте аккаунт' : 'С возвращением!'}</h1>
          <p className="muted">{isRegister ? 'Тіркелу — это займёт минуту' : 'Кіру — войдите, чтобы продолжить обучение'}</p>

          {isRegister && (
            <label className="field">
              <span>Имя</span>
              <input value={form.name} onChange={set('name')} autoComplete="name" maxLength={80} placeholder="Например, Айгерим" />
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={form.email}
              onChange={set('email')}
              autoComplete="email"
              inputMode="email"
              required
              placeholder="name@example.com"
            />
          </label>

          <label className="field">
            <span>Пароль</span>
            <div className="password-wrap">
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={set('password')}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                required
                placeholder={isRegister ? 'Минимум 8 символов, не только цифры' : ''}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                <Icon name={showPassword ? 'eyeOff' : 'eye'} size={18} />
              </button>
            </div>
          </label>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn-primary btn-lg btn-block" disabled={sending || !form.email || !form.password}>
            {sending ? 'Подождите…' : isRegister ? 'Зарегистрироваться' : 'Войти'}
          </button>

          <p className="auth-switch muted">
            {isRegister ? 'Уже есть аккаунт? ' : 'Нет аккаунта? '}
            <Link to={isRegister ? '/auth' : '/auth?mode=register'} state={location.state} replace>
              {isRegister ? 'Войти' : 'Зарегистрироваться'}
            </Link>
          </p>
        </form>
      </main>
    </div>
  )
}
