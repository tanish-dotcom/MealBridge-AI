import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, tokens } from "../lib/api";
import type { AuthResponse, User } from "../lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signupDonor: (payload: Parameters<typeof api.signupDonor>[0]) => Promise<User>;
  signupNgo: (payload: Parameters<typeof api.signupNgo>[0]) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User>;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function persistAuth(res: AuthResponse) {
  tokens.set(res.token_pair.access_token, res.token_pair.refresh_token);
}

async function loadUser(): Promise<User | null> {
  try {
    return await api.getMe();
  } catch {
    tokens.clear();
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      if (!tokens.access) {
        setLoading(false);
        return;
      }
      const u = await loadUser();
      if (active) {
        setUser(u);
        setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const applyAuth = useCallback(async (res: AuthResponse) => {
    persistAuth(res);
    const u = await api.getMe();
    setUser(u);
    return u;
  }, []);

  const login = useCallback(
    (email: string, password: string) =>
      api.login({ email, password }).then(applyAuth),
    [applyAuth],
  );

  const signupDonor = useCallback(
    (payload: Parameters<typeof api.signupDonor>[0]) =>
      api.signupDonor(payload).then(applyAuth),
    [applyAuth],
  );

  const signupNgo = useCallback(
    (payload: Parameters<typeof api.signupNgo>[0]) =>
      api.signupNgo(payload).then(applyAuth),
    [applyAuth],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      tokens.clear();
      setUser(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const u = await api.getMe();
    setUser(u);
    return u;
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, signupDonor, signupNgo, logout, refreshUser, setUser }),
    [user, loading, login, signupDonor, signupNgo, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
