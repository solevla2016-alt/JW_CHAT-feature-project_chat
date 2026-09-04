import type { Metadata } from "next";
import "./globals.css";

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
      <body className="h-screen overflow-hidden">
        {children}
      </body>
    </html>
  );
}
