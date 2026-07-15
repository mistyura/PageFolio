# Phase 4: バッチ複数ファイルOCR - Research

**Researched:** 2026-07-15
**Domain:** Tkinter デスクトップアプリの新規ダイアログ（`BatchOCRDialog`）実装。既存 `OCRRunEngine`（producer-consumer consumer 側）をファイルごとに再利用し、ファイル間逐次・ファイル内並列という二層構造でバッチ処理する。新規外部依存なし（Python 3.8+ 標準ライブラリ + 既存 pagefolio 資産のみ）。
**Confidence:** HIGH（既存コードベースの一次情報源に基づく curated 調査。新規 UI パターン（Treeview）のみ MEDIUM）

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**起動導線・投入方式**
- **D-01:** バッチOCRダイアログは新規メニュー項目「バッチOCR」から起動する独立ダイアログとする。単一ファイルOCR（既存 🔍 ボタン）とは明確に別動線。
- **D-02:** キューへのファイル追加は D&D + 「+ ファイル追加」ボタン（`filedialog.askopenfilenames` 複数選択）の両方に対応する。D&D は既存 `file_drop.py`/`app.py:_on_dnd_drop` の `tk.splitlist` + `SUPPORTED_EXTENSIONS` フィルタパターンを新規ウィジェットへ拡張適用する。
- **D-03:** OCR実行開始前に、バッチ全体の集約コスト確認ダイアログ（対象ファイル数・総ページ数・概算コスト）を一括表示する（FEATURES.md Anti-Features の推奨に従う）。各ファイルのページ数は `fitz.open(path).page_count` の軽量呼び出しでメインスレッド・逐次に事前取得する（V14-D-05/06 の範囲内・レンダリングは行わない）。
- **D-04:** バッチOCRは現在メインウィンドウで開いているファイル（`self.doc`）と完全に独立させる。自動追加はせず、ユーザーが明示的にファイルパスで選ぶ。編集中の未保存変更との衝突を構造的に避ける。

**キュー一覧の表示・操作**
- **D-05:** キュー一覧は `ファイル名 / 状態（待機・実行中・完了・失敗） / ページ内進捗` の3列構成（`ttk.Treeview` 想定）。
- **D-06:** 失敗ファイルは行の文字色をテーマ辞書の警告色（`C["WARNING"]`）にする（`tag_configure` によるTreeviewタグ付けパターン）。
- **D-07:** キュー内ファイルの操作は**削除のみ**、かつ**待機中ファイルのみ**可能とする。実行中・完了・失敗済みの行は削除ボタンを無効化する。並び替えUI（`MergeOrderDialog` パターン）は今回は不採用。
- **D-08:** バッチ全体の進捗（ファイル数軸）は、ダイアログ上部に固定の進捗バー + 「ファイル x/合計」ラベルで常時表示する。キュー一覧の状態列（ページ内進捗）とは別軸として明示的に二段表示する（PITFALLS.md 落とし穴5「ファイル/ページ二軸の進捗集計が矛盾する」への対応）。

**失敗・キャンセルの挙動**
- **D-09:** ファイル単位の失敗（fatal エラー・サーキットブレーカー発動等）発生時は自動スキップして次ファイルへ進む（V180-BATCH-03 の要件文言どおり）。一時停止して確認を挟むことはしない。
- **D-10:** キャンセルUIは「バッチ中止」ボタン1つのみとする。「このファイルのみスキップ」という個別ボタンは設けない。ただし**内部実装は2階層のキャンセルフラグを維持**する（バッチ全体の cancel flag + 既存のファイル内 `_cancel_flag`/`_run_gen`）。「バッチ中止」押下時は両方のフラグを同時にセットし、実行中のファイルも含めて即座に停止させる（PITFALLS.md 落とし穴4の内部ロジックはそのまま踏襲し、UI露出のみユーザー選択で1ボタンに絞る）。
- **D-11:** 「バッチ中止」後も、完了済みファイルの OCR 結果はダイアログ内に保持され、閲覧・統合サマリ生成に引き続き使える。ダイアログを閉じた時点で破棄する（キューの永続化はしない — FEATURES.md Anti-Features の確定方針どおり）。
- **D-12:** 失敗ファイルの一括再試行機能（FEATURES.md で Differentiator/P2 扱い）は本フェーズに含めない。

**統合サマリ・結果閲覧**
- **D-13:** バッチ完了後の統合サマリは手動トリガー（「📊 サマリ作成」ボタン）とする。既存 `OCRDialog` の単一ファイル版と同じUX。バッチ完了時の自動生成はしない（不要な送信コストの発生を避ける）。
- **D-14:** V180-BATCH-05 の「入力過大時の事前警告」は、既存 `_confirm_summary_cost`（文字数表示・毎回確認ダイアログ）をそのまま拡張し、複数ファイル連結後の合計文字数を渡すことで満たす。新規のハード閾値・自動切り詰めロジックは追加しない。
- **D-15:** 統合サマリ生成時、複数ファイルの OCR 結果テキストを連結する際は、各ファイルの先頭にファイル名見出し（例: `=== ファイル名.pdf ===`）を挿入して連結する。LLM がファイル境界を認識しやすくし、サマリ品質を上げる。
- **D-16:** 各ファイルの OCR 結果の閲覧・エクスポートは、ファイル選択ドロップダウン/リストで切り替えて、既存 `OCRDialog` の結果ビュー（Markdown整形描画 `_insert_markdown`・コピー/保存は raw 維持）をそのまま流用する。エクスポートはファイル単位。

### Claude's Discretion
- ページ内進捗表示の具体的なウィジェット（プログレスバー併記 vs テキストのみ「n/m」）
- `PipelineState` の上位に置く薄い純関数層（ファイル完了/失敗イベント集計・落とし穴5対応）の内部データ構造・関数API設計（`BatchState` 等の名称含む）
- キュー投入時の事前ページ数スキャンでファイルが壊れている/開けない場合のエラー表示文言・キュー上の扱い
- ファイル選択ドロップダウン/リスト（D-16）のウィジェット種類（`ttk.Combobox` vs `tk.Listbox`）
- 新規メニュー項目「バッチOCR」（D-01）のメニューバー上の配置位置

