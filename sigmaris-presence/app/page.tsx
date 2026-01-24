"use client";

import Container from "./components/Container";
import { useLang } from "@/store/useLang";
import { translations } from "@/lib/i18n";
import Link from "next/link";

export default function HomePage() {
  const lang = useLang((s) => s.lang);
  const t = translations[lang].home;

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <section className="border-b border-zinc-800 bg-gradient-to-b from-black via-zinc-950 to-black">
        <Container className="flex flex-col gap-10 py-16 lg:flex-row lg:items-center lg:justify-between lg:py-24">
          <div className="max-w-xl space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-300">
              Sigmaris Presence Project
            </p>
            <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl lg:text-5xl">
              {t.heroTitle}
            </h1>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-base">
              {t.heroSubtitle}
            </p>

            <div className="flex flex-wrap gap-3 pt-2">
              <Link
                href="/about"
                className="rounded-full bg-cyan-400 px-5 py-2.5 text-sm font-medium text-black shadow-[0_0_25px_rgba(34,211,238,0.7)] hover:bg-cyan-300 transition-colors"
              >
                {t.heroPrimaryCta}
              </Link>
              <Link
                href="/donate"
                className="rounded-full border border-zinc-700 px-5 py-2.5 text-sm font-medium text-zinc-200 hover:border-cyan-400 hover:text-cyan-300 transition-colors"
              >
                {t.heroSecondaryCta}
              </Link>
            </div>
          </div>

          <div className="relative mt-4 w-full max-w-md lg:mt-0">
            <div className="aspect-[4/5] rounded-3xl border border-cyan-400/40 bg-zinc-950/80 shadow-[0_0_45px_rgba(34,211,238,0.5)]">
              <div className="flex h-full flex-col justify-between p-6">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-zinc-400">
                    Persona OS
                  </p>
                  <p className="mt-2 text-sm text-zinc-200">
                    Reflection / Introspection / Meta-Reflection, trait-based
                    behavior and safety-guarded personality loops.
                  </p>
                </div>
                <div className="space-y-1 text-xs text-zinc-400">
                  <p>calm / empathy / curiosity</p>
                  <p>state: Idle → Dialogue → Reflect → Introspect</p>
                  <p>mode: presence-oriented, not engagement-maximizing</p>
                </div>
              </div>
            </div>
            <div className="pointer-events-none absolute inset-0 -z-10 blur-3xl">
              <div className="h-full w-full rounded-[40px] bg-cyan-500/30" />
            </div>
          </div>
        </Container>
      </section>

      <section className="border-b border-zinc-900 bg-black">
        <Container className="grid gap-10 py-14 lg:grid-cols-[2fr,1.3fr]">
          <div className="space-y-4">
            <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
              {t.section1Title}
            </h2>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              {t.section1Body}
            </p>
            <h3 className="pt-4 text-sm font-semibold tracking-wide text-zinc-200">
              {t.section2Title}
            </h3>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              {t.section2Body}
            </p>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-zinc-400">
              {t.statsTitle}
            </p>
            <div className="mt-4 space-y-4">
              {t.statsItems.map((item) => (
                <div
                  key={item.label}
                  className="flex items-baseline justify-between gap-4"
                >
                  <span className="text-xs text-zinc-400">{item.label}</span>
                  <span className="text-sm font-medium text-cyan-300">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Container>
      </section>
    </main>
  );
}
