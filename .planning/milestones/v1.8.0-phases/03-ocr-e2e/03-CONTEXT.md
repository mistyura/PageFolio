# Phase 3: OCR実行エンジン抽出 + E2Eテスト - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

`ocr_dialog.py`（2154行）から producer-consumer 駆動部を `OCRRunEngine` として抽出し、単一ファイル OCR とバッチ OCR（Phase 4）で共用できる構造にする。あわせて OCR→サマリの一気通貫フローを E2E モックテスト（実 API 非依存）で保証する。UI 変更は一切行わない**内部リファクタリング + テスト整備フェーズ**。

対象要件: V180-REFAC-03（OCRRunEngine 抽出）・V180-QA-01（E2E モックテスト整備）。

**スコープ外:** バッチ複数ファイル OCR の実装（Phase 4）・テンプレート/フォールバック機能の変更（Phase 2 で完了済み）・OCR の UI/UX 変更全般・サムネイル仮想化（Phase 5）。

</domain>

<decisions>
## Implementation Decisions

### 抽出境界（producerの所在・DI方式・配置・呼出し形態）
- **D-01:** producer（fitz レンダリング連鎖・`_render_next_page` 相当）は `OCRRunEngine` に内包せず、呼び出し側（`OCRDialog`／将来の `BatchOCRDialog`）が持ち続ける。`OCRRunEngine` は consumer（キュー + ワーカー + `PipelineState`）のみを提供する。`ocr_pipeline.py` の既存 docstring（「producer 側のスレッドモデルは本モジュールでは規定しない」）と一致する方針であり、V14-D-05/06（`fitz.get_pixmap()` はメインスレッドのみ）の責務を呼び出し側に保ったまま Engine を Tk/fitz 非依存に近づける。
- **D-02:** `OCRRunEngine` へのコンストラクタ/実行メソッドは最小限の値渡し（`provider`・`prompt`・`run_pages`・`concurrency`・`cancel_flag`・コールバック関数群）に限定する。設定 dict（`self._active_ocr_settings` 相当）は丸ごと渡さない。Engine の入力契約を明確にし、Tk 非依存性を保つ。
- **D-03:** 新モジュールは単一ファイル `pagefolio/ocr_engine.py` として新設する（サブパッケージ化しない）。`ocr_pipeline.py`（純ロジック層）と対になる単一責務モジュールとして扱う。1プロバイダ=1ファイルのような細分割は本フェーズの抽出対象（producer-consumer 駆動部1つ）には過剰。
- **D-04:** `OCRDialog` 側の `_worker`/`_render_next_page`/`_start_worker_thread` 等は薄いラッパーメソッドとして維持し、内部で `OCRRunEngine` へ委譲する。現状の `ocr_pipeline.py` への委譲形（v1.7.1 Phase 2）と同じ形を踏襲し、メソッド名・シグネチャは変えず、既存テスト・呼び出し元への影響を最小化する。

### UI通知インターフェース
- **D-05:** `OCRRunEngine` から `OCRDialog` への進捗/結果/完了通知はコールバック注入方式とする。Tk 非依存のイベントキュー + `after()` ポーリング方式は不採用（新しいポーリング機構を増やさない）。
- **D-06:** `on_success`/`on_page_error`/`on_fatal`/`on_retry_wait` 等の個別コールバックは `ocr_pipeline.consume_one` の既存シグネチャをそのまま踏襲し、単一の `on_event(kind, payload)` への統合は行わない。既存パターンとの一貫性・デバッグのしやすさを優先。
- **D-07:** 統合進捗計算（`_done_disp()` 相当: `PipelineState.done_count` + 今回分の skip 件数 + 今回分の render_failed 件数の合算）は `OCRRunEngine` が内部で持ち、進捗数値をコールバック経由で呼び出し側へ渡す。バッチ OCR でも同じ集計ロジックを流用できる。
- **D-08:** 完了理由（complete / cancelled / fatal）は理由別の個別コールバック（`on_complete`/`on_cancelled`/`on_fatal`）で伝える。単一の `on_finished(reason, msg, kind)` は不採用。既存の `_finish_complete`/`_finish_cancelled`/`_finish_error`（`ocr_dialog.py`）との対応が1対1で明瞭になる。

