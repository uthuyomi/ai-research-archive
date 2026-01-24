"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import TopShell from "@/components/top/TopShell";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signIn = async () => {
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        // ★★★ ここが唯一の修正点 ★★★
        emailRedirectTo: `${location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
    } else {
      setSent(true);
    }

    setLoading(false);
  };

  return (
    <TopShell>
      <div className="w-full max-w-sm rounded-xl bg-white/10 p-6 backdrop-blur text-white">
        <h1 className="mb-4 text-lg font-medium">ログイン</h1>

        {sent ? (
          <p className="text-sm text-white/80">
            ログイン用リンクをメールに送信しました。
            <br />
            メールを確認してください。
          </p>
        ) : (
          <>
            <input
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mb-3 w-full rounded-lg bg-black/40 px-3 py-2 text-sm outline-none"
            />

            {error && <p className="mb-2 text-sm text-red-400">{error}</p>}

            <button
              onClick={signIn}
              disabled={loading || !email}
              className="w-full rounded-lg bg-white px-4 py-2 text-sm text-black disabled:opacity-50"
            >
              {loading ? "送信中…" : "ログインリンクを送信"}
            </button>
          </>
        )}

        <button
          onClick={() => router.push("/")}
          className="mt-4 text-xs text-white/60 hover:text-white"
        >
          ← 戻る
        </button>
      </div>
    </TopShell>
  );
}
