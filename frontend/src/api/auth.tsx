import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import type { User as SupabaseUser } from "@supabase/supabase-js";
import { toast } from "sonner";

const PENDING_EMAIL_CONFIRMATION_KEY = "tppr:pending-email-confirmation";

interface User {
  user_id: string; // Supabase uses UUIDs
  username: string;
  email: string;
  admin?: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (formData: FormData) => Promise<string | null>;
  signup: (formData: FormData) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => null,
  signup: async () => null,
  logout: () => {},
});

function mapUser(supabaseUser: SupabaseUser): User {
  return {
    user_id: supabaseUser.id,
    username: supabaseUser.user_metadata?.username ?? supabaseUser.email?.split("@")[0] ?? "",
    email: supabaseUser.email ?? "",
  };
}

function markPendingEmailConfirmation(email: string) {
  localStorage.setItem(PENDING_EMAIL_CONFIRMATION_KEY, email);
}

function consumePendingEmailConfirmation(email: string | undefined) {
  const pendingEmail = localStorage.getItem(PENDING_EMAIL_CONFIRMATION_KEY);
  if (!pendingEmail || pendingEmail !== email) return false;

  localStorage.removeItem(PENDING_EMAIL_CONFIRMATION_KEY);
  return true;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const confirmationToastShown = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ? mapUser(session.user) : null);
      setLoading(false);
    });

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user ? mapUser(session.user) : null);
        if (
          event === "SIGNED_IN" &&
          session?.user &&
          !confirmationToastShown.current &&
          consumePendingEmailConfirmation(session.user.email)
        ) {
          confirmationToastShown.current = true;
          toast.success("Confirmed!");
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  async function login(formData: FormData): Promise<string | null> {
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return error ? error.message : null;
  }

  async function signup(formData: FormData): Promise<string | null> {
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const username = formData.get("username") as string;

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { username } },
    });
    if (!error) {
      markPendingEmailConfirmation(email);
    }
    return error ? error.message : null;
  }

  function logout() {
    supabase.auth.signOut().then(() => {
      navigate("/login", { replace: true });
    });
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
