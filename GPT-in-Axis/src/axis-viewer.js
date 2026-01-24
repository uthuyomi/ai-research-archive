// ====================================================
// 🌌 GPT-in-Axis Viewer — Dual Axis (Left=User / Right=AI)
// ====================================================
// English: A Babylon.js visualization module that renders dual "axes" representing human (left) and AI (right) cognitive spaces.
// 日本語: 人間（左）とAI（右）の認知空間を可視化するための、Babylon.jsベースのビューワーモジュール。

// ----------------------------------------------------
// 🪞 Scene Initialization
// English: Initialize Babylon.js scene, camera, and lighting.
// 日本語: Babylon.jsのシーン・カメラ・ライトを初期化。
const canvas = document.getElementById("renderCanvas");
const engine = new BABYLON.Engine(canvas, true);
const scene = new BABYLON.Scene(engine);
scene.clearColor = new BABYLON.Color3(0.02, 0.02, 0.06); // dark background tone
window.sceneRef = scene; // make accessible globally

// Camera setup
// English: ArcRotateCamera gives orbital control for 3D navigation.
// 日本語: ArcRotateCameraで3D空間を自由に回転操作できる。
const camera = new BABYLON.ArcRotateCamera(
  "cam",
  Math.PI / 4,
  Math.PI / 3.2,
  20,
  BABYLON.Vector3.Zero(),
  scene
);
camera.attachControl(canvas, true);

// Soft glow effect
// English: Adds subtle luminescence to meshes for visual depth.
// 日本語: オブジェクトに柔らかい発光効果を付与。
new BABYLON.GlowLayer("glow", scene, { blurKernelSize: 8 }).intensity = 0.25;

// Ambient light
// English: Balanced hemispheric lighting for realism.
// 日本語: シーン全体に柔らかな環境光を追加。
new BABYLON.HemisphericLight(
  "hemi",
  new BABYLON.Vector3(1, 1, 0.5),
  scene
).intensity = 0.95;

// ----------------------------------------------------
// 🧭 Axis Configuration
// English: Define base offset and axis length for user/AI coordinate systems.
// 日本語: ユーザー軸・AI軸の原点位置と長さを定義。
const AXIS_OFFSET = 10; // X offset for left/right axis origins
const AXIS_LEN = 8; // Length of each axis

// ----------------------------------------------------
// 🧩 createAxisSet()
// English: Generates a labeled 3D coordinate system (Logic / Emotion / Abstract).
// 日本語: 「論理・感情・抽象」の三軸を可視化する3D座標セットを生成。
function createAxisSet(tag, offsetX, labelPrefix) {
  const base = new BABYLON.Vector3(offsetX, 0, 0);

  const make = (to, color, name, labelText, subLabel, icon) => {
    const from = base.clone();
    const toAbs = base.add(to);

    // Draw line (axis)
    // English: Create a colored line to represent an axis direction.
    // 日本語: 軸方向を示すカラ―ラインを描画。
    const line = BABYLON.MeshBuilder.CreateLines(
      `AXIS-${tag}-${name}`,
      { points: [from, toAbs] },
      scene
    );
    line.color = color;

    // Arrow tip
    // English: Add a small arrow cone to emphasize directionality.
    // 日本語: 軸方向を示す矢印形状を追加。
    const arrow = BABYLON.MeshBuilder.CreateCylinder(
      `AXIS-${tag}-ARW-${name}`,
      { diameterTop: 0, diameterBottom: 0.2, height: 0.6 },
      scene
    );
    arrow.material = new BABYLON.StandardMaterial(
      `AXIS-${tag}-ARW-MAT-${name}`,
      scene
    );
    arrow.material.emissiveColor = color;
    arrow.position = toAbs.add(to.normalize().scale(0.4));
    arrow.rotation = new BABYLON.Vector3(
      to.z > 0 ? Math.PI / 2 : to.z < 0 ? -Math.PI / 2 : 0,
      Math.atan2(to.x, to.z),
      0
    );

    // Dual-line label (title + subtitle)
    // English: Each axis has a label icon and description (bilingual ready).
    // 日本語: 各軸にアイコン＋ラベル（2行）を表示。
    const plane = BABYLON.MeshBuilder.CreatePlane(
      `AXIS-${tag}-LBL-${name}`,
      { width: 2.4, height: 1.2 },
      scene
    );
    plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    plane.position = toAbs.add(new BABYLON.Vector3(0, 0.7, 0));

    // Label text
    const tex = new BABYLON.DynamicTexture(
      `AXIS-${tag}-TXT-${name}`,
      { width: 512, height: 256 },
      scene,
      true
    );
    const ctx = tex.getContext();
    ctx.clearRect(0, 0, 512, 256);
    ctx.font = "bold 52px sans-serif";
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.fillText(`${icon} ${labelText}`, 256, 120);
    ctx.font = "28px monospace";
    ctx.fillStyle = "#aaa";
    ctx.fillText(subLabel, 256, 170);
    tex.update();

    const mat = new BABYLON.StandardMaterial(`AXIS-${tag}-MAT-${name}`, scene);
    mat.diffuseTexture = tex;
    mat.emissiveColor = BABYLON.Color3.White();
    mat.backFaceCulling = false;
    plane.material = mat;
  };

  // Logic axis → X+
  make(
    new BABYLON.Vector3(AXIS_LEN, 0, 0),
    new BABYLON.Color3(0.2, 0.4, 1.0),
    "X",
    "Logic",
    "思考・分析",
    "🧠"
  );
  // Emotion axis → Y+
  make(
    new BABYLON.Vector3(0, AXIS_LEN, 0),
    new BABYLON.Color3(1.0, 0.3, 0.3),
    "Y",
    "Emotion",
    "感情・共感",
    "❤️"
  );
  // Abstract axis → Z− (depth)
  make(
    new BABYLON.Vector3(0, 0, -AXIS_LEN),
    new BABYLON.Color3(0.7, 0.3, 1.0),
    "Z",
    "Abstract",
    "抽象・発想",
    "🌌"
  );
}

