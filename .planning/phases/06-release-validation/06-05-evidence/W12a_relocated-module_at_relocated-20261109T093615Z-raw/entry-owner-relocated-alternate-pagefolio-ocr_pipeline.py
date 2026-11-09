# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR 実行パイプライン純ロジック層 — Tkinter / fitz 非依存。

producer-consumer の共有状態管理・1 アイテム消費処理・非ブロッキングキュー
操作を Tk/fitz 非依存の純関数/軽量クラスへ集約する（02-CONTEXT.md D-01/D-02）。
`pagination.py` / `md_render.py` / `undo_store.py` と同格の「Tk/fitz 非依存の
純ロジック層」パターンに従う。

一本化の方向性（D-01・02-RESEARCH.md Pitfall 1）: `ocr_dialog.py` の実戦済み
挙動（非ブロッキング put・世代ガード・waiting 進捗・skip status・render 失敗
時の進捗計上）を仕様として本モジュールを設計する。逆方向（本モジュールの
理想仕様に dialog を合わせる）は取らない。

producer 側のスレッドモデルは本モジュールでは規定しない（V14-D-05:
`fitz.get_pixmap()` はメインスレッドのみのため、本番の producer は
`ocr_dialog.py` のメインスレッド `after()` 連鎖のまま）。本モジュールは
「キューへの安全な enqueue/sentinel 送出」のみを提供する薄いユーティリティに
留め、専用 producer スレッドを内部に持たない（Pitfall 1）。

sentinel（終了シグナル）の容量不変条件（L-6h）:
  終端シグナル（None）は consumer ワーカー数ぶん（合計 workers 本）送る。
  既に送信済みの本数は再送しない。バッファが満杯（queue.Full）の場合は
  送れた分だけ部分送出し、残りは呼び出し元が再試行する責務を持つ
  （`send_sentinels` の戻り値 = 実際に送れた本数）。

