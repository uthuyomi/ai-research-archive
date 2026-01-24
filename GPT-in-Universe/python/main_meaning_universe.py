# ==============================================================
# 🌌 AI Meaning Universe — main_meaning_universe.py
# 日本語の複数質問 → 回答群生成 → TF-IDF → PCA(3D) → KMeans
# → universe.json（Three.js用）とCSVを出力
# 依存: openai, pandas, numpy, scikit-learn, matplotlib(任意), tqdm
# ==============================================================
# English: Entry script for generating an "AI Meaning Universe":
# - Ask multiple Japanese philosophical questions
# - Generate multiple answers via OpenAI API
# - Vectorize with TF-IDF, reduce to 3D with PCA, cluster with KMeans
# - Export CSV for analysis and universe.json for Three.js visualization
# 日本語: 「AI Meaning Universe」を生成するエントリースクリプト。
# ・複数の哲学的質問を日本語で投げる
# ・OpenAI APIで複数回答を生成
# ・TF-IDFでベクトル化→PCAで3次元化→KMeansでクラスタリング
# ・解析用CSVとThree.js可視化用universe.jsonを出力

import os
import re
import json
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# --- 日本語フォント対策（任意） ---
# English: Optional Japanese font setup for matplotlib (useful for local debugging/plots).
# 日本語: 解析時の日本語表示崩れ対策（matplotlibでのデバッグ可視化向け、任意）。
try:
    import matplotlib.pyplot as plt  # 解析デバッグで使うなら
    import matplotlib.font_manager as fm
    if os.name == "nt":
        FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"  # 必要に応じて変更
        if os.path.exists(FONT_PATH):
            plt.rcParams["font.family"] = fm.FontProperties(fname=FONT_PATH).get_name()
            plt.rcParams["axes.unicode_minus"] = False
    try:
        import japanize_matplotlib  # noqa: F401
    except Exception:
        pass
except Exception:
    pass

# --- OpenAI SDK ---
# English: Initialize OpenAI client. Prefer setting OPENAI_API_KEY via environment variable.
# 日本語: OpenAIクライアントの初期化。APIキーは環境変数OPENAI_API_KEYで設定推奨。
from openai import OpenAI
client = OpenAI(api_key="")  # 環境変数 OPENAI_API_KEY が必要

# --- JSONエクスポート関数 ---
# 同ディレクトリまたはパスを通した上で読み込み
# English: Export helper for Three.js universe.json; must exist in import path.
# 日本語: Three.js向けuniverse.jsonを書き出す補助関数。importパス上に配置しておくこと。
from exporter_universe_json import export_universe_json


# ==========================
# 設定
# ==========================
# English: Model name used for chat completions.
# 日本語: 回答生成に用いるモデル名。
MODEL = "gpt-4o"

# ★ここを編集：質問リスト／サンプル数
# English: List of prompts (questions). Keep them concise; model returns short answers (<=30 chars).
# 日本語: 質問文の一覧。短文回答（30文字以内）を想定。
QUESTIONS: List[str] = [
    "人間とは何か？30文字以内で答えてください。",
    "魂とは何か？30文字以内で答えてください。",
    "AIとは何か？30文字以内で答えてください。",
    "生命とは何か？30文字以内で答えてください。",
    "意識とは何か？30文字以内で答えてください。",
    "時間とは何か？30文字以内で答えてください。",
    "宇宙とは何か？30文字以内で答えてください。"
]

# English: Number of samples per question; larger values give denser clouds but take more tokens/time.
# 日本語: 質問ごとの生成回数。大きくすると分布が安定するがコスト/時間増。
NUM_SAMPLES_PER_QUESTION = 15   # フルスケールなら 20〜50 推奨
# English: Number of clusters. If None, it is estimated from point count (see auto_k).
# 日本語: クラスタ数。Noneならデータ点数から自動推定（auto_k参照）。
NUM_CLUSTERS = None             # 自動推定（固定なら整数）

# 出力先（プロジェクトルートから見た相対パスを想定）
# English: Output paths (relative to project root). CSV for raw dataset; JSON for Three.js.
# 日本語: 出力先。CSVは生データ、JSONはThree.js可視化用。
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CSV_OUT = os.path.join(DATA_DIR, "ai_universe_dataset.csv")
JSON_OUT = os.path.join(DATA_DIR, "universe.json")

