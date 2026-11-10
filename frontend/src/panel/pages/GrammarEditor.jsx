import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { errorText, panelApi } from '../../api/client.js'
import Icon from '../../components/Icon.jsx'
import { Loading, PageHead, move, useCrumbs, useDragSort, useFlash, useLoad } from '../ui.jsx'
import { lessonCrumbs } from './crumbs.js'

// 5 · Грамматика
export default function GrammarEditor() {
  const { id } = useParams()
  const { data, error, reload } = useLoad(() => panelApi.grammar(id), [id])
  const [g, setG] = useState(null)
  const [busy, setBusy] = useState(false)
  const [flash, showFlash] = useFlash()
  useCrumbs(lessonCrumbs(data?.lesson, id, 'Грамматика'))

  useEffect(() => {
    if (data) {
      const gr = data.grammar
      setG({
        ...gr,
        table: gr.table.length ? gr.table : [{ form: '', pattern: '', example: '' }],
        examples: gr.examples.length ? gr.examples : [{ kz: '', ru: '' }],
      })
    }
  }, [data])

  const rowDrag = useDragSort((from, to) => setG((s) => ({ ...s, table: move(s.table, from, to) })))

  if (!data || !g) return <Loading error={error} onRetry={reload} />

  const set = (k) => (e) => setG((s) => ({ ...s, [k]: e.target.value }))
  const setRow = (list, i, k) => (e) => setG((s) => ({ ...s, [list]: s[list].map((r, j) => (j === i ? { ...r, [k]: e.target.value } : r)) }))
  const addRow = (list, row) => setG((s) => ({ ...s, [list]: [...s[list], row] }))
  const delRow = (list, i) => setG((s) => ({ ...s, [list]: s[list].filter((_, j) => j !== i) }))

  const save = async () => {
    setBusy(true)
    try {
      await panelApi.saveGrammar(id, g)
      showFlash('Сохранено')
    } catch (e) {
      showFlash(errorText(e), 'error')
    } finally {
      setBusy(false)
    }
  }

  const memo = g.table.map((r) => r.example).filter(Boolean)

  return (
    <>
      <PageHead title="Грамматика" sub="Правило урока: объяснение, таблица форм и примеры с переводом">
        {flash}
        <a href={`/topics/${data.lesson.module_id}`} target="_blank" rel="noreferrer" className="p-btn">
          <Icon name="eye" size={18} /> Предпросмотр
        </a>
        <button className="p-btn p-btn-primary" onClick={save} disabled={busy || !g.title_kz.trim()}>
          Сохранить
        </button>
      </PageHead>

      <div className="p-grid-editor">
        <div className="p-stack">
          <section className="p-card">
            <h2>Правило</h2>
            <div className="p-form-2">
              <label className="p-field">
                <span>Название (қазақша)</span>
                <input value={g.title_kz} onChange={set('title_kz')} placeholder="Қимылды жүзеге асыру мүмкіндігі" />
              </label>
              <label className="p-field">
                <span>Подзаголовок (по-русски)</span>
                <input value={g.title_ru} onChange={set('title_ru')} placeholder="Возможность совершить действие" />
              </label>
            </div>
            <label className="p-field">
              <span>Объяснение</span>
              <textarea rows={4} value={g.explanation} onChange={set('explanation')} />
            </label>
            <p className="p-muted p-small">Ученик увидит текст как есть — абзацы переносятся с новой строки</p>
          </section>

          <section className="p-card">
            <h2>Таблица форм</h2>
            <p className="p-muted">Рубрика «Есте сақтаңыз»</p>
            <div className="p-rows">
              <div className="p-rows-head">
                <span />
                <span>Форма</span>
                <span>Схема</span>
                <span>Пример</span>
                <span />
              </div>
              {g.table.map((r, i) => (
                <div key={i} className="p-row-edit" {...rowDrag(i)}>
                  <span className="p-grip">
                    <Icon name="grip" size={16} />
                  </span>
                  <input value={r.form} onChange={setRow('table', i, 'form')} aria-label="Форма" />
                  <input value={r.pattern} onChange={setRow('table', i, 'pattern')} aria-label="Схема" />
                  <input value={r.example} onChange={setRow('table', i, 'example')} aria-label="Пример" />
                  <button className="p-icon-btn" onClick={() => delRow('table', i)} aria-label="Удалить строку">
                    <Icon name="trash" size={16} />
                  </button>
                </div>
              ))}
            </div>
            <button className="p-btn p-btn-sm p-btn-add" onClick={() => addRow('table', { form: '', pattern: '', example: '' })}>
              <Icon name="plus" size={16} /> Строка
            </button>
          </section>

          <section className="p-card">
            <h2>Примеры</h2>
            <div className="p-rows">
              {g.examples.map((e, i) => (
                <div key={i} className="p-row-edit p-row-2">
                  <input value={e.kz} onChange={setRow('examples', i, 'kz')} placeholder="Қазақша" aria-label="Пример на казахском" />
                  <input value={e.ru} onChange={setRow('examples', i, 'ru')} placeholder="Перевод" aria-label="Перевод примера" />
                  <button className="p-icon-btn" onClick={() => delRow('examples', i)} aria-label="Удалить пример">
                    <Icon name="trash" size={16} />
                  </button>
                </div>
              ))}
            </div>
            <button className="p-btn p-btn-sm p-btn-add" onClick={() => addRow('examples', { kz: '', ru: '' })}>
              <Icon name="plus" size={16} /> Пример
            </button>
          </section>
        </div>

        <aside className="p-card p-preview">
          <span className="p-label">Предпросмотр</span>
          <h3>{g.title_kz || 'Название правила'}</h3>
          {g.title_ru && <p className="p-preview-sub">{g.title_ru}</p>}
          {g.explanation && <p className="p-preview-text">{g.explanation}</p>}
          {memo.length > 0 && (
            <div className="p-memo">
              <b>Есте сақтаңыз</b>
              {memo.map((m, i) => (
                <span key={i}>{m}</span>
              ))}
            </div>
          )}
        </aside>
      </div>
    </>
  )
}
