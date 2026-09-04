"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import { useChatStore } from "@/lib/store";
import { useWebSocket } from "@/lib/useWebSocket";
import { API_URL } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { EmptyState } from "./EmptyState";

export function ChatWindow() {
  const { activeRoom, messages, setSidebarOpen } = useChatStore();
  const { sendMessage, startTyping, editMessage, toggleReaction, sendAiRequest, togglePin, sendRead } = useWebSocket(activeRoom?.name ?? null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const resetRoomUnread = useChatStore((s) => s.resetRoomUnread);
  const [replyTarget, setReplyTarget] = useState<{ id: number; username: string; text: string } | null>(null);
  const [editingTarget, setEditingTarget] = useState<{ id: number; text: string } | null>(null);
  const typingUsers = useChatStore((s) => s.typingUsers);
  const aiTyping = useChatStore((s) => s.aiTyping);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{ id: number; username: string; message: string; created_at: string }>>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const messageRefs = useRef<Map<number, HTMLDivElement>>(new Map);

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
    if (!activeRoom) return;
    resetRoomUnread(activeRoom.id);
    if (messages.length > 0) {
      const lastId = messages[messages.length - 1].id;
      sendRead(lastId);
    }
  }, [activeRoom?.id, messages.length, activeRoom, resetRoomUnread, sendRead]);

  if (!activeRoom) {
    return <EmptyState onOpenSidebar={() => setSidebarOpen(true)} />;
  }

  return (
    <div className="flex h-full flex-col">
      <ChatHeader
        roomName={activeRoom.name}
        onOpenSidebar={() => setSidebarOpen(true)}
        onToggleSearch={() => setSearchOpen((v) => !v)}
        searchOpen={searchOpen}
      />

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
  );
}

export function ChatHeader({
  roomName,
  onOpenSidebar,
  onToggleSearch,
  searchOpen,
}: {
  roomName: string;
  onOpenSidebar: () => void;
  onToggleSearch: () => void;
  searchOpen: boolean;
}) {
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  return (
    <div className="flex items-center justify-between border-b border-[var(--border-color)] px-4 py-3 md:px-6">
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
            <span className="text-brand-600 dark:text-brand-400">#</span> {roomName}
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            {onlineUsers.length} в сети
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
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
        <div className="flex -space-x-2">
          {onlineUsers.slice(0, 5).map((u) => (
            <div
              key={u}
              className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-[var(--bg-primary)] bg-[var(--brand-primary)] text-[10px] font-bold text-white"
            >
              {u.slice(0, 2).toUpperCase()}
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
