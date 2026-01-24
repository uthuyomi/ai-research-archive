# ====================================================
# 🌐 GPT-in-Axis Server (Semantic Embedding Version)
# ====================================================
# English: Flask + Socket.IO backend visualizing AI-human conversation using semantic vector coordinates.
# 日本語: OpenAIの意味ベクトルを用いてAIと人間の会話を3軸構造で可視化するサーバー。

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from dotenv import load_dotenv
from datetime import datetime
import os, json, time, random
import numpy as np

# ----------------------------------------------------
# 🌱 Environment Setup
# ----------------------------------------------------
load_dotenv()

# ----------------------------------------------------
# 🔑 OpenAI Initialization
# ----------------------------------------------------
try:
    from openai import OpenAI
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except Exception:
    client = None

# ----------------------------------------------------
# ⚙️ Flask + Socket.IO
# ----------------------------------------------------
app = Flask(__name__, static_folder='.', static_url_path='')
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# ----------------------------------------------------
# 📂 Data Directories
# ----------------------------------------------------
DATA_DIR = "data"
LOGS_DIR = os.path.join(DATA_DIR, "logs")
CUR_FILE = os.path.join(DATA_DIR, "current_session.txt")

# ----------------------------------------------------
# 🗂️ Initialize Data Environment
# ----------------------------------------------------
def ensure():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    sample = os.path.join(DATA_DIR, "sample-axis.json")
    if not os.path.exists(sample):
        with open(sample, "w", encoding="utf-8") as f:
            json.dump({
                "nodes":[
                    {"id":"Q1","type":"question","text":"AIとは何か？","logic":0.2,"emotion":0.4,"abstract":0.6,"importance":0.8},
                    {"id":"A1","type":"answer","text":"AIは人間の知的行動を模倣する技術群です。","logic":0.5,"emotion":0.3,"abstract":0.7,"importance":0.7}
                ],
                "vectors":[{"from":"Q1","to":"A1","type":"response","strength":0.9}]
            }, f, ensure_ascii=False, indent=2)
    if not os.path.exists(CUR_FILE):
        with open(CUR_FILE, "w", encoding="utf-8") as f:
            f.write("sample-axis")

ensure()

# ----------------------------------------------------
# 🔖 Session Utilities
# ----------------------------------------------------
def current_session_id():
    with open(CUR_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def session_path(sid):
    return os.path.join(DATA_DIR, f"{sid}.json")

def read_axis(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_axis(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------------------------------------------
# 🧠 Embedding Utility
# ----------------------------------------------------
def semantic_coords(text: str):
    """
    English: Get 3D coordinates from text embeddings (1536→3D via PCA-lite)
    日本語: テキストから埋め込みベクトルを取得し、3次元座標へ射影する
    """
    if not client:
        return [random.random() for _ in range(3)]
    try:
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        vec = np.array(resp.data[0].embedding[:9])  # 9要素抜粋
        # PCA-lite: reshape(3,3)平均
        m = vec.reshape(3,3)
        coords = m.mean(axis=1)
        # normalize 0〜1範囲へ
        coords = (coords - coords.min()) / (coords.max() - coords.min() + 1e-8)
        return coords.tolist()
    except Exception:
        return [random.random() for _ in range(3)]

# ----------------------------------------------------
# 🧠 OpenAI / Dummy Response
# ----------------------------------------------------
def ask_openai(q: str, model: str) -> str:
    if client:
        try:
            resp = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[
                    {"role":"system","content":"あなたは論理・感情・抽象の三軸を意識して回答するアシスタントです。"},
                    {"role":"user","content": q}
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return f"(fallback) {q} に対する簡易回答です。"
    return f"『{q}』への簡易な応答です。（デモ）"

# ----------------------------------------------------
# 🧾 Conversation Log (memory)
# ----------------------------------------------------
conversation_log = []

# ----------------------------------------------------
# 🌐 API: /ask
# ----------------------------------------------------
@app.post("/ask")
def ask():
    body = request.get_json() or {}
    q = (body.get("question") or "").strip()
    model = body.get("model") or "gpt-4o-mini"
    if not q:
        return jsonify(success=False, error="empty question"), 400

    # --- generate AI response ---
    a = ask_openai(q, model)

    # --- load current session ---
    sid = current_session_id()
    path = session_path(sid)
    axis = read_axis(path) if os.path.exists(path) else {"nodes":[], "vectors":[]}

    # --- new node id ---
    n = sum(1 for n in axis["nodes"] if n.get("type")=="question") + 1

    # --- semantic coordinate extraction ---
    qvec = semantic_coords(q)
    avec = semantic_coords(a)

    qnode = {
        "id": f"Q{n}",
        "type": "question",
        "text": q,
        "logic": round(float(qvec[0]), 3),
        "emotion": round(float(qvec[1]), 3),
        "abstract": round(float(qvec[2]), 3),
        "importance": 0.8
    }
    anode = {
        "id": f"A{n}",
        "type": "answer",
        "text": a,
        "logic": round(float(avec[0]), 3),
        "emotion": round(float(avec[1]), 3),
        "abstract": round(float(avec[2]), 3),
        "importance": 0.7
    }

    # --- update axis ---
    axis["nodes"].extend([qnode, anode])
    axis["vectors"].append({
        "from": qnode["id"],
        "to": anode["id"],
        "type": "response",
        "strength": 0.9
    })
    write_axis(path, axis)

    # --- append log ---
    conversation_log.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "session_id": sid,
        "question": q,
        "answer": a,
        "coords": {"question": qvec, "answer": avec}
    })

    socketio.emit("new_nodes", {"q": qnode, "a": anode})
    return jsonify(success=True)

# ----------------------------------------------------
# 🌐 Session Controls
# ----------------------------------------------------
@app.post("/session/new")
def new_session():
    sid = f"axis_{int(time.time())}"
    write_axis(session_path(sid), {"nodes":[], "vectors":[]})
    with open(CUR_FILE, "w", encoding="utf-8") as f:
        f.write(sid)
    return f"new session {sid}", 200

@app.get("/session/list")
def list_session():
    files = [os.path.splitext(f)[0] for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    cur = current_session_id()
    return jsonify(sessions=sorted(files), current=cur)

@app.get("/session/load")
def load_session():
    sid = (request.args.get("id") or "").strip()
    if not sid: return "missing id", 400
    p = session_path(sid)
    if not os.path.exists(p): return "not found", 404
    with open(CUR_FILE, "w", encoding="utf-8") as f:
        f.write(sid)
    return f"loaded {sid}", 200

# ----------------------------------------------------
# 🌐 Log View & Save
# ----------------------------------------------------
@app.get("/log")
def get_log():
    return jsonify(conversation_log)

@app.post("/log/save")
def save_log():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sid = current_session_id()
    out_path = os.path.join(LOGS_DIR, f"{sid}_log_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(conversation_log, f, ensure_ascii=False, indent=2)
    return jsonify(success=True, path=out_path)

# ----------------------------------------------------
# 🌐 Root
# ----------------------------------------------------
@app.get("/")
def root():
    return send_from_directory(".", "index.html")

# ----------------------------------------------------
# 🚀 Entry
# ----------------------------------------------------
if __name__ == "__main__":
    print("🚀 GPT-in-Axis (Semantic) running on http://localhost:8080")
    socketio.run(app, host="0.0.0.0", port=8080, debug=False)