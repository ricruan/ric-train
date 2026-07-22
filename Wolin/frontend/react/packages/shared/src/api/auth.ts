import type { AuthStrategy, LoginForm, User, AuthTokens } from '../auth/types.js';

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class MockAuthStrategy implements AuthStrategy {
  async login(form: LoginForm): Promise<{ user: User; tokens: AuthTokens }> {
    await delay(300);
    return {
      user: {
        id: 1,
        username: form.username,
        roles: ['admin'],
        permissions: ['*'],
        is_admin: true,
      },
      tokens: {
        access_token: `mock_access_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        refresh_token: `mock_refresh_${Date.now()}`,
      },
    };
  }

  async refresh(_refreshToken: string): Promise<string> {
    await delay(100);
    return `mock_access_${Date.now()}_refreshed`;
  }

  async getUser(accessToken: string): Promise<User | null> {
    await delay(100);
    if (!accessToken || !accessToken.startsWith('mock_access_')) return null;
    return {
      id: 1,
      username: 'admin',
      roles: ['admin'],
      permissions: ['*'],
      is_admin: true,
    };
  }
}

export class ApiAuthStrategy implements AuthStrategy {
  async login(form: LoginForm): Promise<{ user: User; tokens: AuthTokens }> {
    const axios = (await import('axios')).default;
    const res = await axios.post('/api/auth/login', form);
    const { access_token, refresh_token, ...userFields } = res.data.data;
    return {
      user: userFields as User,
      tokens: { access_token, refresh_token },
    };
  }

  async refresh(refreshToken: string): Promise<string> {
    const axios = (await import('axios')).default;
    const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
    return res.data.data.access_token;
  }

  async getUser(accessToken: string): Promise<User | null> {
    try {
      const axios = (await import('axios')).default;
      const res = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      return res.data.data as User;
    } catch {
      return null;
    }
  }
}

export function createAuthStrategy(): AuthStrategy {
  const mode = import.meta.env.VITE_AUTH_MODE;
  if (mode === 'mock') return new MockAuthStrategy();
  return new ApiAuthStrategy();
}
