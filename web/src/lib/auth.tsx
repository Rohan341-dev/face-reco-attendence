import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import { clearTokens, getAccessToken, setTokens } from './api/client'
import { useMe } from './api/queries'

type AuthValue = {
  authenticated: boolean
  ready: boolean
  signIn: (access: string, refresh?: string | null) => void
  signOut: () => void
  me: ReturnType<typeof useMe>['data']
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(() => Boolean(getAccessToken()))
  const meQuery = useMe({ enabled: authenticated, retry: false })

  const signIn = useCallback((access: string, refresh?: string | null) => {
    setTokens(access, refresh)
    setAuthenticated(true)
  }, [])

  const signOut = useCallback(() => {
    clearTokens()
    setAuthenticated(false)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      authenticated,
      ready: !authenticated || !meQuery.isLoading,
      signIn,
      signOut,
      me: meQuery.data,
    }),
    [authenticated, meQuery.isLoading, meQuery.data, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
