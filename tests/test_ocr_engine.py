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


# ===== E2E モックテスト（OCRRunEngine 自体を実スレッド駆動で起動して検証・D-13）=====
#
# tests/test_ocr_pipeline.py の _drive_pipeline（テスト専用の producer+consumer
# 全自作ドライバ）とは異なり、consumer 側は OCRRunEngine.start() 自身に担わせ、
# テストコードは producer スタブ（engine.queue へ try_enqueue → send_sentinels）
# のみを提供する（03-PATTERNS.md 明記の転用方針）。


def _drive_engine(engine, pages, b64_for, timeout=5.0):
    """E2E 用の薄い producer スタブ + 終端シグナル送出ヘルパー（D-13）。

    engine.start() 済みの Engine に対し、テスト専用スレッドで pages を順に
    try_enqueue し、最後に concurrency 本ぶんの終端シグナルを送り切る
    （_send_all_sentinels・部分送出対応）。producer 側のスレッドモデルは
    本ヘルパーが規定するのみで、consumer（ワーカー）側のコードパスは
    OCRRunEngine 自身に検証させる（テスト専用ドライバの自作ではなく Engine の
    コードパスを高忠実度で通す・D-13）。

    戻り値: 起動した producer スレッド（呼び出し側で timeout=5.0 で join する）。
    """

    def _produce():
        deadline = time.monotonic() + timeout
        for page_idx in pages:
            item = (page_idx, b64_for(page_idx))
            while not try_enqueue(engine.queue, item):
                if time.monotonic() > deadline:
                    return
                time.sleep(0.01)
        _send_all_sentinels(engine.queue, engine.concurrency, timeout=timeout)

    t = threading.Thread(target=_produce, daemon=True)
    t.start()
    return t


class TestOCRRunEngineE2E:
    """OCRRunEngine を実スレッド駆動（threading.Thread + queue.Queue）で起動する
    E2E モックテスト群（実 API 非依存・FakeProvider のみ使用・D-13/D-14/D-15）。
    """

    def test_all_pages_success(self):
        """複数ページ成功で全ページの on_success が呼ばれ、engine.results に
        全件格納され engine.errors は空、on_complete がちょうど1回呼ばれる
        （V180-QA-01・正常系）。
        """
        provider = FakeProvider()
        cancel_flag = threading.Event()
        successes = []
        complete_calls = []
        pages = [0, 1, 2, 3, 4]
        engine = OCRRunEngine(
            provider=provider,
            prompt="prompt",
            run_pages=pages,
            concurrency=2,
            cancel_flag=cancel_flag,
            on_success=lambda p, t, tr: successes.append(p),
            on_complete=lambda: complete_calls.append(1),
        )
        threads = engine.start()
        producer_thread = _drive_engine(engine, pages, lambda i: f"b64-{i}")

        for t in threads:
            t.join(timeout=10.0)
        producer_thread.join(timeout=5.0)
        for t in threads:
            assert not t.is_alive(), "ワーカースレッドが timeout 内に終了しなかった"

        assert set(successes) == set(pages)
        assert engine.errors == {}
        assert set(engine.results.keys()) == set(pages)
        for i in pages:
            assert engine.results[i] == f"text-b64-{i}"
        assert len(complete_calls) == 1

    def test_partial_page_errors(self):
        """特定ページのみ非リトライ由来のページエラーになっても取りこぼしなく
        成功/エラーへ振り分けられ、on_complete で完了する
        （V180-QA-01・異常系・ページエラー混在）。
        """
        fail_pages = {2}

        def side_effect(b64, prompt):
            if b64 == "b64-2":
                raise RuntimeError("ページ処理失敗（テスト用）")
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        cancel_flag = threading.Event()
        complete_calls = []
        pages = list(range(5))
        engine = OCRRunEngine(
            provider=provider,
            prompt="prompt",
            run_pages=pages,
            concurrency=2,
            cancel_flag=cancel_flag,
            on_complete=lambda: complete_calls.append(1),
        )
        threads = engine.start()
        producer_thread = _drive_engine(engine, pages, lambda i: f"b64-{i}")

        for t in threads:
            t.join(timeout=10.0)
        producer_thread.join(timeout=5.0)
        for t in threads:
            assert not t.is_alive(), "ワーカースレッドが timeout 内に終了しなかった"

        assert set(engine.errors.keys()) == fail_pages
        assert set(engine.results.keys()) == set(pages) - fail_pages
        # 取りこぼしなし: 全ページが success か error のいずれかで説明できる
        accounted = set(engine.results.keys()) | set(engine.errors.keys())
        assert accounted == set(pages)
        assert len(complete_calls) == 1

    def test_cancel_stops_processing(self):
        """cancel_flag セット後、有限時間内にキャンセルが反映され残ページの
        ocr_image 呼び出しが行われず on_cancelled 経由で終了する
        （V180-QA-01・キャンセル）。
        """
        call_count = [0]
        lock = threading.Lock()
        cancel_flag = threading.Event()
        cancel_after = 3  # この呼び出し回数に達したらキャンセルを発火

        def side_effect(b64, prompt):
            with lock:
                call_count[0] += 1
                n = call_count[0]
            time.sleep(0.01)
            if n >= cancel_after:
                cancel_flag.set()
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        cancelled_calls = []
        pages = list(range(20))
        engine = OCRRunEngine(
            provider=provider,
            prompt="prompt",
            run_pages=pages,
            concurrency=1,
            cancel_flag=cancel_flag,
            on_cancelled=lambda: cancelled_calls.append(1),
        )
        threads = engine.start()
        producer_thread = _drive_engine(engine, pages, lambda i: f"b64-{i}")

        for t in threads:
            t.join(timeout=10.0)
        producer_thread.join(timeout=5.0)
        for t in threads:
            assert not t.is_alive(), "ワーカースレッドが timeout 内に終了しなかった"

        # キャンセル後は残ページ分の呼び出しが行われず全ページ数未満で収まる
        assert call_count[0] < len(pages)
        assert len(cancelled_calls) == 1
