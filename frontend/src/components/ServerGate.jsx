import { useContent } from '../store/content.jsx'
import { useProgress } from '../store/progress.jsx'
import Icon from './Icon.jsx'

// Пока контент и прогресс грузятся с бэкенда — экран загрузки,
// если бэкенд недоступен — подсказка, как его запустить.
export default function ServerGate({ children }) {
  const content = useContent()
  const progress = useProgress()

  if (content.status === 'error' || progress.status === 'error') {
    const retry = () => {
      content.reload()
      progress.reloadProgress()
    }
    return (
      <div className="soon-page">
        <div className="soon-box">
          <div className="soon-emoji">🔌</div>
          <h1>Нет связи с сервером</h1>
          <p className="muted">
            Запустите бэкенд: в папке <code>backend</code> выполните <code>run.bat</code> (или <code>sh run.sh</code>) и
            обновите страницу.
          </p>
          <button className="btn btn-primary btn-lg" onClick={retry}>
            <Icon name="repeat" size={18} /> Повторить
          </button>
        </div>
      </div>
    )
  }

  if (content.status !== 'ready' || progress.status !== 'ready') {
    return (
      <div className="soon-page">
        <div className="spinner" aria-label="Загрузка" />
      </div>
    )
  }

  return children
}