### Deferred Ideas (OUT OF SCOPE)
- **失敗ファイルの一括再試行機能** — FEATURES.md で Differentiator/P2 扱い。将来の別フェーズ/別タスク候補（D-12 で明示的に不採用）
- バックグラウンド常駐継続（ダイアログを閉じたら処理停止）
- キューの永続化（アプリ再起動でクリア）
- multiprocessing によるファイル並列処理
- サムネイル仮想化（Phase 5）・通知UX/UI一貫性監査（Phase 6）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V180-BATCH-01 | ユーザーは複数 PDF ファイルを一括で OCR キューに投入できる（D&D 対応） | `file_drop.py`/`app.py:_on_dnd_drop`（321-354行）の `tk.splitlist`+`SUPPORTED_EXTENSIONS` パターンをそのまま新規 Toplevel の Canvas/Frame へ拡張適用。「+ ファイル追加」ボタンは `file_ops.py:467` の `askopenfilenames` パターンを流用（下記 Code Examples） |
| V180-BATCH-02 | キュー一覧でファイルごとの状態（待機/実行中/完了/失敗）と全体進捗を確認できる | `ttk.Treeview`（コードベース初導入・下記 Architecture Patterns で新規スタイル定義要）+ `tag_configure` による警告色行（D-06）。全体進捗は「BatchState」薄い純関数層（下記 Pattern 2）が集計しラベル+`ttk.Progressbar` へ反映 |
| V180-BATCH-03 | ファイル単位の失敗は分離され、残りのファイル処理は継続する | `OCRRunEngine` の `on_fatal` コールバックをファイルループの「次ファイルへ進む」トリガーとして扱う。fitz は**ファイル間も**メインスレッド逐次（落とし穴3の直接対応） |
| V180-BATCH-04 | バッチ全体・ファイル単位のキャンセルができる | 2階層 `threading.Event`（バッチ全体 + 既存ファイル内 `_cancel_flag` 相当）。「バッチ中止」1ボタンが両方を `.set()`（D-10）。落とし穴4の回避策をそのまま適用 |
| V180-BATCH-05 | バッチ完了後、複数ファイル横断の統合サマリを生成できる（入力過大時の事前警告を含む） | `ocr_dialog.py:2006-`（`_on_summary`/`_summary_worker`）+ `_confirm_summary_cost`（1237-1265行）をファイル横断連結テキストへそのまま適用。ファイル名見出し連結（D-15）のみ新規ロジック |
</phase_requirements>

## Summary

バッチ OCR は「新規の実行エンジンを書く」フェーズではない。Phase 3 で抽出済みの `OCRRunEngine`（`pagefolio/ocr_engine.py`）を**ファイルごとに新規生成**し、既存の `_render_next_page` 型 producer ループ（fitz レンダリング → `try_enqueue` → Engine 消費）を「ファイルを1つずつ開いて回す」外側ループでもう一段ラップするだけで、単一ファイル OCR の全ロジック（リトライ・サーキットブレーカー・埋め込みテキストスキップ・コスト確認・サマリ生成）がそのまま流用できる。新規実装が必要なのは (1) ファイルキューの状態遷移管理（薄い純関数層）、(2) `BatchOCRDialog`（新規 Toplevel + `ttk.Treeview`）、(3) 2階層キャンセルの配線、(4) ファイル横断サマリの文字列連結ロジックの4点に限定される。

最大のリスクは PITFALLS.md 落とし穴3〜5（fitz スレッド間共有違反・キャンセルスコープ不足・進捗二重集計）だが、いずれも v1.8.0 マイルストーン全体のリサーチ段階で既に回避策が明記済みであり、Phase 3 で確立した「Engine は実行ごとに新規生成（D-11）」「producer は Engine の queue プロパティ経由でのみ参照（落とし穴10対応）」という契約をそのままファイル単位に外挿すれば構造的に安全である。

新規性が高い箇所は UI 層のみ: PageFolio には現時点で **`tk.Menu`（メニューバー）が1つも存在しない**（全機能はトップレベルのツールバー/右パネルの `ttk.Button` で提供）。D-01 の「新規メニュー項目」は文字通りのメニューバー新設を意味し、これは本プロジェクト初の `tk.Menu` 導入になる。また `ttk.Treeview` もコードベース初採用のウィジェットであり、既存の `ttk.Style` 定義（`ui_builder.py:_build_styles`）にはTreeview用スタイルが存在しないため、テーマ色（`C["BG_PANEL"]`/`C["TEXT_MAIN"]`/`C["ACCENT"]`選択色等）に整合する新規スタイルブロックを追加する必要がある。

**Primary recommendation:** `BatchOCRDialog` を新規 `pagefolio/dialogs/batch_ocr.py`（または `pagefolio/batch_ocr_dialog.py`）に実装し、ファイルキューの状態遷移は Tk/fitz 非依存の純関数モジュール（例: `pagefolio/batch_ocr_state.py`）に切り出す。ファイルループは「1ファイルにつき `OCRRunEngine` を1つ新規生成 → そのファイルの全ページ完了/fatal/cancel を待つ → 次ファイルへ」という単純な逐次コントローラとして実装し、既存 `_render_next_page`/`_start_worker_thread` の呼び出し契約をそのまま踏襲する。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| キューへのファイル投入（D&D・ファイル選択ダイアログ） | Browser/Client 相当（Tkinter UI 層・`BatchOCRDialog`） | — | tkinterdnd2 イベント・`filedialog` はすべて UI スレッド完結の操作 |
| キュー状態遷移（待機→実行中→完了/失敗）の集計 | 純ロジック層（新規 `batch_ocr_state.py`、Tk/fitz 非依存） | UI 層（Treeview 描画） | `pagination.py`/`ocr_pipeline.py` と同格の系譜。状態遷移ロジックを Tk から切り離すことでテスト容易性を確保 |
| ファイル内ページOCR実行（レンダリング・API送信・リトライ） | 既存 `OCRRunEngine`（`ocr_engine.py`）+ producer（`BatchOCRDialog` 内メソッド） | プロバイダ層（`ocr_providers/`） | Phase 3 で抽出済みの再利用資産。バッチはこれを「呼ぶ側」であり中身を変更しない |
| fitz レンダリング（`get_pixmap`/`open`） | メインスレッド（UI層） | — | V14-D-05/06 制約により他ティアへ委譲不可。ファイル間も含めて単一スレッドで直列化 |
| コスト確認・送信先確認ダイアログ | UI 層（`messagebox.askyesno` 拡張） | — | 既存 `_confirm_cost`/`_confirm_summary_cost` の直接拡張。新規ティアの追加は不要 |
| 統合サマリ生成（複数ファイル横断） | プロバイダ層（`complete_text_ex`） | UI 層（連結ロジック・ファイル名見出し挿入） | 既存 `_on_summary`/`_summary_worker` パターンをそのまま踏襲。ファイル境界の連結は UI 層の薄い前処理 |
| 設定永続化（バッチ関連の新規設定キーの要否） | 設定層（`settings.py`） | — | 本フェーズは「キュー永続化なし」（D-11・Anti-Feature）のため、新規永続設定キーは基本的に不要と想定（要確認: Open Questions参照） |

## Standard Stack

### Core

