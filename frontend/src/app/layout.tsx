import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "MyKshema – Your Health. Your History. Your Well-being.",
  description: "AI-powered personal health intelligence. Hackathon prototype with synthetic data only.",
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = { themeColor: "#0F2344", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
