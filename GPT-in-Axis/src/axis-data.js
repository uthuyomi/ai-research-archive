// ======================================================
// 🌌 AxisData.js — Right-bottom infoPanel (Refined Final)
// ======================================================
// English: Core logic module of GPT-in-Axis, responsible for generating nodes,
// links, and semantic labels in 3D space using Babylon.js.
// 日本語: GPT-in-Axis の中核モジュール。Babylon.js を用いて、ノード・リンク・意味ラベルを3D空間に生成する。

document.addEventListener("DOMContentLoaded", () => {
  const SCALE = 8; // axis scaling factor / 軸スケール倍率
  const OFFSET = 10; // left-right offset / 左右オフセット距離
  let activeLabelPlane = null; // currently active semantic label / 現在表示中のラベル平面

  // ======================================================
  // 🎚 showSemanticLabel() — Semantic Meter (0–100%)
  // ======================================================
  // English: Displays a small floating semantic meter near the selected node.
  // 日本語: 選択されたノード付近に論理・感情・抽象の3軸メーターを表示。
  function showSemanticLabel(node, scene) {
    if (activeLabelPlane) activeLabelPlane.dispose(); // remove previous label / 既存ラベルを削除

    // position adjustment by side (question=left / answer=right)
    // 日本語: 質問ノード＝左、回答ノード＝右に位置補正
    const offset = node.type === "question" ? -OFFSET : OFFSET;
    const plane = BABYLON.MeshBuilder.CreatePlane(
      `${node.id}-semantic`,
      { width: 6.2, height: 3.8 },
      scene
    );

    // Position label above node
    // 日本語: ノード上方に配置
    plane.position = new BABYLON.Vector3(
      offset + node.logic * SCALE,
      node.emotion * SCALE + 1.8,
      -node.abstract * SCALE
    );
    plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    activeLabelPlane = plane;

    // Create GUI texture
    // 日本語: GUIテクスチャ（動的UI）を生成
    const tex = BABYLON.GUI.AdvancedDynamicTexture.CreateForMesh(plane);
    const stack = new BABYLON.GUI.StackPanel();
    stack.width = "95%";
    stack.paddingTop = "10px";
    tex.addControl(stack);

    // Draw three bars (Logic / Emotion / Abstract)
    // 日本語: 論理・感情・抽象の3種メーターを描画
    ["Logic", "Emotion", "Abstract"].forEach((ax) => {
      const color =
        ax === "Logic" ? "#4aa2ff" : ax === "Emotion" ? "#ff6666" : "#b966ff";
      const value = Math.min(Math.max(node[ax.toLowerCase()], 0), 1);
      const percent = Math.round(value * 100);

      // Outer frame
      const bar = new BABYLON.GUI.Rectangle();
      bar.width = "96%";
      bar.height = "14px";
      bar.color = "#777";
      bar.background = "#111";
      bar.cornerRadius = 8;
      bar.thickness = 1;

      // Fill (progress)
      const fill = new BABYLON.GUI.Rectangle();
      fill.width = `${percent}%`;
      fill.height = 1;
      fill.background = color;
      fill.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_LEFT;
      fill.left = "-47.5%";
      bar.addControl(fill);
      stack.addControl(bar);

      // Label text
      const lbl = new BABYLON.GUI.TextBlock();
      lbl.text = `${ax}: ${percent}%`;
      lbl.color = color;
      lbl.fontSize = 30;
      lbl.height = "28px";
      lbl.paddingTop = "5px";
      lbl.textHorizontalAlignment =
        BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_LEFT;
      stack.addControl(lbl);
    });
  }

  // ======================================================
  // 🧭 showNodeInfo() — Display Node Metadata in Info Panel
  // ======================================================
  // English: Outputs detailed node info (text + metrics) in bottom-right panel.
  // 日本語: 右下パネルにノード詳細情報（テキスト＋数値）を表示。
  function showNodeInfo(node) {
    const p = document.getElementById("infoPanel");
    if (!p) return;

    const pct = (v) => Math.round(Math.min(Math.max(v, 0), 1) * 100);
    const typeLabel = node.type === "answer" ? "A" : "Q";

    p.style.display = "block";
    p.innerHTML = `
      <div style="font-size:16px;font-weight:bold;margin-bottom:4px;">
        ${typeLabel}${node.id.replace(/\D/g, "")} (${node.type})
      </div>
      <div style="margin-bottom:8px;white-space:pre-wrap;line-height:1.5;">
        ${node.text || ""}
      </div>
      <div style="border-top:1px solid #444;margin:6px 0;padding-top:4px;font-size:13px;opacity:0.85;">
        Logic: ${pct(node.logic)}%<br>
        Emotion: ${pct(node.emotion)}%<br>
        Abstract: ${pct(node.abstract)}%
      </div>
    `;
  }

  // ======================================================
  // 🌐 createNode() — Generate Node (Symmetrical Positioning)
  // ======================================================
  // English: Creates a node (sphere) for each question/answer with mirrored positioning.
  // 日本語: 各質問／回答ノードを左右対称位置に生成。
  function createNode(node, scene) {
    const g = new BABYLON.TransformNode(node.id, scene);
    const base = 0.35;
    const offset = node.type === "question" ? -OFFSET : OFFSET;

    // Color differentiation by type
    // 日本語: ノード種別（質問／回答）で色分け
    const color =
      node.type === "question"
        ? new BABYLON.Color3(0.3, 0.6, 1.0)
        : new BABYLON.Color3(1.0, 0.55, 0.25);

    // Core sphere
    // 日本語: ノードのコア球体を生成
    const core = BABYLON.MeshBuilder.CreateSphere(
      `${node.id}-core`,
      { diameter: base },
      scene
    );
    core.parent = g;

    const mat = new BABYLON.StandardMaterial(`${node.id}-mat`, scene);
    mat.emissiveColor = color;
    mat.diffuseColor = color.scale(0.3);
    mat.specularColor = new BABYLON.Color3(0.8, 0.8, 0.8);
    core.material = mat;

    // 🎯 Normalize coordinates before positioning
    // English: Clamp values between 0–1 to prevent visual overflow.
    // 日本語: 値を0〜1に正規化して座標計算。
    const logic = Math.min(Math.max(node.logic, 0), 1);
    const emotion = Math.min(Math.max(node.emotion, 0), 1);
    const abstract = Math.min(Math.max(node.abstract, 0), 1);

    const x = offset + logic * SCALE;
    const y = emotion * SCALE;
    const z = -abstract * SCALE;
    g.position = new BABYLON.Vector3(x, y, z);

    // 💡 On-click: Show semantic meter + info panel
    // 日本語: クリック時にメーターと情報パネルを表示。
    core.actionManager = new BABYLON.ActionManager(scene);
    core.actionManager.registerAction(
      new BABYLON.ExecuteCodeAction(BABYLON.ActionManager.OnPickTrigger, () => {
        window.sceneRef = scene;
        showSemanticLabel(node, scene);
        showNodeInfo(node);
      })
    );

    g.metadata = { node };
    return g;
  }

  // ======================================================
  // 🔗 createLink() — Visual Connection Between Q → A
  // ======================================================
  // English: Draws a glowing line (tube) connecting question and answer nodes.
  // 日本語: 質問ノードと回答ノードを発光直線で結ぶ。
  function createLink(fromId, toId, strength, scene) {
    const f = scene.getTransformNodeByName(fromId);
    const t = scene.getTransformNodeByName(toId);
    if (!f || !t) return;

    const tube = BABYLON.MeshBuilder.CreateTube(
      `${fromId}-${toId}`,
      { path: [f.position, t.position], radius: 0.02 },
      scene
    );

    const m = new BABYLON.StandardMaterial(`${fromId}-${toId}-mat`, scene);
    m.emissiveColor = new BABYLON.Color3(0.95, 0.85, 0.55);
    m.alpha = 0.9;
    m.diffuseColor = new BABYLON.Color3(0.6, 0.5, 0.2);
    tube.material = m;
  }

  // ======================================================
  // 📂 loadAxisData() — Load JSON Session Data
  // ======================================================
  // English: Loads axis data (nodes and vectors) from a JSON file.
  // 日本語: JSONファイルから軸データ（ノードとベクター）を読み込む。
  async function loadAxisData(scene, path = "data/sample-axis.json") {
    const res = await fetch(path);
    const data = await res.json();
    data.nodes.forEach((n) => createNode(n, scene));
    if (data.vectors)
      data.vectors.forEach((v) => createLink(v.from, v.to, 1, scene));
  }

  // ======================================================
  // 🧩 Expose Public Interface
  // ======================================================
  // English: Make createNode(), createLink(), and loadAxisData() accessible globally.
  // 日本語: 主要関数をグローバル変数AxisDataとして公開。
  window.AxisData = { createNode, createLink, loadAxisData };
});
