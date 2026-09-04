"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import { useTheme } from "@/lib/useTheme";
import { Moon, Sun } from "lucide-react";

export default function LOGINPage() {
  const router = useRouter();
  const setUser = useChatStore((s) => s.setUser);
  const { dark, toggle } = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await apiFetch<{ id: number; username: string; email: string; avatar: string | null; status: string }>(
        "/auth/login/",
        { method: "POST", body: JSON.stringify({ username, password }) }
      );
      setUser({ id: data.id, username: data.username, email: data.email, avatar: data.avatar, status: data.status });
      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-br from-brand-50 via-transparent to-brand-100/50 dark:from-brand-950 dark:to-transparent" />

      <button
        onClick={toggle}
        className="glass absolute right-6 top-6 rounded-full p-3 text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
        aria-label="Toggle theme"
      >
        {dark ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="glass-strong w-full max-w-md rounded-3xl p-8 shadow-lg"
      >
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl bg-white shadow-md">
            <img src="/logo.png" alt="JOIN WORK!" className="h-full w-full object-cover" />
          </div>
          <h1 className="text-2xl font-bold">JOIN WORK!</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Вход в мессенджер команды
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="text"
            placeholder="Имя пользователя"
            className="input-base"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
          <input
            type="password"
            placeholder="Пароль"
            className="input-base"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && (
            <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-950/50 dark:text-red-400">
              {error}
            </div>
          )}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? <Loader2 className="mx-auto animate-spin" size={20} /> : "Войти"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
          Нет аккаунта?{" "}
          <Link href="/register" className="font-medium text-[var(--brand-primary)] hover:underline">
            Зарегистрироваться
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
