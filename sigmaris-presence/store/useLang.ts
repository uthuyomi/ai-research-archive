// store/useLang.ts
import { create } from "zustand";
import type { Lang } from "@/lib/i18n";

type LangState = {
  lang: Lang;
  toggle: () => void;
  setLang: (v: Lang) => void;
};

export const useLang = create<LangState>((set) => ({
  lang: "en",
  toggle: () => set((state) => ({ lang: state.lang === "en" ? "ja" : "en" })),
  setLang: (v) => set({ lang: v }),
}));
