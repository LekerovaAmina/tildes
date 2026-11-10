import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { errorText } from '../api/client.js'
import Icon from '../components/Icon.jsx'

// Общие кусочки админ-панели: статусы, загрузка данных, хлебные крошки, перетаскивание

export const STATUS = {
  draft: { label: 'Черновик', tone: 'amber' },
  review: { label: 'На проверке', tone: 'violet' },
  published: { label: 'Опубликован', tone: 'green' },
  archived: { label: 'В архиве', tone: 'gray' },
}

export function Badge({ status, children, tone }) {
  const s = STATUS[status]
  return <span className={`p-badge p-badge-${tone || s?.tone || 'gray'}`}>{children || s?.label || status}</span>
}

export const BLOCKS = {
  cards: { title: 'Карточки слов', kz: 'Сөздер', icon: 'cards', path: 'cards' },
  grammar: { title: 'Грамматика', kz: 'Грамматика', icon: 'book', path: 'grammar' },
  text: { title: 'Текст для чтения', kz: 'Мәтін', icon: 'lines', path: 'text' },
  quiz: { title: 'Тест', kz: 'Сұрақтар', icon: 'question', path: 'text' },
}

// Загрузка данных страницы: { data, setData, loading, error, reload }
export function useLoad(fn, deps) {
  const [state, setState] = useState({ data: null, loading: true, error: '' })
  const fnRef = useRef(fn)
  fnRef.current = fn
  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: '' }))
    return fnRef
      .current()
      .then((data) => setState({ data, loading: false, error: '' }))
      .catch((e) => setState({ data: null, loading: false, error: errorText(e) }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => {
    reload()
  }, [reload])
  const setData = useCallback((upd) => setState((s) => ({ ...s, data: typeof upd === 'function' ? upd(s.data) : upd })), [])
  return { ...state, setData, reload }
}

export function Loading({ error, onRetry }) {
  if (error) {
    return (
      <div className="p-card p-empty">
        <p className="p-error">{error}</p>
        {onRetry && (
          <button className="p-btn" onClick={onRetry}>
            <Icon name="repeat" size={16} /> Повторить
          </button>
        )}
      </div>
    )
  }
  return (
    <div className="p-loading">
      <div className="spinner" aria-label="Загрузка" />
    </div>
  )
}

// Хлебные крошки страница задаёт сама, шапка их показывает
export const CrumbsContext = createContext(() => {})
export function useCrumbs(crumbs) {
  const set = useContext(CrumbsContext)
  const key = JSON.stringify(crumbs)
  useEffect(() => {
    set(crumbs)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, set])
}

export function PageHead({ title, sub, children }) {
  return (
    <div className="p-head">
      <div>
        <h1>{title}</h1>
        {sub && <p className="p-muted">{sub}</p>}
      </div>
      {children && <div className="p-head-actions">{children}</div>}
    </div>
  )
}

// Короткое сообщение «Сохранено» / ошибка рядом с кнопками
export function useFlash() {
  const [flash, setFlash] = useState(null)
  const timer = useRef(null)
  const show = useCallback((text, tone = 'ok') => {
    clearTimeout(timer.current)
    setFlash({ text, tone })
    timer.current = setTimeout(() => setFlash(null), 3500)
  }, [])
  const node = flash && <span className={`p-flash p-flash-${flash.tone}`}>{flash.text}</span>
  return [node, show]
}

// Перетаскивание строк списка (HTML5 drag & drop). onMove(from, to)
export function useDragSort(onMove) {
  const from = useRef(null)
  const [over, setOver] = useState(null)
  return (index) => ({
    draggable: true,
    onDragStart: (e) => {
      from.current = index
      e.dataTransfer.effectAllowed = 'move'
    },
    onDragOver: (e) => {
      e.preventDefault()
      if (over !== index) setOver(index)
    },
    onDragLeave: () => setOver((o) => (o === index ? null : o)),
    onDrop: (e) => {
      e.preventDefault()
      setOver(null)
      if (from.current !== null && from.current !== index) onMove(from.current, index)
      from.current = null
    },
    onDragEnd: () => setOver(null),
    'data-drag-over': over === index || undefined,
  })
}

export const move = (list, from, to) => {
  const copy = [...list]
  const [item] = copy.splice(from, 1)
  copy.splice(to, 0, item)
  return copy
}

export function Modal({ title, sub, onClose, children, footer }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="p-modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="p-modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="p-modal-head">
          <div>
            <h2>{title}</h2>
            {sub && <p className="p-muted">{sub}</p>}
          </div>
          <button className="p-icon-btn" onClick={onClose} aria-label="Закрыть">
            <Icon name="x" size={18} />
          </button>
        </div>
        {children}
        {footer && <div className="p-modal-foot">{footer}</div>}
      </div>
    </div>
  )
}

export const formatWhen = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return 'только что'
  if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}
