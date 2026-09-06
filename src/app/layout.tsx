import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Parallax | Bid intelligence",
  description: "Source-grounded PPP tender document intelligence.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en"><body>{children}</body></html>
  );
}
