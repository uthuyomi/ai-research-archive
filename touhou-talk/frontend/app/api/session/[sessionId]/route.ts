import { NextRequest, NextResponse } from "next/server";
import { supabaseServer, requireUserId } from "@/lib/supabase-server";

/* =========================
   PATCH /api/session/[sessionId]
   - タイトル編集
========================= */

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const { sessionId } = await context.params;

    console.log(
      "[/api/session/[id]][PATCH] cookie:",
      req.headers.get("cookie"),
    );

    const supabase = await supabaseServer();
    const userId = await requireUserId();

    const { title } = await req.json();

    if (!title || typeof title !== "string") {
      return NextResponse.json({ error: "Invalid title" }, { status: 400 });
    }

    // 🔒 存在確認（他人・削除済み防止）
    const { data: exists, error: selectError } = await supabase
      .from("conversations")
      .select("id")
      .eq("id", sessionId)
      .eq("user_id", userId)
      .maybeSingle();

    if (selectError || !exists) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }

    const { error } = await supabase
      .from("conversations")
      .update({ title })
      .eq("id", sessionId)
      .eq("user_id", userId);

    if (error) {
      console.error("[PATCH session] Supabase error:", error);
      return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }

    return NextResponse.json({ ok: true, sessionId });
  } catch (err) {
    console.error("[PATCH session] Error:", err);
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}

/* =========================
   DELETE /api/session/[sessionId]
   - セッション削除（物理削除）
========================= */

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const { sessionId } = await context.params;

    console.log(
      "[/api/session/[id]][DELETE] cookie:",
      req.headers.get("cookie"),
    );

    const supabase = await supabaseServer();
    const userId = await requireUserId();

    // 🔒 存在確認（二重 delete / 他人防止）
    const { data: exists, error: selectError } = await supabase
      .from("conversations")
      .select("id")
      .eq("id", sessionId)
      .eq("user_id", userId)
      .maybeSingle();

    if (selectError || !exists) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }

    // conversations を物理削除
    // messages は DB 側で ON DELETE CASCADE 前提
    const { error } = await supabase
      .from("conversations")
      .delete()
      .eq("id", sessionId)
      .eq("user_id", userId);

    if (error) {
      console.error("[DELETE session] Supabase error:", error);
      return NextResponse.json({ error: "Delete failed" }, { status: 500 });
    }

    return NextResponse.json({ ok: true, sessionId });
  } catch (err) {
    console.error("[DELETE session] Error:", err);
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
