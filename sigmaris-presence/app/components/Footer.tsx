"use client";

import Container from "./Container";
import { useLang } from "@/store/useLang";
import { translations } from "@/lib/i18n";

export default function Footer() {
  const lang = useLang((s) => s.lang);
  const t = translations[lang].footer;

  return (
    <footer className="border-t border-zinc-900 bg-black">
      <Container className="py-4 text-center text-[11px] text-zinc-500">
        {t.line}
      </Container>
    </footer>
  );
}
