import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { AuthState, User, LoginForm } from './types.js';
import { createAuthStrategy } from '../api/auth.js';
import type { AuthStrategy } from './types.js';
import { getToken, setTokens, clearToken } from './token.js';
import { fetchUserMenus, type MenuItem } from '../api/menus.js';

const AuthContext = createContext<AuthState | null>(null);

const strategy: AuthStrategy = createAuthStrategy();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [menus, setMenus] = useState<MenuItem[]>([]);

  useEffect(() => {
    const token = getToken();
    if (token) {
      strategy
        .getUser(token)
        .then((u) => {
          if (u) {
            setUser(u);
            // Fetch menus
            fetchUserMenus()
              .then(setMenus)
              .catch(() => setMenus([]));
          } else {
            clearToken();
          }
        })
        .catch(() => clearToken())
        .finally(() => setReady(true));
    } else {
      setReady(true);
    }
  }, []);

  const login = useCallback(async (form: LoginForm) => {
    const result = await strategy.login(form);
    setTokens(result.tokens.access_token, result.tokens.refresh_token);
    setUser(result.user);

    // Fetch user menus
    try {
      const userMenus = await fetchUserMenus();
      setMenus(userMenus);
    } catch (err) {
      console.error('Failed to fetch menus:', err);
      setMenus([]);
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setMenus([]);
  }, []);

  const hasPermission = useCallback(
    (permission: string) => {
      if (!user) return false;
      if (user.is_admin) return true; // Admin has all permissions
      return user.permissions.includes(permission);
    },
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, ready, menus, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
