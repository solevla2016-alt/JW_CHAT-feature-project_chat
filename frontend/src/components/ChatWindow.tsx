"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Maximize2, Menu, Minimize2, MonitorUp, MonitorStop, Phone, Users, Video, X } from "lucide-react";
import { useChatStore } from "@/lib/store";
import { useWebSocket } from "@/lib/useWebSocket";
import { API_URL, mediaUrl } from "@/lib/api";
import { useIsMobile } from "@/hooks/useIsMobile";
import {
  resetScreenShare,
  setScreenShareHandlers,
  startScreenShare,
  stopScreenShare,
} from "@/lib/screenShare";
import { resetCalls, setCallHandlers, startCall } from "@/lib/calls";
import type { CallMode } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { EmptyState } from "./EmptyState";
import { MembersPanel } from "./MembersPanel";
import { CallPanel } from "./CallPanel";

export function ChatWindow() {
  const { activeRoom, messages, setSidebarOpen } = useChatStore();
  const { sendMessage, startTyping, editMessage, deleteMessage, toggleReaction, sendAiRequest, togglePin, sendRead } = useWebSocket(activeRoom?.name ?? null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const resetRoomUnread = useChatStore((s) => s.resetRoomUnread);
  const call = useChatStore((s) => s.call);
  const setCall = useChatStore((s) => s.setCall);
  const setCallLocalStream = useChatStore((s) => s.setCallLocalStream);
  const setCallRemoteStream = useChatStore((s) => s.setCallRemoteStream);
  const [replyTarget, setReplyTarget] = useState<{ id: number; username: string; text: string } | null>(null);
  const [editingTarget, setEditingTarget] = useState<{ id: number; text: string } | null>(null);
  const typingUsers = useChatStore((s) => s.typingUsers);
  const aiTyping = useChatStore((s) => s.aiTyping);
  const [searchOpen, setSearchOpen] = useState(false);
  const [membersOpen, setMembersOpen] = useState<boolean>(() =>
    typeof window !== "undefined" ? window.innerWidth >= 1280 : false
  );
  const isMobile = useIsMobile();

  useEffect(() => {
    if (isMobile) {
      setMembersOpen(false);
    }
  }, [isMobile]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{ id: number; username: string; message: string; created_at: string }>>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const messageRefs = useRef<Map<number, HTMLDivElement>>(new Map);
  const user = useChatStore((s) => s.user);

  const [screenState, setScreenState] = useState<{ broadcaster: string; isMe: boolean } | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [startingShare, setStartingShare] = useState(false);

  useEffect(() => {
    setScreenShareHandlers({
      onSessionStart: (broadcaster) =>
        setScreenState({ broadcaster, isMe: broadcaster === user?.username }),
      onRemoteStream: (_username, stream) => {
        setRemoteStream((prev) => {
          if (prev && prev !== stream) prev.getTracks().forEach((t) => t.stop());
          return stream;
        });
      },
      onSessionEnd: () => {
        setScreenState(null);
        setRemoteStream((prev) => {
          prev?.getTracks().forEach((t) => t.stop());
          return null;
        });
      },
    });
    setCallHandlers({
      onPhase: (phase, endReason) => {
        const cur = useChatStore.getState().call;
        if (!cur) return;
        useChatStore.getState().setCall({ ...cur, phase, endReason });
        if (phase === "ended") {
          window.setTimeout(() => {
            const state = useChatStore.getState();
            const latest = state.call;
            if (latest?.phase === "ended") {
              state.callRemoteStream?.getTracks().forEach((t) => t.stop());
              state.setCallRemoteStream(null);
              state.setCallLocalStream(null);
              state.setCall(null);
            }
          }, 1800);
        }
      },
      onRemoteStream: (stream) => {
        const prev = useChatStore.getState().callRemoteStream;
        if (prev && prev !== stream) prev.getTracks().forEach((t) => t.stop());
        useChatStore.getState().setCallRemoteStream(stream);
      },
    });
  }, [user?.username]);

  const lastRoomId = useRef<number | null>(null);
  useEffect(() => {
    if (lastRoomId.current !== null && lastRoomId.current !== activeRoom?.id) {
      const state = useChatStore.getState();
      resetScreenShare();
      setScreenState(null);
      setRemoteStream((prev) => {
        prev?.getTracks().forEach((t) => t.stop());
        return null;
      });
      resetCalls();
      state.callRemoteStream?.getTracks().forEach((t) => t.stop());
      state.setCallRemoteStream(null);
      state.setCallLocalStream(null);
      state.setCall(null);
    }
    lastRoomId.current = activeRoom?.id ?? null;
  }, [activeRoom?.id]);

  useEffect(() => {
    return () => {
      resetScreenShare();
      resetCalls();
    };
  }, []);

  const handleStartScreenShare = useCallback(async () => {
    if (startingShare || !activeRoom || !user) return;
    setStartingShare(true);
    try {
      const [mic, display] = await Promise.all([
        navigator.mediaDevices.getUserMedia({ audio: true }),
        navigator.mediaDevices.getDisplayMedia({ video: true }),
      ]);
      const combined = new MediaStream();
      display.getVideoTracks().forEach((t) => combined.addTrack(t));
      mic.getAudioTracks().forEach((t) => combined.addTrack(t));

      setScreenState({ broadcaster: user.username, isMe: true });
      setRemoteStream(combined);
      await startScreenShare(combined, user.username);

      const shutdown = () => {
        display.getVideoTracks()[0]?.removeEventListener("ended", shutdown);
        stopScreenShare();
        setScreenState(null);
      };
      display.getVideoTracks()[0]?.addEventListener("ended", shutdown);
    } catch {
      // пользователь отменил выбор экрана или отказал в микрофоне
    } finally {
      setStartingShare(false);
    }
  }, [startingShare, activeRoom, user]);

  const handleStopScreenShare = useCallback(() => {
    stopScreenShare();
    setScreenState((s) => (s?.isMe ? null : s));
  }, []);;

  const directPeer = useMemo(() => {
    if (activeRoom?.room_type !== "direct") return null;
    const me = user?.username ?? "";
    const fromMembers = activeRoom.members?.find((m) => m.username !== me)?.username;
    if (fromMembers) return fromMembers;
    return activeRoom.name !== me ? activeRoom.name : null;
  }, [activeRoom, user]);

  const handleStartCall = useCallback(
    async (mode: CallMode) => {
      if (!directPeer || !user) return;
      const res = await startCall(directPeer, mode, user.username);
      if (res) {
        setCallLocalStream(res.stream);
        setCall({
          id: res.callId,
          peer: directPeer,
          mode,
          direction: "outgoing",
          phase: "calling",
        });
      }
    },
    [directPeer, user, setCall, setCallLocalStream]
  );

  const scrollToMessage = useCallback((id: number) => {
    const el = messageRefs.current.get(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("ring-2", "ring-[var(--brand-primary)]", "ring-offset-2");
      setTimeout(() => el.classList.remove("ring-2", "ring-[var(--brand-primary)]", "ring-offset-2"), 2000);
    }
  }, []);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() || !activeRoom) return;
    setSearchLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/chat/rooms/${activeRoom.id}/search/?q=${encodeURIComponent(searchQuery)}`,        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch {
      // silently ignore
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery, activeRoom]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length, activeRoom?.id]);

  useEffect(() => {
    if (!activeRoom || messages.length === 0) return;
    resetRoomUnread(activeRoom.id);
    const lastId = messages[messages.length - 1].id;
    sendRead(lastId);
  }, [activeRoom?.id, messages.length, activeRoom, resetRoomUnread, sendRead]);

  const meUsername = user?.username ?? "";
  const isModerator =
    user?.role === "moderator" || user?.role === "admin" || activeRoom?.owner === meUsername;
  const canDelete = (msg: (typeof messages)[number]) =>
    msg.username === meUsername || isModerator;

  if (!activeRoom) {
    return <EmptyState onOpenSidebar={() => setSidebarOpen(true)} />;
  }

  const canScreenShare =
    activeRoom.room_type === "group" || activeRoom.room_type === "channel";

  return (
    <div className="flex h-full min-w-0 flex-1">
      <div className="flex h-full min-w-0 flex-1 flex-col">
        <ChatHeader
          roomName={activeRoom.name}
          roomType={activeRoom.room_type}
          onOpenSidebar={() => setSidebarOpen(true)}
          onToggleSearch={() => setSearchOpen((v) => !v)}
          searchOpen={searchOpen}
          onToggleMembers={() => setMembersOpen((v) => !v)}
          membersOpen={membersOpen}
          canScreenShare={canScreenShare}
          screenShareActive={!!screenState}
          screenShareLoading={startingShare}
          onToggleScreenShare={screenState?.isMe ? handleStopScreenShare : handleStartScreenShare}
          showCallButtons={!!directPeer && !call}
          onCallAudio={() => void handleStartCall("audio")}
          onCallVideo={() => void handleStartCall("video")}
        />

        {screenState && (
          <ScreenShareBar
            broadcaster={screenState.broadcaster}
            isMe={screenState.isMe}
            stream={remoteStream}
            onStop={handleStopScreenShare}
          />
        )}

      {searchOpen && (
        <div className="border-b border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-3 md:px-6">
          <div className="flex gap-2">
            <input
              autoFocus
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Поиск сообщений..."
              className="flex-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)]"
            />
            <button
              onClick={handleSearch}
              disabled={searchLoading}
              className="rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {searchLoading ? "..." : "Найти"}
            </button>
          </div>
          {searchResults.length > 0 && (
            <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
              {searchResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => {
                    scrollToMessage(r.id);
                    setSearchOpen(false);
                    setSearchQuery("");
                    setSearchResults([]);
                  }}
                  className="flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-[var(--bg-tertiary)]"
                >
                  <span className="shrink-0 text-xs font-medium text-[var(--brand-primary)]">
                    {r.username}
                  </span>
                  <span className="min-w-0 truncate text-xs text-[var(--text-secondary)]">
                    {r.message.length > 80 ? r.message.slice(0, 80) + "..." : r.message}
                  </span>
                </button>
              ))}
            </div>
          )}
          {searchResults.length === 0 && !searchLoading && searchQuery && (
            <p className="mt-2 text-xs text-[var(--text-muted)]">Ничего не найдено</p>
          )}
        </div>
      )}

      <div
        ref={scrollRef}
        className="flex-1 space-y-1 overflow-y-auto scrollbar-thin px-4 py-4 md:px-6"
      >
        {messages.map((msg) => (
          <div key={msg.id} ref={(el) => { if (el) messageRefs.current.set(msg.id, el); }}>
            <MessageBubble
              message={msg}
              currentUser={useChatStore.getState().user?.username ?? ""}
              currentUserId={useChatStore.getState().user?.id}
              onReply={() =>
                setReplyTarget({ id: msg.id, username: msg.username, text: msg.message })
              }
              onEdit={() => setEditingTarget({ id: msg.id, text: msg.message })}
              onToggleReaction={(emoji) => toggleReaction(msg.id, emoji)}
              onTogglePin={() => togglePin(msg.id)}
              onDelete={canDelete(msg) ? () => deleteMessage(msg.id) : undefined}
            />
          </div>
        ))}
      </div>

      <div className="px-4 pb-2 md:px-6">
        <TypingIndicator users={typingUsers} />
        {aiTyping && <AiTypingIndicator />}
      </div>

      <ChatInput
        onSend={(text) => {
          sendMessage(text, replyTarget?.id);
          setReplyTarget(null);
        }}
        onSendWithAttachment={(text, attachment) => {
          sendMessage(text, replyTarget?.id, attachment);
          setReplyTarget(null);
        }}
        onSendAiRequest={(prompt) => {
          sendAiRequest(prompt);
        }}
        roomId={activeRoom.id}
        onTyping={startTyping}
        replyTarget={replyTarget}
        onCancelReply={() => setReplyTarget(null)}
        editingTarget={editingTarget}
        onCancelEdit={() => setEditingTarget(null)}
        onSaveEdit={(text) => {
          if (editingTarget) editMessage(editingTarget.id, text);
          setEditingTarget(null);
        }}
      />
        </div>

        {membersOpen && (
          <div className="hidden md:block">
            <MembersPanel onClose={() => setMembersOpen(false)} />
          </div>
        )}
        {membersOpen && (
          <div className="fixed inset-0 z-40 flex justify-end md:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setMembersOpen(false)} />
            <div className="relative z-10">
              <MembersPanel onClose={() => setMembersOpen(false)} />
            </div>
          </div>
        )}

        <CallPanel />
      </div>
  );
}

export function ChatHeader({
  roomName,
  roomType,
  onOpenSidebar,
  onToggleSearch,
  searchOpen,
  onToggleMembers,
  membersOpen,
  canScreenShare,
  screenShareActive,
  screenShareLoading,
  onToggleScreenShare,
  showCallButtons,
  onCallAudio,
  onCallVideo,
}: {
  roomName: string;
  roomType?: "group" | "channel" | "direct";
  onOpenSidebar: () => void;
  onToggleSearch: () => void;
  searchOpen: boolean;
  onToggleMembers: () => void;
  membersOpen: boolean;
  canScreenShare?: boolean;
  screenShareActive?: boolean;
  screenShareLoading?: boolean;
  onToggleScreenShare?: () => void;
  showCallButtons?: boolean;
  onCallAudio?: () => void;
  onCallVideo?: () => void;
}) {
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  const typeLabel =
    roomType === "direct"
      ? "Личный чат"
      : roomType === "channel"
        ? "Канал"
        : "Группа";
  return (
    <div className="flex items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-primary)]/80 px-4 py-3 backdrop-blur-md md:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] md:hidden"
          aria-label="Меню"
        >
          <Menu size={20} />
        </button>
        <div>
          <h2 className="text-base font-semibold">
            <span className="text-brand-600 dark:text-brand-400">
              {roomType === "channel" ? "#" : roomType === "direct" ? "@" : "#"}
            </span>{" "}
            {roomName}
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            {onlineUsers.length} в сети · {typeLabel}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {showCallButtons && onCallAudio && onCallVideo && (
          <>
            <button
              onClick={onCallAudio}
              className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-tertiary)]"
              title="Голосовой вызов"
            >
              <Phone size={18} />
            </button>
            <button
              onClick={onCallVideo}
              className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-tertiary)]"
              title="Видеозвонок"
            >
              <Video size={18} />
            </button>
          </>
        )}
        {canScreenShare && onToggleScreenShare && (
          <button
            onClick={onToggleScreenShare}
            disabled={screenShareLoading}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
              screenShareActive
                ? "bg-red-500 text-white hover:bg-red-600"
                : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
            }`}
            title={screenShareActive ? "Остановить показ экрана" : "Показать экран участникам"}
          >
            {screenShareActive ? <MonitorStop size={16} /> : <MonitorUp size={16} />}
            <span className="hidden sm:inline">
              {screenShareActive ? "Остановить" : "Экран"}
            </span>
          </button>
        )}
        <button
          onClick={onToggleMembers}
          className={`rounded-lg p-2 transition-colors ${
            membersOpen
              ? "bg-[var(--brand-primary)] text-white"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
          }`}
          title="Участники"
        >
          <Users size={18} />
        </button>
        <button
          onClick={onToggleSearch}
          className={`rounded-lg p-2 transition-colors ${
            searchOpen
              ? "bg-[var(--brand-primary)] text-white"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
          }`}
          title="Поиск"
        >
          🔍
        </button>
        <div className="hidden -space-x-2 md:flex">
          {onlineUsers.slice(0, 5).map((u) => (
            <div
              key={u.username}
              className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border-2 border-[var(--bg-primary)] bg-[var(--brand-primary)] text-[10px] font-bold text-white"
              title={u.username}
            >
              {u.avatar ? (
                <img src={mediaUrl(u.avatar)} alt={u.username} className="h-full w-full object-cover" />
              ) : (
                u.username.slice(0, 2).toUpperCase()
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AiTypingIndicator() {
  return (
    <div className="mt-2 flex items-center gap-2 text-xs text-[var(--text-secondary)]">
      <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-[var(--brand-primary)]" />
      AI думает...
    </div>
  );
}

function VideoSurface({
  stream,
  className,
  muted = false,
}: {
  stream: MediaStream;
  className: string;
  muted?: boolean;
}) {
  const ref = useRef<HTMLVideoElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (el) {
      el.srcObject = stream;
      void el.play().catch(() => {});
    }
    return () => {
      if (el) el.srcObject = null;
    };
  }, [stream]);
  return <video ref={ref} autoPlay playsInline muted={muted} className={className} />;
}

function ScreenShareBar({
  broadcaster,
  isMe,
  stream,
  onStop,
}: {
  broadcaster: string;
  isMe: boolean;
  stream: MediaStream | null;
  onStop: () => void;
}) {
  const videoWrapRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  const toggleFullscreen = useCallback(async () => {
    const el = videoWrapRef.current;
    if (!el) return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await el.requestFullscreen();
      }
    } catch {
      // fullscreen не поддерживается или заблокирован
    }
  }, []);

  return (
    <div className="border-b border-[var(--border-color)] bg-[var(--bg-secondary)]/90 backdrop-blur">
      <div className="mx-auto w-full max-w-7xl px-4 py-2 md:px-6">
<div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div
            ref={videoWrapRef}
            className="relative w-full overflow-hidden rounded-xl border border-[var(--border-color)] bg-black"
            style={{ minHeight: "30vh", height: "45vh", maxHeight: "70vh" }}
          >
            {stream ? (
              <VideoSurface stream={stream} muted={isMe} className="h-full w-full object-contain" />
            ) : (
              <div className="flex h-full w-full items-center justify-center gap-2 text-base text-white/70">
                <Loader2 className="animate-spin" size={24} />
                {isMe ? "Вы показываете экран..." : "Подключение к экрану..."}
              </div>
            )}
            <div className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-red-600 px-3 py-1 text-xs font-semibold text-white">
              <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
              LIVE
            </div>
            <button
              onClick={toggleFullscreen}
              className="absolute right-3 top-3 rounded-lg bg-black/60 p-2 text-white/90 backdrop-blur transition-colors hover:bg-black/80 hover:text-white"
              title={isFullscreen ? "Свернуть" : "Во весь экран"}
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
          </div>
          <div className="flex shrink-0 flex-col items-center gap-2">
            <span className="inline-flex items-center gap-2 text-sm font-medium text-[var(--text-secondary)]">
              <MonitorUp size={18} />
              {isMe ? "Вы" : broadcaster} {isMe ? "показываете" : "показывает"} экран
            </span>
            {isMe ? (
              <button
                onClick={onStop}
                className="rounded-lg bg-red-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-600"
              >
                <MonitorStop size={16} className="mr-1 inline" />
                Остановить
              </button>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-sm text-emerald-500">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                смотрите в реальном времени
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
