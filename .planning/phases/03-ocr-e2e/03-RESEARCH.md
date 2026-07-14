# Phase 3: OCR実行エンジン抽出 + E2Eテスト - Research

**Researched:** 2026-07-15
**Domain:** Python 標準ライブラリ（threading/queue）による producer-consumer リファクタリング + pytest 統合テスト設計（既存コードベース内リファクタリング、新規外部依存なし）
**Confidence:** HIGH（対象コードは全て自社コードベースの現物読み取り。外部ライブラリ調査は不要）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**抽出境界（producerの所在・DI方式・配置・呼出し形態）**
- **D-01:** producer（fitz レンダリング連鎖・`_render_next_page` 相当）は `OCRRunEngine` に内包せず、呼び出し側（`OCRDialog`／将来の `BatchOCRDialog`）が持ち続ける。`OCRRunEngine` は consumer（キュー + ワーカー + `PipelineState`）のみを提供する。`ocr_pipeline.py` の既存 docstring（「producer 側のスレッドモデルは本モジュールでは規定しない」）と一致する方針であり、V14-D-05/06（`fitz.get_pixmap()` はメインスレッドのみ）の責務を呼び出し側に保ったまま Engine を Tk/fitz 非依存に近づける。
- **D-02:** `OCRRunEngine` へのコンストラクタ/実行メソッドは最小限の値渡し（`provider`・`prompt`・`run_pages`・`concurrency`・`cancel_flag`・コールバック関数群）に限定する。設定 dict（`self._active_ocr_settings` 相当）は丸ごと渡さない。Engine の入力契約を明確にし、Tk 非依存性を保つ。
- **D-03:** 新モジュールは単一ファイル `pagefolio/ocr_engine.py` として新設する（サブパッケージ化しない）。`ocr_pipeline.py`（純ロジック層）と対になる単一責務モジュールとして扱う。1プロバイダ=1ファイルのような細分割は本フェーズの抽出対象（producer-consumer 駆動部1つ）には過剰。
- **D-04:** `OCRDialog` 側の `_worker`/`_render_next_page`/`_start_worker_thread` 等は薄いラッパーメソッドとして維持し、内部で `OCRRunEngine` へ委譲する。現状の `ocr_pipeline.py` への委譲形（v1.7.1 Phase 2）と同じ形を踏襲し、メソッド名・シグネチャは変えず、既存テスト・呼び出し元への影響を最小化する。

**UI通知インターフェース**
- **D-05:** `OCRRunEngine` から `OCRDialog` への進捗/結果/完了通知はコールバック注入方式とする。Tk 非依存のイベントキュー + `after()` ポーリング方式は不採用（新しいポーリング機構を増やさない）。
- **D-06:** `on_success`/`on_page_error`/`on_fatal`/`on_retry_wait` 等の個別コールバックは `ocr_pipeline.consume_one` の既存シグネチャをそのまま踏襲し、単一の `on_event(kind, payload)` への統合は行わない。既存パターンとの一貫性・デバッグのしやすさを優先。
- **D-07:** 統合進捗計算（`_done_disp()` 相当: `PipelineState.done_count` + 今回分の skip 件数 + 今回分の render_failed 件数の合算）は `OCRRunEngine` が内部で持ち、進捗数値をコールバック経由で呼び出し側へ渡す。バッチ OCR でも同じ集計ロジックを流用できる。
- **D-08:** 完了理由（complete / cancelled / fatal）は理由別の個別コールバック（`on_complete`/`on_cancelled`/`on_fatal`）で伝える。単一の `on_finished(reason, msg, kind)` は不採用。既存の `_finish_complete`/`_finish_cancelled`/`_finish_error`（`ocr_dialog.py`）との対応が1対1で明瞭になる。

**状態保持の所有権**
- **D-09:** `results`/`errors`/`skipped_pages`/`truncated_pages`/`render_failed_pages` は `OCRRunEngine` が内部状態として所有する（`PipelineState` と同格の設計）。`OCRDialog` は完了後またはコールバック経由でこれらを参照する。バッチ OCR ではファイル単位で独立した結果セットを持てる。
- **D-10:** resume（未処理ページのみ再実行）の判断——どのページを再実行するか（`_pending_pages()` 相当）——は `OCRDialog` が行い、確定した `run_pages` リストのみを引数として `OCRRunEngine` へ渡す。Engine は「前回実行の履歴」を一切知らない。
- **D-11:** `OCRRunEngine` インスタンスは1回の OCR 実行（run / rerun / resume）ごとに新規作成する。1つの Engine を使い回してリセットメソッドを呼ぶ方式は不採用。既存の `_run_gen` 世代ガードと同種の安全性（陳腐化状態の排除）を、インスタンス新規作成という構造で機械的に得る。
- **D-12:** resume 時の「今回実行分のみの進捗」差分計算（`_skip_base`/`_render_failed_base` 相当のベースライン管理）は `OCRRunEngine` が内部で持つ（D-07 の統合進捗計算と一貫）。