// Create dual sets (User / AI)
// English: Left = Human dialogue space, Right = AI response space.
// 日本語: 左＝人間の対話空間、右＝AIの応答空間を表現。
createAxisSet("L", -AXIS_OFFSET, "User");
createAxisSet("R", AXIS_OFFSET, "AI");

// ----------------------------------------------------
// 🌐 Language UI (i18n support)
// English: Basic bilingual interface control for Japanese ↔ English toggle.
// 日本語: 日本語と英語を切り替えるUIロジック。
const i18n = {
  ja: {
    send: "送信",
    newSession: "新規セッション",
    save: "保存",
    load: "セッション読込...",
    placeholder: "質問を入力...",
  },
  en: {
    send: "Send",
    newSession: "New Session",
    save: "Save",
    load: "Load session...",
    placeholder: "Enter your question...",
  },
};
let currentLang = "ja";

function updateUIlang(lang) {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key === "placeholder") el.placeholder = i18n[lang][key];
    else el.textContent = i18n[lang][key];
  });
  document.getElementById("langToggle").textContent =
    lang === "ja" ? "🌐 日本語" : "🌐 English";
  currentLang = lang;
}

// Toggle between Japanese and English
// 日本語と英語の切替処理
document.getElementById("langToggle").addEventListener("click", () => {
  updateUIlang(currentLang === "ja" ? "en" : "ja");
  if (window.refreshLangLabels) window.refreshLangLabels(currentLang);
});

// ----------------------------------------------------
// 📦 Axis Data Loader
// English: Wait for AxisData module to load before initializing sample data.
// 日本語: AxisDataモジュールが読み込まれるのを待ってからサンプルデータを初期化。
const waitAxis = setInterval(() => {
  if (window.AxisData) {
    clearInterval(waitAxis);
    AxisData.loadAxisData(scene, "data/sample-axis.json");
  }
}, 50);

// ----------------------------------------------------
// 🔁 Socket.IO Realtime Updates
// English: Synchronize new Q/A nodes generated on the server.
// 日本語: サーバー側で生成された質問／回答ノードをリアルタイム反映。
const socket = io();
socket.on("new_nodes", ({ q, a }) => {
  AxisData.createNode(q, scene);
  AxisData.createNode(a, scene);
  AxisData.createLink(q.id, a.id, 1, scene);
});

// ----------------------------------------------------
// 💬 Question Handling + Session Control
// English: Handles sending questions, creating sessions, and saving/loading dialogue states.
// 日本語: 質問送信・セッション作成・保存／読込の制御処理。
const $ = (id) => document.getElementById(id);

// --- Send question to server ---
$("sendBtn").addEventListener("click", async () => {
  const q = $("questionInput").value.trim();
  if (!q) return;
  const model = $("modelSelect").value;
  $("questionInput").value = "";
  await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q, model, lang: currentLang }),
  });
});
$("questionInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("sendBtn").click();
});

// --- Session controls (new / save / load) ---
$("newSessionBtn").addEventListener("click", async () => {
  // 1️⃣ セッションを新規作成（ファイル生成）
  await fetch("/session/new", { method: "POST" });

  // 2️⃣ ファイル生成完了を少し待機（非同期I/O安定化）
  await new Promise((r) => setTimeout(r, 150));

  // 3️⃣ 旧ノードとトランスフォームを完全削除
  scene.meshes
    .filter((m) => !m.name.startsWith("AXIS-"))
    .forEach((m) => m.dispose());
  scene.transformNodes.forEach((tn) => tn.dispose());

  // 4️⃣ 軸データを完全リロード（鏡軸リセット）
  if (window.AxisData && window.AxisData.loadAxisData) {
    AxisData.loadAxisData(scene, "data/sample-axis.json");
  }

  // 5️⃣ セッションリスト更新
  await refreshSessions();
});
$("saveSessionBtn").addEventListener("click", async () => {
  // セッションデータを保存
  await fetch("/session/save", { method: "POST" });

  // ✅ 履歴ログを保存
  const res = await fetch("/log/save", { method: "POST" });
  const data = await res.json();
  console.log("💾 Conversation log saved:", data.path);
});
$("loadSessionSelect").addEventListener("change", async (e) => {
  const id = e.target.value;
  if (!id) return;
  await fetch(`/session/load?id=${id}`);

  // Clear existing scene and reload data
  scene.meshes
    .filter((m) => !m.name.startsWith("AXIS-"))
    .forEach((m) => m.dispose());
  scene.transformNodes.forEach((tn) => tn.dispose());
  AxisData.loadAxisData(scene, `data/${id}.json`);
});

// --- Refresh session list ---
async function refreshSessions() {
  const r = await fetch("/session/list");
  const { sessions, current } = await r.json();
  $("loadSessionSelect").innerHTML =
    `<option value="">${i18n[currentLang].load}</option>` +
    sessions
      .map(
        (s) =>
          `<option value="${s}" ${
            s === current ? "selected" : ""
          }>${s}</option>`
      )
      .join("");
}
refreshSessions();

// ----------------------------------------------------
// 🎞️ Render Loop
// English: Continuously render the 3D scene and adjust to window resize.
// 日本語: シーンを常時レンダリングし、ウィンドウサイズに応じて調整。
engine.runRenderLoop(() => scene.render());
window.addEventListener("resize", () => engine.resize());
