import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'

// Прогресс пользователя хранится на Django-бэкенде (GET/PATCH /api/progress/ и др.).
// Изменения применяются сразу (оптимистично), а баллы затем сверяются с ответом сервера.

export const POINTS = {
  learned: 10, // «Я выучил»
  again: 2, // «Учить ещё раз» — за честность тоже немного
  topicFirst: 30, // первое прохождение темы карточек
  topicRepeat: 10, // повторное прохождение / повторение
  quizCorrect: 5, // за каждый новый правильный ответ сверх лучшего результата
}

const empty = {
  level: null,
  name: '',
  points: 0,
  wordStats: {}, // { [wordId]: { learned, again } }
  completedCardTopics: [], // id модулей, пройденных в карточках
  quizBest: {}, // { [moduleId]: число правильных }
  readTopics: {}, // { [moduleId]: { words, grammar, text } }
  activeDays: [], // 'YYYY-MM-DD'
}

const fromServer = (d) => ({
  level: d.level,
  name: d.name,
  points: d.points,
  wordStats: d.wordStats,
  completedCardTopics: d.completedCardTopics,
  quizBest: d.quizBest,
  readTopics: d.readTopics,
  activeDays: d.activeDays,
})

const today = () => new Date().toISOString().slice(0, 10)

const withActivity = (s) => (s.activeDays.includes(today()) ? s : { ...s, activeDays: [...s.activeDays, today()].slice(-60) })

// Баллы на сервере только растут (кроме сброса), поэтому берём максимум —
// так не важен порядок, в котором вернутся ответы.
const syncPoints = (setState) => (res) => setState((s) => ({ ...s, points: Math.max(s.points, res.points) }))

const ProgressContext = createContext(null)

export function ProgressProvider({ children }) {
  const [state, setState] = useState(empty)
  const [status, setStatus] = useState('loading')

  const load = useCallback(async () => {
    setStatus('loading')
    try {
      setState(fromServer(await api.progress()))
      setStatus('ready')
    } catch (e) {
      console.error(e)
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const actions = useMemo(() => {
    const onError = (e) => console.error(e)
    return {
      reloadProgress: load,

      setLevel: (level) => {
        setState((s) => ({ ...s, level }))
        api.updateProfile({ level }).catch(onError)
      },

      setName: (name) => {
        setState((s) => ({ ...s, name }))
        return api.updateProfile({ name })
      },

      markWord: (wordId, result) => {
        setState((s) => {
          const prev = s.wordStats[wordId] || { learned: 0, again: 0 }
          return withActivity({
            ...s,
            points: s.points + POINTS[result],
            wordStats: { ...s.wordStats, [wordId]: { ...prev, [result]: prev[result] + 1 } },
          })
        })
        api.answerCard(wordId, result).then(syncPoints(setState)).catch(onError)
      },

      // moduleId = null для режима «Повторение». Возвращает { gained, first }.
      completeCardTopic: async (moduleId) => {
        const res = await api.completeTopic(moduleId)
        setState((s) =>
          withActivity({
            ...s,
            points: Math.max(s.points, res.points),
            completedCardTopics:
              moduleId != null && !s.completedCardTopics.includes(moduleId)
                ? [...s.completedCardTopics, moduleId]
                : s.completedCardTopics,
          })
        )
        return res
      },

      // Проверка теста на сервере. Возвращает { correct, total, best, gained, results }.
      submitQuiz: async (moduleId, answers) => {
        const res = await api.submitQuiz(moduleId, answers)
        setState((s) =>
          withActivity({
            ...s,
            points: Math.max(s.points, res.points),
            quizBest: { ...s.quizBest, [moduleId]: res.best },
          })
        )
        return res
      },

      markRead: (moduleId, section) => {
        setState((s) => ({
          ...s,
          readTopics: { ...s.readTopics, [moduleId]: { ...(s.readTopics[moduleId] || {}), [section]: true } },
        }))
        api.markRead(moduleId, section).catch(onError)
      },

      reset: async () => {
        await api.resetProgress()
        await load()
      },
    }
  }, [load])

  return <ProgressContext.Provider value={{ ...state, status, ...actions }}>{children}</ProgressContext.Provider>
}

export const useProgress = () => useContext(ProgressContext)

// Сколько дней подряд пользователь занимается (включая сегодня или вчера)
export function streakOf(days) {
  const set = new Set(days)
  let n = 0
  const d = new Date()
  if (!set.has(d.toISOString().slice(0, 10))) d.setDate(d.getDate() - 1)
  while (set.has(d.toISOString().slice(0, 10))) {
    n++
    d.setDate(d.getDate() - 1)
  }
  return n
}

export const RANKS = [
  { min: 0, title: 'Бастаушы', ru: 'Новичок' },
  { min: 150, title: 'Үйренуші', ru: 'Ученик' },
  { min: 500, title: 'Білгір', ru: 'Знаток' },
  { min: 1200, title: 'Шебер', ru: 'Мастер' },
  { min: 2500, title: 'Шешен', ru: 'Оратор' },
]

export function rankOf(points) {
  let i = RANKS.length - 1
  while (points < RANKS[i].min) i--
  const next = RANKS[i + 1]
  return { ...RANKS[i], index: i, next, toNext: next ? next.min - points : 0, pct: next ? (points - RANKS[i].min) / (next.min - RANKS[i].min) : 1 }
}
