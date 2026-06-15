import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

interface User {
  user_id: number;
  username: string;
  email: string;
  admin?: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (formData: FormData) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => null,
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  function fetchUser() {
    fetch("/api/whoami", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        let parsedUser: User | null = null;

        if (data?.user) {
          parsedUser = data.user;
        } else if (data?.user_id && data?.username && data?.email) {
          parsedUser = {
            user_id: data.user_id,
            username: data.username,
            email: data.email,
          };
        }

        if (parsedUser) {
          fetch("/api/admin/status", { credentials: "include" })
            .then((r) => (r.ok ? r.json() : { admin: false }))
            .then((s) => setUser({ ...parsedUser!, admin: s.admin }))
            .catch(() => setUser(parsedUser!));
        } else {
          setUser(null);
        }
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchUser();
  }, []);

  async function login(formData: FormData): Promise<string | null> {
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      const data = await res.json();
      if (res.ok && data.user) {
        setUser({ ...data.user, admin: data.admin ?? false });
        return null;
      }
      return data.message || "Login failed";
    } catch {
      return "An error occurred";
    }
  }

  function logout() {
    fetch("/api/logout", { method: "POST", credentials: "include" })
      .then(() => {
        setUser(null);
        navigate("/login", { replace: true });
      });
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext);
}
