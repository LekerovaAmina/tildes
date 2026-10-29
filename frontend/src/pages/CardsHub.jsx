import { Link } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { useContent } from '../store/content.jsx'
import { isHard } from '../store/srs.js'
import { useProgress } from '../store/progress.jsx'

export default function CardsHub() {
  const { modules } = useContent()
  const { wordStats, completedCardTopics } = useProgress()
  const reviewWords = modules.filter((m) => completedCardTopics.includes(m.id)).flatMap((m) => m.words)
  const hardCount = reviewWords.filter((w) => isHard(wordStats[w.id])).length
  const canReview = reviewWords.length > 0

  return (
    <div className="page">
      <div className="page-head">
        <Link to="/home" className="back-link">
          <Icon name="back" size={18} /> Главная
        </Link>
        <h1 className="h1">Карточки</h1>
        <p className="muted">Выберите тему или повторите всё пройденное</p>
      </div>

      <div className={`review-banner card ${canReview ? '' : 'disabled'}`}>
        <div className="review-icon">
          <Icon name="repeat" size={26} />
        </div>
        <div className="review-body">
          <h3>Повторение</h3>
          {canReview ? (
            <p>
              {reviewWords.length} слов из {completedCardTopics.length} пройденных тем
              {hardCount > 0 && <> · <b>{hardCount} трудных</b></>}
            </p>
          ) : (
            <p>Пройдите хотя бы одну тему — и здесь появятся слова для повторения</p>
          )}
        </div>
        {canReview ? (
          <Link to="/cards/review" className="btn btn-white">
            Начать
          </Link>
        ) : (
          <Icon name="lock" size={20} />
        )}
      </div>

      <h2 className="h2">Темы</h2>
      <div className="topic-grid">
        {modules.map((m) => {
          const learned = m.words.filter((w) => wordStats[w.id]?.learned).length
          const done = completedCardTopics.includes(m.id)
          return (
            <Link key={m.id} to={`/cards/${m.id}`} className="topic-tile card">
              <div className="topic-emoji" style={{ background: `${m.color}33` }}>
                {m.emoji}
              </div>
              <div className="topic-info">
                <span className="topic-num">Модуль {m.number}</span>
                <h3>{m.title}</h3>
                <span className="muted small">{m.titleRu}</span>
                <div className="bar">
                  <div className="bar-fill" style={{ width: `${(learned / m.words.length) * 100}%` }} />
                </div>
                <span className="small muted">
                  {learned}/{m.words.length} слов
                </span>
              </div>
              {done && (
                <span className="done-badge" title="Тема пройдена">
                  <Icon name="check" size={14} />
                </span>
              )}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