ここには `fitz` / `tkinter` を一切 import しない（pagination.py の純ロジック
層作法に倣う）。ネットワーク呼び出し関連（OCRRetryableError 判定・
clamp_retry_after/interruptible_sleep・MAX_RETRIES）は `consume_one` 内で
`pagefolio.ocr` / `pagefolio.ocr_providers` から関数内 import する（循環
import 回避のための既存作法・ocr_dialog.py:1479 付近に倣う）。
"""

import logging
import queue
import threading

logger = logging.getLogger(__name__)

# サーキットブレーカー既定閾値（ocr_dialog.py の CB_CONSECUTIVE_FAILURES と同値）。
# 呼び出し元が明示的に閾値を渡すのが基本だが、未指定時のフォールバックとして
# 定義する。
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 3


class PipelineState:
    """producer-consumer 実行中の共有状態（Tk/fitz 非依存・Lock 保護）。

    旧 `ocr_dialog.py` の `_done_lock`/`_done_count`/`_workers_remaining`/
    `_fatal_msg`/`_fatal_kind`/`_consec_err_count`（インスタンス属性群・
    02-RESEARCH.md Pattern 1）を Tk 非依存の 1 クラスへ集約したもの。
    全メソッドは内部 `threading.Lock` で保護され、複数の consumer ワーカー
    スレッドから安全に呼び出せる。
    """

    def __init__(self, workers):
        """workers: このパイプラインで起動する consumer ワーカー本数。"""
        self._lock = threading.Lock()
        self.done_count = 0
        self.consec_err_count = 0
        self.workers_remaining = workers
        self.fatal_msg = None
        self.fatal_kind = None

    def record_success(self):
        """ページ成功を記録し、連続失敗カウンタをリセットする。

        `_record_page_success`（ocr_dialog.py:670-671 の Tk 非依存部）と一致。
        """
        with self._lock:
            self.done_count += 1
            self.consec_err_count = 0

    def record_retryable_failure(
        self, msg, breaker_threshold=DEFAULT_CIRCUIT_BREAKER_THRESHOLD
    ):
        """リトライ上限到達（page エラー）を記録する。

        連続失敗数が breaker_threshold に達したら、最初の 1 回だけ
        fatal_msg/fatal_kind="circuit_breaker" を設定する
        （`_record_retryable_failure` ocr_dialog.py:695-703 と一致）。

        戻り値: 今回の呼び出しでサーキットブレーカーが発動したか（bool）。
        """
        with self._lock:
            self.done_count += 1
            self.consec_err_count += 1
            hit_breaker = self.consec_err_count >= breaker_threshold
            if hit_breaker and self.fatal_msg is None:
                self.fatal_msg = msg
                self.fatal_kind = "circuit_breaker"
            return hit_breaker

    def record_fatal(self, msg, kind):
        """致命的エラー（connection/timeout）を記録する。

        最初の 1 回だけ fatal_msg/fatal_kind を設定する（後続の同種エラーで
        既存の fatal 情報を上書きしない）。done_count は常にインクリメントする
        （ocr_dialog.py:1557-1570 の ConnectionError/TimeoutError 分岐と一致）。
        """
        with self._lock:
            if self.fatal_msg is None:
                self.fatal_msg = msg
                self.fatal_kind = kind
            self.done_count += 1

    def record_page_error(self, msg):
        """非致命的なページ単位のエラー（RuntimeError・その他 Exception）を記録する。

        msg 自体は呼び出し元がページ別 errors 辞書へ格納する想定であり、本
        メソッドは保持しない（Tk 非依存に留めるため errors 辞書はコールバック
        側の責務・ocr_dialog.py:1571-1581 の RuntimeError/Exception 分岐と一致）。
        """
        with self._lock:
            self.done_count += 1

    def is_fatal(self):
        """致命的エラーが確定済みかどうかを返す（consumer の API 呼び出し skip 判定）。

        戻り値: bool
        """
        with self._lock:
            return self.fatal_msg is not None

    def decrement_worker(self):
        """ワーカー終了を1本分減算し、(is_last, fatal_msg, fatal_kind) を返す。

        is_last=True のワーカーだけが終了処理（結果描画・完了通知）を呼ぶ契約
        （ocr_dialog.py:1604-1616 の CR-01 単一終了処理保証と同型）。
        """
        with self._lock:
            self.workers_remaining -= 1
            is_last = self.workers_remaining == 0
            return is_last, self.fatal_msg, self.fatal_kind


def try_enqueue(q, item):
    """item を q へ非ブロッキングで enqueue する。

    成功時 True・queue.Full 時 False を返す（例外を投げない）。「いつ再試行
    するか」（例: after(100) 再スケジュール）は呼び出し元の責務であり、本
    関数はレンダリング方法や再試行タイミングを一切規定しない
    （Pattern 2・Pitfall 1）。
    """
    try:
        q.put_nowait(item)
        return True
    except queue.Full:
        return False


def send_sentinels(q, count):
    """終端シグナル（None）を最大 count 個 q へ非ブロッキングで送出する。

    L-6h 容量不変条件: 実際に送れた本数のみを返す（部分送出可）。呼び出し元
    は戻り値が count 未満なら残り本数のみを再試行する責務を持つ（既に送信
    済みの本数を再送してはならない）。
    """
    sent = 0
    for _ in range(count):
        try:
            q.put_nowait(None)
            sent += 1
        except queue.Full:
            break
    return sent


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
    """キューから取り出した1アイテム (page_idx, b64) を消費する（Tk 非依存）。

    `ocr_dialog.py._worker`（旧 :1466-1528）のリトライ/fatal 分岐をそのまま
    移植したもの。`self.after()`/`self.text` 等の Tk 依存を一切含まない。

    引数:
      provider:          OCRProvider インスタンス（`ocr_image_ex` を呼ぶ）
      item:              (page_idx, b64_png) のタプル
      prompt:            OCR 指示テキスト
      state:             PipelineState インスタンス（共有カウンタ更新先）
      cancel_check:      () -> bool キャンセル判定（None なら常に False）
      breaker_threshold: サーキットブレーカー閾値（呼び出し元の定数を渡す）
      on_success(page_idx, text, truncated):
          成功時コールバック
      on_page_error(page_idx, msg):
          非致命的ページエラー時コールバック（リトライ上限到達・RuntimeError・
          その他 Exception を含む）
      on_fatal(page_idx, msg, kind):
          致命的エラー（connection/timeout）発生時コールバック
      on_retry_wait(page_idx, attempt, delay, exc):
          リトライ待機開始時コールバック（進捗表示用・呼び出し元が任意実装）

    戻り値: なし（結果は state の更新とコールバック経由でのみ伝達）。

    キャンセル済みまたは既に fatal 確定済みの場合は API 呼び出し自体を
    スキップし、state も更新しない（`ocr_dialog.py._worker` の `continue`
    分岐と同型・1512-1514 行）。
    """
    page_idx, b64 = item

    def _is_cancelled():
        return bool(cancel_check and cancel_check())

    if _is_cancelled() or state.is_fatal():
        return

    # 循環 import 回避のための関数内 import（ocr_dialog.py:1479 付近の既存作法）。
    # MAX_RETRIES は ocr.py を真の情報源として都度参照する（重複定義しない）。
    from pagefolio.ocr import MAX_RETRIES, clamp_retry_after, interruptible_sleep
    from pagefolio.ocr_providers import OCRRetryableError

    for attempt in range(1, MAX_RETRIES + 1):
        # WR-02: リトライ待機直後の再開時にもキャンセル/fatal を再確認し、
        # Cancel 後に追加の課金対象 API 呼び出しが発生しないようにする。
        if _is_cancelled() or state.is_fatal():
            return
        try:
            text, truncated = provider.ocr_image_ex(b64, prompt)
            state.record_success()
            if on_success is not None:
                on_success(page_idx, text, truncated)
            return
        except OCRRetryableError as e:
            if attempt >= MAX_RETRIES:
                state.record_retryable_failure(str(e), breaker_threshold)
                if on_page_error is not None:
                    on_page_error(page_idx, str(e))
                return
            raw_delay = (
                e.retry_after
                if e.retry_after is not None
                else 1.0 * (2 ** (attempt - 1))
            )
            delay = clamp_retry_after(raw_delay)
            if on_retry_wait is not None:
                on_retry_wait(page_idx, attempt, delay, e)
            interruptible_sleep(delay, _is_cancelled)
        except ConnectionError as e:
            state.record_fatal(str(e), "connection")
            if on_fatal is not None:
                on_fatal(page_idx, str(e), "connection")
            return
        except TimeoutError as e:
            state.record_fatal(str(e), "timeout")
            if on_fatal is not None:
                on_fatal(page_idx, str(e), "timeout")
            return
        except RuntimeError as e:
            state.record_page_error(str(e))
            if on_page_error is not None:
                on_page_error(page_idx, str(e))
            return
        except Exception as e:
            logger.exception("OCR 呼び出し失敗 (p.%d): %s", page_idx, e)
            state.record_page_error(str(e))
            if on_page_error is not None:
                on_page_error(page_idx, str(e))
            return
