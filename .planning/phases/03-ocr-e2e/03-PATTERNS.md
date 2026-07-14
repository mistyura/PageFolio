# Phase 3: OCR実行エンジン抽出 + E2Eテスト - Pattern Map

**Mapped:** 2026-07-15
**Files analyzed:** 3 (1 new source module, 1 modified source module, 1 new test module + 1 modified test module)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pagefolio/ocr_engine.py` (new) | service（consumer 駆動・軽量クラス） | event-driven / producer-consumer | `pagefolio/ocr_pipeline.py`（`PipelineState`/`consume_one`）+ `pagefolio/ocr_dialog.py:1668-1786`（`_start_worker_thread`/`_worker`） | exact（既存純ロジック層をそのまま呼び出す薄いラッパークラスとして設計） |
| `pagefolio/ocr_dialog.py` (modified: `_start_worker_thread`/`_worker` → 委譲ラッパー化) | controller（Tkinter Mixin 内メソッド群） | request-response（コールバック経由のUI更新） | 同ファイル内の `_render_next_page`（producer・変更不要で残留）が対比参照 | exact（同ファイル内リファクタリング） |
| `tests/test_ocr_engine.py` (new) | test（unit + integration/E2E） | event-driven（実スレッド駆動） | `tests/test_ocr_pipeline.py`（`FakeProvider` パターン・`_drive_pipeline` 実スレッド駆動ヘルパー） | exact |
| `tests/test_ocr_pipeline.py` の `FakeProvider`（modified: 変更しない） / `tests/test_ocr_engine.py` 内で拡張する `FakeProvider` 派生 | test fixture | CRUD（フェイクデータ返却） | `tests/test_ocr_providers.py` の `complete_text_ex`/`supports_text_prompt` テストパターン | role-match |

## Pattern Assignments

### `pagefolio/ocr_engine.py`（新設・service／producer-consumer の consumer 側）

**Analog 1:** `pagefolio/ocr_pipeline.py`（変更不要・そのまま呼び出す）
**Analog 2:** `pagefolio/ocr_dialog.py:1668-1786`（移植元の現状実装）

**モジュール docstring 作法**（`ocr_pipeline.py` 1-33行に倣う。Tk/fitz 非依存の純ロジック層系譜への参加を明記する）:
```python
# Source: pagefolio/ocr_pipeline.py:1-33
"""OCR 実行パイプライン純ロジック層 — Tkinter / fitz 非依存。
...
ここには `fitz` / `tkinter` を一切 import しない（pagination.py の純ロジック
層作法に倣う）。ネットワーク呼び出し関連...は `consume_one` 内で
`pagefolio.ocr` / `pagefolio.ocr_providers` から関数内 import する（循環
import 回避のための既存作法・ocr_dialog.py:1479 付近に倣う）。
"""
```
`ocr_engine.py` も同様に：`import threading`/`import queue`/`import logging` のみをトップレベルで import し、`pagefolio.ocr_pipeline`（`PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`）を import する。`pagefolio.ocr`/`pagefolio.ocr_providers` への依存が必要な場合も `ocr_pipeline.py` と同じく関数内 import（循環 import 回避）を踏襲すること。

**consumer 起動パターン**（コンストラクタ/起動メソッドで `queue.Queue`/`PipelineState` を一度だけ生成 — Pitfall 1 対応。D-01/D-02 準拠の最小限の値渡し）:
```python
# Source: pagefolio/ocr_dialog.py:1668-1681（_start_worker_thread・移植元）
def _start_worker_thread(self, gen=None):
    self._worker_threads = []
    self._pstate = PipelineState(self.concurrency)
    for _ in range(self.concurrency):
        t = threading.Thread(target=self._worker, args=(gen,), daemon=True)
        t.start()
        self._worker_threads.append(t)
```
→ `OCRRunEngine` 側は同型のロジックを起動メソッド（例: `start()`）内に持ち、`self.queue = queue.Queue(maxsize=concurrency + 1)` と `self._pstate = PipelineState(concurrency)` を **Engine 内で一度だけ**生成し、`OCRDialog`（producer）はそれを `self._engine.queue` のようなプロパティ経由でのみ参照する（Open Questions A1 の推奨解に従う）。

**consumer ループ（1 アイテム消費 → `consume_one` 委譲 → 統合進捗コールバック）**:
```python
# Source: pagefolio/ocr_dialog.py:1709-1754（_worker のループ本体・移植元）
while True:
    try:
        item = self._render_queue.get(timeout=1.0)
    except queue.Empty:
        if self._cancel_flag.is_set():
            break
        continue
    if item is None:
        break  # 完了シグナル
    page_idx, b64 = item
    try:
        consume_one(
            self.provider, item, self._ocr_prompt, self._pstate,
            cancel_check=self._cancel_flag.is_set,
            breaker_threshold=CB_CONSECUTIVE_FAILURES,
            on_success=lambda p, t, tr: self._record_page_success(p, t, truncated=tr),
            on_page_error=self._record_page_error,
            on_retry_wait=_on_retry_wait,
        )
    finally:
        del b64  # 送信後即座に破棄（T-06-06）
