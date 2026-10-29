import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import Icon from '../components/Icon.jsx'
import { useContent } from '../store/content.jsx'
import { POINTS, RANKS, rankOf, streakOf, useProgress } from '../store/progress.jsx'

export default function Rating() {
  const { allWords } = useContent()
  const { points, name, wordStats, activeDays, reset, setName } = useProgress()
  const rank = rankOf(points)
  const learned = allWords.filter((w) => wordStats[w.id]?.learned).length

  const [board, setBoard] = useState(null)
  const [boardError, setBoardError] = useState(false)
  const [draft, setDraft] = useState(name)
  const [saving, setSaving] = useState(false)

  const loadBoard = () =>
    api
      .leaderboard()
      .then((b) => {
        setBoard(b)
        setBoardError(false)
      })
      .catch(() => setBoardError(true))

  // Перезагружаем таблицу, когда меняются свои баллы или имя
  useEffect(() => {
    loadBoard()
  }, [points, name])

  useEffect(() => setDraft(name), [name])

  const me = board?.find((u) => u.me)

  const saveName = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await setName(draft.trim())
    } finally {
      setSaving(false)
    }
  }

  const onReset = () => {
    if (window.confirm('Сбросить весь прогресс и баллы?')) reset()
  }

  return (
    <div className="page">
      <div className="page-head">
        <Link to="/home" className="back-link">
          <Icon name="back" size={18} /> Главная
        </Link>
        <h1 className="h1">Рейтинг</h1>
      </div>

      <div className="rating-hero card">
        <div className="rating-place">
          <span className="small">Ваше место</span>
          <b>{me ? `#${me.place}` : '—'}</b>
        </div>
        <div className="rating-main">
          <span className="rank-title">
            {rank.title} <span className="muted">· {rank.ru}</span>
          </span>
          <b className="rating-points">{points} баллов</b>
          <div className="bar bar-light">
            <div className="bar-fill" style={{ width: `${rank.pct * 100}%` }} />
          </div>
          <span className="small">
            {rank.next ? `До уровня «${rank.next.title}» — ${rank.toNext} баллов` : 'Максимальный уровень!'}
          </span>
        </div>
      </div>

      <form className="card name-form" onSubmit={saveName}>
        <label htmlFor="name">Имя в таблице лидеров</label>
        <div className="name-row">
          <input
            id="name"
            value={draft}
            maxLength={60}
            placeholder="Например, Айгерим"
            onChange={(e) => setDraft(e.target.value)}
          />
          <button className="btn btn-primary" disabled={saving || draft.trim() === name}>
            {saving ? '…' : 'Сохранить'}
          </button>
        </div>
      </form>

      <div className="stats-row">
        <div className="stat">
          <Icon name="fire" size={18} />
          <b>{streakOf(activeDays)}</b>
          <span>дней подряд</span>
        </div>
        <div className="stat">
          <Icon name="check" size={18} />
          <b>{learned}</b>
          <span>слов выучено</span>
        </div>
      </div>

      <h2 className="h2">Таблица лидеров</h2>
      <div className="card leaderboard">
        {boardError && <p className="muted lb-empty">Не удалось загрузить таблицу</p>}
        {!board && !boardError && <p className="muted lb-empty">Загружаем…</p>}
        {board?.map((u) => (
          <div key={u.place} className={`lb-row ${u.me ? 'me' : ''}`}>
            <span className={`lb-place p${u.place}`}>{u.place}</span>
            <span className="lb-avatar">{u.name[0]}</span>
            <span className="lb-name">
              {u.name}
              {u.me && <span className="muted"> · вы</span>}
            </span>
            <span className="lb-points">{u.points}</span>
          </div>
        ))}
      </div>

      <h2 className="h2">Как начисляются баллы</h2>
      <div className="card rules">
        <div><span>«Я выучил»</span><b>+{POINTS.learned}</b></div>
        <div><span>«Учить ещё раз»</span><b>+{POINTS.again}</b></div>
        <div><span>Тема карточек пройдена впервые</span><b>+{POINTS.topicFirst}</b></div>
        <div><span>Повторное прохождение / повторение</span><b>+{POINTS.topicRepeat}</b></div>
        <div><span>Правильный ответ в тесте (сверх лучшего)</span><b>+{POINTS.quizCorrect}</b></div>
      </div>

      <h2 className="h2">Уровни</h2>
      <div className="ranks">
        {RANKS.map((r, i) => (
          <div key={r.title} className={`rank-pill ${i <= rank.index ? 'reached' : ''}`}>
            <b>{r.title}</b>
            <span className="small">{r.min}+</span>
          </div>
        ))}
      </div>

      <button className="btn btn-link" onClick={onReset}>
        Сбросить прогресс
      </button>
    </div>
  )
}
