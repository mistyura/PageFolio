---
phase: 06-gemini-provider
reviewed: 2026-06-07T10:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr.py
  - pagefolio/settings.py
  - pagefolio/dialogs/llm_config.py
  - tests/test_ocr.py
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 06 (Gap-Closure 06-04): Code Review Report

**Reviewed:** 2026-06-07T10:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

06-04 ギャップクロージャでは以下の変更が行われた。

- **CR-01**: `_start_worker_thread` で `self.concurrency` 本のワーカースレッドを起動し、`_workers_remaining` / `_done_lock` で最終ワーカーを正しく検出するよう修正。
- **CR-02**: `_finish_cancelled` / `_finish_complete` / `_finish_error` に `if self._done: return` 冪等ガードを追加。
- **WR-01**: `DEFAULT_OCR_SCALE` を 1.5 に統一（`ocr.py` / `ocr_dialog.py` / `llm_config.py` の 3 箇所）。
- **WR-02**: `executor.shutdown(cancel_futures=True)` を `sys.version_info >= (3, 9)` ガードで Python 3.8 互換化（`run_with_bounded_buffer` / `run_parallel` の 2 箇所）。
- **WR-03**: `_SENSITIVE_KEYS` に大文字・小文字バリアント（`google_api_key` / `GOOGLE_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`）を追加。

CR-01・CR-02・WR-01・WR-02 の修正内容は概ね正しく実装されている。ただし、以下の問題が新たに発見された。

1. **BLOCKER × 1**: キャンセル時の終了シグナル（`None`）が `put_nowait` でサイレントにドロップされる場合があり、ワーカースレッドが永久にブロックする。
2. **WARNING × 2**: ワーカースレッドから `self._skipped_pages` / `self.results` / `self.errors` を Lock なしに読み書きするスレッドセーフ違反、および `_done_count` がキャンセル/致命的エラースキップ時に更新されないプログレス表示の不正確さ。
3. **INFO × 3**: テストの冪等ガード検証が `_finish_cancelled` のみ、`TestFinishIdempotent` で `_done` フラグのリセットが検証されていない、`_worker` 内の `time` モジュールをループ外でインポートしている（既存のコメント `# ループ外でインポート（IN-02 修正）` があるが実際にはまだループ内）。

---

## Structural Findings (fallow)

なし（構造解析は実施されていない）。

---

## Narrative Findings (AI reviewer)

---

## Critical Issues

### CR-01: キャンセル時の終了シグナルが `put_nowait` でサイレントにドロップされ、ワーカーが永久ブロックする可能性

**File:** `pagefolio/ocr_dialog.py:888-894`, `935-942`

**Issue:**
`_render_next_page` 内のキャンセル検出パスは `self._render_queue.put_nowait(None)` で全ワーカー分（`self.concurrency` 個）の終了シグナルを送る。しかし `put_nowait` は `queue.Full` 例外を捕捉して **何も送らずに続行**する。

```python
# ocr_dialog.py L888-894
if self._cancel_flag.is_set():
    for _ in range(self.concurrency):
        try:
            self._render_queue.put_nowait(None)   # Full なら何もしない
        except queue.Full:
            pass                                   # ← シグナルがドロップされる
    self._finish_cancelled()
    return
```

同様のパターンが L935-942（ブロッキング put ループ内のキャンセル検出）にも存在する。

キューのサイズは `maxsize = self.concurrency + 1` である。`concurrency = 4` の場合 `maxsize = 5`。ワーカーが全員 API 呼び出し（例: LM Studio への HTTP 要求）でブロック中であれば、キューには未処理の b64 アイテムが `maxsize` 個詰まったままになる。このとき `put_nowait(None)` はすべて `queue.Full` で失敗し、**終了シグナルが 0 本も届かない**。

ワーカーは `get(timeout=1.0)` でキューを監視しており、タイムアウト時に `_cancel_flag.is_set()` をチェックして `break` する設計になっている（L986-989）。しかしこの経路を通る場合、`_workers_remaining` の decrements は正しく行われるので最終ワーカー検出自体は成立する。ただし、キュー内の残アイテムがワーカーによって取り出されると、`_cancel_flag` がセット済みでもアイテムが `continue` されてキューから取り出されるため（L998-1000）、ループが続く。問題の本質は「キュー満杯で `None` が届かない → ワーカーは 1 秒ごとのタイムアウトポーリングに依存せざるを得ない → 大量ページで応答遅延が生じる」ことと、最悪ケースではキューからアイテムが取り出され続け終了に非常に時間がかかることである。

