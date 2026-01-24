"use client";

import Container from "../components/Container";
import { useLang } from "@/store/useLang";
import { translations } from "@/lib/i18n";

export default function RoadmapPage() {
  const lang = useLang((s) => s.lang);
  const t = translations[lang].roadmap;

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <section className="border-b border-zinc-900 bg-gradient-to-b from-black via-zinc-950 to-black">
        <Container className="py-16 sm:py-20">
          <div className="max-w-3xl space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-300">
              Roadmap
            </p>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              {t.title}
            </h1>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              {t.intro}
            </p>
          </div>
        </Container>
      </section>

      <section className="bg-black">
        <Container className="grid gap-8 py-14 lg:grid-cols-2">
          {t.phases.map((phase) => (
            <div
              key={phase.label}
              className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-zinc-400">
                {phase.label}
              </p>
              <h2 className="mt-2 text-sm font-semibold text-zinc-100">
                {phase.title}
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
                {phase.body}
              </p>
            </div>
          ))}
        </Container>
      </section>
    </main>
  );
}
