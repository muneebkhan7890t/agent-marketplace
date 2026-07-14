"use client";

/**
 * lib/auth-context.tsx
 * -----------------------
 * Client-side auth state. Token lives in localStorage (see lib/api.ts);
 * this context just tracks whether we've loaded it yet and who "me" is,
 * so pages can redirect to /login without a flash of the wrong screen.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api, getToken, setToken, clearToken, CurrentUser } from "./api";

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      Promise.resolve().then(() => setLoading(false));
      return;
    }
    api
      .get<CurrentUser>("/auth/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      { email, password }
    );
    setToken(res.access_token);
    const me = await api.get<CurrentUser>("/auth/me");
    setUser(me);
    router.push("/dashboard");
  }

  async function register(fullName: string, email: string, password: string) {
    await api.post("/auth/register", {
      full_name: fullName,
      email,
      password,
    });
    await login(email, password);
  }

  function logout() {
    clearToken();
    setUser(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
