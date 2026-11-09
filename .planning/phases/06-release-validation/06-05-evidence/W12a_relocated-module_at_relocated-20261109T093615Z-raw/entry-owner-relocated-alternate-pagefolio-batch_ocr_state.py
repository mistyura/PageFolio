# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""バッチOCRのファイルキュー状態遷移純ロジック層（Tkinter / fitz 非依存）。

`pagefolio/ocr_pipeline.py`（`PipelineState`）と同格の「Tk/fitz 非依存の純
ロジック層」系譜に連なる新設モジュール（04-01-PLAN.md・V180-BATCH-01/02）。
バッチOCRのファイルキュー（`BatchFileEntry` のリスト）への投入・重複除外
（`enqueue_files`）と、ファイル軸進捗集計（`BatchState`）を提供する。

ファイル内のページ単位進捗（producer-consumer 駆動）は `OCRRunEngine`
（`pagefolio/ocr_engine.py`）・`PipelineState`（`pagefolio/ocr_pipeline.py`）
が真の情報源であり、本モジュールはそこから一切逆算しない（落とし穴5:
ファイル軸/ページ軸の二軸独立を構造的に担保する）。

不変条件（レビュー懸念6）: STATUS_ERROR エントリ（壊れた/開けないPDF）は
実行対象に含めない。`BatchState.total_files` は `count_pending(entries)`
（= STATUS_PENDING のエントリ数のみ）で算出する契約とし、STATUS_ERROR は
分母から除外される。これにより実行完了時にファイル軸進捗
`BatchState.remaining()` が必ず 0 へ収束する。

`BatchFileEntry` は per-file 状態（path・display_name・page_count・status・
results・errors）を独立保持し、使い回さない（`ocr_engine.py` の D-09/D-11
「実行ごとに新規生成」原則をファイル単位へ外挿したもの）。

トップレベル import は `logging`/`threading`/`os` に限定し、`tkinter`・
`fitz`(PyMuPDF) をモジュールレベルで import しない。
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

# ファイルキューの状態遷移を表す文字列定数（相異なる値）。
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"


class BatchFileEntry:
    """バッチOCRキュー内の1ファイル分の状態（per-file・独立保持・使い回さない）。

    属性:
      path:         ファイルの絶対/相対パス（dedup キー）
      display_name: 表示用ファイル名（os.path.basename(path)）
      page_count:   総ページ数（壊れた/開けないPDFは 0）
      status:       STATUS_PENDING/RUNNING/DONE/FAILED/ERROR のいずれか
                    （生成時は常に STATUS_PENDING）
      results:      page_idx（int）-> OCR結果テキスト の辞書（per-file 独立）
      errors:       page_idx（int）-> エラーメッセージ の辞書（per-file 独立）
    """

    def __init__(self, path, page_count=0):
        self.path = path
        self.display_name = os.path.basename(path)
        self.page_count = page_count
        self.status = STATUS_PENDING
        self.results = {}
        self.errors = {}


class BatchState:
    """バッチ全体のファイル単位進捗集計（Tk/fitz 非依存・Lock 保護）。

    ファイル内の詳細（ページ単位進捗）は `OCRRunEngine.progress_count()` が
    真の情報源であり、本クラスは「ファイルが完了/失敗/キャンセルされたか」
    という一段上の事実のみを集計する（責務分離・落とし穴5対応）。

    `total_files` は呼び出し元が `count_pending(entries)`（STATUS_PENDING
    のみ算入）で算出した値を渡す契約とし、STATUS_ERROR のファイルは実行対象
    から除外される（レビュー懸念6）。
    """

    def __init__(self, total_files):
        self._lock = threading.Lock()
        self.total_files = total_files
        self.completed = 0
        self.failed = 0
        self.cancelled = 0

    def mark_completed(self):
        with self._lock:
            self.completed += 1

    def mark_failed(self):
        with self._lock:
            self.failed += 1

    def mark_cancelled(self):
        with self._lock:
            self.cancelled += 1

    def files_done(self):
        with self._lock:
            return self.completed + self.failed + self.cancelled

    def remaining(self):
        return max(0, self.total_files - self.files_done())


def enqueue_files(entries, paths, page_counts=None):
    """entries（既存 BatchFileEntry のリスト）へ、まだ含まれない path のみ

    新規 BatchFileEntry として追加した更新後リストを返す。

    dedup キーは path。page_counts（path -> int の辞書）を渡すと、各新規
    entry.page_count に反映される。空の paths は no-op（entries をそのまま
    返す）。
    """
    updated = list(entries)
    existing_paths = {e.path for e in updated}
    for path in paths:
        if path in existing_paths:
            continue
        page_count = 0
        if page_counts is not None:
            page_count = page_counts.get(path, 0)
        updated.append(BatchFileEntry(path, page_count=page_count))
        existing_paths.add(path)
    return updated


def count_pending(entries):
    """entries のうち status == STATUS_PENDING のエントリ数を返す純関数。

    04-02 は `BatchState(total_files=count_pending(entries))` を構築し、
    STATUS_ERROR（壊れたPDF）を実行対象＝分母から除外する契約とする
    （レビュー懸念6・remaining() 収束の保証）。
    """
    return sum(1 for e in entries if e.status == STATUS_PENDING)
