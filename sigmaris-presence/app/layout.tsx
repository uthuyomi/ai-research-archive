// app/layout.tsx
import "../styles/globals.css";
import { Inter } from "next/font/google";
import Nav from "./components/Nav";
import Footer from "./components/Footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Sigmaris Presence Project",
  description:
    "AI Personas × Robotics — Building the first presence-based AI interface.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="bg-black">
      <body
        className={`${inter.className} bg-[#050508] text-zinc-100 min-h-screen flex flex-col`}
      >
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
