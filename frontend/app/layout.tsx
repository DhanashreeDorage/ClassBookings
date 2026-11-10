import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Royaltica Publishing | Evening Class", description: "Book your daily Royaltica Publishing Masterclass from 5 PM to 10 PM IST." };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
