import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { errorText, panelApi } from '../../api/client.js'
import Icon from '../../components/Icon.jsx'
import { Badge, Loading, Modal, PageHead, STATUS, useCrumbs, useFlash, useLoad } from '../ui.jsx'
import { lessonCrumbs } from './crumbs.js'

// 4 · Карточки слов
const PARTS = ['зат есім', 'етістік', 'сын есім', 'үстеу', 'есімдік', 'сан есім', 'шылау', 'сөз тіркесі']
const EMPTY = { kz: '', ru: '', part_of_speech: '', transcription: '', example_kz: '', example_ru: '', status: 'published', image: null }
const PAGE = 10

export default function CardsEditor() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const { data, setData, error, reload } = useLoad(() => panelApi.words(id), [id])
  const [statusFilter, setStatusFilter] = useState('all')
  const [selected, setSelected] = useState([])
  const [editing, setEditing] = useState(null) // id слова или 'new'
  const [showAll, setShowAll] = useState(false)
  const [importing, setImporting] = useState(false)
  const [flash, showFlash] = useFlash()

  const lesson = data?.lesson
  useCrumbs(lessonCrumbs(lesson, id, 'Карточки'))

  // ?word=… из поиска — сразу открыть это слово
  useEffect(() => {
    if (data && editing === null) {
      const wanted = Number(params.get('word'))
      const found = data.words.find((w) => w.id === wanted)
      setEditing(found ? found.id : data.words[0]?.id ?? 'new')
      if (found && data.words.indexOf(found) >= PAGE) setShowAll(true)
    }
  }, [data, editing, params])

  const words = useMemo(
    () => (data?.words || []).filter((w) => statusFilter === 'all' || (statusFilter === 'published' ? w.status === 'published' : w.status !== 'published')),
    [data, statusFilter]
  )
  if (!data) return <Loading error={error} onRetry={reload} />

  const visible = showAll ? words : words.slice(0, PAGE)
  const current = editing === 'new' ? null : data.words.find((w) => w.id === editing)
  const allChecked = visible.length > 0 && visible.every((w) => selected.includes(w.id))
  const toggle = (wid) => setSelected((s) => (s.includes(wid) ? s.filter((x) => x !== wid) : [...s, wid]))

  const bulk = async (action) => {
    if (action === 'delete' && !window.confirm(`Удалить ${selected.length} карточек? Прогресс учеников по ним тоже удалится.`)) return
    try {
      await panelApi.wordsBulk(id, selected, action)
      setSelected([])
      showFlash(action === 'publish' ? 'Опубликовано' : 'Удалено')
      if (action === 'delete' && selected.includes(editing)) setEditing(null)
      reload()
    } catch (e) {
      showFlash(errorText(e), 'error')
    }
  }

  const onSaved = (word, isNew) => {
    setData((d) => ({ ...d, words: isNew ? [...d.words, word] : d.words.map((w) => (w.id === word.id ? word : w)) }))
    setEditing(word.id)
    showFlash('Карточка сохранена')
  }

  const index = current ? data.words.indexOf(current) + 1 : data.words.length + 1

  return (
    <>
      <PageHead title="Карточки слов" sub="Слова для режима «Карточки» и повторения. Каждое слово привязано к уроку">
        {flash}
        <button className="p-btn" onClick={() => setImporting(true)}>
          <Icon name="upload" size={18} /> Импорт CSV
        </button>
        <button className="p-btn p-btn-primary" onClick={() => setEditing('new')}>
          <Icon name="plus" size={18} /> Карточка
        </button>
      </PageHead>

      <div className="p-chips">
        <span className="p-chip">
          Уровень: <b>{lesson.level_code}</b>
        </span>
        <span className="p-chip">
          Модуль: <b>{lesson.module_number}</b>
        </span>
        <Link to={`/panel/lessons/${id}`} className="p-chip">
          Урок: <b>{lesson.letter}</b> · {lesson.title_kz}
        </Link>
        <label className="p-chip">
          Статус:
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">все</option>
            <option value="published">опубликованные</option>
            <option value="draft">не опубликованные</option>
          </select>
        </label>
      </div>

      <div className="p-grid-cards">
        <section className="p-card">
          <div className="p-card-head">
            <div>
              <h2>{words.length} слов</h2>
              <p className="p-muted">{showAll || words.length <= PAGE ? 'Показаны все' : `Показаны первые ${PAGE}`}</p>
            </div>
            <div className="p-head-actions">
              <button className="p-btn p-btn-soft" disabled={!selected.length} onClick={() => bulk('publish')}>
                Опубликовать выбранные
              </button>
              <button className="p-btn" disabled={!selected.length} onClick={() => bulk('delete')}>
                <Icon name="trash" size={16} /> Удалить
              </button>
            </div>
          </div>

          {words.length === 0 ? (
            <div className="p-empty">
              <p className="p-muted">Карточек пока нет — добавьте первую или импортируйте CSV</p>
            </div>
          ) : (
            <div className="p-table-wrap">
              <table className="p-table p-words">
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        checked={allChecked}
                        onChange={() => setSelected(allChecked ? [] : visible.map((w) => w.id))}
                        aria-label="Выбрать все"
                      />
                    </th>
                    <th>#</th>
                    <th>Қазақша</th>
                    <th>Перевод</th>
                    <th>Часть речи</th>
                    <th>Аудио</th>
                    <th>Статус</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((w) => (
                    <tr key={w.id} className={w.id === editing ? 'active' : ''}>
                      <td>
                        <input type="checkbox" checked={selected.includes(w.id)} onChange={() => toggle(w.id)} aria-label={`Выбрать ${w.kz}`} />
                      </td>
                      <td className="p-muted">{data.words.indexOf(w) + 1}</td>
                      <td>
                        <b>{w.kz}</b>
                      </td>
                      <td>{w.ru}</td>
                      <td className="p-muted">{w.part_of_speech || '—'}</td>
                      <td className="p-muted">{w.has_audio ? 'есть' : '—'}</td>
                      <td>
                        <Badge status={w.status} />
                      </td>
                      <td>
                        <button className="p-icon-btn" onClick={() => setEditing(w.id)} aria-label={`Изменить ${w.kz}`}>
                          <Icon name="pen" size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {words.length > PAGE && (
            <button className="p-link p-small" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Свернуть' : `Показать все ${words.length}`}
            </button>
          )}
          <p className="p-muted p-small">CSV: kz;ru;part_of_speech;example_kz;example_ru — одна строка = одна карточка.</p>
        </section>

        <WordForm
          key={editing}
          lessonId={id}
          word={current}
          moduleNumber={lesson.module_number}
          position={index}
          total={Math.max(data.words.length, index)}
          onSaved={onSaved}
          onCancel={() => setEditing(data.words[0]?.id ?? 'new')}
        />
      </div>

      {importing && (
        <ImportModal
          onClose={() => setImporting(false)}
          onImport={async (csv) => {
            const r = await panelApi.importWords(id, csv)
            setImporting(false)
            showFlash(`Добавлено карточек: ${r.count}`)
            reload()
          }}
        />
      )}
    </>
  )
}

function WordForm({ lessonId, word, moduleNumber, position, total, onSaved, onCancel }) {
  const [form, setForm] = useState(word ? { ...EMPTY, ...word } : EMPTY)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const file = useRef(null)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const uploadImage = async (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    try {
      const media = await panelApi.uploadImage(f)
      setForm((s) => ({ ...s, image: media }))
    } catch (err) {
      setError(errorText(err))
    }
  }

  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    const payload = {
      kz: form.kz,
      ru: form.ru,
      part_of_speech: form.part_of_speech,
      transcription: form.transcription,
      example_kz: form.example_kz,
      example_ru: form.example_ru,
      status: form.status,
      image_id: form.image?.id || null,
    }
    try {
      const saved = word ? await panelApi.updateWord(word.id, payload) : await panelApi.createWord(lessonId, payload)
      onSaved(saved, !word)
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="p-card p-word-form" onSubmit={save}>
      <div className="p-card-head">
        <h2>{word ? 'Карточка' : 'Новая карточка'}</h2>
        <select className="p-status-select" value={form.status} onChange={set('status')} aria-label="Статус">
          {Object.entries(STATUS).map(([k, s]) => (
            <option key={k} value={k}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      <label className="p-field">
        <span>Слово (қазақша)</span>
        <input value={form.kz} onChange={set('kz')} required />
      </label>
      <label className="p-field">
        <span>Перевод (по-русски)</span>
        <input value={form.ru} onChange={set('ru')} required />
      </label>
      <div className="p-form-2">
        <label className="p-field">
          <span>Часть речи</span>
          <select value={form.part_of_speech} onChange={set('part_of_speech')}>
            <option value="">—</option>
            {[...new Set([...PARTS, form.part_of_speech].filter(Boolean))].map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </label>
        <label className="p-field">
          <span>Транскрипция</span>
          <input value={form.transcription} onChange={set('transcription')} placeholder="необязательно" />
        </label>
      </div>
      <label className="p-field">
        <span>Пример (қазақша)</span>
        <input value={form.example_kz} onChange={set('example_kz')} placeholder="Мысалы: Бүгін көңіл-күйім жақсы." />
      </label>
      <label className="p-field">
        <span>Перевод примера</span>
        <textarea rows={2} value={form.example_ru} onChange={set('example_ru')} placeholder="Например: Сегодня у меня хорошее настроение." />
      </label>
      <div className="p-form-2">
        <button type="button" className="p-dropzone" onClick={() => file.current?.click()}>
          {form.image ? <img src={form.image.url} alt="" /> : <Icon name="image" size={20} />}
          {form.image ? 'Заменить картинку' : 'Картинка'}
        </button>
        <input ref={file} type="file" accept="image/*" hidden onChange={uploadImage} />
        <div className="p-dropzone disabled">
          <Icon name="headphones" size={20} /> Аудио · скоро
        </div>
      </div>

      <span className="p-label">Как увидит ученик</span>
      <div className="p-card-preview">
        <small>
          Модуль {moduleNumber} · карточка {position} из {total}
        </small>
        <b>{form.kz || 'сөз'}</b>
        <span>{form.ru || 'перевод'}</span>
      </div>
      <div className="p-preview-btns">
        <span className="again">Учить ещё раз</span>
        <span className="ok">Я выучил</span>
      </div>

      {error && <p className="p-error">{error}</p>}
      <div className="p-form-actions">
        <button className="p-btn p-btn-primary" disabled={busy}>
          Сохранить
        </button>
        <button type="button" className="p-btn" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  )
}

function ImportModal({ onClose, onImport }) {
  const [csv, setCsv] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const readFile = (e) => {
    const f = e.target.files?.[0]
    if (f) f.text().then(setCsv)
  }
  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      await onImport(csv)
    } catch (e) {
      setError(errorText(e))
      setBusy(false)
    }
  }

  return (
    <Modal
      title="Импорт CSV"
      sub="Одна строка — одна карточка: kz;ru;part_of_speech;example_kz;example_ru"
      onClose={onClose}
      footer={
        <>
          <button className="p-btn" onClick={onClose}>
            Отмена
          </button>
          <button className="p-btn p-btn-primary" disabled={busy || !csv.trim()} onClick={submit}>
            Импортировать
          </button>
        </>
      }
    >
      <div className="p-form">
        <label className="p-field">
          <span>Файл .csv</span>
          <input type="file" accept=".csv,text/csv,text/plain" onChange={readFile} />
        </label>
        <label className="p-field">
          <span>или вставьте строки</span>
          <textarea rows={7} value={csv} onChange={(e) => setCsv(e.target.value)} placeholder={'көңіл-күй;настроение;зат есім\nсергек;бодрый;сын есім'} />
        </label>
        {error && <p className="p-error">{error}</p>}
      </div>
    </Modal>
  )
}
