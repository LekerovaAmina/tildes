import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokenStore } from '../api/client.js'

// Вход по email и паролю. status: 'checking' (проверяем сохранённый токен) | 'guest' | 'user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [state, setState] = useState(() => ({ status: tokenStore.get() ? 'checking' : 'guest', user: null }))

  // При открытии сайта проверяем сохранённый токен
  useEffect(() => {
    if (!tokenStore.get()) return
    api
      .me()
      .then((user) => setState({ status: 'user', user }))
      .catch(() => {
        tokenStore.set(null)
        setState({ status: 'guest', user: null })
      })
  }, [])

  // Сервер ответил 401 на любой запрос — разлогиниваем
  useEffect(() => {
    const onLogout = () => setState({ status: 'guest', user: null })
    window.addEventListener('tildes:logout', onLogout)
    return () => window.removeEventListener('tildes:logout', onLogout)
  }, [])

  const signIn = useCallback(({ token, user }) => {
    tokenStore.set(token)
    setState({ status: 'user', user })
    return user
  }, [])

  const actions = useMemo(
    () => ({
      login: async (email, password) => signIn(await api.login(email, password)),
      register: async (email, password, name) => signIn(await api.register(email, password, name)),
      logout: async () => {
        try {
          await api.logout()
        } catch {
          /* токен уже недействителен — всё равно выходим */
        }
        tokenStore.set(null)
        setState({ status: 'guest', user: null })
      },
    }),
    [signIn]
  )

  return <AuthContext.Provider value={{ ...state, ...actions }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
