"use client";

import Container from "../components/Container";
import { useLang } from "@/store/useLang";
import { translations } from "@/lib/i18n";

export default function AboutPage() {
  const lang = useLang((s) => s.lang);
  const t = translations[lang].about;

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      {/* HERO */}
      <section className="border-b border-zinc-900 bg-gradient-to-b from-black via-zinc-950 to-black">
        <Container className="py-16 sm:py-20">
          <div className="max-w-3xl space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-300">
              About
            </p>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              {t.title}
            </h1>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-[15px] whitespace-pre-line">
              {t.intro}
            </p>
          </div>
        </Container>
      </section>

      {/* STORY SECTION — full width reading block */}
      <section className="border-b border-zinc-900 bg-black">
        <Container className="py-14">
          <div className="max-w-3xl space-y-6">
            <h2 className="text-base font-semibold text-zinc-100">
              {t.storyTitle}
            </h2>
            <p className="text-[15px] leading-relaxed text-zinc-300 whitespace-pre-line">
              {t.storyBody}
            </p>
          </div>
        </Container>
      </section>

      {/* TECH + VISION — two-column at large screens */}
      <section className="bg-black border-b border-zinc-900">
        <Container className="py-14">
          <div className="grid gap-12 lg:grid-cols-2">
            {/* TECH */}
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-zinc-100">
                {t.techTitle}
              </h2>
              <p className="text-[15px] leading-relaxed text-zinc-300 whitespace-pre-line">
                {t.techBody}
              </p>
            </div>

            {/* VISION */}
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-zinc-100">
                {t.visionTitle}
              </h2>
              <p className="text-[15px] leading-relaxed text-zinc-300 whitespace-pre-line">
                {t.visionBody}
              </p>
            </div>
          </div>
        </Container>
      </section>
    </main>
  );
}
