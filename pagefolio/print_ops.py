# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""印刷 Mixin — 現在のドキュメントを既定の PDF ハンドラ経由で印刷する。

OS の既定 PDF アプリへ印刷ジョブを渡す方式（Windows: ``os.startfile(path,
"print")``）を採用し、追加の pip 依存を増やさない。編集結果（回転・トリミング
・挿入等）を反映するため、現在の ``fitz.Document`` を一時ファイルへ書き出して
から印刷する。
"""

import logging
import os
import tempfile
from tkinter import messagebox

logger = logging.getLogger(__name__)


def write_print_tempfile(doc, dirpath=None):
    """doc の現在状態を一時 PDF ファイルへ書き出してパスを返す（純ヘルパー）。

    印刷ジョブは非同期で処理されるため、呼び出し側で即時削除はしない。
    既定の一時ディレクトリ（dirpath=None）または指定ディレクトリへ作成する。
    """
    data = doc.tobytes()
    fd, path = tempfile.mkstemp(suffix=".pdf", prefix="pagefolio_print_", dir=dirpath)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


class PrintOpsMixin:
    """PDFEditorApp の印刷メソッド群"""

    def _print_pdf(self):
        """現在のドキュメントを既定の PDF ハンドラで印刷する。"""
        if not self._check_doc():
            return
        try:
            path = write_print_tempfile(self.doc)
        except Exception as e:
            messagebox.showerror(
                self._t("err_print_title"), self._t("err_print_msg").format(e=e)
            )
            return
        self._send_to_printer(path)

    def _send_to_printer(self, path):
        """OS の印刷機能へファイルを渡す。

        Windows ではまず ``os.startfile(path, "print")`` で既定 PDF アプリの印刷
        動詞を起動する。印刷動詞が関連付けられていない場合（WinError 1155 等）は、
        既定アプリで PDF を開く（"open" 動詞）フォールバックを試み、ユーザーが
        アプリ側から手動で印刷できるようにする。どちらも失敗した場合は、PDF を
        開くアプリが無い旨を案内する。それ以外の OS では未対応である旨を通知する。
        """
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            messagebox.showinfo(
                self._t("info_title"), self._t("info_print_unsupported")
            )
            return
        name = os.path.basename(path)
        try:
            startfile(path, "print")
            self._set_status(self._t("status_print_sent").format(name=name))
            return
        except OSError as e:
            # 印刷動詞が未関連付け等。既定アプリで開くフォールバックへ。
            logger.warning("印刷動詞の起動に失敗、open 動詞で再試行: %s", e)
        try:
            startfile(path)
            self._set_status(self._t("status_print_opened").format(name=name))
        except OSError as e:
            logger.exception("既定アプリでのオープンにも失敗: %s", e)
            messagebox.showerror(
                self._t("err_print_title"), self._t("err_print_no_handler")
            )
