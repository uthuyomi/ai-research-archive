# SPEC-03 ProjectState 収集フロー（Extension 実装仕様）

---

## 1. 本章の目的

本章では、VS Code Extension が **ProjectState をどの順序・条件・方法で収集するか** を
完成版仕様として定義する。

ここに記載された手順は **そのまま実装手順** であり、
順序変更・省略・条件緩和は禁止される。

---

## 2. 基本原則（固定）

* 収集主体は **VS Code Extension のみ**
* Backend / UI / SDK は収集に関与しない
* 推測・補完は禁止（事実のみ）
* 途中失敗しても **最後まで走査する**
* 完了後にのみ ProjectState を送信する

---

## 3. 収集トリガ（固定）

Extension は以下のタイミングで **必ず** 収集を開始する。

1. Extension 起動時
2. Workspace フォルダ変更時（追加 / 削除 / リネーム）
3. ChangePlan Apply 完了後
4. Backend 応答に `rescan:true` が含まれた場合

---

## 4. 収集フロー全体（不変）

収集は以下の **直列ステップ** で実行される。

```
A. WorkspaceState
B. StructureState
C. DependencyState
D. DiagnosticsState
E. ExecutionState (build)
F. ExecutionState (tests)
G. RiskState
→ complete 算出
→ Backend 送信
```

* 並列実行は可
* ただし **全ステップ完了待ち** が必須

---

## 5. Step A: WorkspaceState 収集

### 使用 API

* `vscode.workspace.workspaceFolders`
* `process.platform`

### 収集内容

* root（絶対パス）
* name（フォルダ名）
* platform
* languages（拡張子走査）
* frameworks（設定ファイル存在確認のみ）

### 禁止事項

* 設定ファイル内容の解析
* 推測によるフレームワーク判定

---

## 6. Step B: StructureState 収集

### 使用 API

* `vscode.workspace.findFiles`

### 除外パターン（固定）

* `node_modules/**`
* `.git/**`
* `dist/**`
* `build/**`

### 収集内容

* files（相対パス）
* directories（親ディレクトリ列挙）
* entryPoints

  * package.json: main / bin
  * tsconfig.json: files / include

---

## 7. Step C: DependencyState 収集

### 方法

* 対象拡張子：`.ts .js .tsx .jsx`
* 行ベース解析（正規表現）

### 収集内容

* imports[file] = import 文字列配列
* reverseImports[target] = 参照元配列

### 禁止事項

* AST 前提解析
* 依存重要度の評価

---

## 8. Step D: DiagnosticsState 収集

### 使用 API

* `vscode.languages.getDiagnostics()`

### 正規化内容

* file（相対パス）
* line / column（存在すれば）
* message
* source
* severity

### 振り分け

* typescript
* lint
* tests（後続 Step F）
* build（後続 Step E）

---

## 9. Step E: ExecutionState（build）

### 実行条件

* package.json に build script が存在する場合のみ

### 実行

* `npm run build` / `pnpm run build`

### 収集内容

* attempted
* success
* diagnostics.build（stderr/stdout から抽出）

---

## 10. Step F: ExecutionState（tests）

### 実行条件

* package.json に test script が存在する場合のみ

### 実行

* `npm test` / `pnpm test`

### 収集内容

* attempted
* success
* diagnostics.tests（失敗時のみ）

---

## 11. Step G: RiskState 収集

### 判定方法（明示ルールのみ）

* mutableStateFiles

  * 設定ファイル
  * migration
* sideEffectFiles

  * fs / http / db 文字列検出
* criticalFiles

  * entryPoints

### 禁止事項

* 推測によるリスク判定

---

## 12. complete 算出

`SPEC-02` に定義された条件を **そのまま使用** する。

* ここで再定義しない
* ロジック変更禁止

---

## 13. Backend 送信

### Endpoint

```
POST /project/state
```

### 送信ルール

* 全ステップ完了後 **1回のみ送信**
* 分割送信禁止
* complete=false でも必ず送信

---

## 14. エラー時の扱い（固定）

* 例外が出ても収集は継続
* 取得不能な項目は attempted=false
* エラー内容は diagnostics に記録

---

## 15. 禁止事項（再明文化）

* SDK を使った収集
* Backend からの収集命令
* UI からの直接再スキャン
* 部分 ProjectState 生成

---

## 16. 本章で確定したこと

* Extension が実装すべき **正確な収集順序**
* 使用 API と取得条件
* エラー耐性の扱い
* Backend との送信契約

---

**次章：SPEC-04 ChangePlan 仕様**