```
→ `OCRRunEngine` はこのループを内包し、`self._record_page_success`/`self._record_page_error` 相当を **Engine 内部の results/errors 辞書更新（D-09）+ D-05/D-06 のコールバック個別呼び出し**に置き換える。`on_success`/`on_page_error`/`on_fatal`/`on_retry_wait` は `consume_one` の既存シグネチャをそのまま Engine のコンストラクタ引数として受け取り、内部でラップして状態更新後に外側コールバックへ転送する二段構成にする。

**最終ワーカー判定（CR-01・D-08 完了理由別コールバック）**:
```python
# Source: pagefolio/ocr_dialog.py:1756-1786（_worker 末尾・移植元）
is_last, fatal_msg, fatal_kind = self._pstate.decrement_worker()
if not is_last:
    return
if fatal_msg is not None:
    self.after(0, lambda m=fatal_msg, k=fatal_kind: self._finish_error(m, kind=k))
    return
if self._cancel_flag.is_set():
    self.after(0, self._finish_cancelled)
    return
self.after(0, self._render_results_ordered)
self.after(0, self._finish_complete)
```
→ `OCRRunEngine` 側は `self.after()`（Tk 依存）を持たないため、対応する理由別コールバック（`on_fatal`/`on_cancelled`/`on_complete` — D-08）を**直接**呼ぶ。`OCRDialog` 側が受け取ったコールバック内で `self.after(0, ...)` へラップして UI スレッドへディスパッチする（D-05: Engine 自体はコールバックを同期的に呼ぶだけで Tk に触れない）。

**統合進捗計算（D-07・D-12: `_done_disp` 相当を Engine が内部で持つ）**:
```python
# Source: pagefolio/ocr_dialog.py:793-804（_done_disp・移植元ロジック）
def _done_disp(self):
    done_count = self._pstate.done_count if self._pstate is not None else 0
    skipped = len(self._skipped_pages) - self._skip_base
    render_failed = len(self._render_failed_pages) - self._render_failed_base
    return done_count + skipped + render_failed
```
→ Engine はスキップ/レンダー失敗の「今回実行分ベースライン」（D-12 の `_skip_base`/`_render_failed_base` 相当）を持たない設計にできる点に注意：スキップ・レンダー失敗は producer（`OCRDialog._render_next_page`）側の判断であり、Engine が知るのは consumer 側の `done_count` のみ。D-07 は「統合進捗計算を Engine が持つ」としているため、Engine はスキップ数/レンダー失敗数を**引数として受け取る**か、`OCRDialog` から都度渡してもらう設計判断が必要（Claude's Discretion 範囲・A1 と同種の設計選択）。

**結果辞書所有権（D-09: results/errors/skipped_pages/truncated_pages/render_failed_pages）**:
```python
# Source: pagefolio/ocr_dialog.py:765-791（_record_page_success/_record_page_error・移植先イメージ）
def _record_page_success(self, page_idx, text, truncated=False):
    self.results[page_idx] = text
    if truncated:
        self._truncated_pages.add(page_idx)
    else:
        self._truncated_pages.discard(page_idx)

def _record_page_error(self, page_idx, msg):
    self.errors[page_idx] = msg
```
→ `OCRRunEngine.__init__` で `self.results = {}` / `self.errors = {}` / `self.truncated_pages = set()` を初期化し、内部の `on_success`/`on_page_error` ラッパー内でこれらを更新した**後**に、外側コールバック（`OCRDialog` が注入したもの）へ通知する。

---

### `pagefolio/ocr_dialog.py`（既存ファイル・`_start_worker_thread`/`_worker` を委譲ラッパー化）

**Analog:** 同ファイル内の `_render_next_page`（producer・変更不要のまま残留する対比参照）

**委譲後イメージ**（D-04・メソッド名/シグネチャ不変）:
```python
# 抽出後（イメージ・CONTEXT.md D-04 のコード例より）
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
    self._engine.start()
```
`_render_next_page`（`pagefolio/ocr_dialog.py:1542-1647`）は producer としてそのまま残し、`self._render_queue` への参照先のみ `self._engine.queue`（Pitfall 1 対応・キュー同一性の一本化）に差し替える。`_retry_sentinels`（`ocr_dialog.py:1649-1666`）も producer 側ヘルパーとして残留・変更不要。

**完了理由別ハンドラの受け皿**（D-08・変更不要でそのまま活用）:
```python
# Source: pagefolio/ocr_dialog.py:1853-1922（_finish_complete/_finish_cancelled/_finish_error）
def _finish_complete(self):
    if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
        return
    self._done = True
    ...
```
`_on_engine_complete(gen)`/`_on_engine_cancelled(gen)`/`_on_engine_fatal(gen, msg, kind)`（イメージ内の新規メソッド）は世代ガード（`gen == self._run_gen`）チェック後にこれら既存 `_finish_*` メソッドをそのまま呼ぶ薄いアダプタとして実装する。

---

### `tests/test_ocr_engine.py`（新設・unit + E2E モックテスト）

**Analog 1:** `tests/test_ocr_pipeline.py`（`FakeProvider`・`_drive_pipeline`）

**FakeProvider パターン（D-14・再利用元）**:
```python
# Source: tests/test_ocr_pipeline.py:28-44
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
```
→ `tests/test_ocr_engine.py` 内で**この1クラス限定**でサマリ生成カバレッジ用に拡張する（D-14: 他ファイルの `FakeProvider` は変更しない）:
```python
# 拡張イメージ（Wave 0 Gaps に明記済み）
supports_text_prompt = True

