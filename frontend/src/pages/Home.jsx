import { Link } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { useContent } from '../store/content.jsx'
import { rankOf, streakOf, useProgress } from '../store/progress.jsx'

// Блоки обучения. Новые режимы добавляются сюда — в массив future (или сразу в modes).
const modes = [
  {
    to: '/cards',
    icon: 'cards',
    title: 'Карточки',
    kz: 'Сөз карточкалары',
    text: 'Учите слова по темам и повторяйте пройденное',
    tone: 'violet',
  },
  {
    to: '/topics',
    icon: 'book',
    title: 'Темы',
    kz: 'Тақырыптар',
    text: 'Слова, грамматика, текст и вопросы по каждому модулю',
    tone: 'pink',
  },
]

const future = [
  { icon: 'headphones', title: 'Аудирование', kz: 'Тыңдалым' },
  { icon: 'chat', title: 'Диалоги', kz: 'Сөйлесу' },
  { icon: 'pen', title: 'Письмо', kz: 'Жазылым' },
]

export default function Home() {
  const { allWords, modules } = useContent()
  const { points, wordStats, completedCardTopics, quizBest, activeDays } = useProgress()
  const rank = rankOf(points)
  const learned = allWords.filter((w) => wordStats[w.id]?.learned).length
  const streak = streakOf(activeDays)
  const quizzes = Object.keys(quizBest).length

  return (
    <div className="page">
      <section className="welcome card">
        <div>
          <p className="muted small">Сәлеметсіз бе! 👋</p>
          <h1 className="h1">Бүгін не үйренеміз?</h1>
          <p className="muted">Уровень B2 · Ортадан жоғары деңгей</p>
        </div>
        <Link to="/rating" className="rank-mini">
          <span className="rank-mini-label">{rank.title}</span>
          <b>{points}</b>
          <span className="muted small">баллов</span>
          <div className="bar">
            <div className="bar-fill" style={{ width: `${rank.pct * 100}%` }} />
          </div>
        </Link>
      </section>

      <section className="stats-row">
        <div className="stat">
          <Icon name="fire" size={18} />
          <b>{streak}</b>
          <span>дней подряд</span>
        </div>
        <div className="stat">
          <Icon name="check" size={18} />
          <b>
            {learned}/{allWords.length}
          </b>
          <span>слов выучено</span>
        </div>
        <div className="stat">
          <Icon name="cards" size={18} />
          <b>
            {completedCardTopics.length}/{modules.length}
          </b>
          <span>тем в карточках</span>
        </div>
        <div className="stat">
          <Icon name="book" size={18} />
          <b>
            {quizzes}/{modules.length}
          </b>
          <span>тестов пройдено</span>
        </div>
      </section>

      <h2 className="h2">Способы обучения</h2>
      <section className="modes">
        {modes.map((m) => (
          <Link key={m.to} to={m.to} className={`mode card tone-${m.tone}`}>
            <div className="mode-icon">
              <Icon name={m.icon} size={26} />
            </div>
            <div className="mode-body">
              <h3>{m.title}</h3>
              <span className="mode-kz">{m.kz}</span>
              <p>{m.text}</p>
            </div>
            <Icon name="arrow" size={20} className="mode-arrow" />
          </Link>
        ))}

        {future.map((f) => (
          <div key={f.title} className="mode card mode-locked" aria-disabled="true">
            <div className="mode-icon">
              <Icon name={f.icon} size={24} />
            </div>
            <div className="mode-body">
              <h3>{f.title}</h3>
              <span className="mode-kz">{f.kz}</span>
              <p>Скоро появится</p>
            </div>
            <Icon name="lock" size={18} className="mode-arrow" />
          </div>
        ))}
      </section>
    </div>
  )
}
