# SPEC-04 ChangePlan 仕様

---

## 1. 本章の目的

本章では、touhou-talk × VS Code 連携システムにおける
**ChangePlan（変更計画）** の完成版仕様を定義する。

ChangePlan は **人間承認を前提とした変更単位** であり、
ProjectState（事実）と Apply（実行）を接続する唯一の中間表現である。

---

## 2. ChangePlan の位置づけ（固定）

* ChangePlan は **事実ではない**（判断・提案の集合）
* 必ず **ProjectState を根拠** に生成される
* 人間承認なしに Apply されることはない
* diff は **実行可能である必要がある**

---

## 3. トップレベル構造（完成版）

```ts
type ChangePlan = {
  version: "1.0";
  planId: string;              // UUID
  createdAt: number;           // epoch ms

  basis: PlanBasis;
  scope: PlanScope;
  changes: FileChange[];
  validations: PlanValidations;
  risk: PlanRisk;
  explanation: PlanExplanation;

  approval: ApprovalState;
};
```

### 共通ルール

* すべてのフィールドは **必須**
* diff を含まない ChangePlan は禁止
* snapshotId は scope 経由で間接的に紐づく

---

## 4. PlanBasis（生成根拠）

```ts
type PlanBasis = {
  trigger: "error" | "user_request" | "refactor";
  relatedDiagnostics: DiagnosticRef[];
};
```

```ts
type DiagnosticRef = {
  file: string;
  message: string;
  line?: number;
};
```

### ルール

* trigger は必須
* trigger=error の場合、relatedDiagnostics は空であってはならない
* 根拠不明な ChangePlan 生成は禁止

---

## 5. PlanScope（影響範囲）

```ts
type PlanScope = {
  targetFiles: string[];
  affectedFiles: string[];
};
```

### ルール

* targetFiles は changes[].file と **完全一致** する
* affectedFiles は DependencyState から機械的に算出
* 推測による追加は禁止

---

## 6. FileChange（実変更）

```ts
type FileChange = {
  file: string;                // 相対パス
  diff: string;                // unified diff
};
```

### ルール

* diff は WorkspaceEdit に変換可能であること
* ファイルパス不一致は禁止
* 分割 diff・部分適用は禁止

---

## 7. PlanValidations（前提条件）

```ts
type PlanValidations = {
  projectStateComplete: true;
  noConflictFiles: string[];
};
```

### ルール

* projectStateComplete は true 固定
* false の ChangePlan は **生成自体禁止**
* noConflictFiles は生成時点で検証済みのもののみ

---

## 8. PlanRisk（機械的リスク評価）

```ts
type PlanRisk = {
  level: "low" | "medium" | "high";
  reasons: string[];
};
```

### 判定基準（固定）

* criticalFiles を含むか
* mutableStateFiles を含むか
* 変更ファイル数

### ルール

* SDK の感想は禁止
* 人間判断の補助情報としてのみ使用

---

## 9. PlanExplanation（人間向け説明）

```ts
type PlanExplanation = {
  summary: string;
  details: string;
};
```

### ルール

* SDK Adapter により生成される
* 事実と不整合でも Apply 可否には影響しない

---

## 10. ApprovalState（承認管理）

```ts
type ApprovalState = {
  status: "pending" | "approved" | "rejected";
  decidedAt?: number;
  decidedBy?: "user";
};
```

### ルール

* 初期状態は必ず pending
* approved 以外は Apply 禁止
* 自動承認は禁止

---

## 11. ChangePlan の有効期限（固定）

* ChangePlan は **生成時の snapshotId にのみ有効**
* 新しい ProjectState が届いた場合：

  * 既存 ChangePlan は自動的に無効（rejected 扱い）

---

## 12. 禁止事項（明文化）

* diff を含まない ChangePlan
* SDK による承認判断
* UI からの直接 Apply
* Extension による ChangePlan 生成

---

## 13. 本章で確定したこと

* ChangePlan の完成版スキーマ
* 生成根拠と影響範囲の定義
* diff の厳密条件
* 承認フロー前提の不変ルール

---

**次章：SPEC-05 Apply フロー仕様**
