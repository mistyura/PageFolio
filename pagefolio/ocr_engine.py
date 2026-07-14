# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR 実行エンジン — producer-consumer の consumer 駆動部（Tkinter / fitz 非依存）。

`pagefolio/ocr_pipeline.py`（`PipelineState`/`consume_one`/`try_enqueue`/
`send_sentinels`）と対になる、consumer 駆動の軽量クラス（`PipelineState` と
同格の設計であり、完全な純関数ではない）。`pagination.py`/`ocr_pipeline.py`/
`undo_store.py` と同じ「Tk/fitz 非依存の純ロジック層」系譜に連なる新設モジュール
（03-CONTEXT.md D-01〜D-16・V180-REFAC-03）。

producer（fitz レンダリング連鎖・`OCRDialog._render_next_page` 相当）は本
クラスに内包しない（D-01）。`OCRRunEngine` は consumer 側（キュー + ワーカー
+ `PipelineState` + 完了理由別コールバック）のみを提供し、単一ファイル OCR
とバッチ OCR（Phase 4）の双方から新規生成して再利用できる構造にする。

トップレベル import は `threading`/`queue`/`logging` と
`pagefolio.ocr_pipeline` のみに限定し、`tkinter`・`fitz`(PyMuPDF) をモジュール
レベルで import しない（D-01/D-02・落とし穴10 回避）。`pagefolio.ocr`/
`pagefolio.ocr_providers` への依存が必要になった場合は `ocr_pipeline.py` と
同じく関数内 import で循環 import を回避すること。