def complete_text_ex(self, text, prompt, **kwargs):
    return (f"summary-of-{len(text)}", False)
```
`OCRProvider.complete_text_ex`/`supports_text_prompt` のシグネチャは `pagefolio/ocr_providers/base.py:86, 106` の `ocr_image_ex`/`complete_text_ex` 抽象定義を参照して合わせること。

**実スレッド駆動テストヘルパー（D-13・E2E の高忠実度統合テスト前例）**:
```python
# Source: tests/test_ocr_pipeline.py:208-279（_drive_pipeline）
def _drive_pipeline(provider, render_fn, page_indices, concurrency, prompt="", is_cancelled=None):
    ...
    producer_thread = threading.Thread(target=_producer, daemon=True)
    producer_thread.start()
    consumer_threads = [threading.Thread(target=_consumer, daemon=True) for _ in range(workers)]
    for t in consumer_threads:
        t.start()
    for t in consumer_threads:
        t.join(timeout=10.0)
    producer_thread.join(timeout=5.0)
    return results, errors, state, render_failed
```
`tests/test_ocr_engine.py` の E2E テストは、この「テスト専用ドライバの自作」パターンではなく、**`OCRRunEngine` 自体を起動して検証する**形に転用する（RESEARCH.md 明記）。ダミー render 関数から `engine.queue` へ `try_enqueue` する薄い producer スタブをテストコード側に置き、consumer 側は `OCRRunEngine.start()` が内部で担う。タイムアウト設計（`join(timeout=10.0)`/`join(timeout=5.0)`）はそのまま踏襲する。

---

## Shared Patterns

### PipelineState / consume_one（変更禁止・そのまま呼び出す）
**Source:** `pagefolio/ocr_pipeline.py:47-269`
**Apply to:** `ocr_engine.py` 全体
```python
# Source: pagefolio/ocr_pipeline.py:170-181（シグネチャ・変更不要）
def consume_one(
    provider, item, prompt, state, cancel_check=None,
    breaker_threshold=DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    on_success=None, on_page_error=None, on_fatal=None, on_retry_wait=None,
):
    ...
```
`OCRRunEngine` はこれを「再実装」せず「所有・呼び出す」のみ（Anti-Patterns 節・D-01 根拠）。

### 非ブロッキング enqueue/sentinel 送出（変更禁止）
**Source:** `pagefolio/ocr_pipeline.py:138-167`（`try_enqueue`/`send_sentinels`）
**Apply to:** `ocr_engine.py`（キュー公開プロパティ経由）・`ocr_dialog.py` の producer 側（変更なしでそのまま利用継続）

### 世代ガードパターン（D-11 により Engine では不要・OCRDialog 側は継続）
**Source:** `pagefolio/ocr_dialog.py:1552-1553`（`_render_next_page` の `gen != self._run_gen` チェック）
**Apply to:** `ocr_dialog.py` の producer 側・完了理由別アダプタメソッド（`_on_engine_complete` 等）。`OCRRunEngine` 自体は D-11（実行ごと新規生成）により世代カウンタを持たない。

### 循環 import 回避（関数内 import）
**Source:** `pagefolio/ocr_pipeline.py:218-221`
```python
from pagefolio.ocr import MAX_RETRIES, clamp_retry_after, interruptible_sleep
from pagefolio.ocr_providers import OCRRetryableError
```
**Apply to:** `ocr_engine.py` が `pagefolio.ocr`/`pagefolio.ocr_providers` の関数・例外クラスを直接必要とする場合（`consume_one` に委譲するだけなら不要な可能性が高い）。

### Tk 非依存純ロジック層のモジュール docstring 作法
**Source:** `pagefolio/ocr_pipeline.py:1-33`・`pagefolio/pagination.py`（同格）
**Apply to:** `ocr_engine.py` 冒頭 docstring（「`pagination.py`/`ocr_pipeline.py`/`undo_store.py` と同格」という位置づけを明記し、Engine が「完全な純関数」ではなく「軽量クラス（`PipelineState` と同格）」である旨を注記する）

## No Analog Found

なし。全対象ファイルに既存コードベース内で高一致（exact〜role-match）の分析元が存在する（本フェーズは新規機能ではなく既存コードの配置換えリファクタリングのため）。

## Metadata

**Analog search scope:** `pagefolio/ocr_pipeline.py`・`pagefolio/ocr_dialog.py`（全文中の該当範囲）・`pagefolio/ocr_providers/base.py`・`tests/test_ocr_pipeline.py`・`tests/test_ocr_providers.py`
**Files scanned:** 5（読了）+ grep によるメソッド位置特定
**Pattern extraction date:** 2026-07-15
