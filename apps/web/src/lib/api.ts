export type ApiError = { status: number; code: string; message: string };

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_RIVET_API_URL || "";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = apiBaseUrl();
  const url = base ? `${base}${path}` : path;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(url, { ...init, signal: controller.signal, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
    if (!res.ok) {
      let code = "http_error";
      let message = res.statusText;
      try {
        const body = await res.json();
        code = body.code || code;
        message = body.message || message;
      } catch {}
      throw { status: res.status, code, message } as ApiError;
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export function isApiConfigured(): boolean {
  return Boolean(apiBaseUrl());
}