より深刻なシナリオ: 単一ワーカー（`concurrency=1`）でキューが満杯（`maxsize=2`）のとき、キャンセル時に `put_nowait(None)` が Full → シグナルドロップ。ワーカーは次の `get(timeout=1.0)` でキュー内の b64 アイテムを取り出し処理する。その後また `get(timeout=1.0)` を繰り返し、1 秒後のタイムアウトで `_cancel_flag.is_set()` をチェックして `break` する。これはユーザーがキャンセルボタンを押したにもかかわらず 1+ 秒間 API 呼び出しが続く可能性を意味する。

**Fix:**
ブロッキング `put`（`queue.Full` にならない）を使うか、終了シグナルを優先的に積む専用メカニズムを使う必要がある。最もシンプルな修正はキューをクリアしてから `None` を積む（ただし Producer との競合があるため `Lock` が必要）か、以下のように既存のキャンセルポーリング（タイムアウトで `break`）に全面的に依存し、`put_nowait` の失敗を許容しつつ最悪でも 1 秒以内に終了することを保証する方法である。

現実的な短期修正として、`put_nowait` が失敗した場合に `time.sleep(0.05)` でリトライするループを採用する:

```python
# 修正例: キャンセル時シグナル送信をリトライ付きブロッキングputに変更
if self._cancel_flag.is_set():
    for _ in range(self.concurrency):
        while True:
            try:
                self._render_queue.put(None, timeout=0.1)
                break
            except queue.Full:
                continue  # キューが空くまでリトライ（ワーカーがアイテムを取り出すまで待つ）
    self._finish_cancelled()
    return
```

同様の修正を L935-942 の内部キャンセルパスにも適用すること。

---

## Warnings

### WR-01: ワーカースレッドが `self._skipped_pages` を Lock なしで読み取り、`self.results` / `self.errors` を Lock なしで書き込む

**File:** `pagefolio/ocr_dialog.py:1008-1058`, `1064`

**Issue:**
複数ワーカースレッドが以下のデータ構造にアクセスするが、`_done_lock` 以外の保護がない。

```python
# L1008-1010（ワーカースレッド内）
text = self.provider.ocr_image(b64, self._ocr_prompt)
self.results[page_idx] = text           # Lock なし書き込み
...
self.errors[page_idx] = str(e)          # Lock なし書き込み（L1014, L1049, L1055）
```

```python
# L1064（ワーカースレッド内）
skipped_count = len(self._skipped_pages)  # Lock なし読み取り
```

一方、メインスレッド（`_render_next_page`）は `self.results[page_idx] = extracted`（L916）と `self._skipped_pages.add(page_idx)`（L917）を Lock なしで書き込む。

Python の GIL（Global Interpreter Lock）は `dict` / `set` の単一操作（`dict.__setitem__` など）をアトミックに実行するため、CPython 実装では多くのケースで壊滅的なデータ破壊は起きない。しかし:
1. CPython 固有の動作に依存しており、PyPy 等では保証されない。
2. `len(self._skipped_pages)` の呼び出しタイミングにより、メインスレッドが `add()` を実行中と競合するとカウントが瞬間的に不正になりうる。
3. 同じ `page_idx` に対して複数ワーカーが並行して `self.results[page_idx]` を書き込む可能性は実質ゼロ（Producer が各 page_idx をキューに 1 回だけ積む）だが、コードを読む者には保証が不明確。

**Fix:**
`self.results` / `self.errors` の書き込みを `_done_lock` 配下に含めるか、専用の `_result_lock` を設ける。最低限 `skipped_count` の読み取りを `_done_lock` 配下に含める（`_done_count` と同時に読み取ることで一貫性が確保される）:

```python
# 修正例
with self._done_lock:
    skipped_count = len(self._skipped_pages)
    total_done = self._done_count + skipped_count
```

---

### WR-02: キャンセル/致命的エラースキップ時に `_done_count` が更新されずプログレスが過少表示される

**File:** `pagefolio/ocr_dialog.py:996-1000`

**Issue:**
ワーカーがキューからアイテムを取り出した後、`_cancel_flag` または `_fatal_msg` の検出で `continue`（スキップ）する場合、`_done_count` は更新されない:

