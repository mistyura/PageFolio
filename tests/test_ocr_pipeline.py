"""pagefolio.ocr_pipeline のユニットテスト（Tk/fitz 非依存純ロジック層）。

TestProducerConsumerMemory の3件は tests/test_ocr.py の
run_with_bounded_buffer 由来テストを新 API（PipelineState/consume_one/
try_enqueue/send_sentinels）へ書き換えて移設したもの（02-04 Task 1・D-02）。
"""

import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagefolio.ocr import MAX_RETRIES  # noqa: E402
from pagefolio.ocr_pipeline import (  # noqa: E402
    PipelineState,
    consume_one,
    send_sentinels,
    try_enqueue,
)
from pagefolio.ocr_providers import OCRProvider, OCRRetryableError  # noqa: E402

# ===== テスト用ダブル（tests/test_ocr.py の FakeProvider と同型） =====


class FakeProvider(OCRProvider):
    """consume_one テスト用の偽 Provider。ocr_image は b64 をもとにテキストを返す。"""

    default_concurrency = 2
    max_concurrency = 4

    def __init__(self, side_effect=None):
        """side_effect が None なら f"text-{b64}" を返す。callable なら呼び出す。"""
        self._side_effect = side_effect

    def ocr_image(self, b64_png, prompt, **kwargs):
        if self._side_effect is not None:
            return self._side_effect(b64_png, prompt)
        return f"text-{b64_png}"

    def list_models(self):
        return ["fake-model"]


# ===== PipelineState 単体テスト =====


class TestPipelineState:
    def test_record_success_resets_consec_err_and_increments_done(self):
        state = PipelineState(workers=2)
        state.record_retryable_failure("e1", breaker_threshold=5)
        assert state.consec_err_count == 1
        state.record_success()
        assert state.consec_err_count == 0
        assert state.done_count == 2

    def test_record_retryable_failure_hits_breaker_after_threshold(self):
        state = PipelineState(workers=1)
        assert state.record_retryable_failure("e1", breaker_threshold=2) is False
        assert state.is_fatal() is False
        assert state.record_retryable_failure("e2", breaker_threshold=2) is True
        assert state.is_fatal() is True
        assert state.fatal_kind == "circuit_breaker"
        assert state.fatal_msg == "e2"

    def test_record_fatal_first_wins(self):
        state = PipelineState(workers=1)
        state.record_fatal("first", "connection")
        state.record_fatal("second", "timeout")
        assert state.fatal_msg == "first"
        assert state.fatal_kind == "connection"
        assert state.done_count == 2

    def test_record_page_error_increments_done_only(self):
        state = PipelineState(workers=1)
        state.record_page_error("oops")
        assert state.done_count == 1
        assert state.is_fatal() is False

    def test_decrement_worker_returns_is_last_on_final_call(self):
        state = PipelineState(workers=2)
        is_last, msg, kind = state.decrement_worker()
        assert is_last is False
        is_last, msg, kind = state.decrement_worker()
        assert is_last is True
        assert msg is None
        assert kind is None


# ===== enqueue / sentinel ヘルパー =====


class TestEnqueueHelpers:
    def test_try_enqueue_success_then_full(self):
        q = queue.Queue(maxsize=1)
        assert try_enqueue(q, "a") is True
        assert try_enqueue(q, "b") is False  # キュー満杯

    def test_send_sentinels_partial_when_full(self):
        q = queue.Queue(maxsize=2)
        q.put_nowait("occupied")  # 1 スロットを占有
        sent = send_sentinels(q, 3)
        assert sent == 1  # 残り1スロット分のみ送れる（部分送出・L-6h）
        remaining = []
        while not q.empty():
            remaining.append(q.get_nowait())
        assert remaining == ["occupied", None]

    def test_send_sentinels_full_count_when_capacity_available(self):
        q = queue.Queue(maxsize=5)
        sent = send_sentinels(q, 3)
        assert sent == 3


# ===== consume_one 単体テスト =====


