import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, getToken } from '../api/client.js'

// Кнопки «Войти» / «Регистрация» в шапке. Если пользователь вошёл — его имя, ссылка на /auth.
export default function AuthButtons() {
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (!getToken()) return
    let alive = true
    api
      .me()
      .then((r) => alive && setUser(r.user))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  if (user) {
    return (
      <Link to="/auth" className="chip chip-user" title={user.email}>
        {user.name || user.email}
      </Link>
    )
  }

  return (
    <div className="auth-buttons">
      <Link to="/auth" className="btn btn-ghost btn-sm">
        Войти
      </Link>
      <Link to="/auth?mode=register" className="btn btn-primary btn-sm auth-register-btn">
        Регистрация
      </Link>
    </div>
  )
}
