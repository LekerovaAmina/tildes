import { useNavigate, useParams } from 'react-router-dom'
import Icon from '../components/Icon.jsx'

export default function Soon() {
  const { level } = useParams()
  const navigate = useNavigate()
  return (
    <div className="soon-page">
      <div className="soon-box">
        <div className="soon-emoji">🛠️</div>
        <span className="chip chip-level">{level}</span>
        <h1>В разработке</h1>
        <p className="muted">
          Уровень {level} скоро появится. Әзірге B2 деңгейін таңдай аласыз.
        </p>
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/#levels')}>
          <Icon name="back" size={18} /> Назад
        </button>
      </div>
    </div>
  )
}
