"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRef } from "react";
import { startTransition } from "react";

import ChatPane from "@/components/ChatPaneSession";
import CharacterPanel from "@/components/CharacterPanelSession";

import { CHARACTERS } from "@/data/characters";
import { getGroupsByLocation, canEnableGroup, GroupDef } from "@/data/group";

import { useChatController } from "@/hooks/useChatController";


/* =========================
   Types
========================= */

type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  attachments?: {
    name: string;
    size: number;
    type: string;
    previewUrl?: string;
  }[];
  meta?: {
    diff?: string;
    touched_files?: string[];
    next_action?: string;
  } | null;
};

type SessionSummary = {
  id: string;
  title: string;
  characterId: string;
  mode: "single" | "group";
  layer: string | null;
  location: string | null;
};

type PanelGroupContext = {
  enabled: boolean;
  label: string;
  group: GroupDef;
};

type ChatGroupContext = {
  enabled: boolean;
  label: string;
  ui: {
    chatBackground?: string;
    accent?: string;
  };
  participants: Array<{
    id: string;
    name: string;
    title: string;
    ui: {
      chatBackground?: string | null;
      placeholder: string;
    };
    color?: {
      accent?: string;
    };
  }>;
};

type VscodeMeta = {
  diff?: string;
  touched_files?: string[];
  next_action?: string;
};

type ChatApiResponse = {
  role?: "ai" | "user";
  content: string;
  meta?: VscodeMeta | null;
  error?: string;
};

type CreateSessionResponse = {
  sessionId: string;
};

type VscodeState =
  | "idle"
  | "analyzing"
  | "diffing"
  | "analysis_done"
  | "diff_ready"
  | "applying"
  | "applied"
  | "error";

/* =========================
   Component
========================= */

