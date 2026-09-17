"use client";

import { useCallback, useEffect, useState } from "react";
import { Ban, Crown, Phone, Shield, ShieldBan, Unlock, Video, X } from "lucide-react";
import { useChatStore } from "@/lib/store";
import { banUserApi, getRoomBans, mediaUrl, setRoleApi, unbanUserApi } from "@/lib/api";
import { startCall } from "@/lib/calls";
import type { CallMode, RoomBan } from "@/lib/types";

export function MembersPanel({ onClose }: { onClose: () => void }) {
  const activeRoom = useChatStore((s) => s.activeRoom);
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  const user = useChatStore((s) => s.user);
  const setRoomMembers = useChatStore((s) => s.setRoomMembers);
  const setCall = useChatStore((s) => s.setCall);
  const setCallLocalStream = useChatStore((s) => s.setCallLocalStream);
  const [bans, setBans] = useState<RoomBan[]>([]);
  const [loading, setLoading] = useState(false);

  const canModerate =
    !!activeRoom &&
    !!user &&
    (user.role === "admin" ||
      user.role === "moderator" ||
      activeRoom.owner === user.username);

  const canManageRoles = !!user && (user.is_staff || user.role === "admin");

  const refreshBans = useCallback(async () => {
    if (!activeRoom) return;
    try {
      setBans(await getRoomBans<RoomBan[]>(activeRoom.id));
    } catch {
      // ignore
    }
  }, [activeRoom]);

  useEffect(() => {
    void refreshBans();
  }, [refreshBans]);

  if (!activeRoom) return null;

  const members = activeRoom.members ?? [];
  // сортировка: сначала онлайн, потом остальные
  const sorted = [...members].sort((a, b) => {
    const aOnline = onlineUsers.some((u) => u.username === a.username) ? 0 : 1;
    const bOnline = onlineUsers.some((u) => u.username === b.username) ? 0 : 1;
    return aOnline - bOnline;
  });

  const onlineCount = members.filter((m) => onlineUsers.some((u) => u.username === m.username)).length;

  const handleStartMemberCall = useCallback(
    async (username: string, mode: CallMode) => {
      if (!user) return;
      const res = await startCall(username, mode, user.username);
      if (res) {
        setCallLocalStream(res.stream);
        setCall({
          id: res.callId,
          peer: username,
          mode,
          direction: "outgoing",
          phase: "calling",
        });
      }
    },
    [user, setCall, setCallLocalStream]
  );

  const handleBan = async (username: string) => {
    if (!activeRoom || !window.confirm(`Заблокировать ${username} в этой комнате?`)) return;
    setLoading(true);
    try {
      await banUserApi(activeRoom.id, username);
      setRoomMembers(
        activeRoom.id,
        members.filter((m) => m.username !== username)
      );
      await refreshBans();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Не удалось заблокировать пользователя");
    } finally {
      setLoading(false);
    }
  };

  const handlePromote = async (username: string) => {
    if (!activeRoom || !window.confirm(`Назначить ${username} модератором?`)) return;
    setLoading(true);
    try {
      await setRoleApi<{ username: string }>(username, "moderator");
      setRoomMembers(
        activeRoom.id,
        members.map((m) => (m.username === username ? { ...m, role: "moderator" } : m))
      );
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Не удалось назначить модератора");
    } finally {
      setLoading(false);
    }
  };

  const handleUnban = async (ban: RoomBan) => {
    if (!activeRoom) return;
    setLoading(true);
    try {
      await unbanUserApi(activeRoom.id, ban.user_id);
      await refreshBans();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Не удалось разблокировать пользователя");
    } finally {
      setLoading(false);
    }
  };

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
          const isOnline = onlineUsers.some((u) => u.username === m.username);
          const isOwner = m.username === activeRoom.owner;
          const isSelf = m.username === user?.username;
          return (
            <div
              key={m.id}
              className="flex items-center gap-3 rounded-xl px-3 py-2 transition-colors hover:bg-[var(--bg-secondary)]"
            >
              <div className="relative shrink-0">
                {m.avatar ? (
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
                <div className="flex items-center gap-1.5 truncate text-xs text-[var(--text-secondary)]">
                  {m.role && m.role !== "member" && (
                    <span className="rounded bg-[var(--bg-tertiary)] px-1 py-0.5 text-[10px] uppercase tracking-wide">
                      {m.role === "admin" ? "Админ" : "Модератор"}
                    </span>
                  )}
                  {isOnline ? (
                    <span className="text-emerald-500">в сети</span>
                  ) : (
                    "не в сети"
                  )}
                </div>
              </div>
              {isOnline && !isSelf && (
                <button
                  onClick={() => handleStartMemberCall(m.username, "audio")}
                  disabled={loading}
                  className="rounded p-1 text-[var(--text-muted)] hover:text-emerald-500 disabled:opacity-50"
                  title={`Позвонить ${m.username}`}
                >
                  <Phone size={14} />
                </button>
              )}
              {isOnline && !isSelf && (
                <button
                  onClick={() => handleStartMemberCall(m.username, "video")}
                  disabled={loading}
                  className="rounded p-1 text-[var(--text-muted)] hover:text-brand-400 disabled:opacity-50"
                  title={`Видеозвонок ${m.username}`}
                >
                  <Video size={14} />
                </button>
              )}
              {canManageRoles && !isSelf && m.role !== "moderator" && m.role !== "admin" && (
                <button
                  onClick={() => handlePromote(m.username)}
                  disabled={loading}
                  className="rounded p-1 text-[var(--text-muted)] hover:text-amber-500 disabled:opacity-50"
                  title={`Назначить ${m.username} модератором`}
                >
                  <Shield size={14} />
                </button>
              )}
              {isOwner ? (
                <span title="Владелец">
                  <Crown size={14} className="shrink-0 text-amber-500" />
                </span>
              ) : (
                canModerate &&
                !isSelf && (
                  <button
                    onClick={() => handleBan(m.username)}
                    disabled={loading}
                    className="rounded p-1 text-[var(--text-muted)] hover:text-red-500 disabled:opacity-50"
                    title="Заблокировать"
                  >
                    <Ban size={14} />
                  </button>
                )
              )}
            </div>
          );
        })}

        {canModerate && bans.length > 0 && (
          <div className="mt-3 border-t border-[var(--border-color)] pt-2">
            <div className="flex items-center gap-1.5 px-2 pb-1 text-xs font-semibold text-[var(--text-secondary)]">
              <ShieldBan size={12} /> Блокировки
            </div>
            {bans.map((b) => (
              <div
                key={b.user_id}
                className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm hover:bg-[var(--bg-secondary)]"
              >
                <div className="min-w-0 flex-1 truncate">
                  <span className="font-medium">{b.username}</span>
                  {b.reason && (
                    <span className="ml-1 text-xs text-[var(--text-muted)]">— {b.reason}</span>
                  )}
                </div>
                <button
                  onClick={() => handleUnban(b)}
                  disabled={loading}
                  className="rounded p-1 text-[var(--text-muted)] hover:text-emerald-500 disabled:opacity-50"
                  title="Разблокировать"
                >
                  <Unlock size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}