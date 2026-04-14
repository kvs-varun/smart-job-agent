import type { Metadata } from "next";
import { Geist_Mono, Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

import { Navbar } from "@/components/layout/Navbar";
import { PageTransition } from "@/components/layout/PageTransition";
import { Toaster } from "sonner";
import { headers } from "next/headers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Smart Job Agent",
  description: "AI-powered ATS resume builder + job intelligence for Indian freshers.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const hdrs = await headers();
  const pathname = hdrs.get("x-nextjs-pathname") || "";
  const isBuilder = pathname.startsWith("/builder");

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${plusJakarta.variable} ${geistMono.variable} bg-bg text-text-primary`}>
        <Navbar />
        {isBuilder ? (
          <div className="pt-16">
            <PageTransition>
              <main>{children}</main>
            </PageTransition>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-7xl px-6 pt-16">
            <PageTransition>
              <main className="py-6">{children}</main>
            </PageTransition>
          </div>
        )}
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text-primary)",
            },
          }}
        />
      </body>
    </html>
  );
}