本フェーズは新規外部パッケージを一切導入しない。既存 pip 依存（`requirements.txt` 固定）と Python 3.8+ 標準ライブラリのみで実現する。

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tkinter / tkinter.ttk | 標準ライブラリ | `BatchOCRDialog`（新規 `Toplevel`）・`ttk.Treeview`（キュー一覧）・`ttk.Progressbar`（全体進捗） | 既存 `OCRDialog`/`MergeOrderDialog` と同じ GUI 基盤。新規依存不要 |
| PyMuPDF (fitz) | 1.27.2.2（既存固定） | ファイルごとの `fitz.open()`/`page_count`/`get_pixmap()` | 既存バージョンをそのまま使用。バージョン変更は本フェーズの対象外 |
| tkinterdnd2 | 0.4.3（既存固定） | バッチキューへの複数ファイル D&D | 既存 `file_drop.py` と同じ基盤をバッチダイアログの Canvas/Frame へ拡張登録 |
| threading / queue | 標準ライブラリ | ファイル内 OCR 実行の consumer ワーカー（`OCRRunEngine` 内部で既に使用）+ バッチ全体キャンセルフラグ | 既存パターンの延長 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pagefolio.ocr_engine.OCRRunEngine` | 既存（Phase 3 で抽出） | ファイルごとの OCR 実行 consumer 駆動 | ファイルループの1イテレーションごとに新規生成（D-11 と同じ「実行ごと新規生成」原則をファイル単位に外挿） |
| `pagefolio.ocr_pipeline`（`PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`） | 既存 | `OCRRunEngine` が内部で使用（直接呼ばない） | バッチ側は `OCRRunEngine` 経由でのみ触れる。直接 `consume_one` を呼ばない（既存の抽象化を尊重） |
| `pagefolio.ocr.build_provider`/`_resolve_api_key`/`resolve_ocr_prompt`/`resolve_summary_prompt` | 既存 | プロバイダ生成・プロンプト解決 | `ocr.py:_start_ocr`（541-624行）と同型のロジックをファイルループ内で毎回実行（プロバイダ設定はファイル間で不変だが、再生成コスト自体は無視できるレベルであり、単一ファイルOCR実行時の既存パターンをそのまま踏襲するのが最も安全） |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ttk.Treeview`（キュー一覧、D-05 で決定済み） | `tk.Listbox` の複数列擬似表示 | Treeview は列見出し・複数列・タグ着色（D-06）が標準サポートされ実装コストが低い。Listbox で複数列を模倣すると文字列フォーマットで列を揃える必要がありメンテコストが増える。D-05 で Treeview 前提が既に確定しているため代替検討は不要 |
| ファイルごとに `OCRRunEngine` を新規生成 | 単一 `OCRRunEngine` を使い回して `run_pages`/`provider` を差し替え | D-11（Phase 3）が「実行ごとに新規生成」を既に確定方針としており、使い回しは per-run 状態（`results`/`errors`/`skipped_pages` 等）のリークリスクを生む。ファイル単位でも同じ原則を踏襲するのが安全 |
| メニューバー新設（D-01） | 既存ツールバーへのボタン追加 | D-01 は「メニュー項目」を明示決定済み。ただしメニューバー自体が本プロジェクト初導入のため、実装コスト（`tk.Menu`/`root.config(menu=...)`の配線）を過小評価しないこと（Open Questions参照） |

**Installation:** 不要（新規 pip 依存なし）。

**Version verification:** 本フェーズは新規パッケージを追加しないため、レジストリ確認は不要。既存 `requirements.txt` の固定バージョン（PyMuPDF 1.27.2.2 / Pillow 12.2.0 / tkinterdnd2 0.4.3）を変更しないことを確認する。

## Package Legitimacy Audit

**該当なし。** 本フェーズは新規外部パッケージを一切導入しない（既存 `requirements.txt` の依存のみを使用）。Package Legitimacy Gate の実行は不要。

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[ユーザー操作]
    │
    ├─ D&D複数ファイル ──┐
    ├─ 「+ ファイル追加」┤
    │   (askopenfilenames) │
    ▼                      ▼
[BatchOCRDialog UI層]
    │  ファイルパス受領
    ▼
[事前ページ数スキャン] ── fitz.open(path).page_count（メインスレッド逐次・D-03）
    │  失敗ファイルは「開けない」表示 or 除外（Claude's Discretion）
    ▼
[キュー状態: 待機] ── batch_ocr_state（純ロジック層）が管理
    │
    ▼（集約コスト確認ダイアログ・D-03: ファイル数・総ページ数・概算コスト）
    │  ユーザー承認
    ▼
┌─────────────────────────────────────────────┐
│  ファイルループ（逐次・1ファイルずつ）         │
│                                               │
│  [キュー状態: 実行中] ← batch_ocr_state 更新   │
│       │                                      │
│       ▼                                      │
│  fitz.open(file) ── メインスレッドのみ         │
│       │                                      │
│       ▼                                      │
│  OCRRunEngine を新規生成（ファイルごと・D-11型）│
│       │         │                            │
│       │         └─ consumer workers（並列度N）  │
│       │              │                        │
│       ▼              ▼                        │
│  producer:       API送信（プロバイダ層）        │
│  _render_next_page型ループ                     │
│  (1ページずつ render→enqueue、既存パターン踏襲)  │
│       │                                      │
│       ▼                                      │
│  [ページ内進捗] → Treeview行の状態列へ反映      │
│       │                                      │
│       ▼                                      │
│  on_complete / on_fatal(自動スキップ・D-09)     │
│  / on_cancelled(2階層フラグ・D-10)             │
│       │                                      │
│       ▼                                      │
│  [キュー状態: 完了/失敗] ← batch_ocr_state 更新 │
│       │                                      │
│       ▼ 全体進捗バー更新（ファイル x/合計・D-08）│
│       │                                      │
│       └───── 次ファイルへ（バッチ中止フラグ未設定なら）│
└─────────────────────────────────────────────┘
    │  全ファイル終了 or バッチ中止
    ▼
[バッチ完了状態]
    │  完了済みファイルの結果はダイアログ内に保持（D-11）
    ▼
[ファイル選択 Combobox/Listbox（D-16）] → 結果ビュー（既存 _insert_markdown 流用）
    │
    ▼（手動トリガー「📊 サマリ作成」・D-13）
[ファイル横断連結（=== ファイル名.pdf === 見出し挿入・D-15）]
    │
    ▼（_confirm_summary_cost 拡張・入力過大警告・D-14）
[complete_text_ex（既存プロバイダ層）]
    │
    ▼
[統合サマリ結果表示]
```

### Recommended Project Structure

```
pagefolio/
├── batch_ocr_state.py        # 新規・純ロジック層（Tk/fitz 非依存）
│                              #   ファイルキューの状態遷移（待機/実行中/完了/失敗）
│                              #   ファイル横断進捗集計（落とし穴5対応・BatchState 相当）
├── dialogs/
│   └── batch_ocr.py          # 新規・BatchOCRDialog（Toplevel）
│                              #   Treeview キュー一覧・2段進捗表示・D&D投入
│                              #   ファイルループコントローラ（producer 相当をここに実装）
├── ocr_engine.py              # 既存・変更なし（ファイルごとに新規生成して再利用）
├── ocr_pipeline.py            # 既存・変更なし
├── ocr_dialog.py               # 既存・変更なし（結果ビュー描画ロジックの参照元）
├── file_drop.py                # 既存・変更なし（D&D 登録パターンの参照元）
└── ui_builder.py               # 変更: Treeview 用 ttk.Style 追加・メニューバー新設（tk.Menu）

