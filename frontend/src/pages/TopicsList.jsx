import { Link } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { useContent } from '../store/content.jsx'
import { useProgress } from '../store/progress.jsx'

export default function TopicsList() {
  const { modules } = useContent()
  const { quizBest, readTopics } = useProgress()
  return (
    <div className="page">
      <div className="page-head">
        <Link to="/home" className="back-link">
          <Icon name="back" size={18} /> Главная
        </Link>
        <h1 className="h1">Темы</h1>
        <p className="muted">{modules.length} модулей учебника «Қазақ тілі» · B2</p>
      </div>

      <div className="topics-list">
        {modules.map((m) => {
          const best = quizBest[m.id]
          const read = readTopics[m.id] || {}
          const steps = ['words', 'grammar', 'text'].filter((k) => read[k]).length + (best != null ? 1 : 0)
          return (
            <Link key={m.id} to={`/topics/${m.id}`} className="topic-row card">
              <div className="topic-emoji lg" style={{ background: `${m.color}33` }}>
                {m.emoji}
              </div>
              <div className="topic-info">
                <span className="topic-num">Модуль {m.number}</span>
                <h3>{m.title}</h3>
                <span className="muted small">{m.titleRu}</span>
                <div className="lesson-pills">
                  {m.lessons.map((l) => (
                    <span key={l} className="lesson-pill">
                      {l}
                    </span>
                  ))}
                </div>
              </div>
              <div className="topic-progress">
                <span className="ring" style={{ '--p': steps / 4 }}>
                  {steps}/4
                </span>
                {best != null && (
                  <span className="small muted">
                    тест {best}/{m.questions.length}
                  </span>
                )}
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
