# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Undo デルタのページ bytes を一時ファイルへ退避するストア（v1.7.0）。

delete / page_edit / merge_resize 等の undo デルタは「1 ページを単独 PDF に
した bytes」を保持する。高解像度画像 PDF ではこれが 1 ページ数 MB になり、
最大 2 スタック × MAX_UNDO 世代でメモリを圧迫するため、閾値以上の bytes を
tempfile へ退避しメモリから解放する。

Tk / fitz 非依存の純ロジック層。ライフサイクルは FileOpsMixin 側のフックが
管理する（deque 溢れ evict・redo クリア・消費時 dispose・ファイルクローズ /
アプリ終了時 purge）。atexit でも purge するため、異常終了以外で一時ファイル
は残らない。

Windows 考慮:
  - mkstemp の fd は書き込み後すぐ close し、読み取りは都度 open する
    （delete-on-close 系 API は共有違反リスクがあるため使わない）。
  - unlink 失敗（AV 等のロック）は suppress し、purge の rmtree
    （ignore_errors）と atexit の二段回収に委ねる。
"""

import atexit
import contextlib
import logging
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)

# この閾値未満の bytes はメモリ保持のまま（小ページの I/O オーバーヘッド回避）
OFFLOAD_THRESHOLD = 64 * 1024


class MemBlob:
    """閾値未満の小さいデータをメモリ保持する Blob。"""

    __slots__ = ("_data",)

    def __init__(self, data):
        self._data = data

    @property
    def size(self):
        return len(self._data)

    def load(self):
        """保持している bytes を返す。"""
        return self._data

    def release(self):
        """参照を破棄してメモリを解放する。release 後の load は不正。"""
        self._data = b""


class FileBlob:
    """閾値以上のデータを一時ファイルへ退避する Blob。"""

    __slots__ = ("path", "size")

    def __init__(self, path, size):
        self.path = path
        self.size = size

    def load(self):
        """一時ファイルから bytes を読み出して返す。"""
        with open(self.path, "rb") as f:
            return f.read()

    def release(self):
        """一時ファイルを削除する。ロック等の失敗は purge/atexit に委ねる。"""
        with contextlib.suppress(OSError):
            os.unlink(self.path)


class UndoBlobStore:
    """undo デルタ用 Blob の生成と一時ディレクトリの管理。

    ディレクトリは初回 put（閾値以上）で遅延生成し、purge() でまるごと
    削除する。purge 後に再度 put されれば新しいディレクトリを作る。
    """

    def __init__(self, threshold=OFFLOAD_THRESHOLD):
        self.threshold = threshold
        self._dir = None
        atexit.register(self.purge)

    @property
    def dir(self):
        """現在の一時ディレクトリ（未生成なら None）。"""
        return self._dir

    def _ensure_dir(self):
        if self._dir is None or not os.path.isdir(self._dir):
            self._dir = tempfile.mkdtemp(prefix="pagefolio_undo_")
        return self._dir

    def put(self, data):
        """bytes から Blob を生成する。閾値以上ならディスクへ退避する。

        書き込み失敗時（ディスクフル等）は MemBlob へフォールバックし、
        undo 機能自体は維持する。
        """
        if len(data) < self.threshold:
            return MemBlob(data)
        try:
            fd, path = tempfile.mkstemp(
                suffix=".pdf", prefix="page_", dir=self._ensure_dir()
            )
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return FileBlob(path, len(data))
        except OSError as e:
            logger.error("undo デルタのディスク退避に失敗（メモリ保持で継続）: %s", e)
            return MemBlob(data)

    def file_count(self):
        """一時ディレクトリ内のファイル数を返す（テスト・不変条件検証用）。"""
        if self._dir is None or not os.path.isdir(self._dir):
            return 0
        return len(os.listdir(self._dir))

    def purge(self):
        """一時ディレクトリをまるごと best-effort 削除する（冪等）。"""
        if self._dir and os.path.isdir(self._dir):
            shutil.rmtree(self._dir, ignore_errors=True)
        self._dir = None
