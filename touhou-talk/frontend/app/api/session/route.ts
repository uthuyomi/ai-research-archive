/**
 * この API Route の役割
 * ---------------------
 * - 新しいチャットセッションを作成する（POST）
 * - 既存のチャットセッション一覧を返す（GET）
 *
 * 仕様（Auth + RLS 正規）：
 * - conversations テーブルに永続化
 * - user_id は Supabase Auth (auth.uid)
 * - RLS 前提（user_id = auth.uid()）
 *
 * 設計原則：
 * - session が会話の唯一の真実源
 * - character / location / layer は session に従属
 */

import { NextRequest, NextResponse } from "next/server";
import { supabaseServer, requireUserId } from "@/lib/supabase-server";

/* =========================
   型定義
========================= */

type SessionMode = "single" | "group";

type CreateSessionRequest = {
  characterId: string;
  mode?: SessionMode;
  layer?: string;
  location?: string;
};

/** conversations テーブルの行 */
type ConversationRow = {
  id: string;
  title: string | null;
  character_id: string;
  mode: SessionMode;
  layer: string | null;
  location: string | null;
  created_at: string;
};

/** フロント（ChatClient）用 */
export type SessionSummary = {
  id: string;
  title: string;
  characterId: string;
  mode: SessionMode;
  layer: string | null;
  location: string | null;
  createdAt: string;
};

type CreateSessionResponse = {
  sessionId: string;
};

/* =========================
   GET /api/session
   - セッション一覧取得
========================= */

export async function GET(req: NextRequest) {
  try {
    console.log("[/api/session][GET] cookie:", req.headers.get("cookie"));

    const supabase = await supabaseServer();
    const userId = await requireUserId();

    const { data, error } = await supabase
      .from("conversations")
      .select("id, title, character_id, mode, layer, location, created_at")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });

    if (error) {
      console.error("[/api/session][GET] Supabase error:", error);
      return NextResponse.json(
        { error: "Failed to fetch sessions" },
        { status: 500 },
      );
    }

    const sessions: SessionSummary[] =
      (data as ConversationRow[] | null)?.map((row) => ({
        id: row.id,
        title: row.title ?? "新しい会話",
        characterId: row.character_id,
        mode: row.mode,
        layer: row.layer,
        location: row.location,
        createdAt: row.created_at,
      })) ?? [];

    return NextResponse.json({ sessions });
  } catch (err) {
    console.error("[/api/session][GET] Error:", err);
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}

/* =========================
   POST /api/session
   - 新規セッション作成
========================= */

export async function POST(req: NextRequest) {
  try {
    console.log("[/api/session][POST] cookie:", req.headers.get("cookie"));

    const supabase = await supabaseServer();
    const userId = await requireUserId();

    const body = (await req.json()) as CreateSessionRequest;
    const { characterId, mode = "single", layer, location } = body;

    if (!characterId || typeof characterId !== "string") {
      return NextResponse.json(
        { error: "Invalid request body" },
        { status: 400 },
      );
    }

    if (mode !== "single" && mode !== "group") {
      return NextResponse.json(
        { error: "Invalid session mode" },
        { status: 400 },
      );
    }

    const { data, error } = await supabase
      .from("conversations")
      .insert({
        user_id: userId,
        title: "新しい会話",
        character_id: characterId,
        mode,
        layer: layer ?? null,
        location: location ?? null,
      })
      .select("id")
      .single();

    if (error || !data) {
      console.error("[/api/session][POST] Supabase error:", error);
      return NextResponse.json(
        { error: "Failed to create session" },
        { status: 500 },
      );
    }

    const response: CreateSessionResponse = {
      sessionId: data.id,
    };

    return NextResponse.json(response);
  } catch (err) {
    console.error("[/api/session][POST] Error:", err);
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
