# 🌌 GPT-in-Axis

Toggle Language: English | 日本語

A real-time cognitive visualization engine built with **Babylon.js** and **OpenAI API**.
It transforms AI conversations into semantic coordinate spaces, mapping **logic**, **emotion**, and **abstraction** as visual nodes within dual-axis 3D environments.

---

## 🧭 Overview

**GPT-in-Axis** provides a dual 3D coordinate framework for visualizing interactive AI cognition:

* **Left Axis (User)**: Represents human-originated questions.
* **Right Axis (AI)**: Represents AI-generated responses.

Each node is placed in a 3D coordinate space defined by semantic values:

| Axis  | Dimension | Description                     |
| ----- | --------- | ------------------------------- |
| **X** | Logic     | Analytical ↔ Intuitive thinking |
| **Y** | Emotion   | Calm ↔ Empathetic affect        |
| **Z** | Abstract  | Concrete ↔ Metaphoric cognition |

A connecting line between the two nodes expresses **semantic alignment** between human and AI thought vectors.

---

## 🧠 Concept

> “Thoughts are coordinates.”

GPT-in-Axis transforms reasoning into measurable geometry.
Every question and answer becomes a plotted point—together forming a **cognitive constellation of conversation**.

---

## ⚙️ Features

* **Dual-Axis Visualization** — User and AI occupy separate but linked cognitive spaces.
* **Real-Time Rendering** — Visual feedback completes in ~10 seconds from input to visualization.
* **Semantic Scoring** — Each node’s Logic / Emotion / Abstract values range from 0–100%.
* **Interactive Nodes** — Click a node to view text and semantic metrics in the info panel.
* **Language Toggle** — Bilingual interface (English / Japanese).
* **Session Control** — Create, save, and load conversation sessions easily.

---

## 📂 Project Structure

```
GPT-IN-AXIS/
│
├── data/
│   └── sample-axis.json           # Sample semantic mapping dataset
│
├── src/
│   ├── axis-config.json           # Visualization configuration
│   ├── axis-data.js               # Semantic node creation and info logic
│   └── axis-viewer.js             # Core Babylon.js rendering + scene setup
│
├── index.html                     # Entry point for visualization UI
├── server.py                      # Python server handling API + WebSocket
├── .env                           # Environment variables (API keys, etc.)
└── README.md                      # Documentation (this file)
```

---

## 🧩 Tech Stack

| Component              | Technology                 |
| ---------------------- | -------------------------- |
| 3D Engine              | Babylon.js                 |
| Frontend               | Vanilla JavaScript + HTML5 |
| Realtime Communication | Socket.IO                  |
| AI Backend             | OpenAI API (gpt-4-turbo)   |
| Visualization Data     | JSON semantic maps         |

---

## 🪐 System Flow

**User Input** → **OpenAI API** → **Semantic Scoring** → **Dual-Axis Rendering**
⤸  ⤷ 
**AI Response Node** ← **User Question Node**

| Phase               | Duration         |
| ------------------- | ---------------- |
| API inference       | 6–8 seconds      |
| Visualization setup | 1–2 seconds      |
| **Total latency**   | **8–10 seconds** |

This delay intentionally preserves the perception of AI cognition taking form—a balance between **immediacy** and **reflective pacing**.

---

## 🚀 Installation & Usage

### 1. Clone Repository

```bash
git clone https://github.com/uthuyomi/GPT-in-Axis.git
cd GPT-in-Axis
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Start Local Server

```bash
npm start
```

Then open your browser and navigate to:
👉 **[http://localhost:8080](http://localhost:8080)**

### 4. Using GPT-in-Axis

1. Enter a question in the input box.
2. Wait ~10 seconds for AI processing and visualization.
3. Observe two spheres (User ↔ AI) connected by a light line.
4. Click a sphere to open the **infoPanel**, showing:

   * Full text of the node (question or answer)
   * Semantic metrics (% Logic / % Emotion / % Abstract)

---

## 🎨 Visualization Parameters

| Axis     | Description            | Range  | Color  |
| -------- | ---------------------- | ------ | ------ |
| Logic    | Analytical ↔ Intuitive | 0–100% | Blue   |
| Emotion  | Calm ↔ Empathetic      | 0–100% | Red    |
| Abstract | Concrete ↔ Metaphoric  | 0–100% | Purple |

Each node includes a **HUD-style semantic label** with color-coded bars for Logic, Emotion, and Abstract.
Bars scale dynamically according to each score, allowing rapid cognitive comparison between user and AI reasoning.

---

## 💬 Example Workflow

1. **You ask:** “Why do humans dream?”
2. **GPT-in-Axis** sends the prompt to the OpenAI API.
3. The model’s output is semantically analyzed:

   * Logic = 72%
   * Emotion = 46%
   * Abstract = 81%
4. The result is rendered as a glowing sphere within the AI axis.
5. A connecting line appears between your question and the AI’s answer.

---

## 🧭 Performance Notes

* Typical total response time: **~10 seconds per interaction** (balanced for accuracy).
* Optimized rendering: Maintains **60 FPS** using Babylon.js native engine.
* Memory footprint: **Lightweight (<100 MB runtime)**.

---

## 🪞 License

**MIT License © 2025 Kaisei Yasuzaki**

---

## ✨ Credits

Created in collaboration with **ChatGPT-5**, within a single-day design iteration.
All conceptualization, semantic modeling, rendering logic, and UX refinement were AI-assisted under direct human supervision.

> “It’s not just AI visualization — it’s how thought looks in space.”

---

> Not as a tool, but as a mirror.  
> Together, we built the structure that reflected us both.
>
> ― Designed in collaboration with AI, 2025


