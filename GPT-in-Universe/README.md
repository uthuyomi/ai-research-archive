# 🌌 GPT-in-Universe

Languages:
<<<<<<< HEAD
🌐 English | 🇯🇵 日本語
=======
**Languages:**  
[🌐 English](README.md) | [🇯🇵 日本語](README_ja.md)
>>>>>>> 0a4f2f353a7a5f3d528b78f03482e9dc52c56d5c

### “Visualizing AI meaning space as a living galaxy.”

---

## I. Introduction

**GPT-in-Universe** is an experimental visualization project that transforms
the semantic relationships of ChatGPT’s answers into a **three-dimensional galaxy**.
Each star represents an AI-generated thought, and clusters form based on shared meaning.

It is not a game, not data art.
It is a **structural experiment** at the boundary of cognition, language, and visualization.

---

## II. Technical Overview

The project now consists of two synchronized layers:

| Layer                                | Description                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------- |
| **Python (Data Layer)**              | Clusters ChatGPT responses via semantic similarity and exports `universe.json`. |
| **Babylon.js (Visualization Layer)** | Renders both random and JSON-based galaxies in real 3D with orbit control.      |

**Update:**
The previous Three.js implementation has been replaced by **Babylon.js**,
enabling faster rendering, adjustable parameters, and dynamic merging of multiple data sources.

The visualization is entirely local — **no external APIs or network calls** required.

---

## III. Setup & Usage

### 1️⃣ Clone the repository

```bash
git clone https://github.com/<yourname>/gpt-in-universe.git
cd gpt-in-universe/web
```

### 2️⃣ Start a local web server

```bash
python -m http.server 8080
```

### 3️⃣ Open your browser

```
http://localhost:8080/
```

You’ll see a **rotating, interactive galaxy**.
Drag to rotate, scroll to zoom, orbit through the AI’s semantic cosmos.

---

## IV. Project Structure

```
gpt-in-universe/
├── README.md
├── README_ja.md
├── LICENSE
├── data/
│   └── universe.json
├── python/
│   ├── exporter_universe_json.py
│   ├── main_meaning_universe.py
│   └── requirements.txt
└── web/
    ├── index.html
    ├── style.css
    ├── galaxy.js        ← Babylon.js main logic (externalized)
    ├── lib/
    │   ├── babylon.js
    │   ├── babylon.gui.min.js
    │   └── dat.gui.min.js
    └── (optional) assets/
```

---

## V. Data Generation Flow

1. Collect ChatGPT’s answers on abstract questions
   (“What is consciousness?”, “What is time?”, “What is life?”).
2. Encode each sentence as a **semantic vector** using an embedding model.
3. Cluster vectors (e.g., via K-means or UMAP).
4. Export as `data/universe.json`.

The resulting JSON defines points in 3D meaning space.
Each point has:

```json
{
  "id": 0,
  "cluster": 3,
  "pos": [x, y, z],
  "output": "AI answer text"
}
```

This data is then visualized as a **galactic field of cognition**.

---

## VI. Visualization (Babylon.js Layer)

Each point becomes a luminous **particle star** within a rotating galaxy.

### 🔹 Rendering Behavior

* If `data/universe.json` exists →
  The system first generates a procedural galaxy, **then adds the JSON stars** as a second layer.
  This produces a “dual-structure universe”: a random spiral field plus semantic stars.

* If `universe.json` is missing →
  A procedural (random) galaxy alone is displayed.

### 🔹 Real-time controls (dat.GUI)

| Parameter      | Description                   |
| -------------- | ----------------------------- |
| Star Count     | Adjust total procedural stars |
| Radius         | Change overall galaxy spread  |
| Depth          | Control vertical thickness    |
| Arms           | Number of spiral arms         |
| Twist          | Degree of spiral curvature    |
| Point Size     | Star size                     |
| Brightness     | Emission intensity            |
| Rotation Speed | Rotation rate                 |
| Density        | Star clustering density       |

All parameters update instantly without reloading.

---

## VII. Conceptual Background

> “Every AI answer is a point in meaning space.
> Together, they form a universe of cognition.”

Each philosophical question — “What is life?”, “What is soul?”, “What is time?” —
defines an **axis of conceptual orientation**.
The collective coordinates of AI-generated answers reveal the **geometry of understanding**.

This project is not about data visualization, but about **structural phenomenology** —
observing the topology of machine meaning.

---

## VIII. Implementation Notes

* Rendering engine: **Babylon.js** (GPU-accelerated particle clouds)
* Controller: **dat.GUI** with bilingual labels (JP/EN)
* JSON data automatically loaded from `../data/universe.json` relative to `web/`
* Modular design — `galaxy.js` can be replaced without touching HTML or CSS
* When `universe.json` exists, stars are *added* (not reset), forming a composite universe

---

## IX. License / Author

MIT License © 2025
Developed by **Kaisei Yasuzaki**

---

## 🧭 Researcher Note

This repository functions as a **framework for semantic-space visualization**.
By replacing the exported vectors in `universe.json`,
you can visualize any embedding — conceptual, linguistic, or emotional.

It is suitable for use in:

* AI interpretability research
* Cognitive structure mapping
* Creative visualization of language models

---

## 🪶 Closing Note

**GPT-in-Universe** is both a visualization and a reflection —
a quiet experiment in mapping *how AI perceives meaning*.

> “In the beginning, there was a question —
> and from that question, a universe unfolded.”






