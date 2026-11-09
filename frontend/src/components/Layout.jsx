import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth.jsx'
import { useProgress } from '../store/progress.jsx'
import Icon from './Icon.jsx'

const nav = [
  { to: '/home', label: 'Главная', icon: 'home' },
  { to: '/cards', label: 'Карточки', icon: 'cards' },
  { to: '/topics', label: 'Темы', icon: 'book' },
  { to: '/rating', label: 'Рейтинг', icon: 'trophy' },
]

export function Logo() {
  return (
    <Link to="/" className="logo">
      <span className="logo-mark">Т</span>
      <span className="logo-text">Tildes</span>
    </Link>
  )
}

export default function Layout() {
  const { points, level } = useProgress()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  // После ручного выхода и нового входа — на главную, а не на последнюю открытую страницу
  const onLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }
  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar-inner">
          <Logo />
          <nav className="topnav">
            {nav.map((n) => (
              <NavLink key={n.to} to={n.to} className="topnav-link">
                <Icon name={n.icon} size={18} />
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="topbar-right">
            <span className="chip chip-level">{level || 'B2'}</span>
            <Link to="/rating" className="chip chip-points">
              <Icon name="star" size={14} /> {points}
            </Link>
            <button className="icon-btn logout-btn" onClick={onLogout} title={`Выйти (${user.email})`} aria-label="Выйти">
              <Icon name="logout" size={18} />
            </button>
          </div>
        </div>
      </header>

      <main className="container main">
        <Outlet />
      </main>

      <nav className="tabbar">
        {nav.map((n) => (
          <NavLink key={n.to} to={n.to} className="tab">
            <Icon name={n.icon} size={22} />
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