tests/
├── test_batch_ocr_state.py    # 新規・純ロジック層の単体テスト（FakeProvider 不要・状態遷移のみ）
└── test_batch_ocr_dialog.py   # 新規・E2E モックテスト（test_ocr_engine.py の FakeProvider 流用）
```

### Pattern 1: ファイルごとに OCRRunEngine を新規生成する二層ループ

**What:** バッチのファイルループは「1ファイル=1回の単一ファイルOCR実行」として扱い、既存の `_start_worker_thread`/`_render_next_page` の呼び出し契約をそのまま繰り返す。

**When to use:** バッチの各ファイル処理開始時。

**Example:**
```python
# Source: pagefolio/ocr_dialog.py:1664-1694（_start_worker_thread・既存パターン）
# バッチ側は「ファイルごとに」この生成パターンを繰り返す（D-11 のファイル単位外挿）
def _start_file_engine(self, file_entry, gen=None):
    self._engine = OCRRunEngine(
        provider=self.provider,               # ループ内で毎回 build_provider（既存 _start_ocr パターン）
        prompt=self._ocr_prompt,
        run_pages=file_entry.page_indices,     # そのファイルの全ページ
        concurrency=self.concurrency,
        cancel_flag=self._file_cancel_flag,    # ファイル内キャンセル（既存 _cancel_flag 相当）
        on_success=lambda p, t, tr: self._record_page_success(file_entry, p, t, tr),
        on_page_error=lambda p, m: self._record_page_error(file_entry, p, m),
        on_complete=lambda: self._on_file_complete(file_entry, gen),
        on_cancelled=lambda: self._on_file_cancelled(file_entry, gen),
        on_fatal=lambda msg, kind: self._on_file_fatal(file_entry, msg, kind, gen),
        breaker_threshold=CB_CONSECUTIVE_FAILURES,
    )
    self._engine.start()
    self._render_next_page_for(file_entry, gen)  # producer: 既存 _render_next_page と同型
```
`on_fatal`/`on_complete`/`on_cancelled` の中で「次ファイルへ進む」判断（バッチ全体キャンセルフラグが立っていなければ次ファイルの `_start_file_engine` を呼ぶ）を行う。これにより既存の producer-consumer 契約を一切変更せずにファイル横断ループを実現できる。

### Pattern 2: BatchState（薄い純関数層）によるファイル横断進捗集計

**What:** `PipelineState` はファイル内の共有カウンタのみを扱うため、その外側に「ファイル完了/失敗イベントの集計」を担う Tk/fitz 非依存の薄いデータクラスを新設する（PITFALLS.md 落とし穴5への直接対応）。

**When to use:** ダイアログ上部の「ファイル x/合計」ラベル・進捗バー更新、Treeview 行の状態更新のたび。

**Example:**
```python
# 新規実装イメージ（既存 PipelineState の設計思想を踏襲・pagination.py と同格の純ロジック層）
# Source pattern: pagefolio/ocr_pipeline.py:47-135（PipelineState の Lock 保護パターン）
class BatchState:
    """バッチ全体のファイル単位進捗集計（Tk/fitz 非依存・Lock 保護）。

    ファイル内の詳細（ページ単位進捗）は OCRRunEngine.progress_count() が
    真の情報源であり、本クラスは「ファイルが完了/失敗/キャンセルされたか」
    という一段上の事実のみを集計する（責務分離・落とし穴5対応）。
    """

    def __init__(self, total_files):
        self._lock = threading.Lock()
        self.total_files = total_files
        self.completed = 0
        self.failed = 0
        self.cancelled = 0

    def mark_completed(self):
        with self._lock:
            self.completed += 1

    def mark_failed(self):
        with self._lock:
            self.failed += 1

    def files_done(self):
        with self._lock:
            return self.completed + self.failed + self.cancelled
```
`progress_count()`（`OCRRunEngine`、ページ軸）と `BatchState.files_done()`（ファイル軸）は完全に独立したカウンタとして扱い、どちらか一方の値からもう一方を逆算しない。これが「二軸の進捗集計が矛盾する」落とし穴5の直接的な予防策。

### Pattern 3: 2階層キャンセルフラグ（UI は1ボタン、内部は2フラグ）

**What:** バッチ全体の `threading.Event`（例: `self._batch_cancel_flag`）と、既存のファイル内 `_cancel_flag`（`OCRRunEngine.cancel_flag` に渡すもの）を分離して保持する。「バッチ中止」ボタンは両方を同時に `.set()` する。

**Example:**
```python
# 「バッチ中止」ボタンのハンドラ（D-10）
def _on_batch_cancel(self):
    self._batch_cancel_flag.set()   # 次ファイルへ進まない判定に使う
    self._file_cancel_flag.set()    # 実行中の OCRRunEngine を即座に停止させる
```
ファイルループの「次ファイルへ進むか」の判定は、`on_complete`/`on_fatal`/`on_cancelled` コールバック内で必ず `self._batch_cancel_flag.is_set()` をチェックしてから次のファイルの `_start_file_engine` を呼ぶ（呼ばなければバッチはそこで停止する）。ファイル内キャンセル（`_file_cancel_flag`）は次ファイル開始時に必ず `.clear()` してから使う（既存 `_on_run` の `self._cancel_flag.clear()`（1358行）と同型のリセットパターン）。

### Pattern 4: 複数ファイルの D&D 投入（既存 `_on_dnd_drop` パターンの拡張）

**What:** 既存 `app.py:_on_dnd_drop`（321-354行）と全く同じ `tk.splitlist`+`SUPPORTED_EXTENSIONS` フィルタパターンを `BatchOCRDialog` 専用の Drop ターゲットに再登録する。

**Example:**
```python
# Source: pagefolio/app.py:321-333（既存パターン・変更せず踏襲）
def _on_batch_dnd_drop(self, event):
    raw_paths = self.queue_canvas.tk.splitlist(event.data)
    pdf_paths = [
        p for p in raw_paths
        if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
    ]
    if not pdf_paths:
        if raw_paths:
            messagebox.showwarning(self._L["confirm_title"], self._L["dnd_pdf_only"])
        return event.action
    self._enqueue_files(pdf_paths)  # 待機状態でキューへ追加（事前ページ数スキャン込み）
    return event.action
