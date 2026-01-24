# touhou-talk × VS Code 連携仕様書

## SPEC-00 全体概要・不変原則

---

## 1. 本仕様書の目的

本仕様書は、**touhou-talk（Web Chat UI）・Backend・VS Code Extension・SDK Adapter** を統合した
**コード編集支援システムの完成版仕様**を定義するものである。

本仕様は以下を満たすことを目的とする。

* 人間が読んで即実装に着手できる
* AI が読んで仕様前提を誤解せずコード生成できる
* 途中仕様・最小構成・段階導入を一切含まない
* 実装判断が揺れない「不変条件」を明文化する

---

## 2. 絶対前提（本プロジェクトの不変条件）

以下は**例外なく守られる前提条件**であり、
本仕様書内のすべての章に優先する。

### 2.1 開発姿勢

* 最初から **完成版のみ** を扱う
* 「フェーズ1」「最小構成」「とりあえず」は存在しない
* 勝手な解釈・補完は禁止
* 曖昧な部分は **未定義として保持** する

### 2.2 判断責務

* 判断の最終責任は **人間** にある
* AI / SDK は判断補助のみ
* 自動適用・自動承認は禁止

---

## 3. システム全体像

```
[ Browser (Chat UI) ]
        ↑↓  HTTP (poll / event)
[ touhou-talk Backend ]
        ↑↓  HTTP (pull)
[ VS Code Extension ]
```

* UI と Extension は **直接通信しない**
* Backend が **唯一のハブ**
* すべての状態は Backend に集約される

---

## 4. コンポーネント一覧と責務概要

### 4.1 Chat UI（Browser / Next.js）

* Message を描画する
* 承認・却下などの **イベント送信のみ** を行う
* 状態は一切保持しない

### 4.2 Backend（touhou-talk）

* ProjectState / ChangePlan / ApplyHistory の唯一の管理者
* SDK Adapter を通じた説明生成
* UI 向け Message の生成

### 4.3 VS Code Extension

* Workspace 観測
* ProjectState 収集
* ChangePlan の適用（唯一の編集主体）

### 4.4 SDK Adapter

* 説明・要約・レビュー生成
* 事実生成・判断・適用は行わない

---

## 5. 用語定義（固定）

| 用語           | 定義                             |
| ------------ | ------------------------------ |
| ProjectState | ワークスペースの事実状態スナップショット           |
| ChangePlan   | 人間承認前提の変更計画                    |
| Apply        | diff を WorkspaceEdit として適用する行為 |
| Message      | UI 描画専用イベント表現                  |
| complete     | ProjectState が把握完了した状態         |

---

## 6. 本仕様書の構成

本仕様書は以下 **9 分割** で構成される。

1. SPEC-00 全体概要・不変原則（本書）
2. SPEC-01 システム構成・責務分離
3. SPEC-02 ProjectState 仕様
4. SPEC-03 ProjectState 収集フロー
5. SPEC-04 ChangePlan 仕様
6. SPEC-05 Apply フロー仕様
7. SPEC-06 Backend State 管理
8. SPEC-07 SDK Adapter 仕様
9. SPEC-08 Chat UI / Message 仕様

---

## 7. 本仕様書の扱い方

* 各 SPEC は **単独で読める** ことを前提に書かれている
* 実装時は、対応する SPEC を唯一の正とする
* 仕様変更がある場合は **SPEC 単位で更新** する

---

**次章：SPEC-01 システム構成・責務分離**


