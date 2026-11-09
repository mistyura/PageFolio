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
        self._duration_after = None
        self._on_close = None
        self.on_idle = None
        self._idle_after = None
        self._generation = 0
        self._disposed = False

    @property
    def active_category(self):
        return self._active_category

    def show(
        self, category, message, retry_cb=None, *, duration_ms=None, on_close=None
    ):
        """``category`` のトーストを表示する。

        既存トーストが表示中なら（カテゴリを問わず）常に破棄して新規で
        置換する（D-07）。ただし現在表示中カテゴリと同一の場合は Frame を
        再生成せず文言のみ更新する（D-04）。この場合も再試行ボタンの
        コールバックは最新の ``retry_cb`` へ差し替える（WR-03）。
        """
        if self._disposed:
            return
        self._cancel_idle()
        if (
            self._active_category == category
            and self._frame is not None
            and (self._retry_btn is not None) == (retry_cb is not None)
        ):
            self._msg_var.set(message)
            if self._retry_btn is not None:
                self._retry_btn.configure(command=retry_cb)
            self._on_close = on_close
            self._start_timer(duration_ms)
            return
        self._finish("replaced", notify_idle=False)
        self._active_category = category
        self._on_close = on_close
        self._build_frame(category, message, retry_cb)
        self._start_timer(duration_ms)

    def dismiss(self, category, *, reason="programmatic"):
        """一致する category の場合のみトーストを破棄する（D-08）。"""
        if self._active_category != category:
            return
        self._finish(reason)

    def _finish(self, reason, *, notify_idle=True):
        on_close = self._on_close
        self._destroy_frame()
        self._active_category = None
        self._on_close = None
        if on_close is not None:
            on_close(reason)
        if notify_idle and not self._disposed and self._idle_after is None:
            self._idle_after = self.app.root.after_idle(self._notify_idle)

    def _notify_idle(self):
        self._idle_after = None
        if not self._disposed and self._active_category is None and self.on_idle:
            self.on_idle()

    def _cancel_idle(self):
        if self._idle_after is not None:
            try:
                self.app.root.after_cancel(self._idle_after)
            except tk.TclError as e:
                logger.debug("トースト idle 取消失敗: %s", type(e).__name__)
            self._idle_after = None

    def dispose(self, *, reason="rebuild"):
        self._disposed = True
        self._cancel_idle()
        self._finish(reason, notify_idle=False)
        self.on_idle = None

    def _start_timer(self, duration_ms):
        self._generation += 1
        if self._duration_after is not None:
            self.app.root.after_cancel(self._duration_after)
            self._duration_after = None
        if duration_ms is not None:
            generation = self._generation
            self._duration_after = self.app.root.after(
                duration_ms,
                lambda: self._expire(generation),
            )

    def _expire(self, generation):
        if self._disposed or generation != self._generation:
            return
        self._duration_after = None
        self._finish("expired")

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

        if retry_cb is not None:
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
            command=lambda c=category: self.dismiss(c, reason="user"),
        ).pack(side="left", padx=(0, 8))

        self._frame = frame

    def _destroy_frame(self):
        self._generation += 1
        if self._duration_after is not None:
            try:
                self.app.root.after_cancel(self._duration_after)
            except tk.TclError as e:
                logger.debug("トースト timer 取消失敗: %s", type(e).__name__)
            self._duration_after = None
        if self._frame is not None:
            try:
                self._frame.destroy()
            except Exception as e:
                logger.debug("トースト Frame 破棄失敗: %s", e)
            self._frame = None
        self._msg_var = None
        self._retry_btn = None