class TestConsumeOne:
    def test_consume_one_success_calls_on_success(self):
        provider = FakeProvider()
        state = PipelineState(workers=1)
        successes = []
        consume_one(
            provider,
            (3, "b64data"),
            "prompt",
            state,
            on_success=lambda p, t, tr: successes.append((p, t, tr)),
        )
        assert successes == [(3, "text-b64data", False)]
        assert state.done_count == 1
        assert state.consec_err_count == 0

    def test_consume_one_retryable_exhausted_calls_on_page_error(self):
        call_count = [0]

        def side_effect(b64, prompt):
            call_count[0] += 1
            raise OCRRetryableError("rate limited", retry_after=0.0, code=429)

        provider = FakeProvider(side_effect=side_effect)
        state = PipelineState(workers=1)
        page_errors = {}
        consume_one(
            provider,
            (0, "b64"),
            "prompt",
            state,
            on_page_error=lambda p, m: page_errors.__setitem__(p, m),
        )
        assert 0 in page_errors
        assert call_count[0] == MAX_RETRIES
        assert state.done_count == 1

    def test_consume_one_connection_error_sets_fatal(self):
        def side_effect(b64, prompt):
            raise ConnectionError("boom")

        provider = FakeProvider(side_effect=side_effect)
        state = PipelineState(workers=1)
        fatal_calls = []
        consume_one(
            provider,
            (0, "b64"),
            "prompt",
            state,
            on_fatal=lambda p, m, k: fatal_calls.append((p, m, k)),
        )
        assert state.is_fatal() is True
        assert state.fatal_kind == "connection"
        assert fatal_calls == [(0, "boom", "connection")]

    def test_consume_one_skips_when_already_fatal(self):
        call_count = [0]

        def side_effect(b64, prompt):
            call_count[0] += 1
            return "text"

        provider = FakeProvider(side_effect=side_effect)
        state = PipelineState(workers=1)
        state.record_fatal("prior fatal", "connection")

        success_calls = []
        consume_one(
            provider,
            (0, "b64"),
            "prompt",
            state,
            on_success=lambda *a: success_calls.append(a),
        )
        assert call_count[0] == 0  # API 呼び出し自体がスキップされた
        assert success_calls == []
        # record_fatal 分の done_count のみ（consume_one はここで増やさない）
        assert state.done_count == 1


# ===== producer-consumer 駆動ヘルパー（テスト専用・本番コードには持ち込まない） =====
#
# 本番の producer はメインスレッド after() 連鎖（ocr_dialog.py）だが、
# ここでは try_enqueue/send_sentinels/consume_one の組み合わせをスレッド駆動で
# 検証するため、テスト専用の薄いドライバを構築する（Pitfall 1: 本番モジュール
# 側には専用 producer スレッドを持ち込まない）。


def _drive_pipeline(
    provider, render_fn, page_indices, concurrency, prompt="", is_cancelled=None
):
    workers = max(1, min(provider.max_concurrency, int(concurrency)))
    maxsize = max(1, workers + 1)
    buf = queue.Queue(maxsize=maxsize)
    state = PipelineState(workers)
    results = {}
    errors = {}
    render_failed = set()

    def _is_cancelled():
        return bool(is_cancelled and is_cancelled())

    def _producer():
        try:
            for page_idx in page_indices:
                if _is_cancelled():
                    return
                try:
                    b64 = render_fn(page_idx)
                except Exception as e:
                    errors[page_idx] = f"render error: {e}"
                    render_failed.add(page_idx)
                    continue
                if b64 is None:
                    continue
                while not try_enqueue(buf, (page_idx, b64)):
                    if _is_cancelled():
                        return
                    time.sleep(0.01)
        finally:
            sent = 0
            while sent < workers:
                got = send_sentinels(buf, workers - sent)
                sent += got
                if sent < workers:
                    time.sleep(0.01)

    def _consumer():
        while True:
            try:
                item = buf.get(timeout=1.0)
            except queue.Empty:
                if _is_cancelled():
                    break
                continue
            if item is None:
                break
            consume_one(
                provider,
                item,
                prompt,
                state,
                cancel_check=_is_cancelled,
                on_success=lambda p, t, tr: results.__setitem__(p, t),
                on_page_error=lambda p, m: errors.__setitem__(p, m),
                on_fatal=lambda p, m, k: errors.__setitem__(p, m),
            )

    producer_thread = threading.Thread(target=_producer, daemon=True)
    producer_thread.start()
    consumer_threads = [
        threading.Thread(target=_consumer, daemon=True) for _ in range(workers)
    ]
    for t in consumer_threads:
        t.start()
    for t in consumer_threads:
        t.join(timeout=10.0)
    producer_thread.join(timeout=5.0)

    return results, errors, state, render_failed


# ===== producer-consumer メモリ非蓄積リグレッション（D-13・成功基準2・移設元）=====


