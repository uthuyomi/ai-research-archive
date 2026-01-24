"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Container from "./Container";
import { useLang } from "@/store/useLang";
import { translations } from "@/lib/i18n";

export default function Nav() {
  const pathname = usePathname();
  const lang = useLang((s) => s.lang);
  const toggle = useLang((s) => s.toggle);

  const t = translations[lang].nav;

  const links = [
    { href: "/", label: t.home },
    { href: "/about", label: t.about },
    { href: "/roadmap", label: t.roadmap },
    { href: "/donate", label: t.support },
  ];

  return (
    <header className="border-b border-zinc-800/80 bg-black/60 backdrop-blur">
      <Container className="flex items-center justify-between py-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-cyan-400/80 shadow-[0_0_25px_rgba(34,211,238,0.7)]" />
          <span className="text-sm font-semibold tracking-[0.25em] uppercase text-zinc-300">
            Sigmaris Presence
          </span>
        </Link>

        {/* Nav + Lang toggle */}
        <nav className="flex items-center gap-6 text-sm">
          {links.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={
                  "transition-colors " +
                  (active
                    ? "text-cyan-300"
                    : "text-zinc-400 hover:text-zinc-100")
                }
              >
                {link.label}
              </Link>
            );
          })}

          <button
            onClick={toggle}
            className="ml-2 rounded-full border border-zinc-700 px-3 py-1 text-xs text-zinc-300 hover:border-cyan-400 hover:text-cyan-300 transition-colors"
          >
            {t.toggle}
          </button>
        </nav>
      </Container>
    </header>
  );
}
