# LLM-Guard v0 Specification

## Purpose

LLM-Guard v0 is a **system-level prototype** focused on LLM consistency, reliability, and bounded behavior in long-running usage.

This document is intended to be **handoff-safe**: any AI or engineer can continue development without design drift.

---

## Design Principles (v0-fixed)

* This is **not** an intelligence upgrade
* This is **not** a persona system
* This is **not** an agent framework

LLM-Guard v0 exists to:

* enforce context boundaries
* separate memory storage from memory usage
* detect response drift numerically
* provide explainable logs

---

## v0 Scope Definition

### Included

* Context boundary enforcement
* Memory store / use separation
* Drift detection (single-metric)
* Observability via logs
* CLI-based execution

### Explicitly Excluded

* Persona / personality logic
* Autonomy or planning
* Learning or self-optimization
* UI / Web frontend
* Multi-agent behavior

---

## System Architecture

```
Application
   ↓
LLM-Guard
   ├─ Context Boundary Manager
   ├─ Memory Control
   ├─ Drift Detector
   └─ Observability / Logger
   ↓
LLM (ChatGPT)
```

---

## Module Specifications

### 1. Context Boundary Manager

**Goal:** Prevent context leakage across users, sessions, or scopes.

**Required Input Schema:**

```json
{
  "user_id": "string",
  "session_id": "string",
  "scope": "string",
  "intent": "string"
}
```

**Rules (v0):**

* Only rule-based decisions
* If scope mismatches → exclude
* If session mismatches → exclude
* Ambiguity defaults to exclusion

---

### 2. Memory Control (store ≠ use)

**Memory Types (v0-fixed):**

* FACT
* PREFERENCE
* DECISION

**Storage:**

* All memory can be stored
* SQLite or JSON

**Usage Conditions:**
Memory can be injected **only if all conditions pass**:

* scope match
* intent match
* memory_type allowed
* no conflict flag

---

### 3. Drift Detector

**Purpose:** Quantify response instability.

**Method (v0):**

* Re-run fixed intent prompt
* Convert responses to embeddings
* Compute cosine similarity

**Output Example:**

```json
{
  "intent": "explain_policy",
  "previous_response_id": "r_001",
  "current_response_id": "r_014",
  "similarity": 0.61,
  "status": "drifting"
}
```

**Constraints:**

* Single metric only
* Emphasis on explainability over precision

---

### 4. Observability / Logging

**Required Log Fields:**

* timestamp
* user_id
* session_id
* scope
* intent
* injected_memory_ids
* drift_score

**Format:** JSON (stdout or file)

---

## Technology Stack (v0-fixed)

* Language: Python
* LLM: ChatGPT API
* Embeddings: OpenAI Embeddings API
* Storage: SQLite / JSON
* Execution: CLI

---

## Demo Specification

**demo.py must:**

1. Send identical intent twice
2. Use different sessions or time gaps
3. Detect drift
4. Print logs

**Expected Output:**

```
Drift detected: similarity dropped from 0.91 → 0.58
Injected memories: [FACT_12, DECISION_03]
```

---

## v0 Completion Criteria

LLM-Guard v0 is considered complete when:

* Context boundary logic functions
* Memory store/use separation is enforced
* Drift score is computed and logged
* Demo execution is reproducible

No additional features are required for v0.

---

# Folder Structure (v0-fixed)

```
llm-guard/
├─ README.md
├─ demo.py
├─ requirements.txt
├─ config/
│  └─ settings.yaml
├─ core/
│  ├─ context_boundary.py
│  ├─ memory_control.py
│  ├─ drift_detector.py
│  ├─ logger.py
│  └─ llm_client.py
├─ storage/
│  ├─ memory_store.py
│  └─ logs/
└─ tests/
   └─ test_drift.py
```

---

## README Mandatory Statement

```
LLM-Guard is a prototype demonstrating system-level approaches to LLM reliability.
It intentionally avoids intelligence, autonomy, and persona-based behavior.
```

---

## Development Rule (Handoff Guarantee)

* Do not introduce persona logic
* Do not add learning behavior
* Do not relax boundary conditions
* Any extension must be labeled v1+

This document is the authoritative v0 reference.
