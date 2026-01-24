# ==============================================================
# 🌐 AI Semantic Map — Dual-Language Visualization (JA & EN)
# ==============================================================
# 🏷️ Overview / 概要
# --------------------------------------------------------------
# This script generates two semantic maps from a single question.
# It automatically translates the question (JA ↔ EN),
# then visualizes how AI perceives the same concept in both languages.
#
# 日本語または英語の質問を1つ入力すると、
# 自動的にもう一方の言語に翻訳し、
# 「日本語版」と「英語版」の2つの意味空間マップを生成します。
# --------------------------------------------------------------
# Author : 安崎 海星 (Kaisei Yasuzaki)
# Model  : GPT-4o
# Version: 4.0 (2025)
# ==============================================================

from openai import OpenAI
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.font_manager as fm
import textwrap, re

# ==============================================================
# ⚙️ 1. Configuration / 基本設定
# ==============================================================
client = OpenAI(api_key="")  # ← 各自のAPIキーに変更

num_samples = 10  # Responses per language / 言語ごとのサンプル数

font_path_ja = "C:/Windows/Fonts/meiryo.ttc"  # Meiryo for Japanese
font_en = "Arial"  # Fallback for English
plt.rcParams["axes.unicode_minus"] = False


# ==============================================================
# 🧠 2. Core Function — Generate One Semantic Map per Language
# ==============================================================
def generate_semantic_map(question, lang="ja"):
    """
    Generate a semantic visualization for one language.
    1言語分の意味空間マップを生成。
    """

    # ---------- Theme & Font Settings / テーマとフォント ----------
    if lang == "ja":
        color_theme = plt.cm.Blues
        lang_label = "日本語版"
        title_color = "#3fa9f5"
        fm.fontManager.addfont(font_path_ja)
        plt.rcParams["font.family"] = fm.FontProperties(fname=font_path_ja).get_name()
        sep = "・"
    else:
        color_theme = plt.cm.Oranges
        lang_label = "English Version"
        title_color = "#ffa600"
        plt.rcParams["font.family"] = font_en
        sep = " / "

    bg_color = "#0d1117"

    # ==============================================================
    # 🧩 Step 1: Collect AI Responses / 応答収集
    # ==============================================================
    responses = []
    for i in range(num_samples):
        res = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": question}],
        )
        text = res.choices[0].message.content.strip().replace("\n", " ")
        responses.append({"No": i + 1, "Output": text})
    df = pd.DataFrame(responses)

    # ==============================================================
    # 🧮 Step 2: TF-IDF → PCA → KMeans / ベクトル化・次元削減・クラスタ化
    # ==============================================================
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(df["Output"])
    pca = PCA(n_components=3)
    points = pca.fit_transform(vectors.toarray())

    kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(vectors)
    df["Cluster"] = labels

    # ---------- Extract Cluster Labels / クラスタ代表語 ----------
    terms = np.array(vectorizer.get_feature_names_out())
    order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
    cluster_labels = [
        sep.join(terms[order_centroids[i, :3]]) for i in range(len(order_centroids))
    ]

    # ==============================================================
    # 🧩 Step 3: Summary Generation / 要約生成
    # ==============================================================
    if lang == "ja":
        summary_prompt = f"""
        以下はAIが「{question}」という質問に対して出力した回答群です。
        これらからAIがこの概念をどう捉えているかを、
        ①共通点　②相違点　③全体の傾向
        の3点で要約してください。
        【回答群】
        {chr(10).join(df['Output'].tolist())}
        """
    else:
        summary_prompt = f"""
        Below are AI responses to the question: "{question}".
        Summarize how AI perceives this concept in three parts:
        ① Common traits, ② Differences, ③ Overall tendencies.
        [Responses]
        {chr(10).join(df['Output'].tolist())}
        """

    summary_res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": summary_prompt}],
    )
    summary_text = summary_res.choices[0].message.content.strip()

    # ==============================================================
    # 🎨 Step 4: Visualization / 可視化
    # ==============================================================
    fig = plt.figure(figsize=(13, 8), facecolor=bg_color)
    ax3d = fig.add_subplot(2, 2, 1, projection="3d", facecolor=bg_color)
    ax_pie = fig.add_subplot(2, 2, 2, facecolor=bg_color)
    ax_txt = fig.add_subplot(2, 1, 2, facecolor=bg_color)

    colors = color_theme(np.linspace(0.5, 1, num_samples))

    # ---------- Scatter Plot / 散布図 ----------
    for i, row in df.iterrows():
        ax3d.scatter(
            points[i, 0], points[i, 1], points[i, 2],
            c=[colors[i % num_samples]], s=90, edgecolors="white",
            linewidths=0.6, alpha=0.85, marker="o"
        )
        ax3d.text(
            points[i, 0], points[i, 1], points[i, 2],
            str(row["No"]), fontsize=8, color="white", ha="center"
        )

    ax3d.set_title("AI Semantic Space", color="white", fontsize=12)
    ax3d.set_xlabel("Axis 1", color="white")
    ax3d.set_ylabel("Axis 2", color="white")
    ax3d.set_zlabel("Axis 3", color="white")
    ax3d.grid(False)
    ax3d.tick_params(colors="gray")

    # ---------- Cluster Pie / クラスタ分布 ----------
    unique, counts = np.unique(labels, return_counts=True)
    wrapped_labels = [
        "\n".join(textwrap.wrap(f"{cluster_labels[i]} ({counts[i]/len(labels)*100:.1f}%)", width=20))
        for i in unique
    ]
    ax_pie.pie(
        counts,
        labels=wrapped_labels,
        colors=color_theme(np.linspace(0.2, 1, len(unique))),
        textprops={"fontsize": 9, "color": "white"},
        wedgeprops={"edgecolor": "white", "linewidth": 0.6},
    )
    ax_pie.set_title("Cluster Distribution", color="white", fontsize=12)

    # ---------- Summary Box / 要約テキスト ----------
    ax_txt.axis("off")
    sections = re.split(r"(?=①|②|③)", summary_text)
    formatted_sections = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        wrapped = textwrap.fill(sec, width=85)
        formatted_sections.append(wrapped)
    formatted_text = "\n\n".join(formatted_sections)

    ax_txt.text(
        0.02, 0.98, formatted_text,
        fontsize=10, color="white", va="top", ha="left", linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.6", fc="#111", ec="white", alpha=0.15)
    )

    summary_title = "🧩 AI自己要約" if lang == "ja" else "🧩 AI Self-Summary"
    ax_txt.set_title(summary_title, color="white", loc="left", fontsize=13, pad=12)

    # ---------- Titles / タイトル ----------
    fig.suptitle(f"🌐 AI Meaning Map — {lang_label}", fontsize=15, color=title_color, weight="bold")
    subtitle = f"質問：{question}" if lang == "ja" else f"Question: {question}"
    fig.text(0.5, 0.95, subtitle, ha="center", color="lightgray")

    plt.tight_layout(pad=2)
    plt.show()
    # plt.savefig(f"figure_{lang}.png", dpi=300, bbox_inches='tight')  # 保存したい場合ここを有効化


# ==============================================================
# 🚀 3. Main: Input Once → Dual Output / 質問1つで2言語出力
# ==============================================================
question_input = "魂とは何か？30文字以内で答えてください。"

# ---------- Auto Translation / 自動翻訳 ----------
translation_prompt = f"Translate this question into natural English: {question_input}"
translation_res = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": translation_prompt}],
)
question_en = translation_res.choices[0].message.content.strip()

# ---------- Generate Both Figures / 両言語の図を生成 ----------
generate_semantic_map(question_input, lang="ja")
generate_semantic_map(question_en, lang="en")
