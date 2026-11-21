import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type User } from './api/client'

interface AuthState {
  user: User | null
  loading: boolean
  refresh: () => Promise<User | null>
  setUser: (u: User | null) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)
let deviceRequest: Promise<User | null> | null = null

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const { data } = await api.GET('/api/auth/me')
    setUser(data ?? null)
    return data ?? null
  }, [])

  // No sign-up while BetterU runs privately: the first visit creates an account
  // tied to this browser (a long-lived cookie), so data stays on this device's account.
  const ensureDeviceAccount = useCallback(() => {
    // Share one in-flight request so a double-run effect can't create two accounts.
    deviceRequest ??= (async () => {
      const existing = await refresh()
      if (existing) return existing
      const { data } = await api.POST('/api/auth/device')
      setUser(data ?? null)
      return data ?? null
    })().finally(() => { deviceRequest = null })
    return deviceRequest
  }, [refresh])

  useEffect(() => {
    ensureDeviceAccount().finally(() => setLoading(false))
  }, [ensureDeviceAccount])

  const logout = useCallback(async () => {
    await api.POST('/api/auth/logout')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, refresh, setUser, logout }}>{children}</AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
