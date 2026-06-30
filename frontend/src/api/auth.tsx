import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import type { User as SupabaseUser } from "@supabase/supabase-js";
import { toast } from "sonner";
import { apiFetch } from "./client";

const PENDING_EMAIL_CONFIRMATION_KEY = "tppr:pending-email-confirmation";

interface User {
  user_id: string; // Supabase uses UUIDs
  username: string;
  email: string;
  admin?: boolean;
  avatar_url?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (formData: FormData) => Promise<string | null>;
  signup: (formData: FormData) => Promise<string | null>;
  logout: () => void;
  /** Re-fetch the user's backend profile (e.g. after changing their avatar). */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => null,
  signup: async () => null,
  logout: () => {},
  refreshUser: async () => {},
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

  // Pull avatar_url (and any future profile fields) from the backend, since the
  // backend-stored avatar URL is not part of the Supabase user_metadata.
  const refreshUser = useCallback(async () => {
    try {
      const res = await apiFetch("/api/whoami");
      if (!res.ok) return;
      const data = await res.json();
      setUser((prev) =>
        prev ? { ...prev, avatar_url: data.avatar_url } : prev,
      );
    } catch {
      // Backend may be temporarily unreachable; leave the cached user as-is.
    }
  }, []);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ? mapUser(session.user) : null);
      setLoading(false);
      if (session?.user) refreshUser();
    });

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user ? mapUser(session.user) : null);
        if (
          session?.user &&
          (event === "SIGNED_IN" || event === "INITIAL_SESSION")
        ) {
          refreshUser();
        }
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
  }, [refreshUser]);

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
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}