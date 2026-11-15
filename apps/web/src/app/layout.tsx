import type { Metadata } from "next";
<<<<<<< HEAD
import { Shell } from "@/components/Shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "RIVET — Kuwari investigation",
  description: "Evidence-backed geospatial investigation workspace.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
=======
import { Geist, Geist_Mono } from "next/font/google";
import { Shell } from "@/components/Shell";
import { ReviewProvider } from "@/lib/review";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RIVET — Kuwari investigation",
  description: "Provisional evidence record for the historical Kuwari investigation. Not a confirmed water extent.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ReviewProvider>
          <Shell>{children}</Shell>
        </ReviewProvider>
>>>>>>> 61992b8d90d44ff0e2766cee552c1953f5b0a06a
      </body>
    </html>
  );
}
