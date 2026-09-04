"use client";

import { create } from "zustand";
import type { ChatRoom, Message, ReactionItem, User, TypingUser } from "./types";

interface ChatState {
  user: User | null;
  rooms: ChatRoom[];
  activeRoom: ChatRoom | null;
  messages: Message[];
  onlineUsers: string[];
  typingUsers: TypingUser[];
  sidebarOpen: boolean;
  aiTyping: boolean;

  setUser: (user: User | null) => void;
  setRooms: (rooms: ChatRoom[]) => void;
  setActiveRoom: (room: ChatRoom | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: number, text: string, updatedAt: string) => void;
  setMessageReactions: (id: number, reactions: ReactionItem[]) => void;
  setOnlineUsers: (users: string[]) => void;
  setTypingUsers: (users: TypingUser[]) => void;
  addTypingUser: (username: string) => void;
  removeTypingUser: (username: string) => void;
  setAiTyping: (typing: boolean) => void;
  setMessagePinned: (id: number, pinned: boolean) => void;
  setMessageTranscription: (id: number, transcription: string) => void;
  resetRoomUnread: (roomId: number) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  user: null,
  rooms: [],
  activeRoom: null,
  messages: [],
  onlineUsers: [],
  typingUsers: [],
  sidebarOpen: true,
  aiTyping: false,

  setUser: (user) => set({ user }),
  setRooms: (rooms) => set({ rooms }),
  setActiveRoom: (room) => set({ activeRoom: room, messages: [], typingUsers: [] }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  updateMessage: (id, text, updatedAt) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, message: text, is_edited: true, created_at: updatedAt } : m
      ),
    })),
  setMessageReactions: (id, reactions) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, reactions } : m
      ),
    })),
  setOnlineUsers: (users) => set({ onlineUsers: users }),
  setTypingUsers: (users) => set({ typingUsers: users }),
  addTypingUser: (username) =>
    set((state) => {
      const exists = state.typingUsers.find((t) => t.username === username);
      if (exists) return state;
      const timeout = setTimeout(() => {
        set((s) => ({
          typingUsers: s.typingUsers.filter((t) => t.username !== username),
        }));
      }, 4000);
      return { typingUsers: [...state.typingUsers, { username, timeout }] };
    }),
  removeTypingUser: (username) =>
    set((state) => {
      const user = state.typingUsers.find((t) => t.username === username);
      if (user) clearTimeout(user.timeout);
      return { typingUsers: state.typingUsers.filter((t) => t.username !== username) };
    }),
  setAiTyping: (typing) => set({ aiTyping: typing }),
  setMessagePinned: (id, pinned) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, pinned } : m
      ),
    })),
  resetRoomUnread: (roomId) =>
    set((state) => ({
      rooms: state.rooms.map((r) =>
        r.id === roomId ? { ...r, unread_count: 0 } : r
      ),
    })),
  setMessageTranscription: (id, transcription) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, transcription } : m
      ),
    })),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
