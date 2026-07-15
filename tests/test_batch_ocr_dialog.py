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
