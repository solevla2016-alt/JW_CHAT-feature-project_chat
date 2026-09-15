const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/ws/chat";

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

export async function uploadAvatar<T>(file: File): Promise<T> {
  const form = new FormData();
  form.append("avatar", file);
  const res = await fetch(`${API_BASE}/auth/avatar/`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.error ?? error.message ?? "Ошибка загрузки аватара");
  }
  return res.json();
}

export async function joinServer<T>(token: string): Promise<T> {
  return apiFetch<T>(`/chat/servers/join/${token}/`, { method: "POST" });
}

export async function getServerInvite<T>(serverId: number): Promise<T> {
  return apiFetch<T>(`/chat/servers/${serverId}/invite/`);
}

const apiOrigin = new URL(API_URL).origin;
const MEDIA_BASE = apiOrigin;

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${MEDIA_BASE}${path}`;
}

export async function deleteMessageApi(roomId: number, messageId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/rooms/${roomId}/messages/${messageId}/`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.error ?? error.message ?? "Ошибка удаления сообщения");
  }
}

export async function getRoomBans<T>(roomId: number): Promise<T> {
  return apiFetch<T>(`/chat/rooms/${roomId}/bans/`);
}

export async function banUserApi<T>(roomId: number, username: string, reason = ""): Promise<T> {
  return apiFetch<T>(`/chat/rooms/${roomId}/bans/`, {
    method: "POST",
    body: JSON.stringify({ username, reason }),
  });
}

export async function unbanUserApi<T>(roomId: number, userId: number): Promise<T> {
  return apiFetch<T>(`/chat/rooms/${roomId}/bans/${userId}/`, { method: "DELETE" });
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