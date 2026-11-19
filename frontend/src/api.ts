const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'fxnexus.demo.session';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    if (res.status === 401 && path !== '/api/auth/login') {
      clearToken();
      window.dispatchEvent(new Event('fxnexus:unauthorized'));
    }
    throw new Error(data.detail || 'Request failed');
  }
  return data as T;
}

export const post = (path: string, body: any = {}) =>
  api(path, { method: 'POST', body: JSON.stringify(body) });
