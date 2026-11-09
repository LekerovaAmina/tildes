import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../store/auth.jsx'
import { ProgressProvider } from '../store/progress.jsx'
import ServerGate from './ServerGate.jsx'

// Все страницы, кроме входа и регистрации, доступны только после входа.
// Прогресс грузится для конкретного пользователя (key — чтобы при смене аккаунта начать с чистого листа).
export default function RequireAuth() {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'checking') {
    return (
      <div className="soon-page">
        <div className="spinner" aria-label="Загрузка" />
      </div>
    )
  }
  if (status !== 'user') {
    return <Navigate to="/auth" replace state={{ from: location.pathname + location.search + location.hash }} />
  }
  return (
    <ProgressProvider key={user.id}>
      <ServerGate>
        <Outlet />
      </ServerGate>
    </ProgressProvider>
  )
}