**E2Eモックテスト（QA-01）のスコープ**
- **D-13:** E2E モックテストは実スレッド実行を伴う統合テストとする（実際に `threading.Thread` を起動し `queue.Queue` を通す）。実 API 非依存（フェイク provider 使用）。抽出後の `OCRRunEngine` コードパス（ワーカー起動・`PipelineState` 共有・sentinel 送出）を最も高忠実度で検証する。タイミング依存の flaky 化リスクに留意し実装時にタイムアウト/リトライ余裕を設ける。
- **D-14:** フェイク `OCRProvider` は既存の `FakeProvider` パターン（`tests/test_ocr_pipeline.py`・`tests/test_ocr_providers.py`）を再利用・拡張する。E2E 専用の新規フェイク実装はしない。
- **D-15:** カバレッジ範囲は「正常系（複数ページ成功）+ 異常系（ページエラー混在・キャンセル・fatal/サーキットブレーカー）+ サマリ生成（`complete_text_ex` 相当の text-only 応答）」までフルカバーする。QA-01 要件文言の「一気通貫フロー」に対応する範囲を狭めない。
- **D-16:** 新規 E2E テストは新設 `tests/test_ocr_engine.py` に配置する。既存 `tests/test_ocr_pipeline.py`（純ロジック層の単体テスト）とは分離し、`ocr_engine.py` の単体テスト + E2E シナリオを同居させる。

### Claude's Discretion
- `OCRRunEngine` クラスの詳細なメソッドシグネチャ名（`run()`/`start()` 等）・引数の型ヒント
- コールバック関数群の正確な引数順序・命名
- `PipelineState` の生成タイミング（コンストラクタ内 vs 実行メソッド呼び出し時）
- `tests/test_ocr_engine.py` 内のテストクラス構成（`TestOCRRunEngine*` の分割単位）

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V180-REFAC-03 | `ocr_dialog.py`（2154行）から OCR 実行エンジン（`OCRRunEngine`）が抽出され、単一ファイル OCR とバッチ OCR で共用される | 「Architecture Patterns」「Code Examples」節で抽出対象コード（`_start_worker_thread`/`_worker`/`_record_page_success`/`_record_page_error`/`_done_disp`）の現物と、Engine への委譲設計を明示。「Don't Hand-Roll」節で `ocr_pipeline.py` の再利用を明記 |
| V180-QA-01 | OCR→サマリの E2E モックテストが整備される（`OCRRunEngine`/`ocr_pipeline.py` 経由の一気通貫・実 API 非依存） | 「Validation Architecture」節でテスト対象マップ・既存 `_drive_pipeline`（`tests/test_ocr_pipeline.py`）ドライバパターンの転用方法を明示。「Common Pitfalls」節で落とし穴10（スレッド調整コード分離時のロック不整合）を詳述 |

</phase_requirements>

## Summary

本フェーズは新規機能追加ではなく、既存の `ocr_dialog.py`（2520行・調査時点。CONTEXT.md 記載の2154行は基準時点との差分であり、Phase 2 の機能追加で増加した）内に密結合している producer-consumer 駆動部（`_start_worker_thread`/`_worker`/`_render_next_page`/`_record_page_success`/`_record_page_error`/`_done_disp`）を `pagefolio/ocr_engine.py` の `OCRRunEngine` クラスへ抽出するリファクタリングと、抽出後のコードパスを保証する E2E モックテストの整備である。外部ライブラリの追加は一切発生しない（Python 標準ライブラリの `threading`/`queue` のみ）。

抽出の土台は既に v1.7.1 Phase 2 で整備済みの `pagefolio/ocr_pipeline.py`（`PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`）であり、これは変更せずそのまま `OCRRunEngine` から呼び出す。CONTEXT.md の D-01〜D-16 の全決定は「新しい抽象化層を増やさない」「`ocr_pipeline.py` の既存契約（producer 側のスレッドモデルを規定しない・コールバック個別化）をそのまま踏襲する」という一貫方針で貫かれている。研究の核心は、現行 `ocr_dialog.py` の該当メソッド群の正確な現状把握と、それを `OCRRunEngine` へ移す際に「同一のロックオブジェクト・世代カウンタ・キューを全参照者が共有する」という不変条件（PITFALLS.md 落とし穴10）を壊さないための移植手順にある。

**Primary recommendation:** `ocr_dialog.py` の `_start_worker_thread`/`_worker` のロジックをほぼそのまま `OCRRunEngine.run()`（メソッド名は裁量）へ移植し、`_render_next_page`（producer）は `OCRDialog` に残す。`PipelineState` はコンストラクタでも実行メソッド内でもよいが、D-11（実行ごとに Engine を新規生成）により Engine のライフサイクル＝1回の OCR 実行と一致させ、世代ガード相当の安全性を「新しいオブジェクトだから古いコールバックは意味を持たない」という構造で得る。テストは `tests/test_ocr_pipeline.py` の `_drive_pipeline` ヘルパー（テスト専用スレッド駆動）と同型の実スレッド駆動パターンを `tests/test_ocr_engine.py` で `OCRRunEngine` 本体に対して行う。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ページレンダリング（fitz `get_pixmap`/`page_to_png_b64`） | Client（デスクトップ・メインスレッド） | — | V14-D-05/06 により `fitz` API 呼び出しはメインスレッド限定。producer は `OCRDialog` に残留（D-01） |
| OCR API 呼び出し（consumer ワーカー・リトライ/バックオフ） | Client（デスクトップ・ワーカースレッド） | — | `OCRRunEngine` が consumer 側（キュー取り出し→`ocr_pipeline.consume_one` 委譲）を所有。ネットワーク I/O のみでネイティブ依存なし |
| 共有状態管理（done カウンタ・fatal 判定・サーキットブレーカー） | Client（純ロジック層・Tk/fitz 非依存） | — | 既存 `ocr_pipeline.PipelineState` が担う。変更対象外・そのまま再利用 |
| 進捗/結果/完了の UI 反映 | Client（Tkinter・メインスレッド） | — | `OCRDialog` がコールバック経由で受け取り `self.after()` で描画。`OCRRunEngine` 自体は Tk に触れない |
| サマリ生成（`complete_text_ex` 単発呼び出し） | Client（デスクトップ・ワーカースレッド1本） | — | 現状 `_summary_worker` に実装済み。本フェーズでは `OCRRunEngine` へは移さない（producer-consumer 駆動部の対象外・スコープ外セクション参照）が、E2E テストのカバレッジ対象（D-15）には含める |