# 乱数固定（再現性）
# English: Random seed for reproducibility across PCA/KMeans.
# 日本語: PCA/KMeans等の再現性を保つ乱数シード。
RANDOM_STATE = 42


# ==========================
# データ収集
# ==========================
# English: Generate multiple answers for each question via OpenAI Chat Completions.
# - Returns a DataFrame with columns: QID, Question, Output
# 日本語: 各質問に対してOpenAIのChat Completionsで複数回答を生成。
# ・返値はQID/Question/Output列を持つDataFrame。
def generate_answers(questions: List[str], n_per_q: int) -> pd.DataFrame:
    rows = []
    for qi, q in enumerate(questions):
        print(f"🔹 問い {qi+1}/{len(questions)}: '{q}' を {n_per_q} 回生成…")
        for _ in tqdm(range(n_per_q)):
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": q}],
            )
            # English: Normalize newline to space and strip; store as one-line text.
            # 日本語: 改行を空白に変換しstrip、1行テキストとして保持。
            text = res.choices[0].message.content.strip().replace("\n", " ")
            rows.append({"QID": qi, "Question": q, "Output": text})
    df = pd.DataFrame(rows)
    return df


# ==========================
# 前処理・ベクトル化・次元削減・クラスタ
# ==========================
# English: TF-IDF vectorization -> PCA to 3D.
# - Returns (fitted vectorizer, sparse matrix X, 3D numpy array pts3)
# 日本語: TF-IDFでベクトル化→PCAで3次元化。
# ・(学習済みvectorizer, 疎行列X, 3次元座標pts3)を返す。
def vectorize_and_reduce(outputs: pd.Series) -> Tuple[TfidfVectorizer, np.ndarray, np.ndarray]:
    """TF-IDFベクトル化し、PCAで3次元に還元。"""
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(outputs)
    pca = PCA(n_components=3, random_state=RANDOM_STATE)
    # English: Convert sparse TF-IDF to dense before PCA.
    # 日本語: PCA適用のため疎行列をdenseに変換。
    pts3 = pca.fit_transform(X.toarray())
    return vectorizer, X, pts3


# English: Heuristic to estimate number of clusters from point count.
# 日本語: データ点数からクラスタ数を概算するヒューリスティック。
def auto_k(n_points: int) -> int:
    """点数からラフにクラスタ数を推定。"""
    # ざっくり：15点につき1クラスタ、6〜16の範囲にクリップ
    # English: ~1 cluster per 15 points, clamped to [6, 16].
    # 日本語: およそ15点につき1クラスタ、[6,16]にクリップ。
    k = int(np.clip(np.round(n_points / 15), 6, 16))
    return k


# English: Run KMeans on X. If num_clusters is None, infer via auto_k.
# - Returns (fitted kmeans, labels array)
# 日本語: KMeansによるクラスタリング。num_clustersがNoneならauto_kで推定。
# ・(学習済みkmeans, ラベル配列)を返す。
def cluster_points(X, num_clusters: int | None) -> Tuple[KMeans, np.ndarray]:
    if num_clusters is None:
        k = auto_k(X.shape[0])
    else:
        k = int(num_clusters)
    # English: n_init="auto" (scikit-learn ≥1.4) for robust initialization.
    # 日本語: 初期化回数は"auto"（scikit-learn ≥1.4想定）で安定性を確保。
    kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init="auto")
    labels = kmeans.fit_predict(X)
    return kmeans, labels


# English: For each cluster center, pick top-N terms by weight; join with "・".
# 日本語: 各クラスタ中心の重み上位語を抽出し、「・」で連結して返す。
def cluster_top_terms(vectorizer: TfidfVectorizer, kmeans: KMeans, topn: int = 5) -> List[str]:
    """各クラスタの上位語を‘・’で連結して返す。"""
    terms = np.array(vectorizer.get_feature_names_out())
    order = kmeans.cluster_centers_.argsort()[:, ::-1]
    out = []
    for i in range(order.shape[0]):
        top = terms[order[i, :topn]]
        out.append("・".join(top))
    return out