export default function ChatClient() {
  const searchParams = useSearchParams();
  const currentLayer = searchParams.get("layer");
  const currentLocationId = searchParams.get("loc");

  /* =========================
     State
  ========================= */

  /* =========================
     Channel (talk / vscode)
  ========================= */

  const [channel, setChannel] = useState<"talk" | "vscode">("talk");
  const [vscodeConnected, setVscodeConnected] = useState(true);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeCharacterId, setActiveCharacterId] = useState<string | null>(
    null,
  );

  const [messagesBySession, setMessagesBySession] = useState<
    Record<string, Message[]>
  >({});

  const appendMessage = useCallback(
    (m: Message) => {
      if (!activeSessionId) return;

      setMessagesBySession((prev) => ({
        ...prev,
        [activeSessionId]: [...(prev[activeSessionId] ?? []), m],
      }));
    },
    [activeSessionId],
  );

  const controller = useChatController({
    channel,
    appendMessage,
  });

  const [mode] = useState<"single" | "group">("single");

  const autoSelectDoneRef = useRef(false);

  /* =========================
     Mobile UI
  ========================= */

  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [hasSelectedOnce, setHasSelectedOnce] = useState(false);

  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(max-width: 1023px)").matches;
  });

  const [sessionsLoaded, setSessionsLoaded] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  /* =========================
     Active character
  ========================= */

  const activeCharacter = useMemo(() => {
    if (!activeCharacterId) return null;
    return CHARACTERS[activeCharacterId] ?? null;
  }, [activeCharacterId]);

  /* =========================
     Group Context
  ========================= */

  const panelGroupContext = useMemo<PanelGroupContext | null>(() => {
    if (!currentLayer || !currentLocationId) return null;
    const groups = getGroupsByLocation(currentLayer, currentLocationId);
    if (!groups.length) return null;
    const group = groups[0];
    if (!canEnableGroup(group.id)) return null;
    return { enabled: true, label: group.ui.label, group };
  }, [currentLayer, currentLocationId]);

  const chatGroupContext = useMemo<ChatGroupContext | null>(() => {
    if (!panelGroupContext?.enabled) return null;

    const participants = panelGroupContext.group.participants
      .map((id) => CHARACTERS[id])
      .filter(Boolean);

    const groupUi = panelGroupContext.group.ui as {
      chatBackground?: string | null;
      accent?: string;
    };

    return {
      enabled: true,
      label: panelGroupContext.group.ui.label,
      ui: {
        chatBackground: groupUi.chatBackground ?? undefined,
        accent: groupUi.accent,
      },
      participants,
    };
  }, [panelGroupContext]);

  /* =========================
     Initial session list
  ========================= */

  useEffect(() => {
    (async () => {
      const res = await fetch("/api/session", {
        cache: "no-store",
      });
      if (!res.ok) return;
      const data = (await res.json()) as { sessions?: SessionSummary[] };
      setSessions(data.sessions ?? []);
      setSessionsLoaded(true); // ★これ
    })();
  }, []);

  /* =========================
     Character select
  ========================= */

  const selectCharacter = useCallback(
    async (characterId: string) => {
      setChannel("talk"); // ★ セッション切替時は必ず通常会話に戻す

      const existing = sessions.find(
        (s) =>
          s.characterId === characterId &&
          s.layer === currentLayer &&
          s.location === currentLocationId,
      );
      if (existing) {
        setActiveSessionId(existing.id);
        setActiveCharacterId(characterId); // ★これが必須
        setHasSelectedOnce(true);
        setIsPanelOpen(false);
        return;
      }

      const res = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          characterId,
          mode,
          layer: currentLayer,
          location: currentLocationId,
        }),
      });

      if (!res.ok) return;
      const data = (await res.json()) as CreateSessionResponse;

      const newSession: SessionSummary = {
        id: data.sessionId,
        title: "新しい会話",
        characterId,
        mode,
        layer: currentLayer,
        location: currentLocationId,
      };

      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setActiveCharacterId(characterId);
      setMessagesBySession((prev) => ({ ...prev, [newSession.id]: [] }));
      setHasSelectedOnce(true);
      setIsPanelOpen(false);
    },
    [sessions, mode, currentLayer, currentLocationId],
  );

  /* =========================
   Reset auto select flag when URL char changes
========================= */
  useEffect(() => {
    autoSelectDoneRef.current = false;
  }, [searchParams.get("char")]);
  /* =========================
   Auto select character from URL (map → chat)
========================= */
  useEffect(() => {
    if (!sessionsLoaded) return;
    if (autoSelectDoneRef.current) return;

    const charFromUrl = searchParams.get("char");
    if (!charFromUrl) return;
    if (!CHARACTERS[charFromUrl]) return;

    autoSelectDoneRef.current = true;

    // ★ 既存 / 新規の判定は selectCharacter に完全委譲
    Promise.resolve().then(() => {
      selectCharacter(charFromUrl);
    });
  }, [searchParams, sessionsLoaded, selectCharacter]);
  /* =========================
     Session select / delete / rename
  ========================= */

  const selectSession = useCallback(
    (sessionId: string) => {
      const s = sessions.find((x) => x.id === sessionId);
      if (!s) return;
      setActiveSessionId(s.id);
      setActiveCharacterId(s.characterId);
      setChannel("talk"); // ★ 念のためリセット
      setHasSelectedOnce(true);
      setIsPanelOpen(false);
    },
    [sessions],
  );

  const handleDeleteSession = useCallback(
    async (id: string) => {
      const res = await fetch(`/api/session/${id}`, { method: "DELETE" });
      if (!res.ok) return;

      setSessions((prev) => prev.filter((s) => s.id !== id));
      setMessagesBySession((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });

      if (activeSessionId === id) {
        setActiveSessionId(null);
        setActiveCharacterId(null);
        setHasSelectedOnce(false);
        setIsPanelOpen(false);
      }
    },
    [activeSessionId],
  );

  const handleRenameSession = useCallback(async (id: string, title: string) => {
    const t = title.trim();
    if (!t) return;

    const res = await fetch(`/api/session/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: t }),
    });

    if (!res.ok) return;

    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: t } : s)),
    );
  }, []);

  /* =========================
     Messages restore
  ========================= */

  useEffect(() => {
    if (!activeSessionId) return;
    if (!sessions.some((s) => s.id === activeSessionId)) return;
    if (messagesBySession[activeSessionId]) return;

    (async () => {
      const res = await fetch(`/api/session/${activeSessionId}/messages`);
      if (!res.ok) return;
      const data = await res.json();
      setMessagesBySession((prev) => ({
        ...prev,
        [activeSessionId]: data.messages ?? [],
      }));
    })();
  }, [activeSessionId, sessions, messagesBySession]);

  /* =========================
     Message send
  ========================= */

  const handleSendTalk = useCallback(
    async (payload: {
      text: string;
      files: File[];
      attachments?: {
        name: string;
        size: number;
        type: string;
        previewUrl?: string;
      }[];
    }) => {
      if (!activeSessionId || !activeCharacterId) return;

      const { text, files, attachments } = payload;

      // ① user message
      appendMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        attachments: attachments ?? [],
        meta: null,
      });

      // ② talk専用 endpoint
      const endpoint = `/api/session/${activeSessionId}/message`;

      // ③ talkは FormData で files 送る
      const form = new FormData();
      form.append("characterId", activeCharacterId);
      form.append("text", text);

      for (const file of files) {
        form.append("files", file);
      }

      const res = await fetch(endpoint, {
        method: "POST",
        body: form,
      });

      if (!res.ok) return;

      const data = await res.json();

      // ④ ai message
      appendMessage({
        id: crypto.randomUUID(),
        role: "ai",
        content: data.content ?? "",
        meta: data.meta ?? null,
      });
    },
    [activeSessionId, activeCharacterId, appendMessage],
  );

  /* =========================
     Render
  ========================= */

  const activeMessages =
    activeSessionId != null ? (messagesBySession[activeSessionId] ?? []) : [];

  return (
    <div className="relative flex h-dvh w-full overflow-hidden">
      {/* ===== Mobile / Tablet 初回：セッション未選択なら全画面 Panel ===== */}
      {isMobile && !hasSelectedOnce && !activeSessionId && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <CharacterPanel
            characters={CHARACTERS}
            activeCharacterId={activeCharacterId}
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectCharacter={selectCharacter}
            onSelectSession={selectSession}
            onCreateSession={() => {}}
            onRenameSession={handleRenameSession}
            onDeleteSession={handleDeleteSession}
            currentLocationId={currentLocationId}
            currentLayer={currentLayer}
            groupContext={panelGroupContext}
            mode={mode}
            fullScreen
          />
        </div>
      )}

      {/* ===== Desktop ===== */}
      <div className="hidden lg:block">
        <CharacterPanel
          characters={CHARACTERS}
          activeCharacterId={activeCharacterId}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectCharacter={selectCharacter}
          onSelectSession={selectSession}
          onCreateSession={() => {}}
          onRenameSession={handleRenameSession}
          onDeleteSession={handleDeleteSession}
          currentLocationId={currentLocationId}
          currentLayer={currentLayer}
          groupContext={panelGroupContext}
          mode={mode}
        />
      </div>

      {/* ===== Mobile / Tablet 通常 Panel ===== */}
      {isPanelOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={() => setIsPanelOpen(false)}
          />
          <div className="fixed left-0 top-0 z-50 h-full w-80 lg:hidden">
            <CharacterPanel
              characters={CHARACTERS}
              activeCharacterId={activeCharacterId}
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelectCharacter={selectCharacter}
              onSelectSession={selectSession}
              onCreateSession={() => {}}
              onRenameSession={handleRenameSession}
              onDeleteSession={handleDeleteSession}
              currentLocationId={currentLocationId}
              currentLayer={currentLayer}
              groupContext={panelGroupContext}
              mode={mode}
            />
          </div>
        </>
      )}

      {/* ===== Chat ===== */}
      {activeCharacter && activeSessionId && (
        <ChatPane
          character={activeCharacter}
          messages={activeMessages}
          onSend={channel === "vscode" ? controller.send : handleSendTalk}
          onOpenPanel={() => setIsPanelOpen(true)}
          mode={mode}
          groupContext={mode === "group" ? chatGroupContext : null}
        />
      )}
    </div>
  );
}