```
既存の `MergeOrderDialog` 起動分岐（複数ファイル時）はバッチには不要（バッチは元々複数ファイル前提のキューであり、結合順序という概念がない）。

### Pattern 5: 事前ページ数スキャン（fitz、メインスレッド逐次）

**What:** `MergeOrderDialog.__init__`（`pagefolio/dialogs/merge.py:35-43`）と同型の「`fitz.open()`→`page_count`取得→即 close」パターンをそのまま流用する。

**Example:**
```python
# Source: pagefolio/dialogs/merge.py:35-43（既存パターン・そのまま流用）
for p in paths:
    try:
        d = fitz.open(p)
        page_counts[p] = len(d)
        d.close()
    except Exception as e:
        logger.debug("ページ数取得失敗: %s", e)
        page_counts[p] = 0  # 壊れたファイル: キュー上でエラー表示（Claude's Discretion）
```

### Pattern 6: 集約コスト確認ダイアログ（既存 `_confirm_cost` の拡張）

**What:** 既存 `OCRDialog._confirm_cost`（`ocr_dialog.py:1194-1235`）は単一ファイルの `page_count` を前提にしている。バッチ版は全ファイルの合計ページ数を渡すだけで、ロジック自体（プロバイダ別ホスト表示・`_estimate_cost`・`messagebox.askyesno`）は完全に再利用できる。

**Example:**
```python
# 既存 _confirm_cost の呼び出し方をそのまま踏襲し、page_count に合計値を渡すのみ
total_pages = sum(f.page_count for f in queued_files)
if not self._confirm_cost(page_count=total_pages, settings=s):
    return  # バッチ開始を中止
```

### Pattern 7: ファイル横断統合サマリ（ファイル名見出し連結・D-15）

**What:** 既存 `_format_pages_text`（単一ファイル内の全ページ連結、`ocr_dialog.py` 1980行台）と同型のロジックを、ファイルごとに見出しを挿入しながら連結する形に拡張する。

**Example:**
```python
# 既存 _format_pages_text（ocr_dialog.py）と同じ「ページ区切り文言 + 本文」パターンを
# ファイル軸にもう一段適用する（D-15）
def _format_batch_summary_input(self):
    parts = []
    for file_entry in self._completed_files():
        parts.append(f"=== {file_entry.display_name} ===")
        parts.append(file_entry.format_pages_text())  # 既存 _format_pages_text 相当
    return "\n".join(parts)
