# SPEC-05 Apply フロー仕様

---

## 1. 本章の目的

本章では、承認済み ChangePlan を **実際にコードへ反映する一連の処理（Apply）** を、
完成版仕様として定義する。

Apply フローは **最も危険度の高い工程** であり、
誤解釈・自動化・省略を一切許容しない。

---

## 2. Apply フローの位置づけ（固定）

* Apply は **Extension のみが実行主体**
* Backend は命令・管理のみを行う
* UI は Apply を直接実行できない
* 承認済み ChangePlan 以外は一切適用不可

---

## 3. Apply 開始条件（不変）

Apply は以下 **すべてを満たした場合のみ** 開始される。

1. ChangePlan.approval.status === "approved"
2. ProjectState.snapshotId が ChangePlan の生成元と一致
3. Backend が ApplyRequest を送信
4. Extension が idle 状態である

いずれかを満たさない場合、Apply は **即座に拒否** される。

---

## 4. Apply フロー全体（不変）

```
A. 再検証
B. diff 変換
C. 適用前バックアップ
D. diff 適用
E. 保存・反映
F. 結果報告
```

* 全工程は **直列実行**
* 途中中断時は失敗扱い

---

## 5. Step A: 再検証

### 検証項目

* ChangePlan.scope.targetFiles が存在するか
* 対象ファイルが未変更であるか
* Workspace が writable であるか

### 失敗時

* Apply 中止
* Backend に reject_reason を送信

---

## 6. Step B: diff 変換

### 処理内容

* unified diff → VS Code WorkspaceEdit
* ファイル単位で変換

### ルール

* 変換不能な diff が1つでもあれば全体失敗
* 部分適用は禁止

---

## 7. Step C: 適用前バックアップ

### 方法

* 対象ファイル全文を Extension 内メモリに退避
* ファイル単位で保持

### ルール

* ディスク書き込みは禁止
* Apply 完了後に破棄

---

## 8. Step D: diff 適用

### 実行

* `workspace.applyEdit(edit)`

### ルール

* false が返った時点で失敗
* 途中成功は禁止

---

## 9. Step E: 保存・反映

### 実行

* `document.save()` を対象ファイルすべてに実行

### ルール

* 保存失敗＝全体失敗

---

## 10. Step F: 結果報告

### 成功時

```
POST /apply/result
{
  status: "success",
  planId,
  appliedFiles: string[]
}
```

### 失敗時

```
POST /apply/result
{
  status: "failed",
  planId,
  reason: string
}
```

---

## 11. ロールバック（限定）

### 条件

* diff 適用後〜保存前の失敗のみ

### 方法

* Step C のバックアップ内容を再書き込み

---

## 12. Apply 中の状態管理

* Extension 状態: `idle | applying | error`
* applying 中は他操作禁止

---

## 13. 禁止事項（明文化）

* UI からの直接 Apply
* Backend による diff 適用
* 部分ファイル Apply
* 自動再試行

---

## 14. 本章で確定したこと

* Apply の完全フロー
* 再検証と失敗条件
* バックアップとロールバック範囲
* 成功・失敗報告契約

---

**次章：SPEC-06 Backend State 管理**
