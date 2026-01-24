"use client";

import Container from "../components/Container";
import { useLang } from "@/store/useLang";
import { translations } from "@/lib/i18n";

export default function DonatePage() {
  const lang = useLang((s) => s.lang);
  const t = translations[lang].donate;

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <section className="border-b border-zinc-900 bg-gradient-to-b from-black via-zinc-950 to-black">
        <Container className="py-16 sm:py-20">
          <div className="max-w-3xl space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-300">
              Support
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

      <section className="border-b border-zinc-900 bg-black">
        <Container className="grid gap-10 py-14 lg:grid-cols-2">
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-zinc-100">
              {t.whyTitle}
            </h2>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              {t.whyBody}
            </p>
          </div>

          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-zinc-100">
              {t.usageTitle}
            </h2>
            <ul className="space-y-2 text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              {t.usageItems.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-[5px] h-[5px] w-[5px] rounded-full bg-cyan-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </Container>
      </section>

      <section className="bg-black">
        <Container className="py-12 sm:py-14">
          <div className="max-w-3xl space-y-4">
            <h2 className="text-sm font-semibold text-zinc-100">
              {t.thanksTitle}
            </h2>
            <p className="text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              {t.thanksBody}
            </p>

            {/* 実際の決済ボタンはここに埋め込む想定 */}
            <div className="mt-6">
              <button className="rounded-full bg-cyan-400 px-6 py-2.5 text-sm font-medium text-black shadow-[0_0_25px_rgba(34,211,238,0.7)] hover:bg-cyan-300 transition-colors">
                {/* 文言はシンプルに英語ベースで固定でもOK */}
                {lang === "ja" ? "支援ページへ進む" : "Go to support page"}
              </button>
            </div>
          </div>
        </Container>
      </section>
    </main>
  );
}
