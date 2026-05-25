import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

interface User {
  user_id: number
  username: string
  email: string
}

interface AuthContextType {
  user: User | null
  login: (formData: FormData) => Promise<string | null>
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({ user: null, login: async () => null, logout: () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  function fetchUser() {
    fetch("/api/whoami", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        if (data?.user) {
          setUser(data.user)
        } else if (data?.user_id && data?.username && data?.email) {
          setUser({
            user_id: data.user_id,
            username: data.username,
            email: data.email,
          })
        } else {
          setUser(null)
        }
      })
      .catch(() => setUser(null))
  }

  useEffect(() => {
    fetchUser()
  }, [])

  async function login(formData: FormData): Promise<string | null> {
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        body: formData,
        credentials: "include",
      })
      const data = await res.json()
      if (res.ok && data.user) {
        setUser(data.user)
        return null // success
      }
      return data.message || "Login failed"
    } catch {
      return "An error occurred"
    }
  }

  function logout() {
    fetch("/api/logout", { method: "POST", credentials: "include" })
      .then(() => {
        setUser(null)
        window.location.href = "/login"
      })
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