## Standard Stack

### Core

本フェーズは Python 標準ライブラリのみを使用する既存コードのリファクタリングであり、新規外部パッケージは導入しない。

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `threading`（stdlib） | Python 3.8+ 同梱 | consumer ワーカースレッド起動・`Lock`/`Event` | 既存 `ocr_pipeline.py`/`ocr_dialog.py` が既に使用中。変更なし [VERIFIED: codebase — pagefolio/ocr_pipeline.py:36-37] |
| `queue`（stdlib） | Python 3.8+ 同梱 | producer→consumer 間の bounded buffer | 既存 `queue.Queue(maxsize=concurrency+1)` パターンをそのまま踏襲 [VERIFIED: codebase — pagefolio/ocr_dialog.py:1532] |
| `pytest` | 9.0.3（インストール済み実測） | E2E テストランナー | プロジェクト標準（`pyproject.toml`）。バージョンは `python -m pytest --version` で実測確認 [VERIFIED: pytest --version] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pagefolio.ocr_pipeline`（自社純ロジック層） | 既存（変更なし） | `PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels` | `OCRRunEngine` が内部でそのまま呼び出す。再実装しない（D-01根拠） |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| コールバック個別注入（D-05/D-06） | 単一イベントキュー + `after()` ポーリング | CONTEXT.md で明示的に不採用（新しいポーリング機構を増やさない方針）。デバッグ時のコールスタックの追いやすさでも個別コールバックが優位 |
| Engine インスタンス使い回し + reset() | 実行ごとに新規生成（D-11） | 使い回し方式は reset 漏れによる状態リークのリスクがある。新規生成は世代ガードと同種の安全性を構造的に得られ、GC が古い状態を自然に回収する |

**Installation:** 不要（新規パッケージなし。標準ライブラリのみ）。

**Version verification:** 本フェーズは新規パッケージを追加しないため `npm view`/`pip index versions` 等の実行は不要。`pytest --version` を実行し 9.0.3 を確認済み [VERIFIED: pytest --version]。

## Package Legitimacy Audit

**本フェーズは新規外部パッケージを一切導入しない。** `pagefolio/ocr_engine.py` は Python 標準ライブラリ（`threading`/`queue`/`logging`）と自社モジュール（`pagefolio.ocr_pipeline`）のみに依存する。Package Legitimacy Gate は該当なし（実行不要）。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | 対象パッケージなし |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[OCRDialog._on_run]
      │ (1) 設定確定・provider 生成・run_pages 確定
      ▼
[OCRDialog._render_next_page]  ── producer（メインスレッド・fitz 依存）
      │ has_embedded_text() で分岐:
      │   ├─ 埋め込みテキストあり → results へ直接投入・スキップ計上
      │   └─ 埋め込みテキストなし → page_to_png_b64() でレンダリング
      │ try_enqueue(queue, (page_idx, b64))  ── ocr_pipeline.try_enqueue
      ▼
[queue.Queue(maxsize=concurrency+1)]  ── bounded buffer（producer/consumer 境界）
      │
      ▼
[OCRRunEngine]  ── ★本フェーズで新設・consumer 側を所有（Tk/fitz 非依存）
      │ concurrency 本の consumer スレッドを起動
      │ 各スレッド: queue.get() → consume_one() 委譲
      │
      ├─▶ [ocr_pipeline.consume_one] ── 既存・変更なし
      │       │ provider.ocr_image_ex(b64, prompt) 呼び出し
      │       │ リトライ/バックオフ/fatal 判定
      │       ▼
      │   [PipelineState] ── 既存・変更なし（Lock 保護の共有カウンタ）
      │
      ├─▶ on_success(page_idx, text, truncated) コールバック → OCRDialog._record_page_success
      ├─▶ on_page_error(page_idx, msg) コールバック → OCRDialog._record_page_error
      ├─▶ on_fatal(page_idx, msg, kind) コールバック → OCRDialog（フォールバック提案トリガー）
      ├─▶ on_retry_wait(...) コールバック → OCRDialog（進捗文言更新）
      │
      │ 最終ワーカー（decrement_worker で is_last=True）が
      ▼
[on_complete / on_cancelled / on_fatal（完了理由別コールバック・D-08）]
      │
      ▼
[OCRDialog._render_results_ordered → _finish_complete/_finish_cancelled/_finish_error]
      （UI 描画・ボタン状態リセット・フォールバック提案は OCRDialog に残留）
```

producer（fitz レンダリング）は Engine の外側（`OCRDialog`）に残り、consumer（キュー消費 + `PipelineState` + 完了判定）のみが `OCRRunEngine` に移る。これが D-01 の「部分的な純化」の図示である。

### Recommended Project Structure

```
pagefolio/
├── ocr_pipeline.py     # 既存・変更なし（PipelineState/consume_one/try_enqueue/send_sentinels）
├── ocr_engine.py        # ★新設（本フェーズ） — OCRRunEngine（consumer 側の駆動・状態所有）
├── ocr_dialog.py         # 縮小 — producer（_render_next_page）・UI 描画・完了理由別ハンドラのみ残留
tests/
├── test_ocr_pipeline.py  # 既存・変更なし（PipelineState/consume_one 純ロジック単体テスト）
├── test_ocr_engine.py     # ★新設（本フェーズ） — OCRRunEngine 単体テスト + E2E モックテスト（D-16）
```

