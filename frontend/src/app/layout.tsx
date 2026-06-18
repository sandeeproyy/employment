import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "employment — Autonomous Job Application Agent",
  description:
    "24/7 job discovery, AI-powered resume tailoring, and automated applications — all under your control.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