# ==========================
# 要約（全体）
# ==========================
# English: Summarize the entire answer set (JA/EN). This is optional for visualization
# but useful for logging/analysis. Uses the same MODEL.
# 日本語: 全回答集合の要約（日本語/英語）。可視化には不要だが記録・解析に有用。
# 生成には同一MODELを使用。
def summarize_all(df: pd.DataFrame, lang: str = "ja") -> str:
    joined = "\n".join(df["Output"].tolist())

    if lang == "ja":
        prompt = f"""
次のAIの回答群は、複数の哲学的問い（例：{ '、'.join(QUESTIONS[:3]) } …）に対するものです。
この集合から、AIがそれらの概念をどのように理解しているかを
①共通点 ②相違点 ③分布傾向（どの方向に解釈が寄るか）
の3項目で、平易な日本語で要約してください。
【回答群】
{joined}
"""
    else:
        prompt = f"""
These are AI-generated answers to multiple philosophical questions
(e.g., {"; ".join(QUESTIONS[:3])} …).
Please summarize how the AI seems to understand these concepts in three parts:
(1) Common points, (2) Differences, and (3) Overall tendencies of interpretation.
Use simple, clear English.
[Outputs]
{joined}
"""
    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content.strip()


# ==========================
# メイン
# ==========================
# English: Orchestrates the pipeline:
# 1) Generate data -> CSV
# 2) TF-IDF + PCA(3D)
# 3) KMeans clustering
# 4) Extract top terms per cluster
# 5) (Optional) Summarize all outputs (JA/EN) to text files
# 6) Export Three.js-ready universe.json
# 日本語: 全処理の実行順序:
# 1) 回答生成→CSV保存
# 2) TF-IDF＋PCA(3D)
# 3) KMeansでクラスタリング
# 4) クラスタごとの代表語抽出
# 5) （任意）全体要約（JA/EN）をテキストに保存
# 6) Three.js用universe.jsonを書き出し
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1) 収集
    # English: Generate answers and save raw dataset for reproducibility and external analysis.
    # 日本語: 回答を生成し、生データをCSVに保存（再現性・外部解析のため）。
    df = generate_answers(QUESTIONS, NUM_SAMPLES_PER_QUESTION)
    df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
    print(f"💾 CSV: {CSV_OUT}")

    # 2) ベクトル化＋PCA(3D)
    # English: Convert texts to TF-IDF vectors and reduce to 3D coordinates for visualization.
    # 日本語: テキスト→TF-IDF化し、可視化用に3次元座標へ次元圧縮。
    vectorizer, X, pts3 = vectorize_and_reduce(df["Output"])

    # 3) クラスタリング
    # English: Cluster points; attach labels back to DataFrame for downstream exports.
    # 日本語: 点群をクラスタリングし、ラベルをDataFrameへ付与。
    kmeans, labels = cluster_points(X, NUM_CLUSTERS)
    df["Cluster"] = labels

    # 4) 代表語
    # English: Print human-readable top terms for quick sanity check of each cluster.
    # 日本語: 各クラスタの代表語を出力（人間の目での素早い検証用）。
    top_terms = cluster_top_terms(vectorizer, kmeans, topn=5)
    print("🧠 各クラスタ代表語:")
    for i, t in enumerate(top_terms):
        print(f"  C{i}: {t}")

    # 5) 全体要約（任意／Three.jsには不要だがログとして）
    # English: Generate and persist summaries (JA/EN). Fail safe: skip on any exception.
    # 日本語: 日英の要約文を生成して保存。失敗しても処理継続（例外は握りつぶす）。
    try:
        summary_ja = summarize_all(df, lang="ja")
        summary_en = summarize_all(df, lang="en")
        with open(os.path.join(DATA_DIR, "summary_ja.txt"), "w", encoding="utf-8") as f:
            f.write(summary_ja)
        with open(os.path.join(DATA_DIR, "summary_en.txt"), "w", encoding="utf-8") as f:
            f.write(summary_en)
        print("💾 summaries: summary_ja.txt / summary_en.txt")
    except Exception as e:
        print(f"要約はスキップ: {e}")

    # 6) Three.js用の universe.json を出力
    # English: Final export for front-end visualization. The exporter handles schema/format.
    # 日本語: 最終的なThree.js可視化向け出力。フォーマットはexporter側に委譲。
    export_universe_json(
        outfile=JSON_OUT,
        points3d=pts3,
        labels=labels,
        df=df[["Question", "Output"]],
        cluster_terms=top_terms,
        questions=QUESTIONS
    )
    print(f"✅ 完了: {JSON_OUT}")


if __name__ == "__main__":
    main()
    # English: Standard Python entry point.
    # 日本語: Pythonスクリプトの標準エントリーポイント。
