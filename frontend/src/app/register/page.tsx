"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import { useTheme } from "@/lib/useTheme";

export default function RegisterPage() {
  const router = useRouter();
  const setUser = useChatStore((s) => s.setUser);
  const { dark, toggle } = useTheme();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (password !== password2) {
      setError("Пароли не совпадают");
      setLoading(false);
      return;
    }

    try {
      const data = await apiFetch<{ id: number; username: string; email: string; avatar: string | null; status: string; birth_date?: string | null }>(
        "/auth/register/",
        {
          method: "POST",
          body: JSON.stringify({
            username,
            email,
            password,
            password2,
            birth_date: birthDate || undefined,
          }),
        }
      );
      setUser({
        id: data.id,
        username: data.username,
        email: data.email,
        avatar: data.avatar,
        status: data.status,
        birth_date: data.birth_date ?? null,
      });
      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка регистрации");
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
          <h1 className="text-2xl font-bold">Присоединяйся к JOIN WORK!</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Регистрация нового участника
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
            type="email"
            placeholder="Email (необязательно)"
            className="input-base"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <input
              type="date"
              aria-label="Дата рождения"
              className="input-base flex-1"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
            />
            <span className="whitespace-nowrap text-xs text-[var(--text-muted)]">дата рождения</span>
          </div>
          <input
            type="password"
            placeholder="Пароль"
            className="input-base"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Повторите пароль"
            className="input-base"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            required
          />

          {error && (
            <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-950/50 dark:text-red-400">
              {error}
            </div>
          )}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? <Loader2 className="mx-auto animate-spin" size={20} /> : "Создать аккаунт"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="font-medium text-[var(--brand-primary)] hover:underline">
            Войти
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
