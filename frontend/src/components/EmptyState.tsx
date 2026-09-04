"use client";

import { motion } from "framer-motion";
import { MessageSquareText, Menu } from "lucide-react";

export function EmptyState({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-6 text-center">
      <button
        onClick={onOpenSidebar}
        className="mb-6 rounded-xl border border-[var(--border-color)] p-3 text-[var(--text-secondary)] md:hidden"
      >
        <Menu size={20} />
      </button>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-[var(--brand-light)] text-[var(--brand-primary)]"
      >
        <MessageSquareText size={30} />
      </motion.div>
      <h2 className="text-xl font-semibold">Выберите комнату</h2>
      <p className="mt-2 max-w-sm text-sm text-[var(--text-secondary)]">
        Выберите чат слева или создайте новую комнату, чтобы начать общение с командой JOIN WORK!
      </p>
    </div>
  );
}
