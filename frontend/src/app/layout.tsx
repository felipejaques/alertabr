import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AlertaBR - Prevenção a Desastres",
  description:
    "Plataforma de monitoramento e alerta de riscos climáticos no Brasil",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