### Pattern 1: 委譲ラッパーによる後方互換維持（D-04）

**What:** `OCRDialog._start_worker_thread`/`_worker` は現行のシグネチャ・メソッド名を変えず、内部実装のみを `OCRRunEngine` への委譲に置き換える薄いラッパーにする。
**When to use:** 本フェーズの抽出全般。v1.7.1 Phase 2 で `ocr_pipeline.py` へ委譲した際と同じ形。
**Example:**
```python
# Source: pagefolio/ocr_dialog.py:1668-1681（現状・抽出前）
def _start_worker_thread(self, gen=None):
    self._worker_threads = []
    self._pstate = PipelineState(self.concurrency)
    for _ in range(self.concurrency):
        t = threading.Thread(target=self._worker, args=(gen,), daemon=True)
        t.start()
        self._worker_threads.append(t)

# 抽出後（イメージ・裁量範囲）:
def _start_worker_thread(self, gen=None):
    self._engine = OCRRunEngine(
        provider=self.provider,
        prompt=self._ocr_prompt,
        run_pages=self._run_pages,
        concurrency=self.concurrency,
        cancel_flag=self._cancel_flag,
        on_success=lambda p, t, tr: self._record_page_success(p, t, truncated=tr),
        on_page_error=self._record_page_error,
        on_retry_wait=self._on_retry_wait_for(gen),
        on_complete=lambda: self._on_engine_complete(gen),
        on_cancelled=lambda: self._on_engine_cancelled(gen),
        on_fatal=lambda msg, kind: self._on_engine_fatal(gen, msg, kind),
    )
    self._engine.start()  # concurrency 本の consumer スレッドを起動
```

### Pattern 2: producer 側の enqueue は Engine のキューを直接使う

**What:** `_render_next_page`（producer・`OCRDialog` に残留）は `OCRRunEngine` が保持する `queue.Queue` へ `try_enqueue`/`send_sentinels` を呼び続ける。Engine は自身のキューを公開プロパティとして提供する必要がある（D-02 の「最小限の値渡し」原則との整合は、キュー自体を Engine 生成時にコンストラクタで公開する形にするか、Engine 側で生成してプロパティ経由で producer へ渡すかは裁量事項）。
**When to use:** producer/consumer 境界のキュー所有権を一箇所に確定させる設計判断が必要な箇所。
**Example:**
```python
# Source: pagefolio/ocr_dialog.py:1560-1567（現状のキャンセル時 sentinel 送出）
if self._cancel_flag.is_set():
    sent = send_sentinels(self._render_queue, self.concurrency)
    if sent < self.concurrency:
        self._retry_sentinels(gen, self.concurrency - sent)
    self._finish_cancelled()
    return
# 抽出後も producer 側のこの呼び出しパターン自体は変更不要
# （self._render_queue → self._engine.queue のような参照先変更のみ）
```

### Pattern 3: 完了理由別コールバック + 最終ワーカー判定（CR-01 継承）

**What:** `PipelineState.decrement_worker()` が返す `is_last` フラグで「最終ワーカーのみが終了処理を1回だけ呼ぶ」という既存の CR-01 保証（複数ワーカーが同時に完了処理を二重実行しない）を Engine 内部でもそのまま維持する。
**When to use:** `OCRRunEngine` 内の consumer ループ末尾。
**Example:**
```python
# Source: pagefolio/ocr_dialog.py:1756-1786（現状の最終ワーカー判定・移植元）
is_last, fatal_msg, fatal_kind = self._pstate.decrement_worker()
if not is_last:
    return
if fatal_msg is not None:
    # on_fatal コールバックを呼ぶ（D-08）
    ...
elif self._cancel_flag.is_set():
    # on_cancelled コールバックを呼ぶ（D-08）
    ...
else:
    # on_complete コールバックを呼ぶ（D-08）
    ...
```

### Anti-Patterns to Avoid
- **新しい抽象化層の追加（イベント統合層・ポーリング機構）:** CONTEXT.md D-05/D-06 で明示的に不採用。`consume_one` の既存コールバック粒度をそのまま踏襲すること。
- **`PipelineState` の再実装・別クラスへの複製:** `ocr_pipeline.py` は変更不要。`OCRRunEngine` は `PipelineState` を「所有」するが「再実装」してはならない（D-01 の直接的根拠）。
- **ロック/キュー/世代カウンタの分割後の非同一性（落とし穴10）:** クラス境界を切る際、`self._pstate`・`self._render_queue` のようなスレッド間共有オブジェクトを、新旧の参照経路で別インスタンスとして再生成してしまうバグ。抽出後は「誰が Engine のキュー/`PipelineState` インスタンスを生成し、それを producer とワーカー全員が同一オブジェクトとして参照しているか」を必ずコードレビューで確認する。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| producer-consumer 共有状態（done カウンタ・fatal 判定・サーキットブレーカー） | `OCRRunEngine` 内での独自ロック/カウンタ再実装 | `pagefolio.ocr_pipeline.PipelineState`（既存・そのまま import） | v1.7.1 Phase 2 で既に Tk/fitz 非依存の純ロジック層として確立済み。再実装すると落とし穴10（ロック不整合）のリスクを自ら作り出す |
| 1 アイテムのリトライ/バックオフ/fatal 判定 | `OCRRunEngine` 内での独自リトライループ | `pagefolio.ocr_pipeline.consume_one`（既存・そのまま呼び出し） | `MAX_RETRIES`/`clamp_retry_after`/`interruptible_sleep`（`pagefolio.ocr`）との整合を再実装で壊すリスクを避ける |
| 非ブロッキング enqueue/sentinel 送出 | `OCRRunEngine`/`OCRDialog` 双方での独自 `queue.Full` ハンドリング | `pagefolio.ocr_pipeline.try_enqueue`/`send_sentinels`（既存） | L-6h 容量不変条件（部分送出時は残数のみ再試行）を壊さないため |

