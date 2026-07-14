"""pagefolio.ocr_engine のユニットテスト（OCRRunEngine・consumer 駆動の軽量クラス）。

TestOCRRunEngineUnit は Task 1（03-01-PLAN.md）の <behavior> で先に固定した
RED テスト群を GREEN化したもの。producer 側は実際の fitz レンダリングを
持たないため、テストコード側に薄い producer スタブ（try_enqueue/
send_sentinels 呼び出しのみ）を置く（03-RESEARCH.md 明記の転用方針）。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading  # noqa: E402
import time  # noqa: E402

from pagefolio.ocr_engine import OCRRunEngine  # noqa: E402
from pagefolio.ocr_pipeline import send_sentinels, try_enqueue  # noqa: E402
from pagefolio.ocr_providers import OCRProvider  # noqa: E402


def _send_all_sentinels(q, count, timeout=5.0):
    """count 本の終端シグナルを送り切るまで再試行する（部分送出対応・L-6h）。

    キュー満杯（queue.Full）で部分送出になった場合、consumer がアイテムを
    消費して空きができるまで待って残数のみを再送する
    （pagefolio/ocr_dialog.py の _retry_sentinels と同型のテストヘルパー）。
    """
    sent = 0
    deadline = time.monotonic() + timeout
    while sent < count and time.monotonic() < deadline:
        sent += send_sentinels(q, count - sent)
        if sent < count:
            time.sleep(0.01)
    return sent


# tests/test_ocr_pipeline.py の FakeProvider（pipeline 純ロジック層向け）とは
# 意図的に複製・拡張したフェイク実装である（カプセル化のため共有せず本ファイル
# に閉じる。D-14・REVIEW 提案対応）。


class FakeProvider(OCRProvider):
    """OCRRunEngine テスト用の偽 Provider。ocr_image は b64 をもとにテキストを返す。"""

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


class TestOCRRunEngineUnit:
    def test_engine_importable(self):
        """from pagefolio.ocr_engine import OCRRunEngine が成功する。"""
        from pagefolio.ocr_engine import OCRRunEngine as _Engine

        assert _Engine is not None

    def test_single_page_success_invokes_on_success(self):
        """単一ページ成功で on_success が1回呼ばれ engine.results に格納される。"""
        provider = FakeProvider()
        cancel_flag = threading.Event()
        successes = []
        engine = OCRRunEngine(
            provider=provider,
            prompt="prompt",
            run_pages=[0],
            concurrency=1,
            cancel_flag=cancel_flag,
            on_success=lambda p, t, tr: successes.append((p, t, tr)),
        )
        threads = engine.start()

        # テスト側の薄い producer スタブ: engine.queue へ直接 enqueue する。
        assert try_enqueue(engine.queue, (0, "b64-0")) is True
        assert send_sentinels(engine.queue, 1) == 1

        for t in threads:
            t.join(timeout=10.0)

        assert successes == [(0, "text-b64-0", False)]
        assert engine.results[0] == "text-b64-0"

    def test_queue_is_single_shared_instance(self):
        """start() 後の engine.queue が None でない同一 queue.Queue インスタンス
        であり、producer と consumer が同一オブジェクトを参照する
        （落とし穴10 の同一性検証・id() 一致で確認）。
        """
        provider = FakeProvider()
        cancel_flag = threading.Event()
        engine = OCRRunEngine(
            provider=provider,
            prompt="prompt",
            run_pages=[0],
            concurrency=1,
            cancel_flag=cancel_flag,
        )
        threads = engine.start()

        # producer 側が参照するキュー参照を取得
        producer_queue_ref = engine.queue
        assert producer_queue_ref is not None
        # id() 一致で同一インスタンスであることを確認（別々に生成されていない）
        assert id(producer_queue_ref) == id(engine.queue)

        assert try_enqueue(engine.queue, (0, "b64-0")) is True
        assert send_sentinels(engine.queue, 1) == 1

        for t in threads:
            t.join(timeout=10.0)

        # ワーカー完了後も同一インスタンスのまま（再生成されていない）
        assert producer_queue_ref is engine.queue

    def test_final_worker_calls_on_complete_once(self):
        """concurrency=2 で全ページ成功後、on_complete がちょうど1回だけ呼ばれる
        （decrement_worker の is_last 契約・CR-01）。
        """
        provider = FakeProvider()
        cancel_flag = threading.Event()
        complete_calls = []
        engine = OCRRunEngine(
            provider=provider,
            prompt="prompt",
            run_pages=[0, 1],
            concurrency=2,
            cancel_flag=cancel_flag,
            on_complete=lambda: complete_calls.append(1),
        )
        threads = engine.start()

        assert try_enqueue(engine.queue, (0, "b64-0")) is True
        assert try_enqueue(engine.queue, (1, "b64-1")) is True
        assert _send_all_sentinels(engine.queue, 2) == 2

        for t in threads:
            t.join(timeout=10.0)

        assert len(complete_calls) == 1
        assert engine.results == {0: "text-b64-0", 1: "text-b64-1"}
