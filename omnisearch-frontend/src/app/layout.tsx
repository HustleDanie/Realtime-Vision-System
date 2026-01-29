import type { Metadata } from "next";
import "./globals.css";
import { DashboardLayout } from "@/components/layout";

export const metadata: Metadata = {
  title: "Realtime Vision System - AI Monitoring Dashboard",
  description: "Monitor AI-powered visual inspection system with real-time defect detection and analytics",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <DashboardLayout>{children}</DashboardLayout>
      </body>
    </html>
  );
}
