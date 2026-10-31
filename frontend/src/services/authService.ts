import { apiConfig } from './apiClient';

export interface AuthUser {
  id: number;
  email: string;
  fullName: string;
  role: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user?: AuthUser;
}

const TOKEN_KEY = 'adeptlearn_access_token';
const USER_KEY = 'adeptlearn_user';

export class AuthService {
  private currentToken: string | null = null;
  private currentUser: AuthUser | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.currentToken = localStorage.getItem(TOKEN_KEY);
      const savedUser = localStorage.getItem(USER_KEY);
      if (savedUser) {
        try {
          this.currentUser = JSON.parse(savedUser);
        } catch {
          this.currentUser = null;
        }
      }
    }
  }

  getToken(): string | null {
    if (!this.currentToken && typeof window !== 'undefined') {
      this.currentToken = localStorage.getItem(TOKEN_KEY);
    }
    return this.currentToken;
  }

  getCurrentUser(): AuthUser | null {
    return this.currentUser;
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  async login(
    email: string = 'student@adaptive.edu',
    password: string = 'student123'
  ): Promise<AuthTokenResponse> {
    try {
      const response = await fetch(`${apiConfig.baseUrl}/auth/login/json`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Login failed with status ${response.status}`);
      }

      const data: AuthTokenResponse = await response.json();
      this.currentToken = data.access_token;
      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, data.access_token);
      }

      if (data.user) {
        this.currentUser = data.user;
        if (typeof window !== 'undefined') {
          localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        }
      } else {
        // Fallback user details
        this.currentUser = {
          id: 2,
          email,
          fullName: 'Emmy Noether (Student)',
          role: 'STUDENT',
        };
      }

      return data;
    } catch (err) {
      console.warn('AuthService.login fallback or error:', err);
      throw err;
    }
  }

  async ensureAuthenticated(): Promise<string> {
    const existing = this.getToken();
    if (existing) {
      return existing;
    }
    const authRes = await this.login();
    return authRes.access_token;
  }

  logout(): void {
    this.currentToken = null;
    this.currentUser = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }
}

export const authService = new AuthService();
