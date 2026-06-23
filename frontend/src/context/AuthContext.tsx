import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { setApiAuth } from "@/lib/api";

const TOKEN_KEY = "landgrant.jwt";

export type MePersona =
  | "landowner"
  | "land_agent"
  | "in_house_counsel"
  | "outside_counsel"
  | "firm_admin"
  | "platform_admin"
  | "admin";

export type MeResponse = {
  sub: string;
  email?: string;
  firm_id?: string;
  persona: MePersona;
  roles: string[];
  permissions: string[];
};

type AuthContextValue = {
  token: string | null;
  me: MeResponse | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8050";

function readStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

type Props = { children: ReactNode };

export function AuthProvider({ children }: Props) {
  const [token, setToken] = useState<string | null>(() => {
    // Seed the shared API client synchronously during the first render, before
    // any child component fires a request. Without this, a page reload or
    // deep-link restores the token into React state (so /auth/me succeeds via
    // its explicit header) but leaves the shared ``apiFetch`` client tokenless,
    // so every data request 401s and the UI shows "Not authenticated".
    const stored = readStoredToken();
    setApiAuth({ token: stored ?? undefined });
    return stored;
  });
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const persistToken = useCallback((t: string | null) => {
    setToken(t);
    setApiAuth({ token: t ?? undefined });
    if (typeof window === "undefined") return;
    try {
      if (t) window.sessionStorage.setItem(TOKEN_KEY, t);
      else window.sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const refreshMe = useCallback(async () => {
    if (!token) {
      setMe(null);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        persistToken(null);
        setMe(null);
        return;
      }
      const body = (await res.json()) as MeResponse;
      setMe(body);
    } catch {
      // Network/backend failure: drop the token so the app falls back to the
      // login screen instead of hanging on the auth-loading gate.
      persistToken(null);
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, [token, persistToken]);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = (err as { detail?: string }).detail ?? res.statusText;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      const data = (await res.json()) as { access_token: string };
      persistToken(data.access_token);
      const meRes = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) {
        setMe((await meRes.json()) as MeResponse);
      }
    },
    [persistToken],
  );

  const logout = useCallback(() => {
    persistToken(null);
    setMe(null);
  }, [persistToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      me,
      isAuthenticated: Boolean(token),
      loading,
      login,
      logout,
      refreshMe,
    }),
    [token, me, loading, login, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
