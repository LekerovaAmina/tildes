import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'

// Контент (уровни и модули B2) загружается с Django-бэкенда при старте
// и приводится к формату, который используют страницы.

const ContentContext = createContext(null)

const normLevel = (l) => ({ id: l.code, name: l.code, title: l.title, ru: l.title_ru, desc: l.description, available: l.available })

const normModule = (m) => ({
  id: m.id,
  number: m.number,
  title: m.title,
  titleRu: m.title_ru,
  emoji: m.emoji,
  color: m.color,
  lessons: m.lessons,
  grammar: m.grammar,
  text: m.text,
  words: m.words.map((w) => ({ id: w.id, kz: w.kz, ru: w.ru, moduleId: m.id })),
  questions: m.questions.map((q) => ({ id: q.id, q: q.text, options: q.options })),
})

export function ContentProvider({ children }) {
  const [state, setState] = useState({ status: 'loading', levels: [], modules: [] })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading' }))
    try {
      const [levels, content] = await Promise.all([api.levels(), api.content('b2')])
      setState({ status: 'ready', levels: levels.map(normLevel), modules: content.modules.map(normModule) })
    } catch (e) {
      console.error(e)
      setState((s) => ({ ...s, status: 'error' }))
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const value = useMemo(() => {
    const byId = new Map(state.modules.map((m) => [m.id, m]))
    return {
      ...state,
      reload: load,
      getModule: (id) => byId.get(Number(id)),
      allWords: state.modules.flatMap((m) => m.words),
    }
  }, [state, load])

  return <ContentContext.Provider value={value}>{children}</ContentContext.Provider>
}

export const useContent = () => useContext(ContentContext)
