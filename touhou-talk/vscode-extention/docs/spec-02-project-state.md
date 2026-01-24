# SPEC-02 ProjectState 仕様

---

## 1. 本章の目的

本章では、touhou-talk × VS Code 連携システムにおける
**ProjectState（プロジェクト状態スナップショット）** の
完成版仕様を定義する。

ProjectState は本システムにおける **事実の唯一の表現** であり、
ChangePlan・Apply・SDK 入力のすべての前提となる。

---

## 2. ProjectState の位置づけ（固定）

* ProjectState は **事実のみ** を含む
* 推測・評価・要約は含まない
* Extension により生成され、Backend に送信される
* Backend は ProjectState を **改変しない**

---

## 3. トップレベル構造（完成版）

```ts
type ProjectState = {
  version: "1.0";
  snapshotId: string;          // UUID
  capturedAt: number;          // epoch ms

  workspace: WorkspaceState;
  structure: StructureState;
  dependencies: DependencyState;
  diagnostics: DiagnosticsState;
  execution: ExecutionState;
  risk: RiskState;

  complete: boolean;           // 自動算出
};
```

### 共通ルール

* すべてのフィールドは **必須**
* 値が存在しない場合は空配列・false を用いる
* 欠損は禁止

---

## 4. WorkspaceState

```ts
type WorkspaceState = {
  root: string;                // 絶対パス
  name: string;                // ワークスペース名
  platform: "win32" | "darwin" | "linux";

  languages: Array<"ts" | "js" | "python" | "other">;
  frameworks: string[];        // 設定ファイルから確定できたもののみ
};
```

### ルール

* languages は拡張子走査により確定
* frameworks は **存在確認のみ**（内容解析・推測禁止）

---

## 5. StructureState

```ts
type StructureState = {
  files: string[];             // 相対パス
  directories: string[];       // 相対パス
  entryPoints: string[];       // 設定で明示されたもののみ
};
```

### ルール

* 除外対象（node_modules, .git, dist 等）は含めない
* entryPoints は以下のみ許可

  * package.json (main / bin)
  * tsconfig.json (files / include)

---

## 6. DependencyState

```ts
type DependencyState = {
  imports: Record<string, string[]>;        // file -> import targets
  reverseImports: Record<string, string[]>; // file -> 参照元
};
```

### ルール

* 行ベース解析
* AST 必須ではない
* 解釈・重要度付けは禁止

---

## 7. DiagnosticsState

```ts
type DiagnosticsState = {
  typescript: Diagnostic[];
  lint: Diagnostic[];
  tests: Diagnostic[];
  build: Diagnostic[];
};
```

```ts
type Diagnostic = {
  file: string;                // 相対パス
  line?: number;
  column?: number;
  message: string;
  source: "tsc" | "eslint" | "pytest" | "build" | "vscode";
  severity: "error" | "warning";
};
```

### ルール

* VS Code diagnostics を正規化して格納
* source によって配列を振り分ける

---

## 8. ExecutionState

```ts
type ExecutionState = {
  build: {
    attempted: boolean;
    success: boolean;
  };
  tests: {
    attempted: boolean;
    success: boolean;
  };
};
```

### ルール

* 実行していない場合 attempted=false
* success は attempted=true の場合のみ意味を持つ

---

## 9. RiskState

```ts
type RiskState = {
  mutableStateFiles: string[];
  sideEffectFiles: string[];
  criticalFiles: string[];
};
```

### ルール

* 明示的検出のみ
* 推測禁止
* 不明な場合は空配列

---

## 10. complete 判定（固定）

```ts
complete =
  workspace.root !== "" &&
  structure.files.length > 0 &&
  diagnostics.typescript !== undefined &&
  diagnostics.lint !== undefined &&
  diagnostics.tests !== undefined &&
  diagnostics.build !== undefined &&
  execution.build.attempted === true &&
  execution.tests.attempted === true;
```

### 意味

* 成功・失敗は問わない
* 未実行＝未把握

---

## 11. 禁止事項（明文化）

* SDK による ProjectState 生成・補完
* Backend による ProjectState 改変
* UI からの直接参照・操作
* 部分 ProjectState の送信

---

## 12. 本章で確定したこと

* ProjectState の完成版スキーマ
* 各フィールドの意味と制約
* complete 判定条件
* 事実表現の不変ルール

---

**次章：SPEC-03 ProjectState 収集フロー**
