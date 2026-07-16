---
phase: 4
reviewers: [antigravity]
reviewed_at: 2026-07-15T20:27:19+0900
plans_reviewed: [04-01-PLAN.md, 04-02-PLAN.md, 04-03-PLAN.md]
---

# Cross-AI Plan Review — Phase 4

## Antigravity Review

# Cross-AI Plan Review: PageFolio Phase 4 — バッチ複数ファイルOCR

本レビューでは、PageFolio の Phase 4（バッチ複数ファイルOCR）に関する 3 つの実装計画（`04-01-PLAN.md`, `04-02-PLAN.md`, `04-03-PLAN.md`）について、実リポジトリのソースコードと照らし合わせて検証・評価を行いました。

---

## 1. 04-01-PLAN.md (バッチキュー純ロジック層) のレビュー

### 概要
`pagefolio/batch_ocr_state.py` の新規作成および単体テスト `tests/test_batch_ocr_state.py` の整備を行い、Tkinter や fitz に依存しないスレッド安全な状態管理と進捗集計のロジック層を確立する計画です。モジュール境界とテストの独立性が高く、非常に堅牢な設計となっています。

### 強み
* **Tk/fitz 依存の完全な排除**: `ocr_pipeline.py` 同様、GUI や PDF 操作に依存しない純ロジック層として設計されています。これにより、軽量かつ高速に実行可能な単体テストを構築し、事前に状態遷移の網羅的検証を可能にしています。
* **二軸進捗の独立性によるバグ防止**: ファイル単位の進捗 (`BatchState.files_done()`) を、ページ単位の進捗カウンタから逆算せず、独立した Lock 保護カウンタとして集計する設計となっています。これにより、ファイル失敗時のスキップやキャンセルで発生しがちな「進捗率が100%を超える/戻る」という不整合（`.planning/research/PITFALLS.md` の落とし穴5）を構造的に予防しています。
* **重複排除の明確化**: `enqueue_files` がパスによる重複排除 (dedup) を行い、同じファイルを二重に処理しないように保証している点。