```
この連結結果の文字数を既存 `_confirm_summary_cost(char_count, settings=s)`（`ocr_dialog.py:1237-1265`）へそのまま渡せば D-14 の「入力過大時の事前警告」を満たす（新規閾値ロジック不要）。

### Anti-Patterns to Avoid

- **ファイル並列処理（`ThreadPoolExecutor` でファイルごとにスレッドを割り当てる）:** PITFALLS.md 落とし穴3の直接的原因。`fitz.open`/`get_pixmap` はファイルが異なっても同一プロセス内でスレッド安全性が保証されない。ファイル間は必ず逐次処理（Anti-Feature として確定済み）。
- **`OCRRunEngine` の使い回し（`run_pages`/`provider` を差し替えて同一インスタンスを次ファイルに再利用）:** D-11（Phase 3）の「実行ごと新規生成」原則に反する。`results`/`errors`/`skipped_pages` 等の per-run 状態がファイル間でリークする。
- **バッチキャンセルを「現在ファイルの `_cancel_flag`」のみで実装する:** PITFALLS.md 落とし穴4そのもの。次ファイルへ自動的に進んでしまう。必ずバッチ全体フラグを独立して持つ（Pattern 3）。
- **ファイル軸進捗とページ軸進捗を1つのカウンタで表現しようとする:** PITFALLS.md 落とし穴5。`BatchState.files_done()` と `OCRRunEngine.progress_count()` は別軸として独立管理する（Pattern 2）。
- **フォールバック機構（Phase 2 で実装済みの `ocr_fallback.py`）をバッチのファイル失敗処理に混用する:** V180-BATCH-03 は「ファイル単位の失敗は自動スキップ」（D-09）であり、プロバイダ切替を伴うフォールバック（Phase 2 の明示確認フロー）とは別概念。混同すると「送信先確認の再提示」（Phase 2 の確定方針）を無自覚に省略するリスクが生まれる。ファイル失敗時はフォールバック候補を試すのではなく、単純にそのファイルをスキップして次へ進む。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OCR実行のリトライ/バックオフ/サーキットブレーカー | 新規リトライループ | `OCRRunEngine`（`consume_one`/`PipelineState` 経由） | 既に Phase 3 で抽出済み・E2Eテスト済み。ファイルごとに新規生成するだけで完全に流用できる |
| クラウド送信のコスト確認・送信先確認 | 新規確認ダイアログ | `_confirm_cost`/`_confirm_summary_cost` の拡張呼び出し | 引数（page_count/char_count）を集約値に変えるだけで挙動が変わらず一貫性を保てる |
| 埋め込みテキスト検出によるOCRスキップ | 新規判定ロジック | `has_embedded_text(page)`（`pagefolio.ocr`） | ファイル単位でも1ページずつの判定ロジックは変わらない。バッチのproducerループ内でそのまま呼ぶ |
| Markdown整形結果表示・コピー/保存(raw維持) | 新規描画ロジック | `_insert_markdown`（`ocr_dialog.py`） | D-16 で明示的に流用方針が確定済み。ファイル選択時に表示内容を差し替えるだけで良い |
| ページ数取得（壊れたPDF検出含む） | 新規PDF検証ロジック | `fitz.open(path).page_count` + try/except（`merge.py` パターン） | 既存の枯れたパターンをそのまま流用すれば十分 |

**Key insight:** 本フェーズの新規実装量は「見た目より小さい」。既存の producer-consumer・コスト確認・サマリ生成ロジックはすべて「呼び出し方を変えずに、呼ぶ回数（=ファイル数）を増やす」だけで対応できる設計になっている（Phase 3 の `OCRRunEngine` 抽出がまさにこの再利用性のために行われた）。新規に書くべきは「ファイルキューの状態管理」と「ファイルループのオーケストレーション」という薄い配線層のみ。

## Common Pitfalls

### Pitfall 1: fitz.Document のスレッド間共有違反（ファイル並列化の誘惑）

**What goes wrong:** 「複数ファイルを同時に処理したい」という自然な要求から、ファイルごとに `ThreadPoolExecutor` を割り当てて並列に `fitz.open()`→`get_pixmap()` を呼んでしまう。

**Why it happens:** PyMuPDF のスレッドセーフ制約はファイル単位ではなくプロセス全体にかかるが、「ファイルが違えば安全」という誤った直感を持ちやすい。

**How to avoid:** ファイル間も含めて `fitz.open`/`get_pixmap` はメインスレッドの単一シーケンスで直列化する。ワーカースレッドへ渡すのは常に「レンダリング済みの b64 PNG」のみ（既存の V14-D-05/06・OCRRunEngine の設計をそのまま外挿）。

**Warning signs:** 複数ファイル同時実行時のクラッシュ・native crash・原因不明のセグフォルト。

### Pitfall 2: バッチキャンセルが現在ファイルのみに留まる

**What goes wrong:** 「バッチ中止」ボタンがファイル内 `_cancel_flag` のみをセットし、現在のファイルが終わり次第、次のファイルが自動的に始まってしまう。

**Why it happens:** 既存のキャンセル機構は「1回の OCR 実行」を前提に設計されており、バッチという「複数回の実行の列」という階層をそもそも想定していない。

**How to avoid:** Pattern 3 の2階層フラグを必ず実装し、ファイルループの「次へ進む」判定に必ずバッチ全体フラグをチェックする一手を入れる。

**Warning signs:** バッチ中止ボタンを押しても次ファイルの OCR が開始される、進捗バーが止まらない。

### Pitfall 3: バッチ進捗集計がファイル単位/ページ単位で二重に矛盾する

**What goes wrong:** ファイル軸の「x/合計ファイル数」とページ軸の「現在ファイル内 n/合計ページ」の更新タイミングがずれる、あるいは失敗ファイルをスキップした際にファイルカウンタだけ進めてページカウンタとの整合が崩れる。

**Why it happens:** `PipelineState` はファイル内の共有カウンタのみを想定しており、ファイル横断の集計責務を持たない。

**How to avoid:** Pattern 2 の `BatchState` を新設し、ファイル完了/失敗イベントを `PipelineState` の外側で独立集計する。「1ファイルの fatal 判定（サーキットブレーカー）がそのファイルだけスキップする」という D-09 の挙動を、`on_fatal` コールバック内で明示的に「BatchState.mark_failed() → 次ファイルへ」という1本のコードパスに集約する。

**Warning signs:** 進捗バーが100%を超える/戻る、失敗ファイルがあると合計件数の分母がずれる。

### Pitfall 4: 新規 Treeview のテーマ整合漏れ

**What goes wrong:** `ttk.Treeview` はコードベース初導入のウィジェットであり、既存 `ui_builder.py:_build_styles` にはスタイル定義が存在しない。デフォルトの `ttk.Treeview` スタイルはOSテーマ依存の白背景/黒文字になりやすく、PageFolio のダーク/ライトテーマ（`C` 辞書）と食い違う見た目になる。

**Why it happens:** 既存の全ウィジェットは `tk.Frame`/`tk.Label`/`ttk.Button` の組み合わせで自前スタイリングされており、Treeview 特有の `Treeview`/`Treeview.Heading` スタイル要素・選択行の `style.map` 設定を新規に書く必要があることが見落とされやすい。

**How to avoid:** `_build_styles`（または新規メソッド）に `style.configure("Treeview", background=C["BG_PANEL"], foreground=C["TEXT_MAIN"], fieldbackground=C["BG_PANEL"])` と `style.map("Treeview", background=[("selected", C["ACCENT"])])` を追加し、D-06 の警告色行は `tree.tag_configure("failed", foreground=C["WARNING"])` + `tree.item(iid, tags=("failed",))` で実現する。テーマ切替（ライト/ダーク）時に Treeview 配色も追随することを手動確認する。

**Warning signs:** ライトテーマ選択時にキュー一覧の行が読みにくい、警告色（失敗行）がテーマ変更後に反映されない。

### Pitfall 5: メニューバー新設が既存ショートカット/キーバインドと衝突する

**What goes wrong:** PageFolio は現在 `tk.Menu` を1つも使用していない（全機能はツールバー/右パネルの `ttk.Button`）。D-01 で新設するメニューバーに標準的な Alt+文字 アクセラレータキーを設定すると、既存の `ShortcutsDialog`（`root` 直下にバインドされた単キー・修飾キー付きショートカット）と衝突する可能性がある（既知の WR-02 課題：修飾キーなし単キー登録が通常入力ウィジェットと衝突しうる、と同系統のリスク）。

**Why it happens:** メニューバーが本プロジェクト初導入のため、既存のキーバインド一覧（`ShortcutsDialog` の `cmd_map`）との重複チェックが計画時に見落とされやすい。

**How to avoid:** 新設メニュー項目にアクセラレータキー（下線付き文字）を設定する場合は、既存 `ShortcutsDialog` の11コマンドのキーバインドと重複しないことを実装前に確認する。アクセラレータ設定自体を見送り、メニュークリックのみで起動する設計にすればこのリスクは構造的に回避できる（Claude's Discretion範囲）。

**Warning signs:** メニュー項目のアクセラレータキーを押すと意図しない別機能が発火する。

## Code Examples

### 既存 `_start_ocr`（`ocr.py:541-624`）の provider 構築パターン — バッチのファイルループ内でそのまま流用

```python
# Source: pagefolio/ocr.py:541-624
url = self.settings.get("lm_studio_url", DEFAULT_LM_STUDIO_URL)
model = self.settings.get("lm_studio_model", "")
preset = self.settings.get("ocr_prompt_preset", "text")
from pagefolio.settings import load_custom_prompt
custom_prompt = load_custom_prompt(self.settings)
# ... クラウドプロバイダのキー事前解決（成功基準3・D-02/D-03）
name = self.settings.get("ocr_provider", "")
api_key = None
if name in {"claude", "gemini", "runpod"}:
    from pagefolio.ocr_providers import OCRAPIKeyError
    session_keys = getattr(self, "_session_api_keys", {})
    try:
        api_key = _resolve_api_key(name, session_keys)
    except OCRAPIKeyError:
        api_key = None
provider = build_provider(
    self.settings, api_key=api_key,
    plugin_manager=getattr(self, "plugin_manager", None),
)
concurrency = max(1, min(provider.max_concurrency,
    int(self.settings.get("ocr_concurrency", DEFAULT_OCR_CONCURRENCY))))
```
バッチは**この provider/concurrency をファイルループの外側で1回だけ構築し、各ファイルの `OCRRunEngine` 生成時に再利用する**（プロバイダ設定はファイル間で共通のため、ファイルごとの再構築は不要 — ただし D-14 のようにフォールバック候補への切替が発生する場合は例外。本フェーズはフォールバック機構自体を対象外とするため単純化できる）。

### 既存 `_confirm_cost`（`ocr_dialog.py:1194-1235`）— 集約コスト確認への流用ポイント

```python
# Source: pagefolio/ocr_dialog.py:1194-1235
def _confirm_cost(self, page_count=None, settings=None):
    s = settings if settings is not None else self.app.settings
    name = s.get("ocr_provider", "")
    if name == "gemini":
        model = s.get("gemini_model", "gemini-2.5-flash")
        host = "generativelanguage.googleapis.com"
    elif name == "runpod":
        model = s.get("runpod_model", "") or "runpod"
        host = s.get("runpod_url", "") or self._L["llm_runpod_host_unset"]
    else:
        model = s.get("claude_model", "claude-sonnet-4-6")
        host = "api.anthropic.com"
    if page_count is None:
        page_count = len(self.page_indices)
    cost = self._estimate_cost(model, page_count)
    msg = self._L["ocr_cost_confirm_msg"].format(host=host, count=page_count, cost=cost)
    return messagebox.askyesno(self._L["ocr_cost_confirm_title"], msg, parent=self)
