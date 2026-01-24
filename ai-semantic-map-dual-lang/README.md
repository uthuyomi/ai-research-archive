> 🇯🇵 Japanese version available → [README_ja.md](./README_ja.md)

# 🌐 AI Semantic Map (Japanese + English Dual Generator)

**AI Semantic Map** automatically generates two “semantic space maps” —  
a **Japanese version** and an **English version** — from a single question.  
It analyzes multiple AI-generated responses using **TF-IDF, PCA, and KMeans**,  
visualizing the conceptual structure of the AI’s reasoning.

---

## 🚀 Features

- Input a **single question** (either 🇯🇵 Japanese or 🇬🇧 English)
- Automatically collects AI responses via the OpenAI API
- Performs **TF-IDF × Cosine Similarity × PCA × KMeans** semantic analysis
- Extracts representative keywords for each cluster
- Produces an **AI-generated summary** with “common traits / differences / overall tendencies”
- Outputs two high-resolution figures (`figure_ja.png` and `figure_en.png`)

---

## 🧩 Output Example

| Japanese Version                  | English Version                  |
| --------------------------------- | -------------------------------- |
| ![Japanese Figure](figure_ja.png) | ![English Figure](figure_en.png) |

---

## 🧠 Philosophical Background

This project is not about automation —  
it’s about **intellectual expansion through AI as an external cognitive organ.**

It’s built upon three theoretical foundations that explain  
how human cognition evolves through interaction with intelligent systems.

---

### 1️⃣ Extended Mind Theory

> “Thought does not reside solely within the brain;  
> it extends through tools, environments, and others.”

Proposed by Andy Clark and David Chalmers,  
this hypothesis provides the philosophical ground for treating AI as part of our **cognitive network** —  
not a mere tool, but an **active extension of human reasoning**.

---

### 2️⃣ Information Reconstruction Model

> “Intelligence is the ability to reconstruct information.”

Human cognitive systems are limited in how much information they can compress or restructure.  
By cooperating with AI, this capacity expands exponentially —  
not just in speed or scale, but in **structural depth**.  
This process represents an **emergent form of cognitive augmentation.**

---

### 3️⃣ Meta-Cognitive Loop

> “By reflecting on AI’s output, humans reconstruct their own cognitive architecture.”

Through iterative dialogue with AI,  
humans observe and reorganize their own thought processes.  
This self-reflective loop results in the **reconfiguration of meta-cognition** —  
in other words, the mind begins to **reprogram itself**.

---

### ✅ Conclusion

> **“AI makes you smarter”** actually means:  
> the emergence of **Hybrid Intelligence** — a co-intelligent system of human + AI.  
> This phenomenon is philosophically and informationally consistent,  
> with no logical contradictions.

---

## ⚙️ Usage

### 🔧 Setup

```bash
git clone https://github.com/<your-name>/ai-semantic-map-dual-lang.git
cd ai-semantic-map-dual-lang
pip install -r requirements.txt
```
