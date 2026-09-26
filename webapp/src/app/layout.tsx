import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gridlock",
  description: "DESC x Georgia Power planned construction coordination",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