```
バッチ版は `page_count=合計ページ数` を渡すだけで動作する。**新規の lang.py キーを追加する場合は、既存 `ocr_cost_confirm_msg` を再利用するか、`batch_cost_confirm_msg`（ファイル数を含む文言）を ja/en 両方に新設するかを計画時に決定すること（lang.py はキー数の左右一致が回帰テスト `test_lang_parity.py` で保証されているため、追加時は必ず両言語同時追加）。**

### 既存 `OCRRunEngine` コンストラクタ契約（`ocr_engine.py:74-124`）— ファイルごとの新規生成時に渡す引数

```python
# Source: pagefolio/ocr_engine.py:74-89
def __init__(
    self, provider, prompt, run_pages, concurrency, cancel_flag,
    on_success=None, on_page_error=None, on_retry_wait=None,
    on_progress=None, on_complete=None, on_cancelled=None, on_fatal=None,
    breaker_threshold=DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
):
```
「構築済み `provider` インスタンスのみ受け取り、生設定/APIキーは渡さない」（D-02・T-03-01 情報漏洩防止）という既存制約はバッチでも厳守すること。ファイルごとに `OCRRunEngine` を再構築する際も、`provider`（プロバイダインスタンス）自体はファイル間で使い回してよい（インスタンス自体は per-file 状態を持たない）。

## State of the Art

本フェーズは PageFolio 内部の新機能追加であり、外部エコシステムの技術トレンド変化は関係しない。「State of the Art」として記録すべき唯一の変化点は本プロジェクト内の設計進化である。

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 単一ファイルOCRのみ（`OCRDialog` が producer + consumer 駆動を一体で保持） | `OCRRunEngine`（consumer駆動）が `OCRDialog` から抽出済み、バッチ/単一ファイルで共用可能 | Phase 3（v1.8.0・2026-07-14完了） | バッチOCRが「新規実行エンジン」を書かずに済む前提が整った。本フェーズはこの資産を消費する側 |

**Deprecated/outdated:** なし（バッチOCR自体が新規機能のため置き換え対象は存在しない）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-01「新規メニュー項目」は文字通りの `tk.Menu`（メニューバー）新設を意味し、既存ツールバーへのボタン追加ではない | Architectural Responsibility Map / Pitfall 5 | もし実際はツールバーボタンで十分という意図であれば、メニューバー新設という余計な実装コスト（初導入・既存ショートカットとの衝突確認）が不要になる。計画時にユーザー意図を再確認するか、`discuss-phase` の記録（D-01文言）を根拠にメニューバー実装で進めるかを明確化すること |
| A2 | ファイルループ内で `provider`/`concurrency` はバッチ開始時に1回だけ構築し、全ファイルで使い回してよい（フォールバック機構は対象外のため） | Code Examples（`_start_ocr` 流用ポイント） | もし将来的にファイルごとに異なるプロバイダ設定を許容する要件が追加された場合、この単純化は成立しなくなる。現行要件（V180-BATCH-01〜05）はプロバイダ切替を含まないため妥当と判断 |
| A3 | 壊れた/開けないPDFファイルは事前ページ数スキャン時に検出し、キュー上で「エラー」状態として表示する（Claude's Discretion範囲内の推奨） | Architecture Patterns Pattern 5 | 具体的な表示文言・キュー上の扱い（除外するか、失敗状態として残すか）はCONTEXT.mdで計画時裁量とされているため、`test_batch_ocr_state.py` のテストケース設計時に確定が必要 |
| A4 | 新規 lang.py キー（Treeview列見出し・状態ラベル「待機/実行中/完了/失敗」・バッチメニュー項目文言等）は既存の `ocr_`/`dnd_`プレフィックス規約を踏襲し、新規プレフィックス（例: `batch_ocr_`）で追加する | Code Examples | 命名規約が計画者の裁量に委ねられるため、既存キーとの命名衝突・一貫性の欠如リスクがある。`test_lang_parity.py` のキー数一致チェックは自動検証されるため機能的リスクは低い |

**If this table is empty:** 該当なし（上記4件は確認推奨）。

## Open Questions

1. **メニューバー新設のスコープ（D-01・Assumption A1）**
   - What we know: CONTEXT.md D-01は「新規メニュー項目「バッチOCR」から起動」と明記し、Claude's Discretionに「新規メニュー項目のメニューバー上の配置位置」とある（=メニューバー自体の存在は確定済み、配置位置のみ裁量）。
   - What's unclear: 既存に `tk.Menu` が一切存在しないため、メニューバー全体（File/Edit相当の他メニュー項目を含むか、「バッチOCR」1項目のみの最小メニューバーか）をどこまで新設するかが未確定。
   - Recommendation: 計画時は「バッチOCR」1項目のみを持つ最小メニューバー（例: `menubar = tk.Menu(root); root.config(menu=menubar)` + 単一トップレベルメニュー「ツール」→「バッチOCR」、または直接トップレベルに「バッチOCR」ボタン形式のメニュー）として最小実装に留め、他機能のメニュー化は本フェーズのスコープ外と明記する。

2. **事前ページ数スキャン失敗時のキュー表示（Claude's Discretion・Assumption A3）**
   - What we know: `fitz.open()`失敗時のエラーハンドリングパターンは `merge.py` に前例がある（try/except + ログ + 0埋め）。
   - What's unclear: バッチキューでは「0ページ」として待機状態のまま残すのか、専用の「エラー」状態（失敗と同じ警告色）として即座に表示するのかが未確定。
   - Recommendation: 「エラー」状態として即座に警告色表示し、削除のみ可能（D-07と同じ操作制約）とするのが D-06（失敗ファイル警告色）の設計と一貫性がある。計画時に確定すること。

3. **バッチ関連の新規永続設定キーの要否**
   - What we know: キューの永続化はしない（D-11・Anti-Feature確定）。
   - What's unclear: バッチダイアログ固有のUI設定（例: 前回のconcurrency値・ウィンドウジオメトリ）を`pagefolio_settings.json`に永続化するかどうかは要件文言・CONTEXT.mdのどちらにも明記がない。
   - Recommendation: 単一ファイルOCRの `OCRDialog` は既存設定（`ocr_concurrency`等）をそのまま読み込む設計のため、バッチも同じ既存設定キーを共有し、バッチ専用の新規永続キーは追加しない方針が最もシンプルで一貫性が高い。計画時に明示的にこの方針を記載することを推奨。

## Environment Availability

本フェーズはコード/内部機能追加のみで、新規外部サービス・CLIツール・ランタイム依存を追加しない。既存の Python 3.8+ / tkinter / PyMuPDF / tkinterdnd2 環境がそのまま利用可能であることは Phase 1〜3 で既に確認済み（`pytest`/`ruff` 実行環境含む）。本セクションは省略する。

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（`pyproject.toml` の `[tool.pytest.ini_options]`） |
| Config file | `pyproject.toml`（`testpaths = ["tests"]`・`pythonpath = ["src"]`） |
| Quick run command | `pytest tests/test_batch_ocr_state.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V180-BATCH-01 | 複数ファイルD&D投入でキューに追加される（フィルタ・重複除外含む） | unit | `pytest tests/test_batch_ocr_state.py::test_enqueue_files -x` | ❌ Wave 0 |
| V180-BATCH-02 | キュー状態遷移（待機→実行中→完了/失敗）と全体進捗集計が正しい | unit | `pytest tests/test_batch_ocr_state.py::test_state_transitions -x` | ❌ Wave 0 |
| V180-BATCH-03 | ファイル単位の fatal 発生時に自動スキップし次ファイルへ進む（fitz は逐次のまま） | integration | `pytest tests/test_batch_ocr_dialog.py::test_file_failure_continues -x`（`FakeProvider` で fatal を注入、`test_ocr_engine.py` のパターン流用） | ❌ Wave 0 |
| V180-BATCH-04 | バッチ中止ボタン押下で2階層フラグが同時にセットされ、実行中ファイルが停止し次ファイルへ進まない | integration | `pytest tests/test_batch_ocr_dialog.py::test_batch_cancel_stops_all -x` | ❌ Wave 0 |
| V180-BATCH-05 | ファイル横断連結（見出し挿入）+ 入力過大警告（既存 `_confirm_summary_cost` 拡張）が動作する | unit + integration | `pytest tests/test_batch_ocr_dialog.py::test_batch_summary_concat -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_batch_ocr_state.py tests/test_batch_ocr_dialog.py -x`
- **Per wave merge:** `pytest`（フルスイート・既存 700件超の回帰込み）
- **Phase gate:** フルスイート green を `/gsd-verify-work` 前提とする