class TestProducerConsumerMemory:
    """同時保持画像数がバッファ上限（concurrency+1）を超えないことを検証する。

    FakeProvider の ocr_image 呼び出し時点で in-flight な b64 の数が
    concurrency + 1（バッファ上限）を超えないことを threading.Lock で計測する。
    """

    def test_in_flight_count_never_exceeds_maxsize(self):
        """同時保持画像数が concurrency+1 以内に収まること（T-06-06・成功基準2）"""
        in_flight_count = [0]
        max_observed = [0]
        lock = threading.Lock()
        concurrency = 2

        def counting_side_effect(b64, prompt):
            with lock:
                in_flight_count[0] += 1
                max_observed[0] = max(max_observed[0], in_flight_count[0])
            time.sleep(0.01)  # API 処理時間を模擬
            with lock:
                in_flight_count[0] -= 1
            return f"text-{b64}"

        provider = FakeProvider(side_effect=counting_side_effect)
        provider.default_concurrency = concurrency
        provider.max_concurrency = concurrency

        page_indices = list(range(20))  # 20 ページ（100 ページの代替）
        results, errors, state, render_failed = _drive_pipeline(
            provider,
            render_fn=lambda i: f"b64-page-{i}",
            page_indices=page_indices,
            concurrency=concurrency,
        )
        expected_maxsize = concurrency + 1
        assert max_observed[0] <= expected_maxsize, (
            f"同時保持数 {max_observed[0]} がバッファ上限 {expected_maxsize} を超えた"
        )
        assert len(results) == len(page_indices), (
            f"結果取りこぼし: {len(results)} / {len(page_indices)} ページ"
        )
        assert state.is_fatal() is False

    def test_all_results_collected_no_missing(self):
        """全ページの結果が results に揃い取りこぼしがないこと"""
        provider = FakeProvider()
        page_indices = list(range(20))
        results, errors, state, render_failed = _drive_pipeline(
            provider,
            render_fn=lambda i: f"b64-{i}",
            page_indices=page_indices,
            concurrency=2,
        )
        assert len(results) == len(page_indices)
        for i in page_indices:
            assert i in results, f"ページ {i} の結果が欠落"

    def test_cancel_terminates_without_deadlock(self):
        """is_cancelled が途中で True になると残ページを処理せず有限時間で終了する。

        デッドロックしないことをタイムアウトなし（pytest のデフォルト）で検証する。
        """
        call_count = [0]
        cancel_after = 5  # 5 回呼び出し後にキャンセル

        def side_effect(b64, prompt):
            with threading.Lock():
                call_count[0] += 1
            time.sleep(0.01)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        cancel_event = threading.Event()

        def is_cancelled():
            if call_count[0] >= cancel_after:
                cancel_event.set()
            return cancel_event.is_set()

        page_indices = list(range(50))
        results, errors, state, render_failed = _drive_pipeline(
            provider,
            render_fn=lambda i: f"b64-{i}",
            page_indices=page_indices,
            concurrency=1,
            is_cancelled=is_cancelled,
        )
        # キャンセル後は全ページは処理されない
        assert len(results) < len(page_indices), (
            "キャンセル後も全ページが処理されている（キャンセルが効いていない）"
        )


# ===== 拡充ケース（D-02・02-04 Task 1 新規）=====


class TestPipelineHardening:
    def test_render_failure_progress(self):
        """レンダー失敗ページも errors に計上され成功+エラーで全ページに到達（L-6a）。

        パイプライン層としては「render 失敗ページが取りこぼされず必ず
        results/errors のどちらかで説明できる」ことを担保する。ダイアログ側の
        実際のプログレスバー更新（Tk 依存）は 02-04 Task 2 の担当。
        """
        provider = FakeProvider()
        page_indices = list(range(10))
        fail_pages = {2, 5, 8}

        def render_fn(i):
            if i in fail_pages:
                raise RuntimeError(f"render boom {i}")
            return f"b64-{i}"

        results, errors, state, render_failed = _drive_pipeline(
            provider,
            render_fn=render_fn,
            page_indices=page_indices,
            concurrency=2,
        )
        assert render_failed == fail_pages
        for i in fail_pages:
            assert i in errors
        # 取りこぼしなし: 全ページが success か render-error のいずれかで説明できる
        accounted = set(results.keys()) | set(errors.keys())
        assert accounted == set(page_indices)

    def test_cancel_finite_time_no_deadlock(self):
        """キャンセルで有限時間内に終了しデッドロックしない（明示的な経過時間アサート）。"""
        cancel_event = threading.Event()

        def side_effect(b64, prompt):
            time.sleep(0.01)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)

        def is_cancelled():
            return cancel_event.is_set()

        def canceller():
            time.sleep(0.05)
            cancel_event.set()

        canceller_thread = threading.Thread(target=canceller, daemon=True)
        canceller_thread.start()

        started = time.monotonic()
        page_indices = list(range(200))
        results, errors, state, render_failed = _drive_pipeline(
            provider,
            render_fn=lambda i: f"b64-{i}",
            page_indices=page_indices,
            concurrency=2,
            is_cancelled=is_cancelled,
        )
        elapsed = time.monotonic() - started
        assert elapsed < 5.0, "有限時間で終了せずデッドロックの疑いがある"
        assert len(results) < len(page_indices)
