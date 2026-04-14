import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

interface AuthUser {
  sub: string
  email: string | null
  name: string | null
  org_id: string | null
  is_superadmin: boolean
  roles: string[]
}

interface AuthContextType {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  accessToken: string | null
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  accessToken: null,
})

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}

const OIDC_ENABLED = import.meta.env.VITE_OIDC_ENABLED === "true"

const DEV_USER: AuthUser = {
  sub: "dev",
  email: null,
  name: null,
  org_id: null,
  is_superadmin: true,
  roles: [],
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(!OIDC_ENABLED ? DEV_USER : null)
  const [isLoading, setIsLoading] = useState(OIDC_ENABLED)
  const [accessToken] = useState<string | null>(null)

  useEffect(() => {
    if (!OIDC_ENABLED) {
      return
    }

    // OIDC mode: check for token in URL hash (callback) or try silent auth
    // Full OIDC flow will be implemented when oidc-client-ts is added
    // For now, try to fetch /api/v1/me to check if we have a valid session
    fetch("/api/v1/me", {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setUser(data)
        setIsLoading(false)
      })
      .catch(() => setIsLoading(false))
  }, [accessToken])

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, isLoading, accessToken }}
    >
      {children}
    </AuthContext.Provider>
  )
}
