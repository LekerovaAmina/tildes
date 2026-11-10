import { Link } from 'react-router-dom'
import { panelApi } from '../../api/client.js'
import Icon from '../../components/Icon.jsx'
import { Badge, Loading, PageHead, formatWhen, useCrumbs, useLoad } from '../ui.jsx'

// 1 · Дашборд
export default function Dashboard() {
  useCrumbs([{ label: 'Админ-панель', to: '/panel' }, { label: 'Дашборд' }])
  const { data, error, reload } = useLoad(() => panelApi.dashboard('B2'), [])

  return (
    <>
      <PageHead title="Дашборд" sub="Что есть на платформе и что ждёт публикации">
        <a href="/home" target="_blank" rel="noreferrer" className="p-btn">
          <Icon name="eye" size={18} /> Предпросмотр сайта
        </a>
        <Link to="/panel/levels/B2" className="p-btn p-btn-primary">
          <Icon name="plus" size={18} /> Новый урок
        </Link>
      </PageHead>

      {!data ? (
        <Loading error={error} onRetry={reload} />
      ) : (
        <>
          <section className="p-stats">
            <Stat label="Модули" value={data.stats.modules} sub={`уровень ${data.level}`} />
            <Stat label="Уроки" value={data.stats.lessons} sub="во всех модулях уровня" />
            <Stat label="Слова в карточках" value={data.stats.words} sub="из раздела «Сөздік»" />
            <Stat label="Вопросы тестов" value={data.stats.questions} sub="к текстам модулей" />
          </section>

          <div className="p-grid-2-1">
            <section className="p-card">
              <h2>Покрытие уровней</h2>
              <p className="p-muted">Сколько модулей опубликовано на каждом уровне</p>
              <div className="p-coverage">
                {data.coverage.map((lv) => (
                  <Link to={`/panel/levels/${lv.code}`} key={lv.code} className="p-coverage-row">
                    <span className={`p-level-code ${lv.is_published ? 'on' : ''}`}>{lv.code}</span>
                    <span className="p-coverage-name">
                      <b>{lv.title_kz}</b>
                      <small>{lv.title_ru}</small>
                    </span>
                    <span className="p-bar">
                      <span style={{ width: `${lv.module_count ? (lv.published_modules / lv.module_count) * 100 : 0}%` }} />
                    </span>
                    <span className="p-coverage-count">
                      {lv.module_count ? `${lv.published_modules} из ${lv.module_count} модулей` : 'нет модулей'}
                    </span>
                    <Badge tone={lv.is_published ? 'green' : 'amber'}>{lv.is_published ? 'Опубликован' : 'В разработке'}</Badge>
                  </Link>
                ))}
              </div>
            </section>

            <section className="p-card">
              <h2>Черновики</h2>
              <p className="p-muted">Неопубликованные уроки — их видят только админы и редакторы</p>
              <div className="p-drafts">
                {data.drafts.length === 0 && <p className="p-muted p-drafts-empty">Черновиков нет — всё опубликовано</p>}
                {data.drafts.map((d) => (
                  <Link to={`/panel/lessons/${d.id}`} key={d.id} className="p-draft">
                    <span className="p-draft-icon">
                      <Icon name="pen" size={16} />
                    </span>
                    <span className="p-draft-body">
                      <b>Урок «{d.title_kz}»</b>
                      <small>{d.where} · ученики не видят</small>
                    </span>
                    <Badge status={d.status} />
                  </Link>
                ))}
              </div>
              <p className="p-muted p-small">
                Новый урок создаётся из раздела «Уровни и модули»: уровень → модуль → «+ Новый урок».
              </p>
            </section>
          </div>

          <section className="p-card">
            <h2>Активность учеников</h2>
            <div className="p-activity">
              <Stat label="Учеников с аккаунтом" value={data.activity.students} sub={`ещё ${data.activity.anonymous} без входа`} flat />
              <Stat label="Занимались сегодня" value={data.activity.active_today} flat />
              <Stat label="За 7 дней" value={data.activity.active_week} flat />
              <div className="p-top-students">
                <span className="p-label">Лучшие по баллам</span>
                {data.activity.top.length === 0 && <p className="p-muted">Пока никто не зарегистрировался</p>}
                {data.activity.top.map((s, i) => (
                  <div key={i} className="p-top-row">
                    <span className="p-avatar sm">{s.name[0]?.toUpperCase()}</span>
                    <span>{s.name}</span>
                    <b>{s.points}</b>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="p-card">
            <div className="p-card-head">
              <div>
                <h2>Последние изменения</h2>
                <p className="p-muted">Из журнала audit_log: правки в панели и в Django-админке</p>
              </div>
              <a href="/admin/learning/auditlog/" className="p-btn">
                Вся история
              </a>
            </div>
            {data.recent.length === 0 ? (
              <p className="p-muted p-empty-line">Изменений пока не было</p>
            ) : (
              <div className="p-table-wrap">
                <table className="p-table">
                  <thead>
                    <tr>
                      <th>Что изменено</th>
                      <th>Где</th>
                      <th>Действие</th>
                      <th>Кто</th>
                      <th>Когда</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent.map((r) => (
                      <tr key={r.id}>
                        <td>{r.what}</td>
                        <td className="p-muted">{r.where || '—'}</td>
                        <td>
                          <Badge tone={{ publish: 'green', delete: 'red', create: 'violet', update: 'gray' }[r.action]}>
                            {r.action_label}
                          </Badge>
                        </td>
                        <td>{r.who}</td>
                        <td className="p-muted">{formatWhen(r.when)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}

function Stat({ label, value, sub, flat }) {
  return (
    <div className={flat ? 'p-stat-flat' : 'p-card p-stat'}>
      <span className="p-label">{label}</span>
      <b>{value}</b>
      {sub && <small className="p-muted">{sub}</small>}
    </div>
  )
}
