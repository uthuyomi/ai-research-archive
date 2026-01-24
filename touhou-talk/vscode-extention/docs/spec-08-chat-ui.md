# SPEC-08 Chat UI 仕様（Message 仕様／描画仕様／UI イベント API）

---

## 1. 本章の目的

本章では、touhou-talk の **Chat UI** が担う役割と、
**Message 仕様・描画仕様・UI イベント API** を完成版として定義する。

Chat UI は「操作パネル」ではなく、
**状態の可視化と人間の意思表明のみを担う層**である。

---

## 2. Chat UI の位置づけ（固定）

* Chat UI は **判断しない**
* Chat UI は **状態を生成しない**
* Chat UI は **Apply を直接実行しない**
* Chat UI は Backend State を **参照のみ** する

---

## 3. Message 基本構造（完成版）

```ts
type Message = {
  id: string;
  role: "user" | "ai";
  content: string;

  meta?: MessageMeta | null;
};
```

---

## 4. MessageMeta（拡張メタ情報）

```ts
type MessageMeta = {
  type:
    | "project_state"
    | "change_plan"
    | "approval_request"
    | "apply_result"
    | "error";

  snapshotId?: string;
  planId?: string;

  diff?: string;               // unified diff
  touched_files?: string[];

  next_actions?: UiAction[];
};
```

---

## 5. UiAction 仕様

```ts
type UiAction = {
  id: string;
  label: string;
  action:
    | "approve_plan"
    | "reject_plan"
    | "request_rescan"
    | "poll_state";
};
```

### ルール

* UiAction は **明示的操作のみ**
* 自動実行は禁止

---

## 6. Message type 別仕様

### 6.1 project_state

* 内容：ProjectState 要約
* diff 表示禁止
* 操作：なし

---

### 6.2 change_plan

* 内容：PlanExplanation
* diff：全文表示可（read-only）
* touched_files 表示必須
* 操作：approve / reject

---

### 6.3 approval_request

* 内容：承認待ち状態の通知
* 操作：approve / reject

---

### 6.4 apply_result

* 内容：成功 / 失敗メッセージ
* 操作：request_rescan

---

### 6.5 error

* 内容：Backend / Extension エラー
* 操作：poll_state

---

## 7. 描画仕様（固定）

### 共通ルール

* Message は **時系列順のみ**
* 並び替え・折りたたみ禁止
* meta がある場合は視覚的に区別

### diff 表示

* monospaced
* syntax highlight 可
* 編集不可

---

## 8. UI イベント API（完成版）

### 8.1 approve_plan

```
POST /ui/approve
{
  planId: string
}
```

---

### 8.2 reject_plan

```
POST /ui/reject
{
  planId: string
}
```

---

### 8.3 request_rescan

```
POST /ui/request-rescan
```

---

### 8.4 poll_state

```
GET /ui/state
```

---

## 9. UI 側 State 管理

* Message 配列のみ保持
* Backend State のコピー禁止
* 楽観的 UI 更新禁止

---

## 10. エラー表示ルール

* error Message としてのみ表示
* Toast / modal 使用禁止

---

## 11. 禁止事項（明文化）

* Chat UI による状態生成
* Chat UI による diff 編集
* Chat UI による Apply 実行
* UI 独自の承認ロジック

---

## 12. 本章で確定したこと

* Message / MessageMeta 完成版仕様
* 描画ルールと UI イベント API
* Chat UI の責務境界

---

**本仕様書はここで完結する（SPEC-00〜08 完全版）**
