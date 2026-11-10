import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { errorText, panelApi } from '../../api/client.js'
import Icon from '../../components/Icon.jsx'
import { Loading, PageHead, useCrumbs, useFlash, useLoad } from '../ui.jsx'
import { lessonCrumbs } from './crumbs.js'

// 6 · Текст и тест
const newQuestion = () => ({ prompt: '', options: ['', '', '', ''], correct: null })

export default function TextQuizEditor() {
  const { id } = useParams()
  const { data, error, reload } = useLoad(() => panelApi.textQuiz(id), [id])
  const [text, setText] = useState(null)
  const [questions, setQuestions] = useState([])
  const [open, setOpen] = useState([0, 1]) // раскрытые вопросы, как в макете — первые два
  const [busy, setBusy] = useState(false)
  const [flash, showFlash] = useFlash()
  useCrumbs(lessonCrumbs(data?.lesson, id, 'Текст и тест'))

  useEffect(() => {
    if (!data) return
    setText({ title: data.text.title, paragraphs: data.text.paragraphs.length ? data.text.paragraphs : [''] })
    setQuestions(data.questions.length ? data.questions.map((q) => ({ ...q })) : [newQuestion()])
  }, [data])

  if (!data || !text) return <Loading error={error} onRetry={reload} />

  const setPara = (i) => (e) => setText((t) => ({ ...t, paragraphs: t.paragraphs.map((p, j) => (j === i ? e.target.value : p)) }))
  const delPara = (i) => setText((t) => ({ ...t, paragraphs: t.paragraphs.filter((_, j) => j !== i) }))
  const setQ = (i, upd) => setQuestions((qs) => qs.map((q, j) => (j === i ? { ...q, ...upd } : q)))
  const setOpt = (i, k) => (e) => setQ(i, { options: questions[i].options.map((o, j) => (j === k ? e.target.value : o)) })
  const toggle = (i) => setOpen((o) => (o.includes(i) ? o.filter((x) => x !== i) : [...o, i]))
  const delQ = (i) => {
    setQuestions((qs) => qs.filter((_, j) => j !== i))
    setOpen((o) => o.filter((x) => x !== i).map((x) => (x > i ? x - 1 : x)))
  }

  const hasText = text.title.trim() || text.paragraphs.some((p) => p.trim())
  const filled = questions.filter((q) => q.prompt.trim() || q.options.some((o) => o.trim()))

  const save = async () => {
    setBusy(true)
    try {
      const payload = { questions: filled }
      if (hasText) payload.text = text
      await panelApi.saveTextQuiz(id, payload)
      showFlash('Сохранено')
      reload()
    } catch (e) {
      showFlash(errorText(e), 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHead title="Текст и тест" sub="Текст для чтения и вопросы на понимание к нему">
        {flash}
        <a href={`/topics/${data.lesson.module_id}`} target="_blank" rel="noreferrer" className="p-btn">
          <Icon name="eye" size={18} /> Предпросмотр
        </a>
        <button className="p-btn p-btn-primary" onClick={save} disabled={busy}>
          Сохранить
        </button>
      </PageHead>

      <div className="p-grid-half">
        <section className="p-card">
          <h2>Мәтін · Текст</h2>
          <label className="p-field">
            <span>Заголовок текста</span>
            <input value={text.title} onChange={(e) => setText((t) => ({ ...t, title: e.target.value }))} />
          </label>
          {text.paragraphs.map((p, i) => (
            <label key={i} className="p-field">
              <span className="p-field-row">
                Абзац {i + 1}
                {text.paragraphs.length > 1 && (
                  <button type="button" className="p-link p-small p-danger" onClick={() => delPara(i)}>
                    удалить
                  </button>
                )}
              </span>
              <textarea rows={4} value={p} onChange={setPara(i)} />
            </label>
          ))}
          <button className="p-btn p-btn-sm p-btn-add" onClick={() => setText((t) => ({ ...t, paragraphs: [...t.paragraphs, ''] }))}>
            <Icon name="plus" size={16} /> Абзац
          </button>
          <div className="p-dropzone disabled wide">
            <Icon name="headphones" size={18} /> Озвучка текста · скоро
          </div>
        </section>

        <section className="p-card">
          <div className="p-card-head">
            <div>
              <h2>Сұрақтар · Тест</h2>
              <p className="p-muted">Зелёным отмечен правильный ответ</p>
            </div>
            <label className="p-field p-field-inline">
              <span>Тип вопроса</span>
              <select disabled value="single">
                <option value="single">Один ответ из {questions[0]?.options.length || 4}</option>
              </select>
            </label>
          </div>

          <div className="p-questions">
            {questions.map((q, i) =>
              open.includes(i) ? (
                <div key={i} className="p-question">
                  <div className="p-field-row">
                    <button type="button" className="p-q-label" onClick={() => toggle(i)}>
                      Вопрос {i + 1}
                    </button>
                    <button type="button" className="p-link p-small p-danger" onClick={() => delQ(i)}>
                      удалить
                    </button>
                  </div>
                  <input className="p-q-prompt" value={q.prompt} onChange={(e) => setQ(i, { prompt: e.target.value })} placeholder="Текст вопроса" />
                  {q.options.map((o, k) => (
                    <label key={k} className={`p-option ${q.correct === k ? 'right' : ''}`}>
                      <input type="radio" name={`q${i}`} checked={q.correct === k} onChange={() => setQ(i, { correct: k })} />
                      <input value={o} onChange={setOpt(i, k)} placeholder={`Вариант ${k + 1}`} />
                      {q.correct === k && <span className="p-option-tag">верный</span>}
                    </label>
                  ))}
                </div>
              ) : (
                <button key={i} type="button" className="p-question-row" onClick={() => toggle(i)}>
                  <b>Вопрос {i + 1}</b>
                  <span>{q.prompt || 'без текста'}</span>
                  {q.correct === null && <span className="p-badge p-badge-amber">нет ответа</span>}
                  <Icon name="right" size={18} />
                </button>
              )
            )}
          </div>
          <button
            className="p-btn p-btn-sm p-btn-add"
            onClick={() => {
              setQuestions((qs) => [...qs, newQuestion()])
              setOpen((o) => [...o, questions.length])
            }}
          >
            <Icon name="plus" size={16} /> Вопрос
          </button>
          <p className="p-muted p-small">Баллы: +5 за каждый правильный ответ сверх лучшего результата ученика.</p>
        </section>
      </div>
    </>
  )
}
