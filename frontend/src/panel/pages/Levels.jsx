import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { errorText, panelApi } from '../../api/client.js'
import Icon from '../../components/Icon.jsx'
import { BLOCKS, Badge, Loading, Modal, PageHead, STATUS, move, useCrumbs, useDragSort, useLoad } from '../ui.jsx'

// 2 · Уровни и модули
export default function Levels() {
  const { code: param } = useParams()
  const code = (param || 'B2').toUpperCase()
  const navigate = useNavigate()
  useCrumbs([{ label: 'Контент' }, { label: 'Уровни и модули', to: '/admin/levels' }, { label: code }])

  const levels = useLoad(() => panelApi.levels(), [])
  const page = useLoad(() => panelApi.modules(code), [code])
  const [open, setOpen] = useState(null) // id раскрытого модуля
  const [filter, setFilter] = useState('all')
  const [modal, setModal] = useState(null) // {type: 'level'|'newLevel'|'module'|'newModule', data}

  // Сменили уровень — раскрытый модуль выбираем заново
  useEffect(() => setOpen(null), [code])

  // По умолчанию раскрыт первый модуль, как в макете
  useEffect(() => {
    if (page.data && open === null) setOpen(page.data.modules[0]?.id ?? false)
  }, [page.data, open])

  const reloadAll = () => {
    levels.reload()
    page.reload()
  }

  const dragProps = useDragSort((from, to) => {
    const modules = move(page.data.modules, from, to)
    page.setData((d) => ({ ...d, modules }))
    panelApi.reorderModules(code, modules.map((m) => m.id)).catch(page.reload)
  })

  const newLesson = async (moduleId) => {
    const lesson = await panelApi.createLesson(moduleId, { title_kz: 'Жаңа сабақ' })
    navigate(`/admin/lessons/${lesson.id}`)
  }

  const togglePublished = async () => {
    const level = await panelApi.updateLevel(code, { is_published: !page.data.level.is_published })
    page.setData((d) => ({ ...d, level }))
    levels.reload()
  }

  const allLessons = page.data?.modules.flatMap((m) => m.lessons) || []
  const counts = {
    all: allLessons.length,
    published: allLessons.filter((l) => l.status === 'published').length,
    draft: allLessons.filter((l) => l.status !== 'published').length,
  }
  const showLesson = (l) => filter === 'all' || (filter === 'published' ? l.status === 'published' : l.status !== 'published')

  return (
    <>
      <PageHead title="Уровни и модули" sub="Уровень → модуль → урок. Порядок модулей меняется перетаскиванием">
        <button className="p-btn" disabled title="Скоро: пока контент загружается командой load_content">
          <Icon name="upload" size={18} /> Импорт из JSON
        </button>
      </PageHead>

      <div className="p-level-tabs">
        {(levels.data || []).map((lv) => (
          <Link key={lv.code} to={`/admin/levels/${lv.code}`} className={`p-level-tab ${lv.code === code ? 'active' : ''}`}>
            <b>{lv.code}</b> <span>{lv.code === code ? `${lv.module_count} модулей` : lv.module_count}</span>
          </Link>
        ))}
        <button className="p-level-tab p-level-add" onClick={() => setModal({ type: 'newLevel' })}>
          <Icon name="plus" size={16} /> Уровень
        </button>
      </div>

      {!page.data ? (
        <Loading error={page.error} onRetry={page.reload} />
      ) : (
        <>
          <section className="p-card p-level-card">
            <span className="p-level-big">{page.data.level.code}</span>
            <div className="p-level-info">
              <h2>
                {page.data.level.title_kz} <span className="p-muted">· {page.data.level.title_ru}</span>
              </h2>
              <p className="p-muted">{page.data.level.description || `${page.data.modules.length} модулей`}</p>
            </div>
            <label className="p-check">
              <input type="checkbox" checked={page.data.level.is_published} onChange={togglePublished} />
              Виден ученикам
            </label>
            <button className="p-btn" onClick={() => setModal({ type: 'level', data: page.data.level })}>
              <Icon name="pen" size={16} /> Изменить уровень
            </button>
            <button className="p-btn p-btn-primary" onClick={() => setModal({ type: 'newModule' })}>
              <Icon name="plus" size={18} /> Модуль
            </button>
          </section>

          <div className="p-filter">
            <span className="p-muted">Показать уроки:</span>
            <div className="p-segment">
              {[
                ['all', 'Все'],
                ['published', 'Опубликованные'],
                ['draft', 'Черновики'],
              ].map(([k, label]) => (
                <button key={k} className={filter === k ? 'active' : ''} onClick={() => setFilter(k)}>
                  {label} <span>{counts[k]}</span>
                </button>
              ))}
            </div>
          </div>

          {page.data.modules.length === 0 && (
            <div className="p-card p-empty">
              <p className="p-muted">На этом уровне пока нет модулей</p>
              <button className="p-btn p-btn-primary" onClick={() => setModal({ type: 'newModule' })}>
                <Icon name="plus" size={18} /> Первый модуль
              </button>
            </div>
          )}

          <div className="p-modules">
            {page.data.modules.map((m, i) => {
              const isOpen = open === m.id
              const lessons = m.lessons.filter(showLesson)
              if (filter !== 'all' && lessons.length === 0) return null
              return (
                <div key={m.id} className={`p-module ${isOpen ? 'open' : ''}`} {...dragProps(i)}>
                  <div className="p-module-row">
                    <span className="p-grip" title="Перетащите, чтобы поменять порядок">
                      <Icon name="grip" size={16} />
                    </span>
                    <span className="p-module-num" style={{ background: m.color }}>
                      {m.number}
                    </span>
                    <button className="p-module-title" onClick={() => setOpen(isOpen ? false : m.id)}>
                      <b>{m.title_kz}</b>
                      <small>{m.title_ru}</small>
                    </button>
                    <span className="p-muted p-hide-sm">{m.lesson_count} урока</span>
                    <span className="p-muted p-hide-sm">{m.word_count} слов</span>
                    <span className="p-muted p-module-grammar p-hide-sm">{m.grammar_title}</span>
                    <Badge status={m.status} />
                    <button className="p-icon-btn" onClick={() => setModal({ type: 'module', data: m })} aria-label="Изменить модуль">
                      <Icon name="pen" size={16} />
                    </button>
                    <button className="p-icon-btn ghost" onClick={() => setOpen(isOpen ? false : m.id)} aria-label="Уроки модуля">
                      <Icon name={isOpen ? 'down' : 'right'} size={18} />
                    </button>
                  </div>

                  {isOpen && (
                    <div className="p-lessons">
                      {lessons.map((l) => (
                        <div key={l.id} className="p-lesson-row">
                          <span className="p-lesson-letter">Урок {l.letter}</span>
                          <b className="p-lesson-title">{l.title_kz}</b>
                          <span className="p-muted p-small p-hide-sm">
                            {l.blocks.length ? l.blocks.map((b) => BLOCKS[b].kz).join(' · ') : 'Блоков пока нет'}
                          </span>
                          <Badge status={l.status} />
                          <Link to={`/admin/lessons/${l.id}`} className="p-link">
                            Открыть в конструкторе
                          </Link>
                        </div>
                      ))}
                      <div className="p-lesson-add">
                        <button className="p-btn p-btn-sm" onClick={() => newLesson(m.id)}>
                          <Icon name="plus" size={16} /> Новый урок
                        </button>
                        <span className="p-muted p-small">Создаётся черновиком: ученики не увидят его, пока вы не опубликуете</span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}

      {modal?.type === 'newLevel' && (
        <LevelModal
          onClose={() => setModal(null)}
          onSave={async (d) => {
            const lv = await panelApi.createLevel(d)
            setModal(null)
            levels.reload()
            navigate(`/admin/levels/${lv.code}`)
          }}
        />
      )}
      {modal?.type === 'level' && (
        <LevelModal
          level={modal.data}
          onClose={() => setModal(null)}
          onSave={async (d) => {
            await panelApi.updateLevel(code, d)
            setModal(null)
            reloadAll()
          }}
        />
      )}
      {(modal?.type === 'module' || modal?.type === 'newModule') && (
        <ModuleModal
          module={modal.data}
          onClose={() => setModal(null)}
          onSave={async (d) => {
            if (modal.data) await panelApi.updateModule(modal.data.id, d)
            else await panelApi.createModule(code, d)
            setModal(null)
            reloadAll()
          }}
        />
      )}
    </>
  )
}

function useForm(initial, onSave) {
  const [form, setForm] = useState(initial)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onSave(form)
    } catch (err) {
      setError(errorText(err))
      setBusy(false)
    }
  }
  return { form, set, submit, error, busy }
}

function LevelModal({ level, onClose, onSave }) {
  const { form, set, submit, error, busy } = useForm(
    { code: level?.code || '', title_kz: level?.title_kz || '', title_ru: level?.title_ru || '', description: level?.description || '' },
    onSave
  )
  return (
    <Modal title={level ? `Уровень ${level.code}` : 'Новый уровень'} onClose={onClose}>
      <form className="p-form" onSubmit={submit}>
        {!level && (
          <label className="p-field">
            <span>Код уровня</span>
            <input value={form.code} onChange={set('code')} maxLength={4} placeholder="Например, C2" required />
          </label>
        )}
        <div className="p-form-2">
          <label className="p-field">
            <span>Название (қазақша)</span>
            <input value={form.title_kz} onChange={set('title_kz')} required />
          </label>
          <label className="p-field">
            <span>Название (по-русски)</span>
            <input value={form.title_ru} onChange={set('title_ru')} required />
          </label>
        </div>
        <label className="p-field">
          <span>Описание</span>
          <textarea rows={3} value={form.description} onChange={set('description')} />
        </label>
        {error && <p className="p-error">{error}</p>}
        <div className="p-modal-foot">
          <button type="button" className="p-btn" onClick={onClose}>
            Отмена
          </button>
          <button className="p-btn p-btn-primary" disabled={busy}>
            {level ? 'Сохранить' : 'Создать уровень'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ModuleModal({ module, onClose, onSave }) {
  const { form, set, submit, error, busy } = useForm(
    {
      title_kz: module?.title_kz || '',
      title_ru: module?.title_ru || '',
      emoji: module?.emoji || '📘',
      color: module?.color || '#8B5CF6',
      ...(module ? { status: module.status } : {}),
    },
    onSave
  )
  return (
    <Modal title={module ? `Модуль ${module.number}` : 'Новый модуль'} sub={module ? null : 'Создаётся черновиком'} onClose={onClose}>
      <form className="p-form" onSubmit={submit}>
        <div className="p-form-2">
          <label className="p-field">
            <span>Тема (қазақша)</span>
            <input value={form.title_kz} onChange={set('title_kz')} required />
          </label>
          <label className="p-field">
            <span>Тема (по-русски)</span>
            <input value={form.title_ru} onChange={set('title_ru')} />
          </label>
        </div>
        <div className="p-form-3">
          <label className="p-field">
            <span>Эмодзи</span>
            <input value={form.emoji} onChange={set('emoji')} maxLength={4} />
          </label>
          <label className="p-field">
            <span>Цвет</span>
            <input type="color" value={form.color} onChange={set('color')} />
          </label>
          {module && (
            <label className="p-field">
              <span>Статус</span>
              <select value={form.status} onChange={set('status')}>
                {Object.entries(STATUS).map(([k, s]) => (
                  <option key={k} value={k}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {error && <p className="p-error">{error}</p>}
        <div className="p-modal-foot">
          <button type="button" className="p-btn" onClick={onClose}>
            Отмена
          </button>
          <button className="p-btn p-btn-primary" disabled={busy}>
            {module ? 'Сохранить' : 'Создать модуль'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