キュー/`PipelineState` の同一性（落とし穴10・T-03-02）: `start()` 内で
`queue.Queue`/`PipelineState` を**一度だけ**生成し、`self.queue` プロパティで
公開する。producer 側（呼び出し元）はこの単一インスタンスのみを参照すること
（二重生成すると排他制御が壊れる）。
"""

import logging
import queue
import threading

from pagefolio.ocr_pipeline import (
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    PipelineState,
    consume_one,
)

logger = logging.getLogger(__name__)


class OCRRunEngine:
    """producer-consumer の consumer 側を所有する軽量クラス。

    D-02: コンストラクタは最小限の値渡し（`provider`/`prompt`/`run_pages`/
    `concurrency`/`cancel_flag` + 個別コールバック群）に限定する。設定 dict
    や API キー文字列は受け取らない（構築済み `provider` インスタンスのみ・
    T-03-01 情報漏洩防止）。

    D-09: `results`/`errors`/`truncated_pages`/`skipped_pages`/
    `render_failed_pages` は本クラスが内部状態として所有する。D-11 により
    実行（run/rerun/resume）ごとに新規生成されるため、per-run のベースライン
    差分計算（`_skip_base`/`_render_failed_base` 相当）は構造的に不要
    （D-12 を new-instance で満たす）。

    D-05/D-06/D-08: 通知はコールバック注入方式。`on_success`/`on_page_error`/
    `on_retry_wait` は `ocr_pipeline.consume_one` の既存シグネチャをそのまま
    踏襲する。完了理由（complete/cancelled/fatal）は理由別の個別コールバック
    で伝える（単一の `on_finished` は不採用）。
    """

    def __init__(
        self,
        provider,
        prompt,
        run_pages,
        concurrency,
        cancel_flag,
        on_success=None,
        on_page_error=None,
        on_retry_wait=None,
        on_progress=None,
        on_complete=None,
        on_cancelled=None,
        on_fatal=None,
        breaker_threshold=DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    ):
        """provider: OCRProvider インスタンス（構築済み・生設定/APIキーは渡さない）。
        prompt: OCR 指示テキスト。run_pages: 今回実行分の page_idx リスト
        （D-10: どのページを再実行するかは呼び出し側が確定済みで渡す。
        Engine は前回実行の履歴を一切知らない）。concurrency: consumer
        ワーカー本数。cancel_flag: threading.Event。
        breaker_threshold: サーキットブレーカー閾値（呼び出し元の定数を渡す。
        既定は ocr_pipeline.DEFAULT_CIRCUIT_BREAKER_THRESHOLD）。
        """
        self.provider = provider
        self.prompt = prompt
        self.run_pages = list(run_pages)
        self.concurrency = max(1, int(concurrency))
        self.cancel_flag = cancel_flag
        self._on_success = on_success
        self._on_page_error = on_page_error
        self._on_retry_wait = on_retry_wait
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_cancelled = on_cancelled
        self._on_fatal = on_fatal
        self._breaker_threshold = breaker_threshold

        # D-09: per-run 内部状態（実行ごとに新規生成される Engine が所有）。
        self.results = {}
        self.errors = {}
        self.truncated_pages = set()
        self.skipped_pages = set()
        self.render_failed_pages = set()

        # 落とし穴10（Pitfall 1）対策: queue/PipelineState は start() で
        # 一度だけ生成する。producer は self.queue プロパティ経由でのみ
        # 同一インスタンスを参照する。
        self.queue = None
        self._pstate = None
        self._worker_threads = []

    def start(self):
        """queue.Queue/PipelineState を一度だけ生成し、concurrency 本の
        consumer デーモンスレッドを起動する（即座に返る・ブロッキングしない）。

        戻り値: 起動したワーカースレッドのリスト（テストの join 用）。
        """
        self.queue = queue.Queue(maxsize=self.concurrency + 1)
        self._pstate = PipelineState(self.concurrency)
        self._worker_threads = []
        for _ in range(self.concurrency):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._worker_threads.append(t)
        return self._worker_threads

    def note_skip(self, page_idx):
        """producer 側（埋め込みテキスト検出）からのスキップ通知（D-07/D-12）。"""
        self.skipped_pages.add(page_idx)

    def note_render_failed(self, page_idx):
        """producer 側（レンダー失敗）からの通知（D-07/D-12・L-6a）。"""
        self.render_failed_pages.add(page_idx)

    def progress_count(self):
        """統合進捗（done + skip + render_failed）を返す（D-07/D-12）。

        `OCRDialog._done_disp` 相当。D-11 により Engine は実行ごとに新規
        生成されるため、per-run のセットは常に空から始まり、ベースライン
        減算は不要。
        """
        done_count = self._pstate.done_count if self._pstate is not None else 0
        return done_count + len(self.skipped_pages) + len(self.render_failed_pages)

    def is_fatal(self):
        """PipelineState 経由の fatal 確定判定を公開する（producer 参照用）。"""
        return self._pstate is not None and self._pstate.is_fatal()

    @property
    def fatal_msg(self):
        """fatal 確定時のメッセージ（未確定または未 start() は None）。"""
        return self._pstate.fatal_msg if self._pstate is not None else None

    @property
    def fatal_kind(self):
        """fatal 確定時の種別（"connection"/"timeout"/"circuit_breaker"）。"""
        return self._pstate.fatal_kind if self._pstate is not None else None

    def _handle_success(self, page_idx, text, truncated):
        """consume_one の on_success ラッパー。内部状態更新後に外側へ転送する
        二段構成（D-09・結果辞書所有権）。
        """
        self.results[page_idx] = text
        if truncated:
            self.truncated_pages.add(page_idx)
        else:
            self.truncated_pages.discard(page_idx)
        if self._on_success is not None:
            self._on_success(page_idx, text, truncated)

    def _handle_page_error(self, page_idx, msg):
        """consume_one の on_page_error ラッパー（D-09・二段構成）。"""
        self.errors[page_idx] = msg
        if self._on_page_error is not None:
            self._on_page_error(page_idx, msg)

    def _handle_retry_wait(self, page_idx, attempt, delay, exc):
        """consume_one の on_retry_wait ラッパー。Engine 側では加工せず、
        そのまま外側コールバックへ転送する（メッセージ生成は Tk/lang 依存の
        ため呼び出し側の責務）。
        """
        if self._on_retry_wait is not None:
            self._on_retry_wait(page_idx, attempt, delay, exc)

    def _worker_loop(self):
        """consumer スレッド本体（pagefolio/ocr_dialog.py:1709-1786 の移植元）。

        `self.queue.get(timeout=1.0)` → queue.Empty 時は cancel_flag で
        break/continue → None で完了シグナル break → consume_one へ委譲。
        b64 は finally で del する（成功基準2・T-06-06）。
        """
        while True:
            try:
                item = self.queue.get(timeout=1.0)
            except queue.Empty:
                if self.cancel_flag.is_set():
                    break
                continue

            if item is None:
                break  # 完了シグナル

            page_idx, b64 = item
            try:
                consume_one(
                    self.provider,
                    item,
                    self.prompt,
                    self._pstate,
                    cancel_check=self.cancel_flag.is_set,
                    breaker_threshold=self._breaker_threshold,
                    on_success=self._handle_success,
                    on_page_error=self._handle_page_error,
                    on_retry_wait=self._handle_retry_wait,
                )
                if self._on_progress is not None:
                    self._on_progress(self.progress_count(), page_idx)
            except Exception:
                # WR-01: consume_one 自体はプロバイダ例外を握るが、
                # on_success/on_page_error/on_progress コールバックが
                # 送出する例外までは吸収しない。ここで捕捉しないと
                # decrement_worker() に到達できず、ワーカーが完了理由
                # コールバック（on_complete/on_cancelled/on_fatal）を
                # 永久に発火させられなくなる。
                logger.exception(
                    "OCR ワーカーのコールバック処理中に予期しない例外 (p.%d)",
                    page_idx,
                )
            finally:
                del b64  # 送信後即座に破棄（成功基準2・T-06-06）

        # CR-01: 残ワーカー数を減らし、最終ワーカーのみ完了理由別コールバックを呼ぶ。
        is_last, fatal_msg, fatal_kind = self._pstate.decrement_worker()
        if not is_last:
            return  # 最終ワーカー以外は何もしない

        if fatal_msg is not None:
            if self._on_fatal is not None:
                self._on_fatal(fatal_msg, fatal_kind)
        elif self.cancel_flag.is_set():
            if self._on_cancelled is not None:
                self._on_cancelled()
        else:
            if self._on_complete is not None:
                self._on_complete()
