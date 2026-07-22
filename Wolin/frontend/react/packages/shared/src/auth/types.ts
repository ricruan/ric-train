export interface User {
  id: number;
  username: string;
  email?: string;
  roles: string[];
  permissions: string[];
  is_admin: boolean;
}

export interface LoginForm {
  username: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface AuthState {
  user: User | null;
  ready: boolean;
  login: (form: LoginForm) => Promise<void>;
  logout: () => void;
}

export interface AuthStrategy {
  login(form: LoginForm): Promise<{ user: User; tokens: AuthTokens }>;
  refresh(refreshToken: string): Promise<string>;
  getUser(accessToken: string): Promise<User | null>;
}
