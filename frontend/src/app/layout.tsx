import type { Metadata } from "next";
import "./globals.css";
import { DevRedirect } from "@/components/DevRedirect";

export const metadata: Metadata = {
  title: "JOIN WORK! — Мессенджер",
  description: "Современный реально-временный чат для команды JOIN WORK!",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className="chat-app h-screen overflow-hidden">
        <DevRedirect />
        {children}
      </body>
    </html>
  );
}