**Key insight:** 本フェーズに新規のドメインロジックは存在しない。「既に存在する Tk/fitz 非依存の純ロジック層（`ocr_pipeline.py`）を、Tk 依存コードから切り離す境界線をどこに引くか」だけが設計判断であり、CONTEXT.md はその境界線を D-01〜D-16 で既に確定させている。

## Runtime State Inventory

> このフェーズは rename/refactor 分類に該当するが、対象は**同一プロセス内のメモリ状態**（スレッド/キュー/コールバック配線）のみであり、以下のカテゴリは該当しない。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| 保存データ（ストア/DB） | None — `OCRRunEngine` はディスク・DB に一切書き込まない。結果は `OCRDialog.results`/`errors` 辞書（メモリのみ）に集約される | なし |
| ライブサービス設定（UI外・DB内） | None — 本フェーズは外部サービス設定を持たない | なし |
| OS登録状態（タスクスケジューラ等） | None | なし |
| シークレット/環境変数 | None — API キー解決（`_resolve_api_key`）は `OCRDialog._on_run` に残留し `OCRRunEngine` には渡さない（D-02 の「provider インスタンスのみ渡す」設計により、キー自体は Engine に触れない） | なし |
| ビルド成果物/インストール済みパッケージ | None — 新規パッケージなし。`ocr_engine.py` は新規ファイル追加のみで既存ビルド成果物に影響しない | なし |

**結論:** 本フェーズはメモリ内スレッド調整コードのファイル間移動であり、実行時に永続化された状態への影響はゼロ。唯一の「移行」対象は `OCRDialog` インスタンス属性（`self._pstate`/`self._render_queue`/`self._worker_threads` 等）の所有権が `OCRRunEngine` インスタンスへ移ることだが、これはプロセス内メモリのみでディスク/DB/OS 登録状態を伴わない。

## Common Pitfalls

### Pitfall 1: スレッド調整コードの分離時に暗黙の排他制御が壊れる（PITFALLS.md 落とし穴10・本フェーズの中心的リスク）

**What goes wrong:** `_worker`/`_render_queue`/`_pstate`（`PipelineState`）のような、スレッド間で暗黙に密結合したフィールドを別クラス（`OCRRunEngine`）へ切り出す際、producer 側（`OCRDialog._render_next_page`）が参照する `queue.Queue`/`PipelineState` インスタンスと、consumer 側（`OCRRunEngine` 内のワーカースレッド）が参照するインスタンスが、リファクタリングの過程で別々に生成されてしまう。

**Why it happens:** クラス境界を切ると「誰が最初にこのオブジェクトを生成し、誰が参照を保持するか」が曖昧になりやすい。特に `_start_worker_thread`（consumer 起動）と `_render_next_page`（producer 開始）が別メソッドとして呼ばれる現行構造（`_on_run` 内で `self._start_worker_thread(gen)` → `self._render_next_page(gen)` の順で呼ぶ）を分割後も維持する必要があり、どちらが `queue.Queue`/`PipelineState` の生成責任を持つかを一箇所に確定させないと二重生成が起きる。

**How to avoid:** `OCRRunEngine` のコンストラクタまたは起動メソッド内で `queue.Queue`/`PipelineState` を**必ず一度だけ**生成し、producer 側（`OCRDialog`）はそれを Engine のプロパティ（例: `self._engine.queue`）経由でのみ参照する。「Engine が先に生成され、producer はその後にキューへ触れる」という現行の起動順序（consumer 先行起動→producer 開始・`ocr_dialog.py:1538-1540` のコメント「consumer（ワーカー）を先に起動してから producer（レンダリング）を開始する」）をそのまま維持する。

**Warning signs:** 分割後に OCR キャンセルが効かなくなる（producer が古いキューへ sentinel を送り、consumer が新しいキューを待ち続ける）、テスト実行時にデッドロック/ハングが発生する、進捗バーが更新されなくなる。

### Pitfall 2: `OCRRunEngine` 実行ごとの新規生成（D-11）を徹底しないと世代ガード相当の安全性が失われる

**What goes wrong:** D-11 は「1回の OCR 実行ごとに `OCRRunEngine` を新規作成する」という決定だが、実装時に誤って `OCRDialog` インスタンス生存期間中に1つの `OCRRunEngine` を使い回し、`reset()` のようなメソッドで状態をクリアする設計にしてしまうと、リセット漏れのフィールド（例: 古い `_fallback_tried` 相当の残留、古いコールバック参照）が次回実行に持ち越される。

**Why it happens:** 「オブジェクトを作り直すコスト」を気にして使い回し方式に流れやすいが、Python の軽量オブジェクト生成コストは無視できるレベルであり、GC が確実に古い状態を回収する新規生成方式の安全性の方が優先される。

**How to avoid:** `_start_worker_thread`（またはその後継メソッド）内で毎回 `OCRRunEngine(...)` を新規インスタンス化する。既存の `_run_gen` 世代ガードは `OCRDialog` 側の `after()` コールバック無効化のためには引き続き必要（Engine 完了時の `after()` 投函前ガードとして・CONTEXT.md 明記）。

