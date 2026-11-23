export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

const TOKEN_KEY = "mykshema.token";
const USER_KEY = "mykshema.user";

export class ApiError extends Error {
  status: number;
  details?: { field: string; message: string }[];
  constructor(status: number, message: string, details?: { field: string; message: string }[]) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

export const storage = {
  get(key: string): string | null {
    try { return window.localStorage.getItem(key); } catch { return null; }
  },
  set(key: string, value: string) {
    try { window.localStorage.setItem(key, value); } catch { /* storage unavailable */ }
  },
  remove(key: string) {
    try { window.localStorage.removeItem(key); } catch { /* storage unavailable */ }
  },
  getJSON<T>(key: string, fallback: T): T {
    const raw = storage.get(key);
    if (!raw) return fallback;
    try { return JSON.parse(raw) as T; } catch { return fallback; }
  },
  setJSON(key: string, value: unknown) { storage.set(key, JSON.stringify(value)); },
};

export const session = {
  token: () => storage.get(TOKEN_KEY),
  user: <T,>() => storage.getJSON<T | null>(USER_KEY, null),
  save(token: string, user: unknown) { storage.set(TOKEN_KEY, token); storage.setJSON(USER_KEY, user); },
  clear() { storage.remove(TOKEN_KEY); storage.remove(USER_KEY); },
};

type Opts = { method?: string; body?: unknown; form?: FormData; raw?: boolean; signal?: AbortSignal };

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = session.token();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: opts.method || (body ? "POST" : "GET"), headers, body, signal: opts.signal });
  } catch {
    throw new ApiError(0, `Cannot reach the MyKshema API at ${API_URL}. Is the backend running?`);
  }
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/demo-login")) {
    session.clear();
    if (!window.location.pathname.startsWith("/login")) window.location.href = "/login?expired=1";
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    let details;
    try {
      const j = await res.json();
      message = j?.error?.message || j?.detail || message;
      details = j?.error?.details;
    } catch { /* non-JSON */ }
    throw new ApiError(res.status, String(message), details);
  }
  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Fetch a private document with the bearer token and return an object URL. */
export async function fileObjectUrl(docId: string, download = false): Promise<string> {
  const res = await api<Response>(`/api/documents/${docId}/file${download ? "?download=true" : ""}`, { raw: true });
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export function qs(params: Record<string, string | number | undefined | null | false>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "" && v !== false) p.set(k, String(v)); });
  const s = p.toString();
  return s ? `?${s}` : "";
}
