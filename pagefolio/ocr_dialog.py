# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR ダイアログ — 進行表示・キャンセル・結果エクスポート"""

import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pagefolio.constants import LANG, C
from pagefolio.ocr import OCR_PROMPTS, call_lm_studio, page_to_png_b64

logger = logging.getLogger(__name__)


class OCRDialog(tk.Toplevel):
    """OCR 実行中の進行表示と結果のスクロール表示を行うダイアログ"""

    def __init__(
        self,
        parent,
        app,
        doc,
        page_indices,
        url,
        model,
        preset,
        scale,
        timeout,
        lang="ja",
        font_func=None,
    ):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["ocr_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.grab_set()

        self.app = app
        self.doc = doc
        self.page_indices = list(page_indices)
        self.url = url
        self.model = model
        self.scale = scale
        self.timeout = timeout
        self._font = font_func or self._default_font

        self.preset_var = tk.StringVar(value=preset)
        self.results = {}  # page_idx -> text
        self.errors = {}  # page_idx -> message
        self._cancel_flag = threading.Event()
        self._worker_thread = None
        self._done = False

        self._build()
        self._center(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # ダイアログ表示完了後にワーカーを開始
        self.after(50, self._start_worker)

    # ── ユーティリティ ──
    @staticmethod
    def _default_font(delta=0, weight=None):
        if weight:
            return ("Segoe UI", max(7, 10 + delta), weight)
        return ("Segoe UI", max(7, 10 + delta))

    def _font_size(self):
        try:
            return int(self._font(0)[1])
        except Exception:
            return 12

    def _center(self, parent):
        self.update_idletasks()
        fs = self._font_size()
        w = max(640, int(fs * 56))
        h = max(440, int(fs * 36))
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(520, 360)

    # ── UI 構築 ──
    def _build(self):
        tk.Label(
            self,
            text=self._L["ocr_dialog_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(12, 6))

        # プロンプトプリセット
        pf = tk.Frame(self, bg=C["BG_DARK"])
        pf.pack(fill="x", padx=16, pady=4)
        tk.Label(
            pf,
            text=self._L["ocr_prompt_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        for value, key in (
            ("text", "ocr_preset_text"),
            ("table", "ocr_preset_table"),
            ("markdown", "ocr_preset_markdown"),
        ):
            tk.Radiobutton(
                pf,
                text=self._L[key],
                variable=self.preset_var,
                value=value,
                bg=C["BG_DARK"],
                fg=C["TEXT_MAIN"],
                selectcolor=C["BG_CARD"],
                activebackground=C["BG_DARK"],
                activeforeground=C["TEXT_MAIN"],
                font=self._font(-1),
            ).pack(side="left", padx=4)

        # 進行表示
        self.progress_var = tk.StringVar(value=self._L["ocr_progress_init"])
        tk.Label(
            self,
            textvariable=self.progress_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(0, "bold"),
        ).pack(pady=(4, 2))

        self.progress_bar = ttk.Progressbar(
            self, mode="determinate", maximum=max(1, len(self.page_indices))
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))

        # 結果テキスト
        result_frame = tk.Frame(self, bg=C["BG_PANEL"])
        result_frame.pack(fill="both", expand=True, padx=16, pady=4)
        self.text = tk.Text(
            result_frame,
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            font=self._font(-1),
            wrap="word",
            bd=0,
            highlightthickness=0,
        )
        sb = ttk.Scrollbar(result_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        # ボタン行
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=(8, 12))

        self.copy_btn = ttk.Button(
            btn_row, text=self._L["ocr_copy"], command=self._copy_to_clipboard
        )
        self.copy_btn.pack(side="left", padx=4)
        self.copy_btn.state(["disabled"])

        self.save_btn = ttk.Button(
            btn_row, text=self._L["ocr_save"], command=self._save_to_file
        )
        self.save_btn.pack(side="left", padx=4)
        self.save_btn.state(["disabled"])

        self.close_btn = ttk.Button(
            btn_row,
            text=self._L["btn_close"],
            style="Accent.TButton",
            command=self.destroy,
        )
        self.close_btn.pack(side="right", padx=4)
        self.close_btn.state(["disabled"])

        self.cancel_btn = ttk.Button(
            btn_row,
            text=self._L["ocr_cancel"],
            style="Danger.TButton",
            command=self._on_cancel,
        )
        self.cancel_btn.pack(side="right", padx=4)

    # ── ワーカー ──
    def _start_worker(self):
        prompt = OCR_PROMPTS.get(self.preset_var.get(), OCR_PROMPTS["text"])
        self._worker_thread = threading.Thread(
            target=self._worker, args=(prompt,), daemon=True
        )
        self._worker_thread.start()

    def _worker(self, prompt):
        for idx, page_idx in enumerate(self.page_indices, start=1):
            if self._cancel_flag.is_set():
                self.after(0, self._finish_cancelled)
                return
            # ページ画像変換
            try:
                page = self.doc[page_idx]
                b64 = page_to_png_b64(page, scale=self.scale)
            except Exception as e:
                logger.exception("ページ画像変換失敗: %s", e)
                self.errors[page_idx] = f"image conversion error: {e}"
                self.after(
                    0,
                    lambda i=idx, p=page_idx: self._on_progress(i, p, error=True),
                )
                continue
            # LM Studio 呼び出し
            try:
                text = call_lm_studio(
                    self.url,
                    self.model,
                    b64,
                    prompt,
                    timeout=self.timeout,
                )
            except ConnectionError as e:
                # 接続失敗は致命的 — 全体停止
                self.after(
                    0,
                    lambda msg=str(e): self._finish_error(msg, kind="connection"),
                )
                return
            except TimeoutError as e:
                self.after(
                    0,
                    lambda msg=str(e): self._finish_error(msg, kind="timeout"),
                )
                return
            except RuntimeError as e:
                # API エラーは当該ページのみスキップして続行
                self.errors[page_idx] = str(e)
                self.after(
                    0,
                    lambda i=idx, p=page_idx: self._on_progress(i, p, error=True),
                )
                continue
            except Exception as e:
                logger.exception("OCR 呼び出し失敗: %s", e)
                self.errors[page_idx] = str(e)
                self.after(
                    0,
                    lambda i=idx, p=page_idx: self._on_progress(i, p, error=True),
                )
                continue

            self.results[page_idx] = text
            self.after(
                0,
                lambda i=idx, p=page_idx, t=text: self._on_progress(i, p, text=t),
            )
        self.after(0, self._finish_complete)

    # ── UI 更新（メインスレッド） ──
    def _on_progress(self, idx, page_idx, text=None, error=False):
        total = len(self.page_indices)
        self.progress_var.set(
            self._L["ocr_progress"].format(cur=idx, total=total, page=page_idx + 1)
        )
        self.progress_bar["value"] = idx
        sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
        self.text.insert("end", f"\n{sep}\n")
        if error:
            err = self.errors.get(page_idx, "")
            self.text.insert("end", self._L["ocr_page_error"].format(error=err) + "\n")
        elif text is not None:
            self.text.insert("end", text + "\n")
        self.text.see("end")

    def _finish_complete(self):
        self._done = True
        if self._cancel_flag.is_set():
            self.progress_var.set(self._L["ocr_cancelled"])
        else:
            self.progress_var.set(
                self._L["ocr_complete"].format(
                    count=len(self.results), total=len(self.page_indices)
                )
            )
        self.cancel_btn.state(["disabled"])
        self.close_btn.state(["!disabled"])
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

    def _finish_cancelled(self):
        self._done = True
        self.progress_var.set(self._L["ocr_cancelled"])
        self.cancel_btn.state(["disabled"])
        self.close_btn.state(["!disabled"])
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

    def _finish_error(self, msg, kind):
        self._done = True
        if kind == "connection":
            user_msg = self._L["ocr_err_connection"].format(url=self.url, error=msg)
        elif kind == "timeout":
            user_msg = self._L["ocr_err_timeout"].format(
                timeout=self.timeout, error=msg
            )
        else:
            user_msg = msg
        self.progress_var.set(self._L["ocr_failed"])
        self.text.insert("end", "\n" + user_msg + "\n")
        self.text.see("end")
        self.cancel_btn.state(["disabled"])
        self.close_btn.state(["!disabled"])
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

    # ── 操作 ──
    def _on_cancel(self):
        self._cancel_flag.set()
        self.cancel_btn.state(["disabled"])
        self.progress_var.set(self._L["ocr_cancelling"])

    def _on_close(self):
        if not self._done:
            ok = messagebox.askyesno(
                self._L["confirm_title"],
                self._L["ocr_close_during_run"],
                parent=self,
            )
            if not ok:
                return
            self._cancel_flag.set()
        self.destroy()

    def _format_full_text(self):
        parts = []
        for page_idx in self.page_indices:
            if page_idx not in self.results:
                continue
            sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
            parts.append(sep)
            parts.append(self.results[page_idx])
        return "\n".join(parts)

    def _copy_to_clipboard(self):
        text = self._format_full_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        try:
            self.app._set_status(self._L["ocr_copied"])
        except Exception as e:
            logger.debug("ステータス更新失敗: %s", e)

    def _save_to_file(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".txt",
            filetypes=[
                ("Text file", "*.txt"),
                ("Markdown", "*.md"),
                ("All", "*.*"),
            ],
            title=self._L["ocr_save_dialog_title"],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._format_full_text())
            try:
                self.app._set_status(self._L["ocr_saved"].format(path=path))
            except Exception as e:
                logger.debug("ステータス更新失敗: %s", e)
        except OSError as e:
            messagebox.showerror(self._L["err_title"], str(e), parent=self)
