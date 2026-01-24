# SPEC-07 SDK Adapter 仕様

---

## 1. 本章の目的

本章では、touhou-talk Backend が利用する **SDK Adapter** の完成版仕様を定義する。

SDK Adapter は「賢さ」を持たず、
**外部 SDK（LLM / Copilot SDK 等）との接続境界を固定化するための薄い層**である。

---

## 2. SDK Adapter の位置づけ（固定）

* SDK Adapter は Backend 内部コンポーネント
* UI / Extension から直接呼び出されない
* 判断・状態変更を行わない
* 生成・説明・変換のみを担当

---

## 3. SDK Adapter が扱う責務

SDK Adapter の責務は以下に限定される。

1. ChangePlan 生成
2. PlanExplanation 生成
3. UI 表示用テキスト生成

それ以外の用途で SDK を呼び出すことは禁止される。

---

## 4. 外部 SDK 利用方針（固定）

* Copilot SDK / LLM SDK は **最大限利用してよい**
* ただし SDK に以下を委ねてはならない

### 禁止委譲事項

* ProjectState 生成
* ProjectState 補完
* 承認判断
* Apply 判断
* 状態遷移

---

## 5. SDK Adapter インターフェース（完成版）

```ts
interface SdkAdapter {
  generateChangePlan(input: ChangePlanInput): Promise<ChangePlanDraft>;
  generateExplanation(input: ExplanationInput): Promise<PlanExplanation>;
  renderUiMessage(input: UiMessageInput): Promise<string>;
}
```

---

## 6. ChangePlanInput

```ts
type ChangePlanInput = {
  projectState: ProjectState;
  intent: "fix" | "refactor" | "user_request";
  constraints: {
    allowFileCreate: boolean;
    allowFileDelete: boolean;
  };
};
```

### ルール

* projectState.complete === true 必須
* constraints は Backend が決定

---

## 7. ChangePlanDraft

```ts
type ChangePlanDraft = {
  basis: PlanBasis;
  scope: PlanScope;
  changes: FileChange[];
  risk: PlanRisk;
};
```

### ルール

* approval は含めない
* diff は unified diff 必須

---

## 8. ExplanationInput

```ts
type ExplanationInput = {
  plan: ChangePlan;
};
```

---

## 9. UiMessageInput

```ts
type UiMessageInput = {
  context: "plan" | "apply" | "error";
  payload: unknown;
};
```

---

## 10. キャッシュ戦略

* 同一 snapshotId + intent の結果は再利用可
* キャッシュは volatile（永続化禁止）

---

## 11. エラー処理

* SDK エラーはそのまま上位へ返却
* 自動再試行は禁止
* メッセージ変換のみ許可

---

## 12. 禁止事項（明文化）

* SDK Adapter 内での状態保存
* SDK 出力の自動適用
* SDK による diff 修正
* SDK による承認ステータス操作

---

## 13. 本章で確定したこと

* SDK Adapter の責務境界
* 完成版インターフェース
* SDK 利用可能範囲と禁止範囲

---

**次章：SPEC-08 Chat UI 仕様**
