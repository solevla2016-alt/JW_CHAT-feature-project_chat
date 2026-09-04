"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  LogOut,
  Plus,
  Search,
  Users,
  X,
  Loader2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import type { ChatRoom } from "@/lib/types";
import { cn, getInitials } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";

export function Sidebar({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { user, setUser, rooms, setRooms, activeRoom, setActiveRoom, onlineUsers, setSidebarOpen } =
    useChatStore();
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [roomName, setRoomName] = useState("");
  const [roomDesc, setRoomDesc] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState("");

  const filteredRooms = rooms.filter((r) =>
    r.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError("");
    try {
      const room = await apiFetch<ChatRoom>("/chat/rooms/create/", {
        method: "POST",
        body: JSON.stringify({
          name: roomName.trim(),
          description: roomDesc.trim(),
          is_private: isPrivate,
        }),
      });
      setRooms([room, ...rooms]);
      setActiveRoom(room);
      setShowCreate(false);
      setRoomName("");
      setRoomDesc("");
      setIsPrivate(false);
      setSidebarOpen(false);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Ошибка создания");
    } finally {
      setCreateLoading(false);
    }
  };

  const handleLogout = async () => {
    await apiFetch("/auth/logout/", { method: "POST" }).catch(() => {});
    setUser(null);
    router.push("/login");
  };

  return (
    <div className="flex h-full flex-col border-r border-[var(--border-color)] bg-[var(--bg-primary)]">
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand-primary)] text-sm font-bold text-white">
            {getInitials(user?.username ?? "JW")}
          </div>
          <div>
            <div className="text-sm font-semibold">JOIN WORK!</div>
            <div className="flex items-center gap-1 text-xs text-emerald-500">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              {user?.username}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] md:hidden"
            aria-label="Закрыть"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="px-4 pb-3">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
          />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск..."
            className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] py-2 pl-9 pr-3 text-sm placeholder-[var(--text-muted)] focus:border-[var(--brand-primary)] focus:outline-none"
          />
        </div>
      </div>

      <button
        onClick={() => setShowCreate((v) => !v)}
        className="mx-4 mb-2 flex items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] py-2.5 text-sm font-medium text-white transition-all hover:bg-[var(--brand-hover)] active:scale-[0.98]"
      >
        <Plus size={16} />
        Создать комнату
      </button>

      {showCreate && (
        <form onSubmit={handleCreateRoom} className="mx-4 mb-2 flex flex-col gap-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-3">
          <input
            value={roomName}
            onChange={(e) => setRoomName(e.target.value)}
            placeholder="Название комнаты"
            className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-sm focus:outline-none"
            required
            autoFocus
          />
          <input
            value={roomDesc}
            onChange={(e) => setRoomDesc(e.target.value)}
            placeholder="Описание"
            className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-sm focus:outline-none"
          />
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              className="accent-[var(--brand-primary)]"
            />
            Приватная
          </label>
          {createError && <span className="text-xs text-red-500">{createError}</span>}
          <button type="submit" className="btn-primary py-2 text-sm" disabled={createLoading}>
            {createLoading ? <Loader2 className="mx-auto animate-spin" size={16} /> : "Создать"}
          </button>
        </form>
      )}

      <div className="flex items-center gap-2 px-5 pb-2 pt-3 text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
        <Users size={14} />
        Комнаты ({onlineUsers.length} онлайн)
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-2">
        {filteredRooms.length === 0 && (
          <div className="px-3 py-8 text-center text-sm text-[var(--text-muted)]">
            {rooms.length === 0 ? "Комнаты пока пусты" : "Ничего не найдено"}
          </div>
        )}
        {filteredRooms.map((room) => (
          <button
            key={room.id}
            onClick={() => {
              setActiveRoom(room);
              setSidebarOpen(false);
            }}
            className={cn(
              "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
              activeRoom?.id === room.id
                ? "bg-[var(--brand-light)]"
                : "hover:bg-[var(--bg-secondary)]"
            )}
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-sm font-bold text-white">
              {getInitials(room.name)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{room.name}</div>
              <div className="truncate text-xs text-[var(--text-secondary)]">
                {room.last_message
                  ? `${room.last_message.username}: ${room.last_message.text}`
                  : room.description || "Нет сообщений"}
              </div>
            </div>
            {!!room.unread_count && (
              <span className="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-[var(--brand-primary)] px-1.5 text-[10px] font-bold text-white">
                {room.unread_count}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="border-t border-[var(--border-color)] p-4">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30"
        >
          <LogOut size={16} />
          Выйти
        </button>
      </div>
    </div>
  );
}
