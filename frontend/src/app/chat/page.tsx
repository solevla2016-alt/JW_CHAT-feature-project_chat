"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import type { ChatRoom, User } from "@/lib/types";
import { Sidebar } from "@/components/Sidebar";
import { ChatWindow } from "@/components/ChatWindow";

export default function ChatPage() {
  const router = useRouter();
  const {
    user,
    setUser,
    setRooms,
    activeRoom,
    setActiveRoom,
    sidebarOpen,
    setSidebarOpen,
  } = useChatStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const me = await apiFetch<User>("/auth/me/");
        setUser(me);
        const rooms = await apiFetch<ChatRoom[]>("/chat/rooms/");
        setRooms(rooms);
        if (rooms.length > 0 && !activeRoom) {
          setActiveRoom(rooms[0]);
        }
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="animate-spin text-[var(--brand-primary)]" size={40} />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex h-full w-full overflow-hidden">
      <motion.div
        initial={false}
        animate={{
          x: sidebarOpen ? 0 : "-100%",
        }}
        transition={{ duration: 0.2 }}
        className="absolute z-20 h-full w-full bg-white/95 backdrop-blur-lg dark:bg-slate-900/95 md:hidden"
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </motion.div>

      <aside className="hidden h-full w-80 shrink-0 md:block">
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </aside>

      <main className="relative flex flex-1 flex-col min-w-0">
        <ChatWindow />
      </main>
    </div>
  );
}
