import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Logo } from '../components/Layout.jsx'
import Icon from '../components/Icon.jsx'
import { useContent } from '../store/content.jsx'
import AuthButtons from '../components/AuthButtons.jsx'
import { useProgress } from '../store/progress.jsx'

const features = [
  { icon: 'cards', title: 'Карточки слов', text: 'Учите лексику по темам. Трудные слова возвращаются чаще, пока не запомнятся.' },
  { icon: 'book', title: 'Темы из учебника', text: 'Новые слова, грамматика, текст и вопросы с вариантами ответа — по модулям книги.' },
  { icon: 'trophy', title: 'Рейтинг', text: 'Баллы за каждое выученное слово, тему и тест. Следите за прогрессом и серией дней.' },
]

const steps = [
  ['Выберите уровень', 'Пока открыт B2 — «Ортадан жоғары деңгей».'],
  ['Учите слова', 'Карточки «Я выучил» / «Учить ещё раз».'],
  ['Проходите темы', 'Читайте тексты и отвечайте на вопросы.'],
  ['Повторяйте', 'Режим повторения собирает всё пройденное.'],
]

export default function Landing() {
  const navigate = useNavigate()
  const { levels, allWords, modules } = useContent()
  const { level, setLevel } = useProgress()
  const [picked, setPicked] = useState(level)
  const levelsRef = useRef(null)
  const { hash } = useLocation()

  // Возврат со страницы «В разработке» — сразу к выбору уровня
  useEffect(() => {
    if (hash === '#levels') setTimeout(() => levelsRef.current?.scrollIntoView(), 50)
  }, [hash])

  const scrollToLevels = () => levelsRef.current?.scrollIntoView({ behavior: 'smooth' })

  const next = () => {
    const l = levels.find((x) => x.id === picked)
    if (!l) return
    if (!l.available) return navigate(`/soon/${l.id}`)
    setLevel(l.id)
    navigate('/home')
  }

  return (
    <div className="landing">
      <header className="landing-header container">
        <Logo />
        <div className="landing-actions">
          <button className="btn btn-ghost btn-sm" onClick={scrollToLevels}>
            Начать
          </button>
          <AuthButtons />
        </div>
      </header>

      <section className="hero container">
        <div className="hero-text">
          <span className="eyebrow">
            <Icon name="sparkle" size={14} /> Қазақ тілі онлайн
          </span>
          <h1>
            Қазақ тілін <span className="accent">қуанышпен</span> үйреніңіз
          </h1>
          <p className="lead">
            Tildes — тренажёр казахского языка по учебнику «Қазақ тілі». Короткие занятия с карточками, темы с
            грамматикой и текстами, рейтинг и повторение — с телефона или ноутбука.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary btn-lg" onClick={scrollToLevels}>
              Выбрать уровень <Icon name="arrow" size={18} />
            </button>
          </div>
          <div className="hero-stats">
            <div>
              <b>{modules.length}</b>
              <span>модулей</span>
            </div>
            <div>
              <b>{allWords.length}</b>
              <span>слов</span>
            </div>
            <div>
              <b>{modules.reduce((n, m) => n + m.questions.length, 0)}</b>
              <span>вопросов</span>
            </div>
          </div>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <div className="demo-card demo-back" />
          <div className="demo-card">
            <span className="demo-tag">Көңіл-күйіңіз қалай?</span>
            <div className="demo-word">көңіл-күй</div>
            <div className="demo-tr">настроение</div>
            <div className="demo-btns">
              <span className="demo-btn ok">Я выучил</span>
              <span className="demo-btn again">Учить ещё раз</span>
            </div>
          </div>
        </div>
      </section>

      <section className="container section">
        <h2 className="section-title">Что внутри</h2>
        <div className="grid-3">
          {features.map((f) => (
            <div key={f.title} className="card feature">
              <div className="feature-icon">
                <Icon name={f.icon} size={22} />
              </div>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container section">
        <h2 className="section-title">Как это работает</h2>
        <ol className="steps">
          {steps.map(([t, d], i) => (
            <li key={t} className="step">
              <span className="step-num">{i + 1}</span>
              <div>
                <b>{t}</b>
                <p>{d}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="container section levels-section" ref={levelsRef} id="levels">
        <h2 className="section-title">Выберите свой уровень</h2>
        <p className="muted center">Деңгейіңізді таңдаңыз</p>
        <div className="levels">
          {levels.map((l) => (
            <button
              key={l.id}
              className={`level ${picked === l.id ? 'selected' : ''}`}
              onClick={() => setPicked(l.id)}
              aria-pressed={picked === l.id}
            >
              <span className="level-badge">{l.name}</span>
              <span className="level-body">
                <b>{l.ru}</b>
                <span className="level-kz">{l.title}</span>
                <small>{l.desc}</small>
              </span>
              {!l.available && <span className="soon-tag">скоро</span>}
              <span className="level-radio" />
            </button>
          ))}
        </div>
        <button className="btn btn-primary btn-lg btn-block next-btn" disabled={!picked} onClick={next}>
          Далее <Icon name="arrow" size={18} />
        </button>
      </section>

      <footer className="footer container">
        <span>© 2026 Tildes · MVP</span>
        <span className="muted">Материалы: «Қазақ тілі. B2», Астана, 2022</span>
      </footer>
    </div>
  )
}
