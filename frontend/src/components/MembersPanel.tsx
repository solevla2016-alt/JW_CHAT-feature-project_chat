"use client";

import { X, Crown } from "lucide-react";
import { useChatStore } from "@/lib/store";
import { mediaUrl } from "@/lib/api";

export function MembersPanel({ onClose }: { onClose: () => void }) {
  const activeRoom = useChatStore((s) => s.activeRoom);
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  const user = useChatStore((s) => s.user);

  if (!activeRoom) return null;

  const members = activeRoom.members ?? [];
  // сортировка: сначала онлайн, потом остальные
  const sorted = [...members].sort((a, b) => {
    const aOnline = onlineUsers.includes(a.username) ? 0 : 1;
    const bOnline = onlineUsers.includes(b.username) ? 0 : 1;
    return aOnline - bOnline;
  });

  const onlineCount = members.filter((m) => onlineUsers.includes(m.username)).length;

  return (
    <div className="flex h-full w-64 flex-col border-l border-[var(--border-color)] bg-[var(--bg-primary)]">
      <div className="flex items-center justify-between px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold">Участники</h3>
          <p className="text-xs text-[var(--text-secondary)]">
            {onlineCount} в сети / {members.length} всего
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
          aria-label="Закрыть"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-3">
        {sorted.map((m) => {
          const isOnline = onlineUsers.includes(m.username);
          const isOwner = m.username === activeRoom.owner;
          const isSelf = m.username === user?.username;
          return (
            <div
              key={m.id}
              className="flex items-center gap-3 rounded-xl px-3 py-2 transition-colors hover:bg-[var(--bg-secondary)]"
            >
              <div className="relative shrink-0">
                {m.avatar ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaUrl(m.avatar)}
                    alt={m.username}
                    className="h-9 w-9 rounded-full object-cover"
                  />
                ) : (
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-bold text-white">
                    {m.username.slice(0, 2).toUpperCase()}
                  </div>
                )}
                <span
                  className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[var(--bg-primary)] ${
                    isOnline ? "bg-emerald-500" : "bg-gray-400"
                  }`}
                />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 truncate text-sm font-medium">
                  {m.username}
                  {isSelf && <span className="text-xs text-[var(--text-muted)]">(вы)</span>}
                </div>
                <div className="truncate text-xs text-[var(--text-secondary)]">
                  {isOnline ? (
                    <span className="text-emerald-500">в сети</span>
                  ) : (
                    "не в сети"
                  )}
                </div>
              </div>
              {isOwner && (
                <span title="Владелец">
                  <Crown size={14} className="shrink-0 text-amber-500" />
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
