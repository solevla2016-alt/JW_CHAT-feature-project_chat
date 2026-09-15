"use client";

import { create } from "zustand";
import type { ChatRoom, ChatRoomMember, Message, OnlineUser, ReactionItem, Server, User, TypingUser } from "./types";

interface ChatState {
  user: User | null;
  rooms: ChatRoom[];
  servers: Server[];
  activeServer: Server | null;
  activeRoom: ChatRoom | null;
  messages: Message[];
  onlineUsers: OnlineUser[];
  typingUsers: TypingUser[];
  sidebarOpen: boolean;
  aiTyping: boolean;
  screenSession: ScreenSession | null;

  setUser: (user: User | null) => void;
  setRooms: (rooms: ChatRoom[]) => void;
  setServers: (servers: Server[]) => void;
  setActiveServer: (server: Server | null) => void;
  setActiveRoom: (room: ChatRoom | null) => void;
  setRoomMembers: (roomId: number, members: ChatRoomMember[]) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  removeMessage: (id: number) => void;
  updateMessage: (id: number, text: string, updatedAt: string) => void;
  setMessageReactions: (id: number, reactions: ReactionItem[]) => void;
  setOnlineUsers: (users: OnlineUser[]) => void;
  setTypingUsers: (users: TypingUser[]) => void;
  addTypingUser: (username: string) => void;
  removeTypingUser: (username: string) => void;
  setAiTyping: (typing: boolean) => void;
  setMessagePinned: (id: number, pinned: boolean) => void;
  setMessageTranscription: (id: number, transcription: string) => void;
  resetRoomUnread: (roomId: number) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setScreenSession: (session: ScreenSession | null) => void;
}

export interface ScreenSession {
  roomId: number;
  broadcaster: string;
}

export const useChatStore = create<ChatState>((set) => ({
  user: null,
  rooms: [],
  servers: [],
  activeServer: null,
  activeRoom: null,
  messages: [],
  onlineUsers: [],
  typingUsers: [],
  sidebarOpen: true,
  aiTyping: false,
  screenSession: null,

  setUser: (user) => set({ user }),
  setRooms: (rooms) => set({ rooms }),
  setServers: (servers) => set({ servers }),
  setActiveServer: (server) => set({ activeServer: server, activeRoom: null, messages: [] }),
  setActiveRoom: (room) => set({ activeRoom: room, messages: [], typingUsers: [], screenSession: null }),
  setRoomMembers: (roomId, members) =>
    set((state) => ({
      rooms: state.rooms.map((r) => (r.id === roomId ? { ...r, members } : r)),
      activeRoom:
        state.activeRoom?.id === roomId ? { ...state.activeRoom, members } : state.activeRoom,
    })),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({
      messages: state.messages.some((m) => m.id === message.id)
        ? state.messages
        : [...state.messages, message],
    })),
  removeMessage: (id) =>
    set((state) => ({
      messages: state.messages.filter((m) => m.id !== id),
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
  setScreenSession: (session) => set({ screenSession: session }),
}));
