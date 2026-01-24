# ==============================================================
# 🌌 exporter_universe_json.py
# AI Meaning Universe — Three.js用データ出力モジュール
# ==============================================================
# English: Module for exporting AI Meaning Universe data into a JSON format usable in Three.js visualization.
# 日本語: Three.jsによる可視化用にAI Meaning UniverseデータをJSON形式で出力するモジュール。

import json
import numpy as np


def export_universe_json(
    outfile: str,
    points3d: np.ndarray,
    labels: np.ndarray,
    df,
    cluster_terms,
    questions,
):
    """
    points3d: (N, 3) 位置情報 (PCA結果)
    labels: 各点のクラスタID
    df: DataFrame（Question, Output含む）
    cluster_terms: 各クラスタ代表語（上位語5個程度）
    questions: 入力質問リスト
    """
    # English:
    #   Export a 3D "universe" dataset combining PCA results, cluster info, and text outputs
    #   into a structured JSON for front-end rendering (Three.js).
    # 日本語:
    #   PCA結果・クラスタ情報・テキスト出力を統合した「宇宙データセット」を
    #   Three.jsフロントエンド向けの構造化JSONとして出力する関数。

    data = []
    # English: Iterate over each record (row) of the DataFrame and build the data payload.
    # 日本語: DataFrameの各行を処理し、出力用データペイロードを構築。
    for i in range(len(df)):
        # English: If "QID" exists, cast it to int; else set to 0.
        # 日本語: "QID"列が存在すればint化、なければ0。
        qid = int(df.iloc[i]["QID"]) if "QID" in df.columns else 0
        # English: Original question text.
        # 日本語: 元の質問文。
        q = df.iloc[i]["Question"]
        # English: Model-generated output (short philosophical answer).
        # 日本語: モデルが生成した短い哲学的回答。
        o = df.iloc[i]["Output"]
        # English: Extract the PCA 3D coordinates for this point.
        # 日本語: PCAで得られた3次元座標を取得。
        x, y, z = points3d[i]
        # English: Cluster ID assigned by KMeans.
        # 日本語: KMeansによって割り当てられたクラスタID。
        cluster = int(labels[i])

        # English: Append a dictionary representing a single data point in the universe.
        # 日本語: 宇宙内の1点を表す辞書オブジェクトを追加。
        data.append({
            "id": i,
            "question": q,
            "output": o,
            "cluster": cluster,
            "qid": qid,
            "pos": [float(x), float(y), float(z)]
        })

    # English: Build metadata for each cluster including representative terms.
    # 日本語: 各クラスタに対応する代表語（特徴語）のメタ情報を作成。
    clusters_meta = [
        {"id": i, "terms": cluster_terms[i]}
        for i in range(len(cluster_terms))
    ]

    # English:
    #   Construct final JSON payload containing meta info, clusters, and all 3D points.
    #   Structure:
    #   {
    #       "meta": {...},
    #       "clusters": [...],
    #       "points": [...]
    #   }
    # 日本語:
    #   メタ情報・クラスタ・全ポイントデータを含む最終JSON構造を構築。
    #   構造:
    #   {
    #       "meta": {...},
    #       "clusters": [...],
    #       "points": [...]
    #   }
    payload = {
        "meta": {
            "total_points": len(df),            # English: Total number of data points / 日本語: データ点の総数
            "num_clusters": len(cluster_terms), # English: Number of clusters / 日本語: クラスタ数
            "questions": questions,             # English: List of input questions / 日本語: 入力質問リスト
        },
        "clusters": clusters_meta,
        "points": data
    }

    # English:
    #   Write the payload to a JSON file with UTF-8 encoding.
    #   ensure_ascii=False → keeps Japanese readable.
    # 日本語:
    #   構築したペイロードをUTF-8でJSONファイルに書き出す。
    #   ensure_ascii=Falseにより日本語も可読な形で保存。
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # English: Print confirmation with file path.
    # 日本語: 出力完了メッセージを表示。
    print(f"💾 Universe JSON Exported: {outfile}")