```python
# L996-1000
with self._done_lock:
    has_fatal = self._fatal_msg is not None
if self._cancel_flag.is_set() or has_fatal:
    continue  # ← _done_count を更新しない
```

このアイテムは実質「処理済み（スキップ）」であるにもかかわらず、プログレス計算 `total_done = self._done_count + skipped_count` には反映されない。キャンセル後に部分的な結果を表示する `_finish_cancelled` では `_render_results_ordered()` を呼ぶが、プログレスバー最終値が実際の処理数より少なく表示される（視覚的な不整合）。

**重要度評価**: 表示上の不整合であり機能的な正確性（どのページが処理されたか）には影響しない。しかし `_workers_remaining` の最終ワーカー検出には影響しないため、デッドロックや誤った終了処理は発生しない。

**Fix:**

```python
# 修正例: スキップ時も _done_count を更新する
with self._done_lock:
    has_fatal = self._fatal_msg is not None
if self._cancel_flag.is_set() or has_fatal:
    with self._done_lock:
        self._done_count += 1   # スキップ扱いとしてカウント
    continue
```

ただし、この修正を行うとキャンセル後に `total_done` が跳ね上がりプログレスバーが満杯になりうる。視覚的な整合性を優先するなら、`_finish_cancelled` の時点でプログレスバーをリセットまたは確定値に設定する方が望ましい。

---

## Info

### IN-01: `TestFinishIdempotent` が `_finish_complete` / `_finish_error` の冪等性を検証していない

**File:** `tests/test_ocr.py:1355-1401`

**Issue:**
CR-02 の冪等ガードは `_finish_cancelled` / `_finish_complete` / `_finish_error` の 3 つに適用されているが、テストは `_finish_cancelled` のみを対象とする。`_finish_complete` や `_finish_error` が 2 回呼ばれるシナリオ（例: `_finish_error` が after で遅延呼び出しされる間に `_cancel_flag` がセットされる）は本来起きにくいが、防御テストとしての価値がある。

**Fix:**
`TestFinishIdempotent` に `test_finish_complete_renders_once` および `test_finish_error_renders_once` テストケースを追加する。

---

### IN-02: `test_termination_signals_match_concurrency` がキャンセル経路のシグナルドロップを検証していない

**File:** `tests/test_ocr.py:1312-1349`

**Issue:**
`TestWorkerConcurrency.test_termination_signals_match_concurrency` は「0 ページ完了」の経路（`idx >= total` 分岐）のみを検証する。`_render_next_page` 冒頭のキャンセル検出パス（`_cancel_flag.is_set()` が True の場合の `put_nowait` ループ）は検証されていない。CR-01（BLOCKER）で指摘したように、このパスは `queue.Full` 時にシグナルをドロップする潜在的バグを持つ。

**Fix:**
キャンセル検出パスのシグナルドロップを再現するテストを追加する:

```python
def test_cancel_path_signals_with_full_queue(self):
    """キューが満杯状態でキャンセルが発生したとき、終了シグナルが届くことを検証。"""
    # キューを b64 アイテムで満杯にしてからキャンセルフラグをセットし、
    # _render_next_page を呼び出して None が concurrency 本届くことを確認する。
```

---

### IN-03: `_worker` 内の `time` インポートは `import time as _time` の形式でファイル先頭に移動すべき

**File:** `pagefolio/ocr_dialog.py:978`

**Issue:**
```python
def _worker(self):
    import time as _time  # ループ外でインポート（IN-02 修正）
```

コメントには「ループ外でインポート」とあるが、`import` 文は関数スコープに留まっており、スレッドが起動するたびに（ただし Python のモジュールキャッシュにより副作用は軽微）実行される。プロジェクト規約（CLAUDE.md）・標準慣習ともに、`import` はファイル先頭に置くことが求められる。`ocr_dialog.py` のモジュールレベルには既に `import threading` 等が集められており、`import time` もそこに追加すべきである。

`OCRRetryableError` の関数内インポート（L1003）は循環インポート回避のための意図的な設計と見られるため、変更対象ではない。

**Fix:**
```python
# pagefolio/ocr_dialog.py ファイル先頭のインポートブロックに追加
import time
```

```python
# _worker 内の L978 を削除し、代わりにファイル先頭のインポートを使用
# import time as _time  <- 削除
# _time.sleep(delay)    <- time.sleep(delay) に変更
```

---

_Reviewed: 2026-06-07T10:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