**Warning signs:** 2回目以降の OCR 実行（リラン/resume）で前回実行のエラー・完了フラグが残留する、`test_ocr_engine.py` で複数回連続実行するテストケースが不安定になる。

### Pitfall 3: E2E テストのタイミング依存 flaky 化（D-13 で明示された懸念）

**What goes wrong:** 実 `threading.Thread` + `queue.Queue` を使う統合テストは、CI環境やマシン負荷によってタイミングが変動し、`queue.get(timeout=1.0)` のようなポーリング間隔に依存する箇所で稀に失敗する。

**Why it happens:** モックを使わず実スレッドを起動する方式（D-13 の選定理由：最も高忠実度）はトレードオフとしてタイミング依存性を内包する。既存 `tests/test_ocr_pipeline.py` の `TestProducerConsumerMemory`/`TestPipelineHardening` は `thread.join(timeout=10.0)`/`thread.join(timeout=5.0)` のように十分なタイムアウト余裕を持たせている。

**How to avoid:** 既存 `_drive_pipeline`（`tests/test_ocr_pipeline.py:208-279`）のタイムアウト設計（`join(timeout=10.0)` 等）をそのまま踏襲する。フェイク provider の `side_effect` に `time.sleep(0.01)` のような短い遅延を入れて並列性を検証しつつ、アサーション自体は「結果セットの内容」で行い「実行時間の正確な一致」では行わない（既存パターンと同じ）。

**Warning signs:** ローカルでは通るが CI で稀に落ちる、`pytest -x --lf` の再実行で通る（非決定性の兆候）。

### Pitfall 4: サマリ生成（`complete_text_ex`）を Engine 抽出対象と誤認する

**What goes wrong:** D-15 は「E2E テストのカバレッジ範囲にサマリ生成を含める」と定めているが、これは「`_summary_worker`/`_on_summary` のロジックも `OCRRunEngine` へ移す」という意味ではない。CONTEXT.md のスコープ外節に「テンプレート/フォールバック機能の変更」は含まれないが、サマリ生成コード自体（`_on_summary`/`_summary_worker`）の producer-consumer 駆動部への統合は D-01〜D-12 のどの決定にも明記されていない。

**Why it happens:** 「OCR→サマリの一気通貫フロー」という QA-01 の要件文言から、「サマリもエンジンに含める」と早合点しやすい。

**How to avoid:** サマリ生成は単発 API 呼び出し（ワーカースレッド1本・producer-consumer 構造なし）であり、`OCRRunEngine` の抽出対象（producer-consumer 駆動部）とは構造が異なる。E2E テストは「OCR 実行（`OCRRunEngine` 経由）→その後サマリ生成（`complete_text_ex` 相当）」という**フロー全体**をモックで検証すればよく、サマリ生成ロジック自体を Engine へ統合する必要はない（Claude's Discretion の範囲内でプランナーが判断）。

## Code Examples

### `PipelineState` の生成と consumer ループの委譲（既存パターン・そのまま踏襲）

```python
# Source: pagefolio/ocr_dialog.py:1668-1786（抽出元の現状実装・全文参照済み）
# _start_worker_thread: PipelineState 生成 + consumer スレッド起動
# _worker: queue.get() → consume_one() 委譲 → 統合進捗コールバック → 最終ワーカー判定
```

### `consume_one` のシグネチャ（変更不要・そのまま呼び出す）

```python
# Source: pagefolio/ocr_pipeline.py:170-181
def consume_one(
    provider,
    item,
    prompt,
    state,
    cancel_check=None,
    breaker_threshold=DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    on_success=None,
    on_page_error=None,
    on_fatal=None,
    on_retry_wait=None,
):
    ...
```

### 既存 `FakeProvider` パターン（D-14 の再利用元・E2E テストのフェイク基盤）

```python
# Source: tests/test_ocr_pipeline.py:28-44（純ロジック層向け・そのまま流用可）
class FakeProvider(OCRProvider):
    default_concurrency = 2
    max_concurrency = 4

    def __init__(self, side_effect=None):
        self._side_effect = side_effect

    def ocr_image(self, b64_png, prompt, **kwargs):
        if self._side_effect is not None:
            return self._side_effect(b64_png, prompt)
        return f"text-{b64_png}"

    def list_models(self):
        return ["fake-model"]

# サマリ生成カバレッジ（D-15）のため complete_text_ex/supports_text_prompt の
# オーバーライドも追加する必要がある（既存 FakeProvider にはまだ実装されていない）:
#   supports_text_prompt = True
#   def complete_text_ex(self, text, prompt, **kwargs): return (f"summary-of-{len(text)}", False)
```

### 既存の実スレッド駆動テストヘルパー（D-13 の高忠実度統合テストの前例）

