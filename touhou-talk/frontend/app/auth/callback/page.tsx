// app/auth/callback/page.tsx

"use client";

// ★ prerender / SSG を完全に無効化（最重要）
export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      /**
       * magic link / OTP
       * - URL fragment (#access_token=...) は supabase-js が自動取得
       * - getSession() を呼ぶだけで Cookie に保存される
       */
      const { data, error } = await supabase.auth.getSession();

      if (cancelled) return;

      if (error || !data.session) {
        console.error("[auth/callback] session error:", error);
        setError("ログインに失敗しました。もう一度お試しください。");
        return;
      }

      // ★ セッション確定後に遷移
      router.replace("/map/session/gensokyo");
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center bg-black text-white">
      {error ? (
        <div className="text-sm text-red-400">{error}</div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
          <p className="text-sm text-white/70">ログイン処理中…</p>
        </div>
      )}
    </div>
  );
}
