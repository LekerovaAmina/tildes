import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { errorText, panelApi } from '../../api/client.js'
import Icon from '../../components/Icon.jsx'
import { BLOCKS, Badge, Loading, Modal, PageHead, STATUS, formatWhen, move, useCrumbs, useDragSort, useFlash, useLoad } from '../ui.jsx'

// 3 · Конструктор урока  +  3а · Модалка «Добавить блок»
export default function LessonBuilder() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: lesson, setData, error, reload } = useLoad(() => panelApi.lesson(id), [id])
  const level = useLoad(() => (lesson ? panelApi.modules(lesson.level.code) : Promise.resolve(null)), [lesson?.level.code])
  const [form, setForm] = useState(null)
  const [adding, setAdding] = useState(false)
  const [busy, setBusy] = useState(false)
  const [savedAt, setSavedAt] = useState(null)
  const [flash, showFlash] = useFlash()

  useCrumbs(
    lesson
      ? [
          { label: 'Уровни и модули', to: '/admin/levels' },
          { label: lesson.level.code, to: `/admin/levels/${lesson.level.code}` },
          { label: `Модуль ${lesson.module.number}`, to: `/admin/levels/${lesson.level.code}` },
          { label: `Урок ${lesson.letter}${lesson.status === 'published' ? '' : ' · ' + STATUS[lesson.status].label.toLowerCase()}` },
        ]
      : [{ label: 'Уровни и модули', to: '/admin/levels' }, { label: 'Урок' }]
  )

  // Форма настроек заполняется из урока (и после каждого сохранения)
  useEffect(() => {
    if (lesson)
      setForm({
        title_kz: lesson.title_kz,
        title_ru: lesson.title_ru,
        module_id: lesson.module.id,
        position: lesson.position,
        status: lesson.status,
      })
  }, [lesson])

  const dragProps = useDragSort((from, to) => {
    const types = move(lesson.blocks.map((b) => b.type), from, to)
    setData((l) => ({ ...l, blocks: move(l.blocks, from, to) }))
    panelApi.reorderBlocks(id, types).then(setData).catch(reload)
  })

  if (!lesson || !form) return <Loading error={error} onRetry={reload} />

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const dirty =
    form.title_kz !== lesson.title_kz ||
    form.title_ru !== lesson.title_ru ||
    Number(form.module_id) !== lesson.module.id ||
    Number(form.position) !== lesson.position ||
    form.status !== lesson.status

  const run = async (fn, okText) => {
    setBusy(true)
    try {
      const res = await fn()
      if (res) setData(res)
      setSavedAt(new Date().toISOString())
      if (okText) showFlash(okText)
      return res
    } catch (e) {
      // Отказ в публикации: сервер присылает актуальную «Готовность» (ok — булевы true/false)
      const readiness = e.data?.readiness
      if (readiness && typeof readiness.ok === 'boolean') setData((l) => ({ ...l, readiness }))
      showFlash(errorText(e), 'error')
    } finally {
      setBusy(false)
    }
  }

  const save = () => {
    const patch = { title_kz: form.title_kz, title_ru: form.title_ru, position: Number(form.position) }
    if (Number(form.module_id) !== lesson.module.id) patch.module_id = Number(form.module_id)
    // «Опубликован» ставится только кнопкой «Опубликовать» — после проверки готовности
    if (form.status !== lesson.status && form.status !== 'published') patch.status = form.status
    return run(() => panelApi.updateLesson(id, patch), 'Сохранено')
  }

  const publish = async () => {
    if (dirty) await save()
    const res = await run(() => panelApi.publishLesson(id), 'Урок опубликован — ученики его видят')
    if (res) level.reload()
  }

  const removeLesson = async () => {
    if (!window.confirm(`Удалить урок «${lesson.title_kz}» вместе со всем содержимым?`)) return
    await panelApi.deleteLesson(id)
    navigate(`/admin/levels/${lesson.level.code}`)
  }

  const removeBlock = (type) => {
    const warn = type === 'cards' ? ' Прогресс учеников по этим словам тоже удалится.' : ''
    if (!window.confirm(`Удалить блок «${BLOCKS[type].title}» и всё его содержимое?${warn}`)) return
    run(() => panelApi.deleteBlock(id, type), 'Блок удалён')
  }

  const addBlock = async (type) => {
    setAdding(false)
    await run(() => panelApi.addBlock(id, type), 'Блок добавлен')
    navigate(editorPath(id, type))
  }

  const isDraft = lesson.status !== 'published'
  const missing = ['cards', 'grammar', 'text', 'quiz'].filter((t) => !lesson.blocks.some((b) => b.type === t))
  const modules = level.data?.modules || []

  return (
    <>
      <PageHead title="Конструктор урока" sub={`Урок ${lesson.letter} · модуль ${lesson.module.number} «${lesson.module.title_kz}» · ${lesson.level.code}`}>
        {flash}
        <Badge status={lesson.status} />
        <a href={`/topics/${lesson.module.id}`} target="_blank" rel="noreferrer" className="p-btn">
          <Icon name="eye" size={18} /> Предпросмотр
        </a>
        <button className="p-btn p-btn-primary" onClick={save} disabled={busy || !dirty}>
          {isDraft ? 'Сохранить черновик' : 'Сохранить'}
        </button>
        <button
          className="p-btn"
          onClick={publish}
          disabled={busy || !lesson.readiness.ok || !isDraft}
          title={lesson.readiness.ok ? '' : 'Сначала выполните пункты «Готовность к публикации»'}
        >
          {isDraft ? 'Опубликовать' : 'Опубликован'}
        </button>
      </PageHead>

      {isDraft && (
        <div className="p-banner">
          <Icon name="eye" size={18} />
          <p>
            <b>{STATUS[lesson.status].label}.</b> Ученики не видят этот урок. Сохраняйте сколько угодно раз и публикуйте, когда все
            пункты справа будут выполнены.
          </p>
          <span>Последнее сохранение: {formatWhen(savedAt || lesson.updated_at)}</span>
        </div>
      )}

      <section className="p-card">
        <h2>Настройки урока</h2>
        <div className="p-form-4">
          <label className="p-field">
            <span>Название (қазақша)</span>
            <input value={form.title_kz} onChange={set('title_kz')} />
          </label>
          <label className="p-field">
            <span>Название (по-русски)</span>
            <input value={form.title_ru} onChange={set('title_ru')} placeholder="Например: Хочу подарить цветы" />
          </label>
          <label className="p-field">
            <span>Уровень</span>
            <select value={lesson.level.code} disabled>
              <option>
                {lesson.level.code} · {lesson.level.title_kz}
              </option>
            </select>
          </label>
          <label className="p-field">
            <span>Модуль</span>
            <select value={form.module_id} onChange={set('module_id')}>
              {(modules.length ? modules : [lesson.module]).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.number} · {m.title_kz}
                </option>
              ))}
            </select>
          </label>
          <label className="p-field">
            <span>Порядок в модуле</span>
            <select value={form.position} onChange={set('position')} disabled={Number(form.module_id) !== lesson.module.id}>
              {lesson.positions.map((p, i) => (
                <option key={i} value={i}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="p-field">
            <span>Статус</span>
            <select value={form.status} onChange={set('status')}>
              {Object.entries(STATUS).map(([k, s]) => (
                <option key={k} value={k} disabled={k === 'published' && lesson.status !== 'published'}>
                  {s.label}
                  {k === 'published' && lesson.status !== 'published' ? ' — кнопкой «Опубликовать»' : ''}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <div className="p-grid-2-1">
        <section className="p-card">
          <div className="p-card-head">
            <div>
              <h2>Блоки урока</h2>
              <p className="p-muted">Ученик проходит их сверху вниз. Порядок — перетаскиванием</p>
            </div>
            <button className="p-btn p-btn-primary" onClick={() => setAdding(true)} disabled={!missing.length}>
              <Icon name="plus" size={18} /> Добавить блок
            </button>
          </div>
          <div className="p-blocks">
            {lesson.blocks.map((b, i) => (
              <div key={b.type} className="p-block" {...dragProps(i)}>
                <span className="p-grip">
                  <Icon name="grip" size={16} />
                </span>
                <span className="p-block-num">{i + 1}</span>
                <span className="p-block-icon">
                  <Icon name={BLOCKS[b.type].icon} size={18} />
                </span>
                <span className="p-block-body">
                  <b>
                    {b.type === 'cards' ? 'Сөздер · Карточки слов' : b.type === 'quiz' ? 'Сұрақтар · Тест' : b.type === 'text' ? 'Мәтін · Текст' : 'Грамматика'}
                  </b>
                  <small className="p-muted">{b.summary}</small>
                </span>
                <Link to={editorPath(id, b.type)} className="p-btn p-btn-sm">
                  <Icon name="pen" size={14} /> Редактировать
                </Link>
                <button className="p-icon-btn" onClick={() => removeBlock(b.type)} aria-label="Удалить блок">
                  <Icon name="trash" size={16} />
                </button>
              </div>
            ))}
            {missing.length > 0 && (
              <button className="p-block-empty" onClick={() => setAdding(true)}>
                {missingText(missing)} — нажмите «Добавить блок»
              </button>
            )}
          </div>
        </section>

        <section className="p-card">
          <h2>Готовность к публикации</h2>
          <ul className="p-ready">
            {lesson.readiness.items.map((r) => (
              <li key={r.key} className={r.ok ? 'ok' : 'todo'}>
                <span className="p-ready-icon">
                  <Icon name={r.ok ? 'check' : 'alert'} size={14} />
                </span>
                {r.label}
              </li>
            ))}
          </ul>
          <p className="p-muted p-small">
            {lesson.readiness.ok
              ? 'Всё готово — урок можно публиковать.'
              : 'Пока пункты не выполнены, урок можно только сохранять как черновик.'}
          </p>
          <button className="p-link p-danger p-small" onClick={removeLesson}>
            Удалить урок
          </button>
        </section>
      </div>

      {adding && (
        <Modal
          title="Добавить блок"
          sub="Выберите, что будет в уроке. Каждый тип можно добавить один раз."
          onClose={() => setAdding(false)}
          footer={
            <button className="p-btn" onClick={() => setAdding(false)}>
              Отмена
            </button>
          }
        >
          <div className="p-block-choices">
            {[
              ['cards', 'Карточки слов', 'Сөздер: слово, перевод, пример'],
              ['grammar', 'Грамматика', 'Правило, таблица форм и примеры'],
              ['text', 'Текст для чтения', 'Мәтін: заголовок и абзацы'],
              ['quiz', 'Тест', 'Сұрақтар: вопросы с вариантами ответа'],
            ].map(([type, title, sub]) => {
              const has = lesson.blocks.some((b) => b.type === type)
              return (
                <button key={type} className="p-block-choice" disabled={has} onClick={() => addBlock(type)}>
                  <span className="p-block-icon">
                    <Icon name={BLOCKS[type].icon} size={18} />
                  </span>
                  <b>{title}</b>
                  <small>{has ? 'Уже есть в уроке' : sub}</small>
                </button>
              )
            })}
          </div>
        </Modal>
      )}
    </>
  )
}

const editorPath = (lessonId, type) => `/admin/lessons/${lessonId}/${BLOCKS[type].path}`

function missingText(missing) {
  const names = { cards: 'карточек', grammar: 'грамматики', text: 'текста', quiz: 'теста' }
  const list = missing.map((m) => names[m])
  const joined = list.length > 1 ? `${list.slice(0, -1).join(', ')} и ${list[list.length - 1]}` : list[0]
  return `${joined[0].toUpperCase()}${joined.slice(1)} пока нет`
}
