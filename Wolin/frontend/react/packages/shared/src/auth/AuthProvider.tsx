import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { AuthState, User, LoginForm } from './types.js';
import { createAuthStrategy } from '../api/auth.js';
import type { AuthStrategy } from './types.js';
import { getToken, setTokens, clearToken } from './token.js';

const AuthContext = createContext<AuthState | null>(null);

const strategy: AuthStrategy = createAuthStrategy();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (token) {
      strategy.getUser(token).then((u) => {
        if (u) setUser(u);
        else clearToken();
        setReady(true);
      }).catch(() => {
        clearToken();
        setReady(true);
      });
    } else {
      setReady(true);
    }
  }, []);

  const login = useCallback(async (form: LoginForm) => {
    const { user: u, tokens } = await strategy.login(form);
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
