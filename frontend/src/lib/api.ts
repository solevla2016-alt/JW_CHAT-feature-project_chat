const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.error ?? error.message ?? "Ошибка запроса");
  }

  return res.json();
}

export async function uploadFile<T>(
  path: string,
  file: File,
  extra?: Record<string, string>
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  if (extra) {
    Object.entries(extra).forEach(([k, v]) => form.append(k, v));
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.error ?? error.message ?? "Ошибка загрузки");
  }
  return res.json();
}

const MEDIA_BASE = "http://localhost:8000";

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${MEDIA_BASE}${path}`;
}

export async function searchMessages<T>(roomId: number, q: string): Promise<T> {
  const res = await fetch(
    `${API_BASE}/chat/rooms/${roomId}/search/?q=${encodeURIComponent(q)}`,
    { credentials: "include" }
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.error ?? error.message ?? "Ошибка поиска");
  }
  return res.json();
}