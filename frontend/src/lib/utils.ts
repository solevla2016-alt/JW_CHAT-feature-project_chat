import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  const timeStr = date.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (diffDays === 0) return timeStr;
  if (diffDays === 1) return `Вчера, ${timeStr}`;
  if (diffDays < 7) {
    const dayNames = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
    return `${dayNames[date.getDay()]}, ${timeStr}`;
  }
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
  }) + `, ${timeStr}`;
}

export function getInitials(username: string): string {
  return username.slice(0, 2).toUpperCase();
}

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
