// frontend/src/context/AuthContext.tsx
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { API_BASE_URL } from "../api/client";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("auth_token")
  );
  const [loading, setLoading] = useState<boolean>(true);

  const fetchCurrentUser = useCallback(
    async (t: string) => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${t}`,
          },
        });
        if (!response.ok) {
          throw new Error("Не вдалося отримати дані користувача");
        }
        const data = (await response.json()) as User;
        setUser(data);
      } catch {
        setUser(null);
        setToken(null);
        localStorage.removeItem("auth_token");
      }
    },
    []
  );

  useEffect(() => {
    const t = localStorage.getItem("auth_token");
    if (!t) {
      setLoading(false);
      return;
    }
    fetchCurrentUser(t).finally(() => setLoading(false));
  }, [fetchCurrentUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      // backend чекає OAuth2PasswordRequestForm: username/password у form-data
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      if (!response.ok) {
        let msg = "Помилка авторизації";
        try {
          const err = await response.json();
          if (err && err.detail) msg = err.detail;
        } catch {
          // ignore
        }
        throw new Error(msg);
      }

      const data = (await response.json()) as {
        access_token: string;
        token_type: string;
      };

      localStorage.setItem("auth_token", data.access_token);
      setToken(data.access_token);
      await fetchCurrentUser(data.access_token);
    },
    [fetchCurrentUser]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName ?? null,
        }),
      });

      if (!response.ok) {
        let msg = "Помилка реєстрації";
        try {
          const err = await response.json();
          if (err && err.detail) msg = err.detail;
        } catch {
          // ignore
        }
        throw new Error(msg);
      }

      // Після успішної реєстрації автоматично логінимо
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token");
    setToken(null);
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    token,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
