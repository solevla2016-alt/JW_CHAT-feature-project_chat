"use client";

import { useCallback, useEffect, useRef } from "react";
import { useChatStore } from "./store";
import { WS_URL } from "./api";
import type { Message, WebSocketMessage } from "./types";

const WS_BASE = WS_URL;

export function useWebSocket(roomName: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttempts = useRef(0);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const isTypingRef = useRef(false);

  const {
    addMessage,
    updateMessage,
    setMessages,
    setOnlineUsers,
    addTypingUser,
    removeTypingUser,
    setMessageReactions,
    setAiTyping,
    setMessagePinned,
  } = useChatStore();

  const connect = useCallback(() => {
    if (!roomName) return;

    const ws = new WebSocket(`${WS_BASE}/${roomName}/`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.type) {
        case "history":
          if (data.messages) {
            setMessages(data.messages);
          }
          break;

        case "message":
          if (data.id && data.username && data.created_at) {
            const msg: Message = {
              id: data.id,
              username: data.username,
              avatar: data.avatar ?? null,
              message: data.message ?? "",
              created_at: data.created_at,
              is_edited: data.is_edited ?? false,
              reply_to: data.reply_to ?? null,
              reactions: data.reactions ?? [],
              attachment_type: data.attachment_type ?? "none",
              attachment_url: data.attachment_url ?? null,
              attachment_name: data.attachment_name ?? "",
              duration: data.duration ?? null,
              is_ai: data.is_ai ?? false,
              transcription: data.transcription ?? "",
            };
            addMessage(msg);
            removeTypingUser(data.username);
          }
          break;

        case "typing":
          if (data.username && data.is_typing !== undefined) {
            if (data.is_typing) {
              addTypingUser(data.username);
            } else {
              removeTypingUser(data.username);
            }
          }
          break;

        case "online_users":
          if (data.users) {
            setOnlineUsers(data.users);
          }
          break;

        case "message_edited":
          if (data.id && data.message && data.updated_at) {
            updateMessage(data.id, data.message, data.updated_at);
          }
          break;

        case "reaction":
          if (data.id && data.reactions) {
            setMessageReactions(data.id, data.reactions);
          }
          break;

        case "user_status":
          break;

        case "ai_typing":
          if (data.ai_typing !== undefined) {
            setAiTyping(data.ai_typing);
          }
          break;

        case "pinned":
          if (data.id && data.pinned !== undefined) {
            setMessagePinned(data.id, data.pinned);
          }
          break;

        case "error":
          console.error("WS error:", data.error);
          break;
      }
    };

    ws.onclose = () => {
      if (wsRef.current !== ws) return;
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
      reconnectAttempts.current += 1;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [roomName, addMessage, updateMessage, setMessages, setOnlineUsers, addTypingUser, removeTypingUser, setMessageReactions, setAiTyping]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((text: string, replyToId?: number, attachment?: { attachment_type: string; attachment_url: string; attachment_name: string; duration?: number | null }) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const payload: Record<string, unknown> = { action: "message", message: text };
    if (replyToId) payload.reply_to_id = replyToId;
    if (attachment) Object.assign(payload, attachment);
    wsRef.current.send(JSON.stringify(payload));
  }, []);

  const sendTyping = useCallback((isTyping: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: "typing", is_typing: isTyping }));
  }, []);

  const editMessage = useCallback((messageId: number, text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: "edit", message_id: messageId, text }));
  }, []);

  const toggleReaction = useCallback((messageId: number, emoji: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: "reaction", message_id: messageId, emoji }));
  }, []);

  const sendAiRequest = useCallback((prompt: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: "ai_request", prompt }));
  }, []);

  const togglePin = useCallback((messageId: number) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: "pin", message_id: messageId }));
  }, []);

  const sendRead = useCallback((lastMessageId: number) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: "read", last_message_id: lastMessageId }));
  }, []);

  const startTyping = useCallback(() => {
    if (!isTypingRef.current) {
      isTypingRef.current = true;
      sendTyping(true);
    }
    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      isTypingRef.current = false;
      sendTyping(false);
    }, 3000);
  }, [sendTyping]);

  return { sendMessage, startTyping, editMessage, toggleReaction, sendAiRequest, togglePin, sendRead };
}
