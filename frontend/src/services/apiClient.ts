/**
 * API Client Configuration and HTTP Methods
 * Supports dual-mode execution:
 * 1. Live FastAPI Backend (http://127.0.0.1:8000/api/v1) with JWT Bearer auth
 * 2. Standalone Autonomous Mock Mode for offline presentations and CI/CD testing
 */

import { authService } from './authService';

export type BackendConnectionState = 'connected' | 'offline' | 'checking';

export interface ApiConfig {
  baseUrl: string;
  useMock: boolean;
  simulateLatencyMs: number;
}

export const apiConfig: ApiConfig = {
  baseUrl: (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  useMock: true, // Default to mock mode for isolated unit testing and initial standalone state
  simulateLatencyMs: 150,
};

type ConnectionListener = (state: BackendConnectionState, isMock: boolean) => void;
const listeners: Set<ConnectionListener> = new Set();
let currentConnectionState: BackendConnectionState = 'checking';

export function subscribeConnectionState(listener: ConnectionListener): () => void {
  listeners.add(listener);
  listener(currentConnectionState, apiConfig.useMock);
  return () => {
    listeners.delete(listener);
  };
}

function notifyListeners(): void {
  listeners.forEach((fn) => fn(currentConnectionState, apiConfig.useMock));
}

export function setUseMock(mock: boolean): void {
  apiConfig.useMock = mock;
  notifyListeners();
}

export function isUsingMock(): boolean {
  return apiConfig.useMock;
}

export function getConnectionState(): BackendConnectionState {
  return currentConnectionState;
}

export async function simulateDelay(ms: number = apiConfig.simulateLatencyMs): Promise<void> {
  if (ms <= 0) return;
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Health check probe to determine whether FastAPI backend is responsive
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const healthUrl = apiConfig.baseUrl.replace(/\/api\/v1\/?$/, '/health');
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(healthUrl, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      currentConnectionState = 'connected';
      notifyListeners();
      return true;
    }
    currentConnectionState = 'offline';
    notifyListeners();
    return false;
  } catch {
    currentConnectionState = 'offline';
    notifyListeners();
    return false;
  }
}

/**
 * Core authenticated fetch wrapper
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${apiConfig.baseUrl}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  };

  // Attach JWT Bearer token if available
  const token = authService.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Attempt re-auth once
    try {
      const newToken = await authService.login();
      headers['Authorization'] = `Bearer ${newToken.access_token}`;
      const retryRes = await fetch(url, {
        ...options,
        headers,
      });
      if (!retryRes.ok) {
        throw new Error(`HTTP error ${retryRes.status}: ${retryRes.statusText}`);
      }
      return retryRes.json() as Promise<T>;
    } catch {
      authService.logout();
    }
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || errorBody.message || `HTTP error ${res.status}: ${res.statusText}`;
    throw new Error(message);
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return {} as T;
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'GET', ...options }),
  post: <T>(endpoint: string, data?: unknown, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'POST',
      body: data !== undefined ? JSON.stringify(data) : undefined,
      ...options,
    }),
  put: <T>(endpoint: string, data?: unknown, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: data !== undefined ? JSON.stringify(data) : undefined,
      ...options,
    }),
  delete: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'DELETE', ...options }),
};
