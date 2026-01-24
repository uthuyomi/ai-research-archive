# SPEC-01 システム構成・責務分離

---

## 1. 本章の目的

本章では、touhou-talk × VS Code 連携システムにおける
**全コンポーネントの構成・責務・境界**を明確に定義する。

ここで定義される内容は、

* 実装判断の迷いを排除する
* 責務の越境・重複を防ぐ
* AI による誤った補完・推論を防止する

ための **基準点** である。

---

## 2. システム全体構成（固定）

```
[ Browser / Chat UI ]
        ↑↓  HTTP (poll / event)
[ touhou-talk Backend ]
        ↑↓  HTTP (pull)
[ VS Code Extension ]
```

### 固定ルール

* UI と Extension は **直接通信しない**
* Backend が **唯一の通信ハブ**
* すべての状態は Backend に集約される

---

## 3. コンポーネント一覧

| コンポーネント           | 実体                | 主な責務              |
| ----------------- | ----------------- | ----------------- |
| Chat UI           | Browser / Next.js | 描画・ユーザー操作送信       |
| Backend           | touhou-talk       | 状態管理・判断・Message生成 |
| VS Code Extension | VS Code API       | 観測・編集実行           |
| SDK Adapter       | LLM SDK           | 説明・要約・レビュー生成      |

---

## 4. Chat UI の責務（固定）

### 4.1 やること

* Backend から Message を取得して描画
* ChangePlan に対する

  * Approve
  * Reject
* 再スキャン要求の送信

### 4.2 やらないこと（厳守）

* 状態（ProjectState / ChangePlan）を保持しない
* diff を扱わない
* apply を直接呼ばない
* Extension と通信しない

### 4.3 設計原則

* **表示専用**
* 判断結果は Message を通じてのみ反映

---

## 5. Backend の責務（固定）

### 5.1 やること

* ProjectState の保存・世代管理
* ChangePlan の生成・状態管理
* ApplyHistory の保存
* SDK Adapter を用いた説明生成
* UI 向け Message の生成

### 5.2 やらないこと（厳守）

* Workspace を直接編集しない
* UI の表示ロジックを持たない
* Extension の内部状態を保持しない

### 5.3 Backend は唯一の正

* すべての状態遷移は Backend で決定される
* 他コンポーネントは **要求のみ** 行う

---

## 6. VS Code Extension の責務（固定）

### 6.1 やること

* Workspace 構造の観測
* ProjectState の収集
* Backend への状態送信
* ChangePlan の apply（唯一の実行主体）
* apply 後の再スキャン

### 6.2 やらないこと（厳守）

* ChangePlan の生成
* 承認・却下の判断
* UI の表示
* SDK の直接呼び出し

---

## 7. SDK Adapter の責務（固定）

### 7.1 やること

* ProjectState の説明生成
* Diagnostics の整理・要約
* ChangePlan の説明・レビュー生成

### 7.2 やらないこと（厳守）

* 事実（ProjectState）を生成・補完
* ChangePlan の承認可否判断
* diff の生成・適用

---

## 8. コンポーネント間通信の原則

### 8.1 UI → Backend

* HTTP
* イベント送信のみ
* 状態更新は Message を待つ

### 8.2 Backend → UI

* HTTP poll
* Message 配信のみ

### 8.3 Extension → Backend

* HTTP
* pull 主体
* ProjectState / ApplyResult の送信

### 8.4 Backend → Extension

* push しない
* 応答データとしてのみ返す

---

## 9. 越境禁止ルール（重要）

以下は **明示的に禁止** される。

* UI が ProjectState を変更する
* UI が apply を実行する
* Extension が判断を行う
* SDK が状態を更新する
* Backend が Workspace を直接操作する

---

## 10. 本章で確定したこと

* 各コンポーネントの **唯一の責務**
* 通信経路の固定
* 越境禁止の明文化
* 実装判断の基準点

---

**次章：SPEC-02 ProjectState 仕様**
