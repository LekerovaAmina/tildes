import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { panelApi, serverUrl } from '../api/client.js'
import Icon from '../components/Icon.jsx'
import { useAuth } from '../store/auth.jsx'
import { CrumbsContext } from './ui.jsx'
import './panel.css'

// Каркас админ-панели по макету Figma: меню слева, сверху хлебные крошки, поиск и уровень.

const ROLE = { admin: 'admin', editor: 'редактор', student: 'ученик' }

export default function PanelLayout() {
  const { status, user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [crumbs, setCrumbs] = useState([])
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => setMenuOpen(false), [location.pathname])

  if (status === 'checking') {
    return (
      <div className="soon-page">
        <div className="spinner" aria-label="Загрузка" />
      </div>
    )
  }
  if (status !== 'user') return <Navigate to="/auth" replace state={{ from: location.pathname }} />
  if (!user.is_staff) return <Navigate to="/home" replace />

  const onLogout = async () => {
    await logout()
    navigate('/auth', { replace: true })
  }

  return (
    <div className="panel">
      <aside className={`p-side ${menuOpen ? 'open' : ''}`}>
        <Link to="/panel" className="p-brand">
          <span className="logo-mark">T</span>
          <span>
            <b>Tildes</b>
            <small>Админ-панель</small>
          </span>
        </Link>

        <nav className="p-nav">
          <span className="p-nav-group">Обзор</span>
          <NavLink to="/panel" end className="p-nav-link">
            <Icon name="home" size={18} /> Дашборд
          </NavLink>
          <span className="p-nav-group">Контент</span>
          <NavLink to="/panel/levels" className={({ isActive }) => `p-nav-link ${isActive || location.pathname.startsWith('/panel/lessons') ? 'active' : ''}`}>
            <Icon name="layers" size={18} /> Уровни и модули
          </NavLink>
          <span className="p-nav-group">Скоро</span>
          <NavLink to="/panel/listening" className="p-nav-link">
            <Icon name="headphones" size={18} /> Аудирование
          </NavLink>
          <NavLink to="/panel/speaking" className="p-nav-link">
            <Icon name="mic" size={18} /> Говорение
          </NavLink>
          <NavLink to="/panel/writing" className="p-nav-link">
            <Icon name="pen" size={18} /> Письмо
          </NavLink>
        </nav>

        <div className="p-user">
          <span className="p-avatar">{(user.name || user.email)[0].toUpperCase()}</span>
          <span className="p-user-info">
            <b>{user.name || 'Администратор'}</b>
            <small>роль: {ROLE[user.role] || user.role}</small>
          </span>
          <button className="p-icon-btn" onClick={onLogout} title="Выйти" aria-label="Выйти">
            <Icon name="logout" size={16} />
          </button>
        </div>
        <div className="p-side-links">
          <Link to="/home">
            <Icon name="external" size={14} /> На сайт
          </Link>
          <a href={serverUrl('/admin/')}>
            <Icon name="external" size={14} /> Django-админка
          </a>
        </div>
      </aside>
      {menuOpen && <div className="p-side-backdrop" onClick={() => setMenuOpen(false)} />}

      <div className="p-main">
        <header className="p-top">
          <button className="p-icon-btn p-burger" onClick={() => setMenuOpen(true)} aria-label="Меню">
            <Icon name="lines" size={18} />
          </button>
          <nav className="p-crumbs" aria-label="Навигация">
            {crumbs.map((c, i) => (
              <span key={i}>
                {i > 0 && <span className="p-crumb-sep">/</span>}
                {c.to && i < crumbs.length - 1 ? <Link to={c.to}>{c.label}</Link> : <b>{c.label}</b>}
              </span>
            ))}
          </nav>
          <Search />
          <Link to="/panel/levels/B2" className="p-level-chip">
            Уровень: B2
          </Link>
        </header>
        <main className="p-content">
          <CrumbsContext.Provider value={setCrumbs}>
            <Outlet />
          </CrumbsContext.Provider>
        </main>
      </div>
    </div>
  )
}

function Search() {
  const [q, setQ] = useState('')
  const [res, setRes] = useState(null)
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (q.trim().length < 2) {
      setRes(null)
      return
    }
    const t = setTimeout(() => panelApi.search(q.trim()).then(setRes).catch(() => setRes(null)), 250)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    const onDoc = (e) => box.current && !box.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const go = (to) => {
    setOpen(false)
    setQ('')
    navigate(to)
  }
  const empty = res && !res.lessons.length && !res.words.length

  return (
    <div className="p-search" ref={box}>
      <Icon name="search" size={18} />
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        placeholder="Поиск по урокам и словам"
        aria-label="Поиск по урокам и словам"
      />
      {open && res && (
        <div className="p-search-drop">
          {empty && <p className="p-muted">Ничего не нашлось</p>}
          {res.lessons.length > 0 && <span className="p-drop-group">Уроки</span>}
          {res.lessons.map((l) => (
            <button key={`l${l.id}`} onClick={() => go(`/panel/lessons/${l.id}`)}>
              <b>{l.title}</b>
              <small>{l.where}</small>
            </button>
          ))}
          {res.words.length > 0 && <span className="p-drop-group">Слова</span>}
          {res.words.map((w) => (
            <button key={`w${w.id}`} onClick={() => go(`/panel/lessons/${w.lesson_id}/cards?word=${w.id}`)}>
              <b>{w.kz}</b> — {w.ru}
              <small>{w.where}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
