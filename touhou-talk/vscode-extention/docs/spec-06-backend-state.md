# SPEC-06 Backend State 管理

---

## 1. 本章の目的

本章では、touhou-talk Backend が保持・管理する **全状態（State）** の
完成版仕様を定義する。

Backend は「判断主体」ではなく、
**状態の正規化・整合性維持・履歴管理** のみを責務とする。

---

## 2. Backend State 管理の基本原則（固定）

* Backend は **事実を生成しない**
* Extension から受信したもののみを保存する
* 状態は **世代管理** される
* UI / SDK は Backend State を直接変更できない

---

## 3. 管理対象 State 一覧（完成版）

Backend は以下の State を管理する。

1. ProjectState
2. ChangePlan
3. ApplyHistory
4. BackendSessionState

---

## 4. ProjectState 管理

### 4.1 保存単位

```ts
type StoredProjectState = {
  snapshotId: string;
  capturedAt: number;
  state: ProjectState;
};
```

### 4.2 ルール

* snapshotId ごとに **完全保存**
* 上書き禁止
* 最新 snapshotId を current として保持

---

## 5. ChangePlan 管理

### 5.1 保存単位

```ts
type StoredChangePlan = {
  planId: string;
  snapshotId: string;
  plan: ChangePlan;
};
```

### 5.2 ルール

* snapshotId と **必ず紐づく**
* ProjectState 更新時に自動 invalid 化
* 承認状態は immutable

---

## 6. ApplyHistory 管理

### 6.1 保存単位

```ts
type ApplyHistory = {
  planId: string;
  snapshotId: string;
  status: "success" | "failed";
  appliedAt: number;
  detail?: string;
};
```

### 6.2 ルール

* Apply 結果は **必ず保存**
* 書き換え禁止
* UI 表示・監査用途のみ

---

## 7. BackendSessionState

```ts
type BackendSessionState = {
  sessionId: string;
  activeSnapshotId: string;
  activePlanId?: string;
  status: "idle" | "waiting_approval" | "applying";
};
```

### ルール

* セッションは 1 Workspace = 1 Session
* status 遷移は Backend のみが行う

---

## 8. 状態遷移ルール（固定）

```
ProjectState 更新
  ↓
ChangePlan 生成可能
  ↓
Approval 待ち
  ↓
Apply 実行
  ↓
ApplyHistory 記録
  ↓
ProjectState 再収集
```

* 逆順遷移は禁止

---

## 9. 排他制御

### 原則

* 同一 sessionId に対する Apply は同時に 1 件のみ
* applying 中は他リクエスト拒否

### 実装指針

* インメモリロック or DB トランザクション

---

## 10. 永続化モデル

### 必須要件

* 再起動後も State が復元可能
* 少なくとも ProjectState / ChangePlan / ApplyHistory を保存

### 技術非拘束

* DB 種別は問わない

---

## 11. 禁止事項（明文化）

* Backend による ProjectState 改変
* ChangePlan の自動承認
* Apply の再実行
* 履歴削除

---

## 12. 本章で確定したこと

* Backend が保持する State の全種
* 世代管理・不変ルール
* 状態遷移と排他制御

---

**次章：SPEC-07 SDK Adapter 仕様**
