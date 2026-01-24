import { NextRequest, NextResponse } from "next/server";
import "server-only";

import { supabaseServer, requireUserId } from "@/lib/supabase-server";

/* =========================
   Persona OS API 設定
========================= */

// 本番は Fly、開発のみ localhost
const PERSONA_OS_ENDPOINT =
  process.env.NODE_ENV === "development" && process.env.PERSONA_OS_LOCAL_URL
    ? process.env.PERSONA_OS_LOCAL_URL
    : (process.env.PERSONA_OS_URL ?? "https://touhou-talk-core.fly.dev/chat");

/* =========================
   型定義
========================= */

type PersonaOsResponse = {
  reply: string;
  meta?: Record<string, unknown>;
};

/* =========================
   POST Handler
========================= */

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    /* =========================
       ① sessionId
    ========================= */

    const { sessionId } = await context.params;

    if (!sessionId || typeof sessionId !== "string") {
      return NextResponse.json({ error: "Missing sessionId" }, { status: 400 });
    }

    /* =========================
       ② Auth（必須）
    ========================= */

    let userId: string;
    try {
      userId = await requireUserId();
    } catch {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    /* =========================
       ③ body（multipart のみ）
    ========================= */

    const contentType = req.headers.get("content-type") ?? "";
    if (!contentType.includes("multipart/form-data")) {
      return NextResponse.json(
        { error: "multipart/form-data required" },
        { status: 400 },
      );
    }

    const formData = await req.formData();

    const characterId = formData.get("characterId");
    const text = formData.get("text");

    if (
      typeof characterId !== "string" ||
      typeof text !== "string" ||
      !characterId ||
      !text
    ) {
      return NextResponse.json(
        { error: "Invalid request body" },
        { status: 400 },
      );
    }

    const files = formData
      .getAll("files")
      .filter((f): f is File => f instanceof File);

    /* =========================
       ④ DB ownership check
    ========================= */

    const supabase = await supabaseServer();

    const { data: conv, error: convError } = await supabase
      .from("conversations")
      .select("id")
      .eq("id", sessionId)
      .eq("user_id", userId)
      .maybeSingle();

    if (convError) {
      console.error("[DB conversation select error]", convError);
      return NextResponse.json({ error: "DB error" }, { status: 500 });
    }

    if (!conv) {
      return NextResponse.json(
        { error: "Conversation not found or forbidden" },
        { status: 403 },
      );
    }

    /* =========================
       ⑤ user message 保存
    ========================= */

    const { error: userInsertError } = await supabase.from("messages").insert({
      conversation_id: sessionId,
      user_id: userId,
      role: "user",
      content: text,
      speaker_id: null,
    });

    if (userInsertError) {
      console.error("[DB user message insert error]", userInsertError);
      return NextResponse.json(
        { error: "Failed to save user message" },
        { status: 500 },
      );
    }

    /* =========================
       ⑥ Persona OS へ中継（FormData 固定）
    ========================= */

    const fd = new FormData();
    fd.append("user_id", userId);
    fd.append("session_id", sessionId);
    fd.append("character_id", characterId);
    fd.append("text", text);

    for (const file of files) {
      fd.append("files", file);
    }

    const personaResponse = await fetch(PERSONA_OS_ENDPOINT, {
      method: "POST",
      body: fd,
    });

    if (!personaResponse.ok) {
      const body = await personaResponse.text();
      console.error("[Persona OS Error]", {
        endpoint: PERSONA_OS_ENDPOINT,
        status: personaResponse.status,
        body,
      });
      return NextResponse.json(
        { error: "Persona OS API failed" },
        { status: 502 },
      );
    }

    const personaJson = (await personaResponse.json()) as PersonaOsResponse;

    /* =========================
       ⑦ ai message 保存
    ========================= */

    const { error: aiInsertError } = await supabase.from("messages").insert({
      conversation_id: sessionId,
      user_id: userId,
      role: "ai",
      content: personaJson.reply,
      speaker_id: characterId,
    });

    if (aiInsertError) {
      console.error("[DB ai message insert error]", aiInsertError);
      return NextResponse.json(
        { error: "Failed to save ai message" },
        { status: 500 },
      );
    }

    /* =========================
       ⑧ FE 返却
    ========================= */

    return NextResponse.json({
      role: "ai",
      content: personaJson.reply,
      meta: personaJson.meta ?? null,
    });
  } catch (error) {
    console.error("[/api/session/[sessionId]/message] Fatal Error:", error);
    return NextResponse.json(
      {
        role: "ai",
        content: "……少し調子が悪いみたい。時間をおいて試して。",
      },
      { status: 500 },
    );
  }
}