### 状態保持の所有権
- **D-09:** `results`/`errors`/`skipped_pages`/`truncated_pages`/`render_failed_pages` は `OCRRunEngine` が内部状態として所有する（`PipelineState` と同格の設計）。`OCRDialog` は完了後またはコールバック経由でこれらを参照する。バッチ OCR ではファイル単位で独立した結果セットを持てる。
- **D-10:** resume（未処理ページのみ再実行）の判断——どのページを再実行するか（`_pending_pages()` 相当）——は `OCRDialog` が行い、確定した `run_pages` リストのみを引数として `OCRRunEngine` へ渡す。Engine は「前回実行の履歴」を一切知らない。
- **D-11:** `OCRRunEngine` インスタンスは1回の OCR 実行（run / rerun / resume）ごとに新規作成する。1つの Engine を使い回してリセットメソッドを呼ぶ方式は不採用。既存の `_run_gen` 世代ガードと同種の安全性（陳腐化状態の排除）を、インスタンス新規作成という構造で機械的に得る。
- **D-12:** resume 時の「今回実行分のみの進捗」差分計算（`_skip_base`/`_render_failed_base` 相当のベースライン管理）は `OCRRunEngine` が内部で持つ（D-07 の統合進捗計算と一貫）。

### E2Eモックテスト（QA-01）のスコープ
- **D-13:** E2E モックテストは実スレッド実行を伴う統合テストとする（実際に `threading.Thread` を起動し `queue.Queue` を通す）。実 API 非依存（フェイク provider 使用）。抽出後の `OCRRunEngine` コードパス（ワーカー起動・`PipelineState` 共有・sentinel 送出）を最も高忠実度で検証する。タイミング依存の flaky 化リスクに留意し実装時にタイムアウト/リトライ余裕を設ける。
- **D-14:** フェイク `OCRProvider` は既存の `FakeProvider` パターン（`tests/test_ocr_pipeline.py`・`tests/test_ocr_providers.py`）を再利用・拡張する。E2E 専用の新規フェイク実装はしない。
- **D-15:** カバレッジ範囲は「正常系（複数ページ成功）+ 異常系（ページエラー混在・キャンセル・fatal/サーキットブレーカー）+ サマリ生成（`complete_text_ex` 相当の text-only 応答）」までフルカバーする。QA-01 要件文言の「一気通貫フロー」に対応する範囲を狭めない。
- **D-16:** 新規 E2E テストは新設 `tests/test_ocr_engine.py` に配置する。既存 `tests/test_ocr_pipeline.py`（純ロジック層の単体テスト）とは分離し、`ocr_engine.py` の単体テスト + E2E シナリオを同居させる。

### Claude's Discretion
- `OCRRunEngine` クラスの詳細なメソッドシグネチャ名（`run()`/`start()` 等）・引数の型ヒント
- コールバック関数群の正確な引数順序・命名
- `PipelineState` の生成タイミング（コンストラクタ内 vs 実行メソッド呼び出し時）
- `tests/test_ocr_engine.py` 内のテストクラス構成（`TestOCRRunEngine*` の分割単位）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・フェーズ定義
- `.planning/REQUIREMENTS.md` — V180-REFAC-03・V180-QA-01 の要件文言（本フェーズの対象2要件）
- `.planning/ROADMAP.md` — Phase 3 の Goal・Success Criteria（成功基準3項目）・依存関係（Phase 2 完了前提）・Phase 4（バッチ OCR）が OCRRunEngine を再利用する前提の明記

### リサーチ成果物
- `.planning/research/PITFALLS.md` — 落とし穴10「スレッド調整コードの分離時に暗黙の排他制御（ロック/世代カウンタ共有）が壊れる」（本フェーズの中心的リスク。回避策として `ocr_pipeline.py` の一本化方針をそのまま流用することが明記されている）
- `.planning/research/SUMMARY.md` — 「ocr_dialog.py 分割（OCRRunEngine 抽出）」セクションの推奨アプローチ（バッチ OCR 直前配置の理由・落とし穴10対応）

