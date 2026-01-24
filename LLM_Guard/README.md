🛡️ LLM-Guard

System-level reliability primitives for long-running LLM usage

LLM-Guard is a system-focused prototype that demonstrates how to make LLM behavior predictable, bounded, explainable, and auditable over long-running usage.

> ⚠️ This project intentionally avoids intelligence upgrades, autonomy, agents, and persona-based behavior.

LLM-Guard treats LLMs as powerful but fallible system components, not as self-directing entities.




---

📌 Why LLM-Guard Exists

Large Language Models (LLMs) such as ChatGPT are extremely capable in short, stateless interactions.

However, when deployed across long time spans—days, weeks, repeated sessions, or production workloads—system-level failure modes reliably emerge:

Responses drift over time

Context leaks between sessions or users

Past information is reused inconsistently

Safety constraints conflict with continuity

Outputs become hard to explain, audit, or reproduce


These are often treated as model problems.

> LLM-Guard takes a different stance:

This is not a model problem. This is a system design problem.




---

🧩 What LLM-Guard Is (v1)

LLM-Guard v1 is a system-layer control and observability wrapper that sits between an application and an LLM.

It focuses on reliability primitives, not intelligence.

Core primitives

1. Context Boundary Enforcement


2. Explicit Memory Control (store ≠ use)


3. Deterministic Memory Injection


4. Response Drift Detection


5. Policy Evaluation (post-hoc gating)


6. Deterministic Replay (auditability)


7. Explainable, append-only logging



Application
   ↓
LLM-Guard
   ├─ Context Boundary Manager
   ├─ Memory Store & Selector
   ├─ Drift Detector
   ├─ Policy Gate
   ├─ Replay Engine
   └─ Observability / Logger
   ↓
LLM (ChatGPT)


---

🚫 What LLM-Guard Is NOT

LLM-Guard explicitly does not include:

Persona or personality systems

Autonomous decision-making

Agent frameworks

Learning or self-optimization

Prompt engineering tricks

UI / frontend components


> This is a reliability and control prototype, not an intelligence upgrade.




---

🧠 Core Concepts

1️⃣ Context Boundary Enforcement

Every request must explicitly declare:

user_id

session_id

scope

intent


If any boundary mismatches, information is excluded by default.

> Ambiguity is treated as unsafe.



This prevents:

Cross-user leakage

Session contamination

Accidental long-term state bleed



---

2️⃣ Memory Control (store ≠ use)

Memory storage and memory usage are strictly separated.

All memory can be stored

No memory is reused automatically

Injection requires explicit rule-based approval


Supported memory types:

FACT

PREFERENCE

DECISION


This design prevents silent reuse, contradiction, and unintended accumulation.


---

3️⃣ Deterministic Memory Injection

Injected memory is:

Explicit

Deterministic

Order-stable

Fully traceable by memory ID


Same inputs → same injected text.

If conflicts are detected (via conflict_key), all injection is blocked.


---

4️⃣ Drift Detection

LLM-Guard quantifies response drift using a single explainable metric:

Embedding-based cosine similarity


This detects when:

> "The same intent no longer produces the same answer."



Precision is intentionally secondary to auditability and interpretability.


---

5️⃣ Policy Gate (Post-drift)

Policy decisions are evaluated after drift is measured.

Policies are:

Declarative

Deterministic

Non-learning


Example policies:

Block if drift exceeds threshold

Raise incident flags

Allow continuation with warnings


No hidden inference. No state mutation.


---

6️⃣ Deterministic Replay (Audit)

Every policy decision can be replayed using recorded inputs:

No model calls

No time dependency

No randomness


Identical inputs always produce identical decisions.

This enables:

Incident audits

Post-mortem analysis

Compliance verification



---

7️⃣ Observability & Logging

Each interaction emits a single canonical JSON log line containing:

Context identifiers

Injected memory IDs

Drift scores

Policy decisions

Replay verification


Logs are:

JSON-only

Append-only

Machine-parseable


Designed for traceability, not dashboards.


---

▶️ Demo

The included CLI demo shows the full v1 pipeline working end-to-end.

Requirements

Python 3.10+

OpenAI API key


Run

export OPENAI_API_KEY=your_api_key
pip install -r requirements.txt
python demo.py

Demo behavior

Sends the same intent across two sessions

Applies boundary filtering

Attempts deterministic memory injection

Measures drift

Evaluates policy

Replays the policy decision

Emits a canonical JSON log



---

🗂️ Project Structure

llm-guard/
├─ README.md
├─ demo.py
├─ requirements.txt
├─ core/
│  ├─ llm_client.py
│  ├─ context_boundary.py
│  ├─ memory_control.py
│  ├─ drift_detector.py
│  ├─ policy_gate.py
│  ├─ replay_engine.py
│  └─ logger.py
├─ storage/
│  ├─ memory.json
│  └─ logs/
└─ tests/


---

🔖 Versioning

v1: System-level reliability, policy gating, deterministic replay (current)


Future versions are intentionally undefined and driven by real operational feedback.


---

🎯 Intended Audience

LLM-Guard is designed for:

Engineers operating LLMs in production

AI platform / infrastructure teams

Reliability & safety engineers

Teams building long-running LLM-backed systems


It is not optimized for demos, marketing, or prompt engineering tutorials.


---

📦 Status

LLM-Guard v1 is feature-complete within its declared scope.

Small by design. Opinionated by necessity.


---

📄 License

MIT License