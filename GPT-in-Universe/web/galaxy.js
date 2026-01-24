// ====================================================
// 🌌 GPT-in-Universe Viewer (Babylon.js版・JSON追記対応)
// ====================================================
// English: Visualization script for the "AI Meaning Universe" using Babylon.js.
// It can display both a randomly generated galaxy and AI-generated data from universe.json.
// 日本語: Babylon.jsを用いた「AI Meaning Universe」可視化スクリプト。
// ランダム生成された銀河と、AI生成データ（universe.json）の両方を描画可能。

const canvas = document.getElementById("renderCanvas");
const engine = new BABYLON.Engine(canvas, true);
const scene = new BABYLON.Scene(engine);
scene.clearColor = new BABYLON.Color3(0, 0, 0);
// English: Set background color to black.
// 日本語: 背景色を黒に設定。

// ====================================================
// 📷 Camera & Light
// ====================================================
// English: Create a rotatable camera and a hemispheric light to illuminate the galaxy.
// 日本語: 銀河を照らすための回転カメラと半球ライトを設定。
const camera = new BABYLON.ArcRotateCamera(
  "camera",
  Math.PI / 2,
  Math.PI / 3,
  2500,
  BABYLON.Vector3.Zero(),
  scene
);
camera.attachControl(canvas, true);
camera.wheelPrecision = 20; // English: Mouse wheel zoom sensitivity / 日本語: ホイールズームの感度
camera.minZ = 1; // English: Minimum zoom distance / 日本語: 最小ズーム距離
new BABYLON.HemisphericLight("light", new BABYLON.Vector3(0, 1, 0), scene);

// ====================================================
// 🎨 Color Palette
// ====================================================
// English: Define base color variations for random galaxy stars.
// 日本語: ランダム銀河の星に使用する基本色のバリエーション。
const palette = [
  new BABYLON.Color3(1.0, 1.0, 1.0),
  new BABYLON.Color3(0.85, 0.9, 1.0),
  new BABYLON.Color3(0.8, 0.85, 1.0),
  new BABYLON.Color3(1.0, 0.95, 0.9),
];

// ====================================================
// 🧮 Parameters
// ====================================================
// English: Define key parameters for galaxy structure, brightness, rotation, etc.
// 日本語: 銀河の構造・明るさ・回転速度などの主要パラメータを定義。
const params = {
  starCount: 2000,
  radius: 1500,
  depth: 600,
  arms: 6,
  twist: 5.0,
  pointSize: 10,
  emissive: 1.2,
  rotationSpeed: 0.0003,
  density: 0.25,
};

let pcs, material; // English: Global references for point cloud system and material / 日本語: 星群とマテリアルの参照保持

// ====================================================
// 🌌 ランダム銀河生成
// ====================================================
// English: Generate a procedural spiral galaxy using PointsCloudSystem.
// 日本語: PointsCloudSystemを使ってランダムな渦巻銀河を生成。
function createGalaxy() {
  if (pcs && pcs.mesh) pcs.mesh.dispose(); // English: Dispose old galaxy if exists / 日本語: 既存の銀河を破棄

  pcs = new BABYLON.PointsCloudSystem(
    "stars",
    BABYLON.PointsCloudSystem.POINTMODE,
    scene
  );

  // English: Add N stars based on parametric spiral galaxy logic.
  // 日本語: パラメトリックな渦巻銀河ロジックに基づいてN個の星を追加。
  pcs.addPoints(params.starCount, (p, i) => {
    const armIndex = i % params.arms;
    const baseAngle = (armIndex / params.arms) * 2 * Math.PI;
    const radius = Math.pow(Math.random(), 0.8) * params.radius;
    const theta = baseAngle + (radius / params.radius) * params.twist * Math.PI;
    const phi = Math.random() * Math.PI * 2;

    const spread = params.density;
    const x =
      Math.cos(theta) * Math.sin(phi) * radius +
      (Math.random() - 0.5) * radius * spread * 0.1;
    const y =
      (Math.random() - 0.5) * params.depth * (1 - radius / params.radius);
    const z =
      Math.sin(theta) * Math.sin(phi) * radius +
      (Math.random() - 0.5) * radius * spread * 0.1;

    // English: Assign 3D position and color gradient by radius.
    // 日本語: 半径に応じて位置と色のグラデーションを設定。
    p.position = new BABYLON.Vector3(x, y, z);
    const t = radius / params.radius;
    const base = palette[Math.floor(Math.random() * palette.length)];
    p.color = new BABYLON.Color4(
      base.r * (1.0 - t * 0.15),
      base.g * (1.0 - t * 0.25),
      base.b * (1.0 - t * 0.45),
      1.0
    );
  });

  // English: Build and render point cloud with emissive material.
  // 日本語: 発光マテリアルを適用して星群を描画。
  pcs.buildMeshAsync().then(() => {
    material = new BABYLON.PointsMaterial("pointsMat", scene);
    material.pointSize = params.pointSize;
    material.disableLighting = true;
    material.emissiveColor = new BABYLON.Color3(
      params.emissive,
      params.emissive,
      params.emissive
    );
    pcs.mesh.material = material;
    pcs.mesh.alwaysSelectAsActiveMesh = true;
    scene.addMesh(pcs.mesh);
    console.log("✅ ランダム銀河生成完了");
  });
}

