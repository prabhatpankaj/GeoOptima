import "../styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Leaplat | Open Maps",
  description: "Free and open-source mapping with Leaflet + Next.js",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
