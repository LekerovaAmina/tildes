import Icon from '../../components/Icon.jsx'
import { Badge, useCrumbs } from '../ui.jsx'

// 7–9 · Разделы в разработке: Аудирование, Говорение, Письмо
const SECTIONS = {
  listening: {
    title: 'Аудирование',
    kz: 'Тыңдалым',
    icon: 'headphones',
    frames: [
      ['upload', 'Фрейм: загрузка аудио'],
      ['lines', 'Фрейм: транскрипт'],
      ['question', 'Фрейм: задания к аудио'],
    ],
  },
  speaking: {
    title: 'Говорение',
    kz: 'Сөйлесу',
    icon: 'mic',
    frames: [
      ['mic', 'Фрейм: запись ответа'],
      ['chat', 'Фрейм: диалоги и реплики'],
      ['check', 'Фрейм: проверка и оценка'],
    ],
  },
  writing: {
    title: 'Письмо',
    kz: 'Жазылым',
    icon: 'pen',
    frames: [
      ['pen', 'Фрейм: задание на письмо'],
      ['lines', 'Фрейм: образец ответа'],
      ['check', 'Фрейм: критерии проверки'],
    ],
  },
}

export default function Placeholder({ section }) {
  const s = SECTIONS[section]
  useCrumbs([{ label: 'Контент' }, { label: s.title }])
  return (
    <>
      <div className="p-head">
        <div>
          <h1>
            {s.title} <span className="p-muted-title">· {s.kz}</span>
          </h1>
          <p className="p-muted">Раздел в разработке — формат заданий ещё обсуждаем</p>
        </div>
        <Badge tone="amber">В разработке</Badge>
      </div>
      <div className="p-soon">
        <Icon name={s.icon} size={32} />
        <h2>Здесь будет редактор раздела «{s.title}»</h2>
        <p className="p-muted">Пустые фреймы ниже — места под будущие блоки. Заполним, когда команда решит, как работает раздел.</p>
      </div>
      <div className="p-soon-frames">
        {s.frames.map(([icon, label]) => (
          <div key={label} className="p-soon-frame">
            <Icon name={icon} size={22} />
            <b>{label}</b>
          </div>
        ))}
      </div>
    </>
  )
}
