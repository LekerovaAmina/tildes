import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, getToken } from '../api/client.js'

// Вход по email и паролю (backend/learning/auth.py).
// status: 'checking' (проверяем сохранённый токен) | 'guest' | 'user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [state, setState] = useState(() => ({ status: getToken() ? 'checking' : 'guest', user: null }))

  // При открытии сайта проверяем сохранённый токен
  useEffect(() => {
    if (!getToken()) return
    api
      .me()
      .then((r) => setState({ status: 'user', user: r.user }))
      .catch(() => setState({ status: 'guest', user: null }))
  }, [])

  // Сервер ответил 401 на любой запрос — разлогиниваем
  useEffect(() => {
    const onLogout = () => setState({ status: 'guest', user: null })
    window.addEventListener('tildes:logout', onLogout)
    return () => window.removeEventListener('tildes:logout', onLogout)
  }, [])

  // Ответ login/register: { token, user, redirect? }. Токен сохраняет api-клиент.
  const signIn = useCallback((res) => {
    setState({ status: 'user', user: res.user })
    return res
  }, [])

  const actions = useMemo(
    () => ({
      login: async (email, password) => signIn(await api.login(email, password)),
      register: async (email, password, name) => signIn(await api.register({ email, password, name })),
      logout: async () => {
        await api.logout().catch(() => {}) // токен уже недействителен — всё равно выходим
        setState({ status: 'guest', user: null })
      },
    }),
    [signIn]
  )

  return <AuthContext.Provider value={{ ...state, ...actions }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
