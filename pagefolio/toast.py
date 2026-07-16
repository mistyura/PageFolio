# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""トースト通知コンポーネント（V180-QA-02）。

保存/印刷失敗の再試行アクション付き非モーダル通知。

メインウィンドウ（``app.root``）直下へ ``place()`` で右下オーバーレイ表示する
常駐 Frame。同時表示は1件のみで、新しい ``show()`` は既存トーストを常に置換
する（D-07）。同一カテゴリで再度 ``show()`` された場合は文言のみを更新して
残す（D-04・回数制限なし）。消滅条件は ✕ ボタン押下、または
``dismiss(category)`` の呼び出し（再試行成功・別経路での同一操作成功）の
いずれかで、``dismiss`` は現在表示中カテゴリと一致する場合のみ作用する
（D-08）。

``ui_builder.UIBuilderMixin._build_ui()`` が毎回インスタンス化し直す設計の
ため、``_rebuild_ui()``（テーマ切替時の全ウィジェット破棄）を経ても常に
有効な ``ToastManager`` が ``app._toast`` に存在する（Pitfall 2）。
"""

import logging
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import C

logger = logging.getLogger(__name__)


class ToastManager:
    """メインウィンドウ内オーバーレイの単一トースト通知を管理する。"""

    def __init__(self, app):
        self.app = app
        self._active_category = None
        self._frame = None
        self._msg_var = None
        self._retry_btn = None

    def show(self, category, message, retry_cb):
        """``category`` のトーストを表示する。

        既存トーストが表示中なら（カテゴリを問わず）常に破棄して新規で
        置換する（D-07）。ただし現在表示中カテゴリと同一の場合は Frame を
        再生成せず文言のみ更新する（D-04）。この場合も再試行ボタンの
        コールバックは最新の ``retry_cb`` へ差し替える（WR-03）。
        """
        if self._active_category == category and self._frame is not None:
            self._msg_var.set(message)
            if self._retry_btn is not None:
                self._retry_btn.configure(command=retry_cb)
            return
        self._destroy_frame()
        self._active_category = category
        self._build_frame(category, message, retry_cb)

    def dismiss(self, category):
        """一致する category の場合のみトーストを破棄する（D-08）。"""
        if self._active_category != category:
            return
        self._destroy_frame()
        self._active_category = None

    def _build_frame(self, category, message, retry_cb):
        app = self.app
        frame = tk.Frame(app.root, bg=C["BG_CARD"], bd=1, relief="solid")
        frame.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)

        self._msg_var = tk.StringVar(value=message)
        tk.Label(
            frame,
            textvariable=self._msg_var,
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            font=app._font(-1),
            wraplength=320,
            justify="left",
        ).pack(side="left", padx=(12, 4), pady=8)

        retry_btn = ttk.Button(
            frame,
            text=app._t("toast_retry_btn"),
            style="Accent.TButton",
            command=retry_cb,
        )
        retry_btn.pack(side="left", padx=4)
        self._retry_btn = retry_btn

        ttk.Button(
            frame,
            text="✕",
            width=2,
            command=lambda c=category: self.dismiss(c),
        ).pack(side="left", padx=(0, 8))

        self._frame = frame

    def _destroy_frame(self):
        if self._frame is not None:
            try:
                self._frame.destroy()
            except Exception as e:
                logger.debug("トースト Frame 破棄失敗: %s", e)
            self._frame = None
        self._msg_var = None
        self._retry_btn = None