```python
# Source: tests/test_ocr_pipeline.py:208-279（_drive_pipeline）
# producer スレッド + concurrency 本の consumer スレッドを実際に起動し、
# try_enqueue/send_sentinels/consume_one の組み合わせを検証する。
# OCRRunEngine の E2E テスト（tests/test_ocr_engine.py）はこのパターンを
# 「テスト専用ドライバの自作」ではなく「OCRRunEngine 自体を起動して検証する」
# 形に転用する（Engine が producer 相当のダミー render_fn からキューへ投入される
# 想定で、consumer 側はテストコードではなく OCRRunEngine 内部が担う点が
# _drive_pipeline との違い）。
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `OCRDialog` が producer-consumer 駆動部の全ロジック（キュー・ワーカー起動・状態集約）を直接保持 | `ocr_pipeline.py`（純ロジック層）+ `OCRRunEngine`（consumer 駆動の薄いラッパー、本フェーズで新設）に分離 | 本フェーズ（v1.8.0 Phase 3） | バッチ OCR（Phase 4）が `OCRRunEngine` を再利用可能になる。単一ファイル OCR の挙動（キャンセル/リトライ/進捗）は変更されない（同一ロジックの配置換えのみ） |

**Deprecated/outdated:**
- なし。`ocr_pipeline.py` の設計（v1.7.1 Phase 2）は変更されず、本フェーズはその上に薄い consumer 駆動レイヤーを追加するのみ。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `OCRRunEngine` のキュー所有権（producer が Engine のキューへ触れる方式 vs Engine 生成前に `OCRDialog` がキューを生成し Engine へ渡す方式）はプランナー/実装時の裁量事項として未確定（CONTEXT.md「Claude's Discretion」の範囲） | Architecture Patterns（Pattern 2） | 設計選択を誤ると D-02（最小限の値渡し）と producer 側の直接キューアクセスが衝突しうる。計画時にどちらの所有モデルを取るか明示的に決めることを推奨 |
| A2 | サマリ生成（`_on_summary`/`_summary_worker`）は `OCRRunEngine` の抽出対象外（producer-consumer 構造を持たないため）という解釈 | Common Pitfalls（Pitfall 4） | CONTEXT.md に明示的な除外記載はないため、プランナーが誤ってサマリロジックの Engine 統合をタスク化する可能性がある。要件文言「OCR→サマリの一気通貫フロー」はテストカバレッジの話であり実装統合の話ではないと解釈した |

**この2件は CONTEXT.md の決定事項からの論理的推論であり、直接的な決定文言はない。計画時に discuss-phase の追加確認、または plan-checker でのレビューを推奨する。**

## Open Questions

1. **Engine のキュー生成責任の所在**
   - What we know: D-01（producer は Engine に内包しない）・D-02（最小限の値渡し）が決定済み
   - What's unclear: `queue.Queue` 自体を誰が生成するか（Engine 内部で生成し producer がプロパティ経由で参照する／`OCRDialog` が生成し Engine コンストラクタへ渡す）は未確定
   - Recommendation: Pitfall 1（落とし穴10）を避けるため、「Engine が起動時に一度だけキューを生成し、producer はそのプロパティを参照する」方式を計画時に第一候補として推奨する（producer/consumer 双方が同一キューインスタンスを確実に共有できるため）

2. **サマリ生成コードの E2E テスト内での扱い**
   - What we know: D-15 でサマリ生成（`complete_text_ex` 相当の text-only 応答）が E2E カバレッジに含まれることが決定済み
   - What's unclear: サマリロジック自体を `OCRRunEngine` の一部にするか、`OCRDialog._summary_worker` 相当のロジックとして別途（E2E テストからは直接 `provider.complete_text_ex` を呼ぶ形で）検証するか
   - Recommendation: Assumptions Log A2 の解釈（サマリはEngine抽出対象外・フローとしてのみテスト対象）を計画に反映することを推奨。既存 `_summary_worker` のロジック自体は変更不要

## Environment Availability

本フェーズは新規外部依存・外部サービスを持たないため、このセクションはスキップする（コード内リファクタリング + 既存 pytest 環境のみで完結）。

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3（実測・`pyproject.toml` で `pythonpath = ["src"]` 等を設定） |
| Config file | `pyproject.toml`（既存） |
| Quick run command | `pytest tests/test_ocr_engine.py -x` |
| Full suite command | `pytest`（実測ベースライン: 987 件グリーン・36.21秒） |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| V180-REFAC-03 | `OCRRunEngine` が単独 import 可能で、単一ページ成功時に `on_success` コールバックが呼ばれる | unit | `pytest tests/test_ocr_engine.py::TestOCRRunEngineUnit -x` | ❌ Wave 0（新規） |
| V180-REFAC-03 | `_worker`/`_render_next_page` 等の既存 `OCRDialog` メソッドが `OCRRunEngine` へ委譲後も同一シグネチャ・挙動を維持する（回帰） | integration | `pytest tests/test_provider_ui.py tests/test_ocr_fallback.py tests/test_ocr.py -x`（`OCRDialog` に触れる既存テストファイル群。専用の `test_ocr_dialog.py` は存在しない — `OCRDialog` は Tkinter 依存が強くこれらのファイルへ分散して間接テストされている） | ✅ 既存（新規ファイル不要） |
| V180-QA-01 | 複数ページ正常系（成功のみ）が `OCRRunEngine` 経由で全ページ結果を返す | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_all_pages_success -x` | ❌ Wave 0（新規） |
| V180-QA-01 | ページエラー混在（一部ページ失敗）でも取りこぼしなく完了する | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_partial_page_errors -x` | ❌ Wave 0（新規） |
| V180-QA-01 | キャンセルが有限時間で反映され残ページを処理しない | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_cancel_stops_processing -x` | ❌ Wave 0（新規） |
| V180-QA-01 | サーキットブレーカー（連続失敗閾値到達）で fatal 確定・残ページの API 呼び出しをスキップする | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_circuit_breaker_stops_calls -x` | ❌ Wave 0（新規） |
| V180-QA-01 | OCR 完了後、複数ページ結果を連結してサマリ生成（`complete_text_ex` 相当）まで一気通貫で成功する | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_ocr_then_summary_flow -x` | ❌ Wave 0（新規） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_ocr_engine.py -x`（新規/変更ファイルの高速フィードバック）
- **Per wave merge:** `pytest`（全 987+件のフルスイート・ruff もあわせて実行: `ruff check . && ruff format .`）
- **Phase gate:** フルスイートグリーン + ruff クリーンを `/gsd-verify-work` 前に必達

### Wave 0 Gaps
- [ ] `tests/test_ocr_engine.py` — 新設。`OCRRunEngine` 単体テスト（D-16）+ E2E モックシナリオ（D-13/D-15）を同居させる
- [ ] `FakeProvider` の `complete_text_ex`/`supports_text_prompt` 拡張 — 既存 `tests/test_ocr_pipeline.py`/`tests/test_ocr.py` の `FakeProvider` にはサマリ生成用のオーバーライドがまだない。D-14（既存パターン再利用・新規フェイク実装なし）を守りつつ `tests/test_ocr_engine.py` 内でこの1クラスに限り拡張が必要（他ファイルの `FakeProvider` は変更しない）
- [ ] `_pending_pages()`/`_can_resume()` 等の resume 判断ロジックの回帰確認 — D-10 により `OCRRunEngine` はこれらを知らない前提のため、`OCRDialog` 側に残った resume 判断ロジックの既存回帰テストが引き続き通ることを分割後に確認する（新規テストファイルは不要、既存 `test_ocr_dialog系` があれば流用）
- [ ] フレームワーク自体のインストールは不要（pytest 9.0.3 導入済み）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | no | 本フェーズはユーザー認証を扱わない（デスクトップアプリ・OS ローカル実行） |
| V3 Session Management | no | セッション概念なし |
| V4 Access Control | no | 単一ユーザーローカルアプリ |
| V5 Input Validation | no（変更なし） | OCR 対象ページインデックス（`run_pages`）は既存 `OCRDialog._pending_pages`/`page_indices` の検証済みリストをそのまま渡すのみ。`OCRRunEngine` は新規の外部入力を受け付けない |
| V6 Cryptography | no | 本フェーズは暗号化処理を扱わない |
| V9 Communication (該当なし項目だがOCR文脈で言及) | no（変更なし） | クラウド OCR の https 通信自体は `OCRProvider` 実装済み（変更対象外）。`OCRRunEngine` は provider インスタンスを受け取るのみで通信ロジックには触れない |

### Known Threat Patterns for {stack}

本フェーズは新規の入力経路・通信経路・認証経路を作らない内部リファクタリングのため、新規脅威パターンは identify されなかった。既存の脅威対策（API キー非保存・`_SENSITIVE_KEYS` ガード・クラウド送信の明示同意）は変更対象外であり、`OCRRunEngine` はこれらの機構に一切触れない設計（D-02: provider インスタンスと最小限の値のみ受け取る）。

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| リファクタリングによる意図しないキー/機密値の Engine への混入 | Information Disclosure | D-02 が「設定 dict を丸ごと渡さない」と明示しているため、実装時に `provider`（既に構築済みインスタンス）以外の生設定・API キー文字列を `OCRRunEngine` の引数に含めないことをコードレビューで確認する |

## Sources

### Primary (HIGH confidence)
- `pagefolio/ocr_pipeline.py`（全文読了） — `PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels` の現行契約
- `pagefolio/ocr_dialog.py`（該当範囲: 100-300, 690-830, 1330-1930, 1980-2520 行を読了） — 抽出対象の producer-consumer 駆動部・状態保持フィールド・サマリ生成ロジックの現状実装
- `pagefolio/ocr_providers/base.py`（全文読了） — `OCRProvider` 抽象基底クラス・`ocr_image_ex`/`complete_text_ex`/`supports_text_prompt` の契約
- `pagefolio/ocr.py`（grep確認） — `MAX_RETRIES`/`clamp_retry_after`/`interruptible_sleep`/`build_provider` の所在確認
- `tests/test_ocr_pipeline.py`（全文読了） — `FakeProvider` パターン・`_drive_pipeline` 実スレッド駆動テストヘルパーの現行実装
- `tests/test_ocr_providers.py`（該当範囲抜粋確認） — `complete_text_ex`/`supports_text_prompt` のテストパターン
- `.planning/phases/03-ocr-e2e/03-CONTEXT.md`（全文読了） — D-01〜D-16 の全決定事項
- `.planning/REQUIREMENTS.md`・`.planning/STATE.md`（全文読了） — 要件文言・フェーズ依存関係・マイルストーン方針
- `.planning/research/PITFALLS.md`（全文読了） — 落とし穴10（本フェーズの中心的リスク）・落とし穴9（import 回帰）
- 実測: `python -m pytest --version`（9.0.3）・`python -m pytest -q`（987 passed, 36.21s ベースライン）

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md`（該当範囲抜粋確認） — Phase 4（旧採番）の位置づけ・`ocr_engine.py` 新設という命名の裏付け

### Tertiary (LOW confidence)
- なし（本フェーズは全て自社コードベースの現物確認で完結し、外部 Web リサーチは不要だった）

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 新規パッケージなし、既存コードベースの現物確認のみ
- Architecture: HIGH — 抽出対象コードを行単位で読了し、CONTEXT.md の全16決定と突き合わせ済み
- Pitfalls: HIGH — PITFALLS.md 落とし穴10が本フェーズを名指しで対象化しており、既存の `_drive_pipeline` テストパターンで裏付け済み

**Research date:** 2026-07-15
**Valid until:** 60日（内部リファクタリングのため外部エコシステムの変化に依存しない。ただし `ocr_dialog.py` が Phase 2 完了時点で2154→2520行に増加した実績があるため、実装着手前に対象メソッドの行番号を再確認すること）