### 懸念事項
* **`test_no_unused_lang_keys` 回帰テストとの競合 (Severity: MEDIUM)**:
  `tests/test_lang_parity.py` の [L55-76](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py#L55-L76) に定義されている `test_no_unused_lang_keys` は、`pagefolio/lang.py` 内に定義された全言語キーがソースコードのどこかで（シングルまたはダブルクォーテーションで囲まれた文字列として）使用されていることを検証します。Task 1 で言語キーを定義し、Task 2 や後続の 04-03 でそれを使い始めるという段階を踏むと、Task 1 の verification 実行時 (`pytest tests/test_lang_parity.py`) に「未使用キー」としてアサーションエラーになってしまいます。
* **エラー状態の初期遷移設計の不足 (Severity: LOW)**:
  壊れたPDFを事前ページ数スキャン時に検出し、`STATUS_ERROR` として記録する設計ですが、このエントリに対して `BatchState` の進捗集計（`files_done()`, `total_files`）がどのように影響を受けるのかについて記述が曖昧です。開始時点でエラーとなったファイルは `total_files` にカウントされたまま `mark_failed` を明示的に呼び出して処理済みにしないと、実行完了時に `remaining()` が 0 にならなくなる可能性があります。

### 提案
* **未使用キーアサーションの回避**:
  Task 1 で言語キーを `lang.py` に追加する際、一時的に `tests/test_lang_parity.py` の `_ALLOWLIST`（L18）に一時的なキー名を追加するか、UI骨格のファイル (`batch_ocr.py`) にダミーの参照を書き込むように手順を補足してください。
* **エラーファイル進捗処理の明確化**:
  `BatchState` において、`STATUS_ERROR` を含む壊れたファイルがキュー登録された時点で、初期から「処理済み」としてマークされ `files_done()` に加算されるのか、それとも実行開始時にスキップされて `mark_failed()` されるのか、その遷移フローを `batch_ocr_state.py` のドキュメントまたはアサーションで明確化してください。

### リスク評価
* **リスクレベル**: **LOW**
* **理由**: 並行安全性やモジュール境界が非常に明確であり、新規導入の範囲も狭いため、計画通り安全に実装可能です。

---

## 2. 04-02-PLAN.md (BatchOCRDialog コア & ファイルループ) のレビュー

### 概要
`BatchOCRDialog` (`pagefolio/dialogs/batch_ocr.py`) のコアUIと、1ファイルずつ sequential に OCR 処理を実行するファイルループコントローラ、およびキャンセル/失敗時の処理フローを実装する計画です。既存の `OCRRunEngine` をファイルごとに新規生成するアプローチを採用し、`fitz` のスレッド制限をメインスレッド逐次処理でクリアします。

### 強み
* **実証済み資産 `OCRRunEngine` の再利用**: Phase 3 で `ocr_dialog.py` から抽出された `OCRRunEngine` (`pagefolio/ocr_engine.py`) をファイルループ内で毎回新規生成し再利用する設計。`results` や `errors` などの実行時状態のリークを構造的に防止しています。
* **同期的なワーカー減算と完了判定**: `OCRRunEngine` 側の `_pstate.decrement_worker()`（[ocr_engine.py:L246-260](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_engine.py#L246-L260)）が最終ワーカーの終了をスレッド安全に検出し、完了/致命的エラー/キャンセルコールバックを1回だけ呼び出すため、バッチ側の前進処理 (`_advance_to_next_file`) が複数回呼ばれる競合状態が防がれている点。
* **スレッドセーフな `fitz` 操作の直列化**: `fitz.open` / `get_pixmap` をすべてメインスレッドで逐次処理し、ワーカースレッドへは base64 PNG のみを渡す。これにより、PyMuPDF のスレッド非互換性によるネイティブクラッシュ（落とし穴3）を完全に回避しています。

### 懸念事項
* **ダイアログクローズ時のスレッドリーク (Severity: HIGH)**:
  バッチ処理がバックグラウンドスレッドで実行されている最中に、ユーザーがダイアログの「✕」ボタンや OS のクローズ機能で `BatchOCRDialog` を閉じた場合、`WM_DELETE_WINDOW` のハンドリングが実装されていないと、UI 自体は消滅するが、ワーカースレッドが回り続け、`fitz` の操作や外部 API 送信が走り続けてしまいます。また、存在しないウィジェットに対して `after` 経由で UI 更新が走ると、`tk.TclError` が多発します。
* **再実行時のボタン活性化および状態遷移 (Severity: MEDIUM)**:
  「バッチ中止」を押した後に再度「▶ 実行」を押した場合、あるいはバッチが一旦完了した後に新しいファイルをキューに追加して再度「▶ 実行」を押した場合の挙動が考慮されていません。「▶ 実行」ボタンが完了または中止後に活性化されるのか、その場合、すでに `STATUS_DONE` となっているファイルはスキップされるのか、などの再実行制御フローが欠落しています。
* **事前ページ数スキャン時の UI ブロッキング (Severity: MEDIUM)**:
  D&D またはファイルダイアログから大量の PDF (例: 100 ファイル以上) を一括投入した際、メインスレッド逐次で `fitz.open(p)` からページ数を取得します。このスキャンは比較的軽量であるものの、ディスクI/Oを伴うため、大量ファイル投入時には一時的に UI のフリーズ（応答なし）が発生し、ユーザー体験を損ねる恐れがあります。

### 提案
* **`WM_DELETE_WINDOW` のバインドとクリーンアップ**:
  `BatchOCRDialog` の `__init__` で `self.protocol("WM_DELETE_WINDOW", self._on_close)` をバインドし、ダイアログ破棄時に `_on_batch_cancel` を強制呼び出ししてスレッドを安全に停止させてから `destroy()` を呼ぶようにタスクを追加してください。
* **「▶ 実行」ボタンの活性化・再実行ガード**:
  バッチ実行中は「▶ 実行」ボタン、ファイル追加/削除ボタンを `disabled` にし、バッチ中止・完了後は「▶ 実行」を再活性化させてください。また、再実行時には `STATUS_PENDING` および `STATUS_ERROR` 以外の完了済みファイルをスキップするロジック（またはキューをリセットする仕様）を明確に定義してください。
* **事前スキャンの進捗表示または順次取得**:
  事前ページ数スキャン時、ファイル数が多い場合は簡易的な「読み込み中...」のステータス表示（またはプログレスバー）を出すことを検討してください。あるいは、D&D 投入時に一括ですべて取得するのではなく、OCR 実行ループの直前でそのファイルの `page_count` を取得する設計への変更も視野に入れてください。

### リスク評価
* **リスクレベル**: **MEDIUM**
* **理由**: ダイアログが破棄されたときのスレッド制御や、実行完了・中止後のUIコントロールが欠落しており、リソースリークやフリーズなどの不安定さにつながるリスクがあるためです。

---

## 3. 04-03-PLAN.md (統合サマリ・メニュー導線) のレビュー

### 概要
`BatchOCRDialog` にファイル横断の統合サマリ生成とファイル別結果閲覧を追加し、新設されるメニューバー（`tk.Menu`）からの起動導線、Treeview やメニューのテーマに沿った ttk.Style、および後方互換再エクスポートを配線してバッチOCR機能を完成させる計画です。

### 強み
* **手動トリガーによるコスト制御**: 統合サマリを自動生成せず手動（「📊 サマリ作成」ボタン）のみで動作させ、`_confirm_summary_cost` による合計文字数の過大入力警告（D-14）を通すことで、不要な API 送信コストの発生やトークン制限超過を確実に回避しています。
* **アクセラレータ衝突の構造的回避**: メニュー項目「バッチOCR」にアクセラレータキー（Ctrl+Bなど）を設定せず、クリック起動のみに限定しています。これにより、既存の `ShortcutsDialog` の 11 コマンド（[shortcuts.py:L27-39](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/shortcuts.py#L27-L39)）との衝突（落とし穴5）を完全に排除しています。
* **結果閲覧時の Raw 状態維持**: ファイル別結果閲覧時に `_insert_markdown` を使って Markdown プレビューを表示しつつも、コピーや保存の対象となる raw テキストデータは変更せず維持しています。

### 懸念事項
* **`ocr_dialog.py` 依存メソッドの再利用設計の曖昧さ (Severity: MEDIUM)**:
  `ocr_dialog.py` の `_insert_markdown`（[ocr_dialog.py:L1800-1819](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_dialog.py#L1800-L1819)）や `_confirm_summary_cost`（[ocr_dialog.py:L1237-1265](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_dialog.py#L1237-L1265)）は `OCRDialog` クラスのインスタンスメソッドとして定義されており、`BatchOCRDialog` はこれを継承していません。`ocr_dialog.py` 自体は変更対象（`files_modified`）に入っていないため、これらのメソッドを `BatchOCRDialog` でどのように流用するか（同一ロジックを自前定義するのか、それとも `ocr_dialog.py` からインポートしてハック的に呼ぶのか）が明確になっていません。

### 提案
* **共通描画・確認メソッドのコピペ移植または共通化**:
  `_insert_markdown` や `_confirm_summary_cost` のコードはシンプルであるため、`BatchOCRDialog` クラスに同一シグネチャ・同一挙動のメソッドとして自前実装（コピペ移植）することを計画に明記してください。
* **Treeview 配色のテーマ追随確認**:
  `ui_builder.py`（[ui_builder.py:L15-93](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/ui_builder.py#L15-L93)）に Treeview スタイルを追記する際、`_build_styles` 内で `C` 辞書を参照していることを確認し、テーマ切り替え時に `_build_styles()` が再呼び出しされて Treeview ウィジェットの色が正しく更新されることを実装タスクの受け入れ基準に明記してください。

### リスク評価
* **リスクレベル**: **LOW**
* **理由**: サマリの連結（`=== ファイル名.pdf ===` 見出し）や、アクセラレータ回避による既存ショートカットとの共存など、実用的な UIUX がうまく統合されており、安全性が高いです。

---

## 4. 全体的な依存関係・マイルストーン評価

* **開発履歴・整合性**: 計画全体を通じて、 fitz (PyMuPDF) のメインスレッド限定制約や、`OCRRunEngine` の使い捨て原則（D-11）などの重要決定事項が正確に踏襲されており、コードベース全体の設計思想と一貫性があります。
* **検証体制の充実**: `FakeProvider` を使用した決定的な統合テスト（`test_batch_ocr_dialog.py`）により、E2E モック検証がしっかりと組まれており、回帰テストが容易です。

上記のいくつかの懸念事項（特にダイアログクローズ時のクリーンアップ処理）を実装タスク内に取り込むことで、マイルストーン v1.8.0 の成功基準を完璧に満たす強固なバッチ OCR 機能が実現できると評価します。

---

## Consensus Summary

今回のレビューは Antigravity CLI（agy 1.1.2・既定モデル）単独のため、複数レビュアー間の合意形成は行えない。以下は単一レビュアーの所見をフェーズ計画への反映優先度順に整理したもの。レビューはリポジトリのソースコード実読（`file:line` 引用）に基づくグラウンデッドな検証である。

### 主要懸念（優先度順）

1. **[HIGH — 04-02] ダイアログクローズ時のスレッドリーク**: `BatchOCRDialog` に `WM_DELETE_WINDOW` ハンドリングの計画記述がなく、バッチ実行中に「✕」で閉じるとワーカースレッドが走り続け、破棄済みウィジェットへの `after` 更新で `tk.TclError` が多発する恐れ。`self.protocol("WM_DELETE_WINDOW", ...)` でキャンセル強制→`destroy()` の順序をタスク化すべき。
2. **[MEDIUM — 04-01] `test_no_unused_lang_keys` との段階実装競合**: `tests/test_lang_parity.py:55-76` の未使用キー検査により、04-01（Task 1）で LANG キーだけ先行追加すると verification の pytest が落ちる。`_ALLOWLIST`（同ファイル L18）への一時追加か、キー追加をキー消費プランへ移す対処が必要。
3. **[MEDIUM — 04-02] 再実行制御フローの欠落**: バッチ中止後・完了後の「▶ 実行」再押下時の挙動（完了済みファイルのスキップ有無、ボタン活性化制御）が未定義。
4. **[MEDIUM — 04-02] 事前ページ数スキャンの UI ブロッキング**: 大量ファイル投入時にメインスレッド逐次 `fitz.open` で一時フリーズの恐れ。読み込み中表示か遅延取得を検討。
5. **[MEDIUM — 04-03] `OCRDialog` インスタンスメソッド流用方式の曖昧さ**: `_insert_markdown`（`ocr_dialog.py:1800-1819`）・`_confirm_summary_cost`（同 1237-1265）は `OCRDialog` のメソッドであり、`BatchOCRDialog` は継承しない。コピペ移植か共通化かを計画に明記すべき。
6. **[LOW — 04-01] 事前スキャンで `STATUS_ERROR` になったファイルの進捗集計遷移**: `files_done()`/`remaining()` への算入タイミングが曖昧で、完了判定が収束しない可能性。

### 評価された強み

- Tk/fitz 非依存の純ロジック層（`batch_ocr_state.py`）と Lock 保護の二軸独立進捗カウンタによる進捗不整合の構造的予防（04-01）
- ファイルごとの `OCRRunEngine` 使い捨て再生成（D-11 踏襲）と `_pstate.decrement_worker()`（`ocr_engine.py:246-260`）による完了判定の競合回避（04-02）
- fitz 操作の完全メインスレッド直列化によるネイティブクラッシュ回避（04-02）
- 手動トリガー＋`_confirm_summary_cost` 警告によるサマリ API コスト制御（D-14）、アクセラレータ非設定による `ShortcutsDialog` 11 コマンド（`shortcuts.py:27-39`）との衝突回避（04-03）

### リスク総評

04-01: LOW / 04-02: MEDIUM / 04-03: LOW。ダイアログクローズ時のクリーンアップ（懸念 1）を計画へ取り込めばフェーズ成功基準の達成見込みは高い、との評価。

### Divergent Views

単一レビュアーのため該当なし。
