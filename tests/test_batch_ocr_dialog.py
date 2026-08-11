# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""`BatchOCRDialog` の E2E モックテスト（失敗分離・2階層キャンセル・エッジ）。

`tests/test_ocr_engine.py` の `FakeProvider` パターン（決定的・実 API 非依存）
をそのまま流用し、fitz レンダリングは monkeypatch で決定的な canned b64 を
返すよう差し替える（04-02-PLAN.md Task 3・04-RESEARCH.md Test Map）。

実 tkinterdnd2 のネイティブ D&D と Treeview の実配色は手動検証
（04-VALIDATION.md）に委ね、本テストはファイルループのオーケストレーション
（複数ファイル分の OCRRunEngine 生成・失敗分離・キャンセル・進捗集計）を
検証する。`tk.Tk()` の後 `root.withdraw()` した隠しルート上に
`BatchOCRDialog` を構築し、`after()` 連鎖は `mainloop()`/`quit()` による
ポンピングで駆動する（Python 3.14 の tkinter はワーカースレッドからの
`after()` 呼び出しに「メインスレッドが mainloop 内にいること」を要求する
ため、`update()` のみの単純ポンピングでは `RuntimeError` になる）。
"""

import os
import sys
import threading
import time
import tkinter as tk
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagefolio.batch_ocr_state import STATUS_DONE, STATUS_FAILED  # noqa: E402
from pagefolio.dialogs import batch_ocr  # noqa: E402
from pagefolio.ocr_providers import OCRProvider, OCRRetryableError  # noqa: E402


# ── FakeProvider（他ファイルの FakeProvider とはカプセル化のため共有せず、
#    意図的に本ファイルへ複製する・D-14 と同方針）───────────────────────
class FakeProvider(OCRProvider):
    """BatchOCRDialog テスト用の偽 Provider（実 API 非依存の決定的な偽実装）。

    ocr_image は b64 から決定的にテキストを返す（D-14 の意図的な複製方針）。
    """

    default_concurrency = 1
    max_concurrency = 4
    supports_text_prompt = True

    def __init__(self, side_effect=None):
        """side_effect が None なら f"text-{b64}" を返す。callable なら呼び出す。"""
        self._side_effect = side_effect

    def ocr_image(self, b64_png, prompt, **kwargs):
        if self._side_effect is not None:
            return self._side_effect(b64_png, prompt)
        return f"text-{b64_png}"

    def list_models(self):
        return ["fake-model"]


class _FakePage:
    """`fitz.Page` の代替。path/idx のみを保持する（monkeypatch した
    `has_embedded_text`/`page_to_png_b64` が参照する最小限の属性）。
    """

    def __init__(self, path, idx):
        self.path = path
        self.idx = idx


class _FakeDoc:
    """`fitz.Document` の代替。事前ページ数スキャンとレンダリングの両方で
    `fitz.open()` の戻り値として使われる（`__len__`/`__getitem__`/`close`）。
    """

    def __init__(self, path, page_count):
        self.path = path
        self._page_count = page_count
        self.closed = False

    def __len__(self):
        return self._page_count

    def __getitem__(self, idx):
        return _FakePage(self.path, idx)

    def close(self):
        self.closed = True


def _make_app_stub(settings):
    class _AppStub:
        pass

    app = _AppStub()
    app.settings = settings
    app._session_api_keys = {}
    app.plugin_manager = None
    return app


def _build_dialog(root, monkeypatch, provider, page_counts, concurrency=1):
    """BatchOCRDialog を fitz/provider を monkeypatch した状態で構築する。

    `page_counts`: path -> ページ数 の辞書（事前スキャン・レンダリング両方が参照）。
    """

    def _fake_fitz_open(path):
        return _FakeDoc(path, page_counts.get(path, 0))

    monkeypatch.setattr(batch_ocr.fitz, "open", _fake_fitz_open)
    monkeypatch.setattr(batch_ocr, "has_embedded_text", lambda page: False)
    monkeypatch.setattr(
        batch_ocr,
        "page_to_png_b64",
        lambda page, scale=1.5: f"b64::{page.path}::{page.idx}",
    )
    monkeypatch.setattr(batch_ocr, "build_provider", lambda *a, **k: provider)

    settings = {
        "ocr_provider": "lmstudio",
        "lang": "ja",
        "ocr_concurrency": concurrency,
    }
    app = _make_app_stub(settings)
    return batch_ocr.BatchOCRDialog(root, app, lang="ja")


def _pump_until(widget, predicate, timeout=10.0, poll_ms=20):
    """`predicate()` が True になるまで `widget.mainloop()` を実行してイベント
    ループを駆動する（`after()` 連鎖・ワーカースレッドからのコールバックを
    メインスレッドで処理させるため）。

    Python 3.14 の tkinter はワーカースレッドからの `after()` 呼び出しに
    「メインスレッドが mainloop 内にいること」を要求する（`update()` による
    単純ポンピングでは `RuntimeError: main thread is not in main loop` になる）。
    そのため `widget.after(poll_ms, _poll)` で自己再帰的にポーリングしつつ
    `widget.mainloop()` を実際に実行し、条件成立/タイムアウトで `quit()` する。
    """
    deadline = time.monotonic() + timeout
    result = {"done": False}

    def _poll():
        if predicate():
            result["done"] = True
            widget.quit()
            return
        if time.monotonic() >= deadline:
            widget.quit()
            return
        widget.after(poll_ms, _poll)

    widget.after(poll_ms, _poll)
    widget.mainloop()
    return result["done"]


def _pump_for(widget, duration, poll_ms=20):
    """`duration` 秒だけ `widget.mainloop()` を実行してイベントループを駆動する。

    完了を待つ対象がない（クローズ後の残存コールバック無害化確認など）場合に
    使う固定時間版のポンピングヘルパー。
    """
    _pump_until(widget, lambda: False, timeout=duration, poll_ms=poll_ms)


@pytest.fixture(scope="module")
def tk_root():
    """モジュール全体で1つの `tk.Tk()` を共有する（複数 Tk() の逐次生成は
    ttk テーマ再読込で `TclError` を誘発するため・環境依存の既知制約）。
    個々のダイアログ（Toplevel）は各テストが生成・破棄する。
    """
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


class TestBatchOCRDialogE2E:
    """ファイルループコントローラの E2E モックテスト群（実 API 非依存）。"""

    def test_file_failure_continues(self, tk_root, monkeypatch):
        """先頭ファイルがサーキットブレーカーで fatal → 自動スキップ →
        2番目ファイルの OCRRunEngine が新規生成され継続する（V180-BATCH-03・D-09）。
        """

        def side_effect(b64, prompt):
            if "::/fileA.pdf::" in b64:
                raise OCRRetryableError("simulated failure", retry_after=0.01)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        dialog = _build_dialog(
            tk_root, monkeypatch, provider, {"/fileA.pdf": 3, "/fileB.pdf": 2}
        )
        try:
            dialog._enqueue_files(["/fileA.pdf", "/fileB.pdf"])
            dialog._on_start_batch()

            ok = _pump_until(dialog, lambda: not dialog._running, timeout=10.0)
            assert ok, "バッチが時間内に終了しなかった"

            entry_a = dialog._entry_by_path("/fileA.pdf")
            entry_b = dialog._entry_by_path("/fileB.pdf")
            assert entry_a.status == STATUS_FAILED
            assert entry_b.status == STATUS_DONE
            assert dialog._batch_state.failed == 1
            assert dialog._batch_state.completed == 1
        finally:
            dialog.destroy()

    def test_batch_cancel_stops_all(self, tk_root, monkeypatch):
        """実行中に `_on_batch_cancel` を呼ぶと2階層フラグが同時 set され、
        実行中ファイルが停止し次ファイルの Engine が新規生成されない
        （V180-BATCH-04・D-10・Pitfall 2）。
        """
        started_event = threading.Event()
        release_event = threading.Event()

        def side_effect(b64, prompt):
            started_event.set()
            release_event.wait(timeout=5.0)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        dialog = _build_dialog(
            tk_root,
            monkeypatch,
            provider,
            {"/fileA.pdf": 2, "/fileB.pdf": 1},
            concurrency=1,
        )
        try:
            dialog._enqueue_files(["/fileA.pdf", "/fileB.pdf"])
            dialog._on_start_batch()

            assert started_event.wait(timeout=5.0), "ワーカーが処理を開始しなかった"

            dialog._on_batch_cancel()
            assert dialog._batch_cancel_flag.is_set()
            assert dialog._file_cancel_flag.is_set()

            release_event.set()

            # `_on_batch_cancel` は即座に `_running=False` へ戻すため、
            # 非同期の後始末（`_current_engine` クリア）完了を直接待つ。
            ok = _pump_until(
                dialog, lambda: dialog._current_engine is None, timeout=10.0
            )
            assert ok, "キャンセル後にワーカー後始末が完了しなかった"

            entry_b = dialog._entry_by_path("/fileB.pdf")
            assert entry_b.status != STATUS_DONE
        finally:
            dialog.destroy()

    def test_cancel_before_start_noop(self, tk_root, monkeypatch):
        """実行前に `_on_batch_cancel` を呼んでも例外にならず、Engine は
        新規生成されない（cancel-before-start・エッジ）。
        """
        provider = FakeProvider()
        dialog = _build_dialog(tk_root, monkeypatch, provider, {"/fileA.pdf": 1})
        try:
            dialog._enqueue_files(["/fileA.pdf"])
            dialog._on_batch_cancel()  # 実行前でも例外にならない

            assert dialog._batch_cancel_flag.is_set()
            assert dialog._file_cancel_flag.is_set()
            assert dialog._current_engine is None
        finally:
            dialog.destroy()

    def test_all_files_fail(self, tk_root, monkeypatch):
        """全ファイルが fatal でもバッチが停止せず全件処理される
        （BatchState.failed == 総数・エッジ）。
        """

        def side_effect(b64, prompt):
            raise OCRRetryableError("simulated failure", retry_after=0.01)

        provider = FakeProvider(side_effect=side_effect)
        dialog = _build_dialog(
            tk_root, monkeypatch, provider, {"/fileA.pdf": 3, "/fileB.pdf": 3}
        )
        try:
            dialog._enqueue_files(["/fileA.pdf", "/fileB.pdf"])
            dialog._on_start_batch()

            ok = _pump_until(dialog, lambda: not dialog._running, timeout=10.0)
            assert ok, "バッチが時間内に終了しなかった"

            assert dialog._entry_by_path("/fileA.pdf").status == STATUS_FAILED
            assert dialog._entry_by_path("/fileB.pdf").status == STATUS_FAILED
            assert dialog._batch_state.failed == 2
            assert dialog._batch_state.completed == 0
        finally:
            dialog.destroy()

    def test_progress_never_exceeds_total(self, tk_root, monkeypatch):
        """進捗更新後 `BatchState.files_done()` が `total_files` を超えない
        （エッジ・落とし穴5の構造的回帰防止）。
        """
        from pagefolio.batch_ocr_state import BatchState

        observed = []
        orig_mark_completed = BatchState.mark_completed

        def _wrapped(self):
            orig_mark_completed(self)
            observed.append((self.files_done(), self.total_files))

        monkeypatch.setattr(BatchState, "mark_completed", _wrapped)

        provider = FakeProvider()
        dialog = _build_dialog(
            tk_root, monkeypatch, provider, {"/f1.pdf": 1, "/f2.pdf": 1}
        )
        try:
            dialog._enqueue_files(["/f1.pdf", "/f2.pdf"])
            dialog._on_start_batch()

            ok = _pump_until(dialog, lambda: not dialog._running, timeout=10.0)
            assert ok, "バッチが時間内に終了しなかった"

            assert observed, "完了イベントが1件も記録されなかった"
            for done, total in observed:
                assert done <= total
        finally:
            dialog.destroy()

    def test_close_during_run_stops_threads(self, tk_root, monkeypatch):
        """バッチ実行中に `_on_close`（WM_DELETE_WINDOW 相当）を呼ぶと
        2階層フラグが set され `_run_gen` がインクリメントされて destroy
        される。クローズ後の遅延コールバックは世代ガードで無害化される
        （レビュー懸念1・HIGH）。
        """
        started_event = threading.Event()
        release_event = threading.Event()

        def side_effect(b64, prompt):
            started_event.set()
            release_event.wait(timeout=5.0)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        dialog = _build_dialog(
            tk_root, monkeypatch, provider, {"/fileA.pdf": 2}, concurrency=1
        )

        dialog._enqueue_files(["/fileA.pdf"])
        dialog._on_start_batch()
        assert started_event.wait(timeout=5.0), "ワーカーが処理を開始しなかった"

        gen_before = dialog._run_gen
        dialog._on_close()

        assert dialog._run_gen == gen_before + 1
        assert dialog._batch_cancel_flag.is_set()
        assert dialog._file_cancel_flag.is_set()

        # ワーカーを解放し、destroy 後に遅延コールバックが発火しても
        # tk.TclError が上位へ伝播しないことを確認する（dialog は destroy 済み
        # のため、まだ生きている tk_root 側で mainloop を駆動する）。
        release_event.set()
        try:
            _pump_for(tk_root, 0.4)
        except tk.TclError:
            pytest.fail("destroy 後の after コールバックで TclError が伝播した")

    def test_rerun_skips_completed(self, tk_root, monkeypatch):
        """1件目が STATUS_DONE、2件目が STATUS_PENDING の状態で
        `_on_start_batch` を再実行すると `count_pending` の結果で
        BatchState.total_files==1 となり、STATUS_DONE ファイルは
        再送信されず STATUS_PENDING のみが処理される（レビュー懸念3）。
        """
        calls = []

        def side_effect(b64, prompt):
            calls.append(b64)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        dialog = _build_dialog(
            tk_root, monkeypatch, provider, {"/done.pdf": 1, "/pending.pdf": 1}
        )
        try:
            dialog._enqueue_files(["/done.pdf", "/pending.pdf"])
            entry_done = dialog._entry_by_path("/done.pdf")
            entry_pending = dialog._entry_by_path("/pending.pdf")
            entry_done.status = STATUS_DONE

            dialog._on_start_batch()
            assert dialog._batch_state.total_files == 1

            ok = _pump_until(dialog, lambda: not dialog._running, timeout=10.0)
            assert ok, "バッチが時間内に終了しなかった"

            assert entry_pending.status == STATUS_DONE
            assert entry_done.status == STATUS_DONE
            assert all("/done.pdf" not in c for c in calls), (
                "完了済みファイルが再送信された"
            )
        finally:
            dialog.destroy()


class TestBatchSummary:
    """ファイル横断統合サマリ（D-13/D-14/D-15）・後方互換 re-export のテスト。

    実 fitz/実ネットワーク非依存。バッチ実行そのものは行わず、
    `_entries`/`entry.results`/`entry.status` を直接操作して統合サマリ
    ロジック（`_format_batch_summary_input`/`_on_batch_summary`）のみを
    決定的に検証する（04-RESEARCH.md Test Map・04-03-PLAN.md Task 3）。
    """

    def test_batch_summary_concat(self, tk_root, monkeypatch):
        """`_format_batch_summary_input` が完了ファイルごとに見出し
        （`=== name ===`）を挿入して連結する（D-15・V180-BATCH-05）。
        """
        provider = FakeProvider()
        dialog = _build_dialog(
            tk_root, monkeypatch, provider, {"/a.pdf": 1, "/b.pdf": 1}
        )
        try:
            dialog._enqueue_files(["/a.pdf", "/b.pdf"])
            entry_a = dialog._entry_by_path("/a.pdf")
            entry_b = dialog._entry_by_path("/b.pdf")
            entry_a.status = STATUS_DONE
            entry_a.results[0] = "テキストA"
            entry_b.status = STATUS_DONE
            entry_b.results[0] = "テキストB"

            combined = dialog._format_batch_summary_input()

            assert "a.pdf" in combined
            assert "b.pdf" in combined
            assert "テキストA" in combined
            assert "テキストB" in combined
            # ファイル名見出しが本文より先に現れる（見出し→本文の連結順）
            assert combined.index("a.pdf") < combined.index("テキストA")
            assert combined.index("b.pdf") < combined.index("テキストB")
        finally:
            dialog.destroy()

    def test_batch_summary_zero_completed_noop(self, tk_root, monkeypatch):
        """完了ファイル0件で `_on_batch_summary` を呼んでも `complete_text_ex`
        は呼ばれず no-op（zero-completed エッジ・D-13）。
        """
        calls = []
        provider = FakeProvider()
        provider.complete_text_ex = lambda *a, **k: calls.append(1)
        dialog = _build_dialog(tk_root, monkeypatch, provider, {"/a.pdf": 1})
        try:
            dialog._enqueue_files(["/a.pdf"])  # STATUS_PENDING のまま（未完了）
            dialog.provider = provider

            dialog._on_batch_summary()

            assert not calls
            assert not dialog._summary_running
        finally:
            dialog.destroy()

    def test_batch_summary_oversized_warns(self, tk_root, monkeypatch):
        """連結文字数が `SUMMARY_TOO_LONG_CHARS` を超える場合、`askyesno` 警告を
        経由し、承認しなければ `complete_text_ex` は呼ばれない（D-14）。
        """
        calls = []
        provider = FakeProvider()
        provider.complete_text_ex = lambda *a, **k: calls.append(1)
        dialog = _build_dialog(tk_root, monkeypatch, provider, {"/a.pdf": 1})
        try:
            dialog._enqueue_files(["/a.pdf"])
            entry = dialog._entry_by_path("/a.pdf")
            entry.status = STATUS_DONE
            entry.results[0] = "x" * (batch_ocr.SUMMARY_TOO_LONG_CHARS + 1)
            dialog.provider = provider

            monkeypatch.setattr(batch_ocr.messagebox, "askyesno", lambda *a, **k: False)

            dialog._on_batch_summary()

            assert not calls
            assert not dialog._summary_running
        finally:
            dialog.destroy()

    def test_batch_dialog_reexport(self):
        """後方互換 re-export: `from pagefolio.dialogs import BatchOCRDialog`
        が成功する（到達性 smoke）。
        """
        from pagefolio.dialogs import BatchOCRDialog

        assert BatchOCRDialog is batch_ocr.BatchOCRDialog


class TestBatchSummaryRetrySleepRegression:
    """CR-01 回帰: サマリのリトライ待機が `TypeError` で死なない。

    `_batch_summary_worker` は `OCRRetryableError`（429/5xx）を受けると
    `interruptible_sleep(delay, <キャンセル判定関数>)` で待機する。ここへ
    `threading.Event` インスタンスそのものを渡すと `interruptible_sleep` が
    `is_cancelled()` として呼ぶため `TypeError: 'Event' object is not callable`
    になる。この `TypeError` はリトライ用 `except OCRRetryableError` 節の
    **内部**で送出されるため同じ try の `except Exception` には捕まらず、
    ワーカースレッドごと落ちて `_summary_ui_reset` が呼ばれず、サマリボタンが
    永久に disabled のままハングしていた（`ocr_dialog.py:_summary_worker` /
    `ocr.py` / `ocr_pipeline.py` の同型箇所は正しく `.is_set` を渡している）。

    Tk ウィジェットに依存させず `_batch_summary_worker` を未バインド呼び出し
    する（本ファイル後半の `TestBatchIsCloudProviderOpenAI` 等と同型）。
    """

    def _make_stub(self, complete_text_ex):
        """`_batch_summary_worker` が触る属性だけを持つ最小スタブを返す。"""
        after_calls = []
        stub = types.SimpleNamespace(
            provider=types.SimpleNamespace(complete_text_ex=complete_text_ex),
            _summary_cancel_flag=threading.Event(),
            _run_gen=1,
            after=lambda delay, fn=None: after_calls.append(fn),
            # 終端で `self.after(0, self.<callback>)` として参照されるだけで
            # 呼び出しはされない（after がスタブのため）。存在だけ用意する。
            _on_batch_summary_cancelled=lambda: None,
            _on_batch_summary_done=lambda text, truncated: None,
            _on_batch_summary_error=lambda msg: None,
        )
        return stub, after_calls

    def test_retryable_error_sleep_does_not_raise_typeerror(self, monkeypatch):
        """429 相当を1回受けてリトライ待機に入っても `TypeError` にならず、
        2回目の呼び出しで成功して完了コールバックが `after` へ積まれる。
        """
        # 待機で実時間を消費しないよう即時 return させ、渡された第2引数が
        # 「呼び出せる」ことを実際に呼んで確認する（Event を渡す退行の検出点）。
        passed = []

        def _fake_sleep(total, is_cancelled, step=0.5):
            passed.append(is_cancelled)
            is_cancelled()  # Event インスタンスならここで TypeError

        monkeypatch.setattr(batch_ocr, "interruptible_sleep", _fake_sleep)
        monkeypatch.setattr(batch_ocr, "clamp_retry_after", lambda d: 0.0)

        attempts = []

        def _complete_text_ex(full_text, prompt):
            attempts.append(1)
            if len(attempts) == 1:
                raise OCRRetryableError("429 Too Many Requests")
            return ("要約テキスト", False)

        stub, after_calls = self._make_stub(_complete_text_ex)

        # TypeError が漏れるとここで落ちる（修正前の失敗モード）
        batch_ocr.BatchOCRDialog._batch_summary_worker(stub, 1, "本文", "プロンプト")

        assert len(attempts) == 2, "リトライ後に再試行されていない"
        assert passed, "リトライ待機に入っていない"
        assert callable(passed[0]), (
            f"interruptible_sleep へ呼び出し不可能な値が渡された: {passed[0]!r}"
        )
        # 完了コールバックが積まれている = ワーカーが最後まで到達している
        assert len(after_calls) == 1

    def test_cancel_flag_is_observed_during_retry_sleep(self, monkeypatch):
        """待機中にキャンセルされたことを渡された判定関数が観測できる
        （`.is_set` を渡しているので Event の状態変化が見える）。
        """
        observed = []

        def _fake_sleep(total, is_cancelled, step=0.5):
            observed.append(is_cancelled())  # 待機開始時点: 未キャンセル
            stub_ref["stub"]._summary_cancel_flag.set()
            observed.append(is_cancelled())  # セット後: キャンセル済みが見える

        monkeypatch.setattr(batch_ocr, "interruptible_sleep", _fake_sleep)
        monkeypatch.setattr(batch_ocr, "clamp_retry_after", lambda d: 0.0)

        def _complete_text_ex(full_text, prompt):
            raise OCRRetryableError("503 Service Unavailable")

        stub, after_calls = self._make_stub(_complete_text_ex)
        stub_ref = {"stub": stub}

        batch_ocr.BatchOCRDialog._batch_summary_worker(stub, 1, "本文", "プロンプト")

        assert observed == [False, True], (
            f"キャンセルフラグの状態変化が観測できていない: {observed!r}"
        )


# ══════════════════════════════════════════════════════════════
#  02-02 Task 3(C): openai の catalog 移行回帰（Tk ウィジェット非依存・
#  ocr_dialog.py の TestIsCloudProvider 等と同型の未バインド呼び出しパターン）
# ══════════════════════════════════════════════════════════════


class TestBatchIsCloudProviderOpenAI:
    """V190-CAT-01/V190-OAI-06: openai がバッチ側でもクラウド判定される。"""

    def test_openai_settings_returns_true(self):
        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings={"ocr_provider": "openai"}),
            provider=None,
        )
        stub._is_cloud_provider = lambda settings=None: (
            batch_ocr.BatchOCRDialog._is_cloud_provider(stub, settings)
        )
        assert stub._is_cloud_provider() is True

    def test_unregistered_plugin_name_returns_false(self):
        """D-04: catalog 未登録のプラグイン名は False を返す。"""
        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings={"ocr_provider": "my-custom-plugin"}),
            provider=None,
        )
        stub._is_cloud_provider = lambda settings=None: (
            batch_ocr.BatchOCRDialog._is_cloud_provider(stub, settings)
        )
        assert stub._is_cloud_provider() is False


class TestBatchConfirmCostOpenAI:
    """V190-OAI-04/05/06: バッチ側 _confirm_cost の openai ケース
    （`ocr_dialog.py:TestConfirmCost`/`TestVisionUnverifiedNotice` と対称）。
    """

    def _stub(self, openai_model=None):
        from pagefolio.constants import LANG

        settings = {"ocr_provider": "openai"}
        if openai_model is not None:
            settings["openai_model"] = openai_model
        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            _entries=[],
            _L=LANG["ja"],
        )
        stub._estimate_cost = lambda m, c: batch_ocr.BatchOCRDialog._estimate_cost(
            stub, m, c
        )
        stub._confirm_cost = lambda page_count=None, settings=None: (
            batch_ocr.BatchOCRDialog._confirm_cost(stub, page_count, settings)
        )
        return stub

    def test_confirm_cost_openai_shows_openai_host(self, monkeypatch):
        stub = self._stub()
        captured = {}
        monkeypatch.setattr(
            batch_ocr.messagebox,
            "askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost(page_count=3)
        assert "api.openai.com" in captured["msg"]

    def test_confirm_cost_openai_vision_unverified_note(self, monkeypatch):
        stub = self._stub(openai_model="gpt-9-hypothetical")
        captured = {}
        monkeypatch.setattr(
            batch_ocr.messagebox,
            "askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost(page_count=1)
        from pagefolio.constants import LANG

        note = LANG["ja"]["ocr_model_vision_unverified"].format(
            model="gpt-9-hypothetical"
        )
        assert note in captured["msg"]

    def test_confirm_cost_openai_verified_model_no_note(self, monkeypatch):
        from pagefolio.constants import LANG
        from pagefolio.ocr_providers import OpenAIProvider

        stub = self._stub(openai_model=OpenAIProvider.RECOMMENDED_MODELS[0])
        captured = {}
        monkeypatch.setattr(
            batch_ocr.messagebox,
            "askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost(page_count=1)
        marker = LANG["ja"]["ocr_model_vision_unverified"].split("{")[0]
        assert marker not in captured["msg"]


class TestBatchConfirmSummaryCostOpenAI:
    """V190-OAI-06: バッチ側 _confirm_summary_cost の openai ケース。"""

    def test_confirm_summary_cost_openai_shows_host(self, monkeypatch):
        from pagefolio.constants import LANG

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings={"ocr_provider": "openai"}),
            _L=LANG["ja"],
        )
        stub._confirm_summary_cost = lambda cc, settings=None: (
            batch_ocr.BatchOCRDialog._confirm_summary_cost(stub, cc, settings)
        )
        captured = {}
        monkeypatch.setattr(
            batch_ocr.messagebox,
            "askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_summary_cost(500)
        assert "api.openai.com" in captured["msg"]


class TestBatchCheckCloudApiKeyOpenAI:
    """V190-OAI-06: バッチ側 _check_cloud_api_key の openai ケース。"""

    def _stub(self, session_keys=None):
        from pagefolio.constants import LANG

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(
                settings={"ocr_provider": "openai"},
                _session_api_keys=dict(session_keys or {}),
            ),
            provider=None,
            _L=LANG["ja"],
        )
        stub._is_cloud_provider = lambda settings=None: (
            batch_ocr.BatchOCRDialog._is_cloud_provider(stub, settings)
        )
        stub._check_cloud_api_key = lambda settings=None: (
            batch_ocr.BatchOCRDialog._check_cloud_api_key(stub, settings)
        )
        return stub

    def test_missing_key_shows_error(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub = self._stub()
        captured = {}

        def mock_showerror(title, msg, parent=None):
            captured["msg"] = msg

        monkeypatch.setattr(batch_ocr.messagebox, "showerror", mock_showerror)
        assert stub._check_cloud_api_key() is False
        assert "OPENAI_API_KEY" in captured["msg"]

    def test_session_key_resolves(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub = self._stub(session_keys={"openai": "dummy-test-key"})
        called = []
        monkeypatch.setattr(
            batch_ocr.messagebox,
            "showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is True
        assert called == []


class TestSingleVsBatchHostParity:
    """単発 OCR とバッチ OCR で同一 settings に対する _confirm_cost の
    送信先ホスト行が一致することを固定する（独立実装の挙動一致・レビュー
    LOW-10 対応）。
    """

    def test_openai_host_matches_between_dialogs(self, monkeypatch):
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        settings = {"ocr_provider": "openai"}

        single_stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            page_indices=[0],
            _L=LANG["ja"],
        )
        single_stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(
            single_stub, m, c
        )
        single_stub._confirm_cost = lambda: OCRDialog._confirm_cost(single_stub)

        batch_stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            _entries=[],
            _L=LANG["ja"],
        )
        batch_stub._estimate_cost = lambda m, c: (
            batch_ocr.BatchOCRDialog._estimate_cost(batch_stub, m, c)
        )
        batch_stub._confirm_cost = lambda page_count=None, settings=None: (
            batch_ocr.BatchOCRDialog._confirm_cost(batch_stub, page_count, settings)
        )

        captured = {}

        def _capture_single(title, msg, parent=None):
            captured["single"] = msg
            return True

        def _capture_batch(title, msg, parent=None):
            captured["batch"] = msg
            return True

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.askyesno", _capture_single)
        single_stub._confirm_cost()

        monkeypatch.setattr(batch_ocr.messagebox, "askyesno", _capture_batch)
        batch_stub._confirm_cost(page_count=1)

        single_host_line = captured["single"].splitlines()[0]
        batch_host_line = captured["batch"].splitlines()[0]
        assert single_host_line == batch_host_line == "送信先: api.openai.com"


class TestBatchConfirmDenialStopsSend:
    """レビュー 02-02 Suggestion 3（バッチ版）: 集約コスト確認で「いいえ」を
    選んだとき _build_provider_once に到達しないことを固定する。
    """

    def test_openai_denial_never_reaches_build_provider_once(self, monkeypatch):
        from pagefolio.batch_ocr_state import STATUS_PENDING
        from pagefolio.constants import LANG

        class _Entry:
            def __init__(self):
                self.status = STATUS_PENDING
                self.page_count = 2

        monkeypatch.setattr(batch_ocr.messagebox, "askyesno", lambda *a, **kw: False)

        build_calls = []
        fake = types.SimpleNamespace(
            app=types.SimpleNamespace(
                settings={"ocr_provider": "openai"}, _session_api_keys={}
            ),
            provider=None,
            _running=False,
            _entries=[_Entry()],
            _batch_state=None,
            _batch_cancel_flag=None,
            _file_cancel_flag=None,
            _L=LANG["ja"],
        )
        fake._check_cloud_api_key = lambda: True
        fake._is_cloud_provider = lambda settings=None: (
            batch_ocr.BatchOCRDialog._is_cloud_provider(fake, settings)
        )
        fake._estimate_cost = lambda m, c: batch_ocr.BatchOCRDialog._estimate_cost(
            fake, m, c
        )
        fake._confirm_cost = lambda page_count=None, settings=None: (
            batch_ocr.BatchOCRDialog._confirm_cost(fake, page_count, settings)
        )
        fake._confirm_batch_cost = lambda: batch_ocr.BatchOCRDialog._confirm_batch_cost(
            fake
        )
        fake._build_provider_once = lambda: build_calls.append(True)
        fake._set_running_ui = lambda running: None
        fake._update_overall_progress = lambda: None
        fake._advance_to_next_file = lambda: None

        batch_ocr.BatchOCRDialog._on_start_batch(fake)

        assert build_calls == [], "拒否後に _build_provider_once が呼ばれた"
