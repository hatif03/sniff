import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import SmoothScroll from "@/components/SmoothScroll";
import { cn } from "@/lib/utils";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sniff — AI Signup Experiments With Instant Team Alerts",
  description: "Persona-driven mobile/web signup experiments with diagnosis and instant team alerts.",
  openGraph: {
    title: "Sniff — AI Signup Experiments With Instant Team Alerts",
    description: "Persona-driven mobile/web signup experiments with diagnosis and instant team alerts.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn(spaceGrotesk.variable, inter.variable, jetbrainsMono.variable, "font-sans")}>
      <body>
        <SmoothScroll />
        {children}
      </body>
    </html>
  );
}
