import type { Metadata } from "next";
import { Geist, Geist_Mono, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "./markdown-styles.css";
import { ConciliacionProvider } from "@/contexts/ConciliacionContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sistema de Conciliación Bancaria",
  description: "Sistema avanzado de conciliación bancaria con OCR para estados de cuenta",
  icons: {
    icon: [
      {
        url: '/favicon.png?v=5',
        type: 'image/png',
        sizes: '32x32',
      }
    ],
    shortcut: '/favicon.png?v=5',
    apple: '/favicon.png?v=5',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" type="image/png" href="/favicon.png?v=5" />
        <link rel="shortcut icon" type="image/png" href="/favicon.png?v=5" />
        <link rel="apple-touch-icon" href="/favicon.png?v=5" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${jetbrainsMono.variable} antialiased`}
        suppressHydrationWarning={true}
      >
        <ConciliacionProvider>
          {children}
        </ConciliacionProvider>
      </body>
    </html>
  );
}
