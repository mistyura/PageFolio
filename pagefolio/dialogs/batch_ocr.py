# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""バッチOCRダイアログ（`BatchOCRDialog`）。

現在メインウィンドウで開いているファイル（メインアプリの doc/filepath 属性）
とは完全に独立した設計（04-CONTEXT.md D-04）。ユーザーが明示的に選んだ複数
PDF/画像ファイルをキューへ投入し、ファイル間逐次で `OCRRunEngine`
（`pagefolio/ocr_engine.py`）をファイルごとに新規生成して実行する。

`OCRDialog`（`pagefolio/ocr_dialog.py`）のコスト確認系メソッド
（`_confirm_cost`/`_estimate_cost`/`_is_cloud_provider`/`_check_cloud_api_key`）
は同一シグネチャ・同一挙動の独立実装（コピペ移植）であり、`OCRDialog` を継承
せず・そのインスタンスメソッドを import して流用しない
（04-02-PLAN.md Review Incorporation 懸念5）。
"""

import logging
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import fitz

from pagefolio.batch_ocr_state import (
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    enqueue_files,
)
from pagefolio.constants import LANG, SUPPORTED_EXTENSIONS, C
from pagefolio.settings import get_current_font_size

try:
    from tkinterdnd2 import DND_FILES

    _HAS_TKDND = True
except ImportError:
    _HAS_TKDND = False

logger = logging.getLogger(__name__)

# コスト概算用モデル別単価テーブル（$/MTok, 入力, 出力）。
# `ocr_dialog.py:OCR_PRICE_TABLE`（M-6）と同一挙動のコピペ移植（レビュー懸念5）。
OCR_PRICE_TABLE: "dict[str, tuple[float, float]]" = {
    # Gemini
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.0),
    # Claude
    "claude-3-haiku": (1.0, 5.0),
    "claude-3-5-haiku": (1.0, 5.0),
    "claude-haiku": (1.0, 5.0),
    "claude-3-sonnet": (3.0, 15.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-7-sonnet": (3.0, 15.0),
    "claude-sonnet": (3.0, 15.0),
    "claude-3-opus": (5.0, 25.0),
    "claude-opus": (5.0, 25.0),
}
_PRICE_FALLBACK = (5.0, 25.0)

# キュー状態 → lang キーの写像（全 batch_status_* キーをソース内文字列
# リテラルとして出現させ test_no_unused_lang_keys の未使用キー assertion を
# 回避する・レビュー懸念2）。
_STATUS_LABEL_KEYS = {
    STATUS_PENDING: "batch_status_pending",
    STATUS_RUNNING: "batch_status_running",
    STATUS_DONE: "batch_status_done",
    STATUS_FAILED: "batch_status_failed",
    STATUS_ERROR: "batch_status_error",
}


def _lookup_price(model):
    """OCR_PRICE_TABLE からモデル単価を取得する（部分一致フォールバック付き）。

    `ocr_dialog.py:_lookup_price` と同一挙動のコピペ移植。
    """
    for key, prices in OCR_PRICE_TABLE.items():
        if key in model:
            return prices
    return _PRICE_FALLBACK


class BatchOCRDialog(tk.Toplevel):
    """複数PDF/画像ファイルの一括OCRを行う独立ダイアログ（D-04）。

    `self.app` は保持するが、メインアプリの doc/filepath 属性は一切参照
    しない（現在開いているファイルと独立・D-04）。
    """

    def __init__(self, parent, app, lang="ja", font_func=None):
        super().__init__(parent)
        self._L = LANG[lang]
        self._lang = lang
        self.title(self._L["batch_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(True, True)
        self.grab_set()

        self.app = app
        self._font_size = get_current_font_size()
        self._font = font_func or self._default_font

        # ── ファイルキュー状態（04-01 の BatchFileEntry のリスト）──
        self._entries = []
        self._file_progress = {}  # path -> "done/total" 表示文字列
        self._last_scan_errors = set()

        # ── バッチ実行状態（Task 2 でファイルループコントローラが使用）──
        self._batch_state = None
        self._batch_cancel_flag = threading.Event()
        self._file_cancel_flag = threading.Event()
        self._run_gen = 0
        self._running = False
        self.provider = None
        self.concurrency = 1
        self._ocr_prompt = ""
        self._ocr_scale = 1.5
        self._render_idx = 0
        self._current_entry = None
        self._current_engine = None
        self._current_doc = None

        # レビュー懸念1（HIGH）: バッチ実行中のクローズによるワーカーリーク防止。
        # 束ねるのは __init__ のここのみ。_on_close 本体は Task 2 で実装する。
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = self._font_size
        w = max(560, int(fs * 46))
        h = max(480, int(fs * 34))
        try:
            h = min(h, max(400, parent.winfo_height() - 40))
        except tk.TclError:
            pass
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(480, 400)

    def _default_font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    # ── UI 構築 ──────────────────────────────────────────
    def _build(self):
        tk.Label(
            self,
            text=self._L["batch_dialog_title"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4))

        # 全体進捗（ファイル軸・D-08）
        progress_frame = tk.Frame(self, bg=C["BG_DARK"])
        progress_frame.pack(fill="x", padx=16, pady=4)
        self.overall_progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.overall_progress_bar.pack(side="left", fill="x", expand=True)
        self.overall_progress_var = tk.StringVar(
            value=self._L["batch_overall_progress"].format(done=0, total=0)
        )
        tk.Label(
            progress_frame,
            textvariable=self.overall_progress_var,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
        ).pack(side="left", padx=(8, 0))

        self.status_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self.status_var,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
        ).pack(fill="x", padx=16)

        # キュー一覧（D-05: ファイル名/状態/ページ内進捗の3列）
        tree_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=6)
        sb = ttk.Scrollbar(tree_frame, orient="vertical")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("file", "status", "progress"),
            show="headings",
            yscrollcommand=sb.set,
        )
        self.tree.heading("file", text=self._L["batch_col_file"])
        self.tree.heading("status", text=self._L["batch_col_status"])
        self.tree.heading("progress", text=self._L["batch_col_progress"])
        self.tree.column("file", width=260, anchor="w")
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("progress", width=90, anchor="center")
        # D-06: 失敗/エラー行はテーマの警告色で表示（tag_configure）
        self.tree.tag_configure("warn", foreground=C["WARNING"])
        sb.configure(command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        if _HAS_TKDND:
            try:
                tree_frame.drop_target_register(DND_FILES)
                tree_frame.dnd_bind("<<Drop>>", self._on_batch_dnd_drop)
            except tk.TclError:
                logger.debug("バッチOCR: tkinterdnd2 の drop 登録に失敗しました")

        # 操作ボタン行
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=(4, 14))
        self._add_btn = ttk.Button(
            btn_row, text=self._L["batch_add_files_btn"], command=self._on_add_files
        )
        self._add_btn.pack(side="left", padx=4)
        self._remove_btn = ttk.Button(
            btn_row, text=self._L["batch_remove_btn"], command=self._on_remove_selected
        )
        self._remove_btn.pack(side="left", padx=4)
        self._start_btn = ttk.Button(
            btn_row,
            text=self._L["batch_start_btn"],
            style="Accent.TButton",
            command=self._on_start_batch,
        )
        self._start_btn.pack(side="left", padx=4)
        self._cancel_btn = ttk.Button(
            btn_row,
            text=self._L["batch_cancel_btn"],
            style="Danger.TButton",
            command=self._on_batch_cancel,
        )
        self._cancel_btn.pack(side="left", padx=4)
        self._cancel_btn.state(["disabled"])

    # ── キュー投入（D-02）──────────────────────────────────
    def _on_add_files(self):
        _supported_filter = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            parent=self,
            filetypes=[
                (self._L["filetypes_supported"], _supported_filter),
                (self._L["filetypes_pdf"], "*.pdf"),
                (self._L["filetypes_all"], "*.*"),
            ],
        )
        if not paths:
            return
        self._enqueue_files(list(paths))

    def _on_batch_dnd_drop(self, event):
        """D&D 投入ハンドラ（app.py:_on_dnd_drop の tk.splitlist パターン複製）。"""
        raw_paths = self.tk.splitlist(event.data)
        self._enqueue_files(list(raw_paths))
        return event.action

    def _enqueue_files(self, paths):
        """SUPPORTED_EXTENSIONS フィルタ → dedup → 事前ページ数スキャン → 行追加。"""
        filtered = [
            p for p in paths if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
        ]
        if not filtered:
            if paths:
                messagebox.showwarning(
                    self._L["confirm_title"], self._L["dnd_pdf_only"], parent=self
                )
            return

        existing_paths = {e.path for e in self._entries}
        new_paths = [p for p in filtered if p not in existing_paths]
        if not new_paths:
            return

        page_counts = self._scan_page_counts(new_paths)
        self._entries = enqueue_files(self._entries, new_paths, page_counts=page_counts)
        for entry in self._entries:
            if entry.path in self._last_scan_errors:
                entry.status = STATUS_ERROR
        self._last_scan_errors = set()

        for path in new_paths:
            entry = self._entry_by_path(path)
            if entry is not None:
                self._insert_queue_row(entry)
        self._update_overall_progress()

    def _scan_page_counts(self, paths):
        """`merge.py` の事前ページ数スキャンパターンをメインスレッド逐次で実行する。

        レビュー懸念4: 複数ファイル投入時は `batch_scanning_msg` を表示し、
        各反復後に `update_idletasks()` を呼んで UI 応答性を保つ。壊れた/開けない
        ファイルは page_count=0 とし、`self._last_scan_errors` へパスを記録する
        （呼び出し側が STATUS_ERROR へ反映する）。
        """
        page_counts = {}
        error_paths = set()
        show_progress = len(paths) > 0
        if show_progress:
            self.status_var.set(self._L["batch_scanning_msg"])
        for p in paths:
            try:
                d = fitz.open(p)
                page_counts[p] = len(d)
                d.close()
            except Exception as e:
                logger.debug("バッチOCR: ページ数取得失敗: %s", e)
                page_counts[p] = 0
                error_paths.add(p)
            if show_progress:
                self.update_idletasks()
        if show_progress:
            self.status_var.set("")
        self._last_scan_errors = error_paths
        return page_counts

    def _entry_by_path(self, path):
        for e in self._entries:
            if e.path == path:
                return e
        return None

    # ── キュー一覧・進捗表示（D-05/D-08）────────────────────
    def _status_label(self, status):
        key = _STATUS_LABEL_KEYS.get(status, "batch_status_pending")
        return self._L[key]

    def _progress_text_for(self, entry):
        if entry.status == STATUS_ERROR:
            return self._L["batch_scan_error"]
        return self._file_progress.get(entry.path, f"0/{entry.page_count}")

    def _row_tags_for(self, entry):
        if entry.status in (STATUS_ERROR, STATUS_FAILED):
            return ("warn",)
        return ()

    def _insert_queue_row(self, entry):
        self.tree.insert(
            "",
            "end",
            iid=entry.path,
            values=(
                entry.display_name,
                self._status_label(entry.status),
                self._progress_text_for(entry),
            ),
            tags=self._row_tags_for(entry),
        )

    def _refresh_queue_row(self, entry):
        if not self.tree.exists(entry.path):
            return
        self.tree.item(
            entry.path,
            values=(
                entry.display_name,
                self._status_label(entry.status),
                self._progress_text_for(entry),
            ),
            tags=self._row_tags_for(entry),
        )

    def _update_overall_progress(self):
        if self._batch_state is None:
            done, total = 0, 0
        else:
            done, total = self._batch_state.files_done(), self._batch_state.total_files
        self.overall_progress_bar.configure(maximum=max(1, total))
        self.overall_progress_bar["value"] = done
        self.overall_progress_var.set(
            self._L["batch_overall_progress"].format(done=done, total=total)
        )

    def _on_remove_selected(self):
        """D-07: 待機中（STATUS_PENDING）行のみ削除可能。"""
        sel = self.tree.selection()
        for iid in sel:
            entry = self._entry_by_path(iid)
            if entry is None or entry.status != STATUS_PENDING:
                continue
            self._entries = [e for e in self._entries if e.path != iid]
            self._file_progress.pop(iid, None)
            if self.tree.exists(iid):
                self.tree.delete(iid)
        self._update_overall_progress()

    # ── コスト確認（OCRDialog からのコピペ移植・レビュー懸念5）────────
    def _is_cloud_provider(self, settings=None):
        """`ocr_dialog.py:_is_cloud_provider` と同一挙動の独立実装。"""
        from pagefolio.ocr_providers import (
            ClaudeProvider,
            GeminiProvider,
            RunPodProvider,
        )

        s = settings if settings is not None else self.app.settings
        name = s.get("ocr_provider", "")
        if name in ("claude", "gemini", "runpod"):
            return True
        if isinstance(self.provider, (ClaudeProvider, GeminiProvider, RunPodProvider)):
            return True
        return False

    def _estimate_cost(self, model, page_count):
        """`ocr_dialog.py:_estimate_cost` と同一挙動の独立実装。"""
        input_price, output_price = _lookup_price(model)
        input_tokens = page_count * 1600
        output_tokens = page_count * 500
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        lang = self.app.settings.get("lang", "ja")
        return LANG[lang]["ocr_cost_estimate"].format(cost=cost)

    def _confirm_cost(self, page_count=None, settings=None):
        """`ocr_dialog.py:_confirm_cost` と同一挙動の独立実装。"""
        s = settings if settings is not None else self.app.settings
        name = s.get("ocr_provider", "")
        if name == "gemini":
            model = s.get("gemini_model", "gemini-2.5-flash")
            host = "generativelanguage.googleapis.com"
        elif name == "runpod":
            model = s.get("runpod_model", "") or "runpod"
            host = s.get("runpod_url", "") or self._L["llm_runpod_host_unset"]
        else:
            model = s.get("claude_model", "claude-sonnet-4-6")
            host = "api.anthropic.com"
        if page_count is None:
            page_count = sum(
                e.page_count for e in self._entries if e.status != STATUS_ERROR
            )
        cost = self._estimate_cost(model, page_count)
        msg = self._L["ocr_cost_confirm_msg"].format(
            host=host, count=page_count, cost=cost
        )
        return messagebox.askyesno(self._L["ocr_cost_confirm_title"], msg, parent=self)

    def _check_cloud_api_key(self, settings=None):
        """`ocr_dialog.py:_check_cloud_api_key` と同一挙動の独立実装。"""
        s = settings if settings is not None else self.app.settings
        if not self._is_cloud_provider(settings=s):
            return True
        from pagefolio.ocr import _resolve_api_key
        from pagefolio.ocr_providers import OCRAPIKeyError
        from pagefolio.ocr_providers.registry import primary_env_var

        name = s.get("ocr_provider", "")
        session_keys = getattr(self.app, "_session_api_keys", {})
        try:
            _resolve_api_key(name, session_keys)
        except OCRAPIKeyError:
            msg_key = {
                "claude": "ocr_api_key_missing",
                "gemini": "ocr_api_key_missing_gemini",
                "runpod": "ocr_api_key_missing_runpod",
            }.get(name, "ocr_api_key_missing")
            env_var = primary_env_var(name)
            messagebox.showerror(
                self._L["err_title"],
                self._L[msg_key].format(env_var=env_var),
                parent=self,
            )
            return False
        return True

    def _confirm_batch_cost(self):
        """D-03: 対象ファイル数・総ページ数の集約コスト確認（STATUS_ERROR 除外）。"""
        if not self._is_cloud_provider():
            return True
        total_pages = sum(
            e.page_count for e in self._entries if e.status != STATUS_ERROR
        )
        return self._confirm_cost(page_count=total_pages)

    # ── ファイルループコントローラ（Task 2 で実装）────────────────
    def _on_start_batch(self):
        """バッチ実行開始（Task 2 でファイルループコントローラを実装する）。"""

    def _on_batch_cancel(self):
        """バッチ中止（Task 2 で2階層フラグ set を実装する）。"""

    def _on_close(self):
        """WM_DELETE_WINDOW ハンドラ（Task 2 で2階層キャンセル+世代無効化を実装）。"""
        self._run_gen += 1
        self.destroy()