### Wave 0 Gaps
- [ ] `tests/test_batch_ocr_state.py` — 新規純ロジック層（キュー状態遷移・BatchState進捗集計）の単体テスト。`tests/test_ocr_pipeline.py`（`PipelineState`のLock保護テストパターン）を参考にする
- [ ] `tests/test_batch_ocr_dialog.py` — E2Eモックテスト。`tests/test_ocr_engine.py` の `FakeProvider` パターンをそのまま流用し、複数ファイル分の `OCRRunEngine` 生成を検証する
- [ ] Framework install: 不要（pytest は既存導入済み）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本フェーズはローカルデスクトップアプリの機能追加であり認証機構は対象外 |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし |
| V5 Input Validation | yes | ファイルパス検証（`SUPPORTED_EXTENSIONS`フィルタ・既存パターン踏襲）・ページ数スキャン時の壊れたPDF検出（`fitz.open`のtry/except） |
| V6 Cryptography | no | 本フェーズは新規暗号化機構を追加しない（既存パスワード付与機能とは独立） |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| バッチ経由の意図しない大量クラウド送信（複数ファイル×大量ページの一括送信によるコスト超過・情報漏洩） | Information Disclosure / Repudiation | D-03（集約コスト確認ダイアログを一括表示・既存 `_confirm_cost` 拡張）+ D-14（サマリの入力過大警告）で対応済み。フォールバックによる無断別ベンダー送信は本フェーズのスコープ外（Phase 2 で既に確定方針） |
| APIキーのログ混入（バッチ化でログ出力量が増えることによる相対リスク増） | Information Disclosure | 既存の「キー名のみログ・値は非出力」規約（`_resolve_api_key`/`OCRAPIKeyError`）をバッチのファイルループ経路にもそのまま適用する。新規ログ出力箇所（ファイル完了/失敗ログ）でAPIキー文字列を直接ログしないことを実装時に確認 |
| 悪意あるファイル名によるパストラバーサル的懸念 | Tampering | ローカルファイルダイアログ/D&D経由のパスのみを扱い、外部入力（ネットワーク経由）は一切受け付けない設計のためリスクは低い。既存 `_open_pdf_path`/`fitz.open`のエラーハンドリングパターンをそのまま踏襲すれば十分 |

## Sources

### Primary (HIGH confidence)
- `pagefolio/ocr_engine.py`（Phase 3 で抽出済みの `OCRRunEngine`・全文精査） — 一次情報源
- `pagefolio/ocr_pipeline.py`（`PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`・全文精査） — 一次情報源
- `pagefolio/ocr_dialog.py`（`_confirm_cost`/`_confirm_summary_cost`/`_on_run`/`_render_next_page`/`_on_summary`/`_summary_worker`・該当範囲精査） — 一次情報源
- `pagefolio/ocr.py`（`_start_ocr`/`build_provider`・541-624行精査） — 一次情報源
- `pagefolio/file_drop.py`・`pagefolio/app.py:_on_dnd_drop`（321-354行）・`pagefolio/dialogs/merge.py`（ページ数スキャンパターン） — 一次情報源
- `.planning/phases/03-ocr-e2e/03-PATTERNS.md`（Phase 3 の producer-consumer 抽出パターン詳細） — 一次情報源（前フェーズ成果物）
- `.planning/research/PITFALLS.md`（落とし穴3/4/5・全文） — curated一次情報源
- `.planning/research/FEATURES.md` §3（バッチ複数ファイルOCR・全文） — curated一次情報源
- `.planning/research/SUMMARY.md`（Phase 5 相当の推奨アプローチ記述） — curated一次情報源
- `.planning/phases/04-ocr/04-CONTEXT.md`（D-01〜D-16・全文） — ユーザー決定の一次情報源

### Secondary (MEDIUM confidence)
- なし（本フェーズは既存コードベース資産の再利用が中心のため外部ソースの参照は不要と判断）

### Tertiary (LOW confidence)
- なし

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 新規外部依存なし、既存固定バージョンをそのまま使用するため検証不要
- Architecture: HIGH — 実コードベース直接精査に基づく一次情報源。Phase 3 の抽出設計がバッチ再利用を前提に作られている
- Pitfalls: HIGH（落とし穴3/4/5は自プロジェクトのマイルストーンリサーチで既に特定済み）/ MEDIUM（Pitfall 4/5 は本フェーズ固有の新規UI要素に対する追加調査で、コードベース内に前例がないため実装時の確認が必要）

**Research date:** 2026-07-15
**Valid until:** 2026-08-14（30日・安定した内部コードベースのため長め妥当）
