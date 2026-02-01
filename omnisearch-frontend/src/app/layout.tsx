import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

export const metadata: Metadata = {
  title: "Vision Inspector | AI-Powered Defect Detection",
  description: "Upload or capture images for real-time AI defect detection and inspection",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased font-mono">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          {/* Mobile blocker - hidden on desktop (md and above) */}
          <div className="md:hidden fixed inset-0 z-50 bg-white dark:bg-gray-950 flex items-center justify-center p-8">
            <div className="text-center">
              <div className="text-4xl mb-4">🖥️</div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Desktop Only</h1>
              <p className="text-gray-600 dark:text-gray-400">
                This application is designed for desktop use only. Please access it from a computer.
              </p>
            </div>
          </div>
          {/* Main content - hidden on mobile */}
          <div className="hidden md:block">
            {children}
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