### 前フェーズの決定事項
- `.planning/phases/01-foundation-split/01-CONTEXT.md` — 純ロジック層の新設方針（Tk/fitz 非依存を保ち循環 import を避ける設計）が本フェーズの `ocr_engine.py` 配置にも一貫して適用される
- `.planning/phases/02-ai/02-CONTEXT.md` — 同一マイルストーン内での新規純ロジック層設計（`ocr_fallback.py` 等）との一貫性参考

### 前例パターン（コード内）
- `pagefolio/ocr_pipeline.py` — `PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`（Tk/fitz 非依存の既存純ロジック層）。「producer 側のスレッドモデルは規定しない」という docstring の明示方針が D-01 の直接的根拠。`OCRRunEngine` はこれをそのまま呼び出す
- `pagefolio/ocr_dialog.py:1330-1786` — 現行の `_start_run`/`_render_next_page`/`_retry_sentinels`/`_start_worker_thread`/`_worker`（抽出対象の producer-consumer 駆動部の現状構造）
- `pagefolio/ocr_dialog.py:765-804` — `_record_page_success`/`_record_page_error`/`_done_disp`（Engine 所有に移す結果辞書・統合進捗計算ロジックの現状実装）
- `pagefolio/ocr_dialog.py:1813-1922` — `_render_results_ordered`/`_finish_complete`/`_finish_cancelled`/`_finish_error`（UI 表示専用ロジックとして `OCRDialog` に残る部分。理由別個別コールバックの受け皿）
- `tests/test_ocr_pipeline.py`・`tests/test_ocr_providers.py` — `FakeProvider`（`side_effect` 差し替え可能）パターン（D-14 の再利用元）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pagefolio/ocr_pipeline.py`（`PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`）: `OCRRunEngine` がそのまま呼び出す既存の純ロジック層。変更不要でそのまま利用できる
- 既存 `FakeProvider` パターン（`tests/test_ocr_pipeline.py`/`tests/test_ocr_providers.py`）: E2E テストのフェイク provider 基盤としてそのまま拡張利用できる

### Established Patterns
- `_run_gen` 世代ガードパターン（陳腐化コールバック破棄）: D-11「実行ごとに Engine 新規作成」により同種の安全性を構造的に得る。`OCRDialog` 側の `_run_gen` チェック自体は UI コールバック無効化のために引き続き必要（Engine 完了時の `after()` 投函前ガードとして）
- Tk 非依存純ロジック層への集約方針（`pagination.py`/`ocr_pipeline.py`/`undo_store.py` と同格）: `ocr_engine.py` もこの系譜に連なるが、Engine 自体はスレッド管理・状態集約を担うため「完全な純関数」ではなく「軽量クラス」（`PipelineState` と同格の設計）になる

### Integration Points
- `OCRDialog._start_run` 内のプロバイダ生成・設定解決ロジック（provider 再生成・concurrency 再クランプ等、`ocr_dialog.py:1330-1526`）は `OCRDialog` に残り、生成済み provider を Engine へ渡す
- Phase 4（バッチ OCR）は `BatchOCRDialog` がファイルごとに `OCRRunEngine` を新規生成して再利用する設計になる（D-01/D-11 の直接の恩恵）

</code_context>

<specifics>
## Specific Ideas

- 「新しい抽象化層を作りすぎない」という一貫方針: コールバック粒度もイベント統合層も既存 `consume_one` パターンをそのまま踏襲する選択が続いた（D-02・D-06）
- Engine 自体は Tk 非依存だが、fitz 依存（producer 側）は呼び出し側に残すという「部分的な純化」が本フェーズの一貫した設計思想（D-01 が起点であり、以降の全決定がこの方針と整合している）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった）

</deferred>

---

*Phase: 3-OCR実行エンジン抽出 + E2Eテスト*
*Context gathered: 2026-07-14*