// ====================================================
// 🪐 JSONデータを既存の銀河に追記
// ====================================================
// English: Append AI-generated data points from universe.json onto existing galaxy.
// 日本語: universe.json内のAI生成データを既存の銀河へ追加描画。
function addGalaxyFromData(data) {
  if (!pcs) {
    console.warn(
      "⚠️ 既存の星が存在しません。createGalaxy() を先に呼んでください。"
    );
    return;
  }

  const SCALE = 3000; // English: Scale factor for positioning / 日本語: 座標スケーリング係数
  const colorMap = [
    new BABYLON.Color3(0.9, 0.9, 1.0),
    new BABYLON.Color3(1.0, 0.85, 0.85),
    new BABYLON.Color3(0.85, 1.0, 0.9),
    new BABYLON.Color3(0.95, 0.95, 1.0),
    new BABYLON.Color3(1.0, 0.9, 0.7),
    new BABYLON.Color3(0.7, 0.9, 1.0),
    new BABYLON.Color3(0.8, 0.8, 0.8),
  ];

  // English: Loop over points and add each as a new star in the existing galaxy.
  // 日本語: 各データ点を既存銀河内に新たな星として追加。
  data.points.forEach((p) => {
    if (!p.pos || p.pos.length < 3) return;
    const [x, y, z] = p.pos.map((v) => v * SCALE);
    const clusterColor =
      colorMap[p.cluster % colorMap.length] || new BABYLON.Color3(1, 1, 1);

    pcs.addPoints(1, (pt) => {
      pt.position = new BABYLON.Vector3(x, y, z);
      pt.color = new BABYLON.Color4(
        clusterColor.r,
        clusterColor.g,
        clusterColor.b,
        1.0
      );
    });
  });

  pcs.buildMeshAsync().then(() => {
    pcs.mesh.material = material;
    scene.addMesh(pcs.mesh);
    console.log("✨ JSONデータの星を既存銀河に追記しました");
  });
}

// ====================================================
// JSONファイルを読み込み → 追記モードで適用
// ====================================================
// English: Fetch universe.json and overlay data onto the procedural galaxy.
// 日本語: universe.jsonを読み込み、ランダム銀河に重ねて表示。
fetch("../data/universe.json")
  .then((res) => {
    if (!res.ok) throw new Error("JSONなし → ランダム生成へ");
    return res.json();
  })
  .then((data) => {
    createGalaxy(); // English: Create base galaxy first / 日本語: まずランダム銀河を生成
    setTimeout(() => addGalaxyFromData(data), 500); // English: Delay slightly before merging / 日本語: 少し遅らせて追記
  })
  .catch(() => {
    console.warn("⚠️ universe.json が見つからないためランダム銀河のみ描画");
    createGalaxy();
  });

// ====================================================
// 🎛 dat.GUI Setup (日本語 + English)
// ====================================================
// English: Create GUI panel for interactive parameter tuning.
// 日本語: パラメータをインタラクティブに調整するGUIパネルを作成。
const gui = new dat.GUI({ width: 360 });
gui
  .add(params, "starCount", 500, 10000, 500)
  .name("星の数 / Star Count")
  .onChange(createGalaxy);
gui
  .add(params, "radius", 500, 3000, 100)
  .name("銀河の広がり / Radius")
  .onChange(createGalaxy);
gui
  .add(params, "depth", 100, 1200, 50)
  .name("厚み / Depth")
  .onChange(createGalaxy);
gui
  .add(params, "arms", 2, 12, 1)
  .name("腕の数 / Spiral Arms")
  .onChange(createGalaxy);
gui
  .add(params, "twist", 0, 10, 0.5)
  .name("渦のねじれ / Twist")
  .onChange(createGalaxy);
gui
  .add(params, "pointSize", 2, 20, 1)
  .name("星の大きさ / Point Size")
  .onChange(() => {
    if (material) material.pointSize = params.pointSize;
  });
gui
  .add(params, "emissive", 0.5, 2.0, 0.1)
  .name("明るさ / Brightness")
  .onChange(() => {
    if (material)
      material.emissiveColor = new BABYLON.Color3(
        params.emissive,
        params.emissive,
        params.emissive
      );
  });
gui
  .add(params, "rotationSpeed", 0, 0.002, 0.0001)
  .name("回転速度 / Rotation Speed");
gui
  .add(params, "density", 0.05, 0.6, 0.05)
  .name("密度 / Density")
  .onChange(createGalaxy);

// ====================================================
// ♻️ Animation Loop
// ====================================================
// English: Continuously rotate and render the scene.
// 日本語: シーンを継続的にレンダリングし、銀河を回転させる。
engine.runRenderLoop(() => {
  scene.render();
  if (pcs && pcs.mesh) {
    pcs.mesh.rotation.y += params.rotationSpeed;
    pcs.mesh.rotation.x += params.rotationSpeed / 3;
  }
});

window.addEventListener("resize", () => engine.resize());
// English: Adjust canvas and camera when browser window resizes.
// 日本語: ウィンドウサイズ変更時にキャンバスとカメラを調整。
