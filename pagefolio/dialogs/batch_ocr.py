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
    BatchState,
    count_pending,
    enqueue_files,
)
from pagefolio.constants import LANG, SUPPORTED_EXTENSIONS, C
from pagefolio.md_render import parse_markdown
from pagefolio.ocr import (
    DEFAULT_OCR_CONCURRENCY,
    DEFAULT_OCR_SCALE,
    MAX_RETRIES,
    build_provider,
    clamp_retry_after,
    has_embedded_text,
    interruptible_sleep,
    page_to_png_b64,
    resolve_ocr_prompt,
    resolve_summary_prompt,
)
from pagefolio.ocr_dialog import SUMMARY_TOO_LONG_CHARS
from pagefolio.ocr_engine import OCRRunEngine
from pagefolio.ocr_pipeline import send_sentinels, try_enqueue
from pagefolio.ocr_providers import OCRRetryableError
from pagefolio.settings import (
    get_current_font_size,
    load_custom_prompt,
    load_summary_prompt,
)

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

# サーキットブレーカー閾値。`ocr_dialog.py:CB_CONSECUTIVE_FAILURES` と同一値の
# コピペ移植（レビュー懸念5）。
CB_CONSECUTIVE_FAILURES = 3

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

        # ── ファイル横断統合サマリ状態（04-03・D-13/D-14）──
        self._summary_running = False
        self._summary_cancel_flag = threading.Event()

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

        # ── ファイル別結果閲覧・統合サマリ（D-15/D-16）──────────────
        result_frame = tk.Frame(self, bg=C["BG_DARK"])
        result_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        select_row = tk.Frame(result_frame, bg=C["BG_DARK"])
        select_row.pack(fill="x")
        tk.Label(
            select_row,
            text=self._L["batch_file_select_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
        ).pack(side="left", padx=(0, 6))
        self.file_select_var = tk.StringVar(value="")
        self.file_select_combo = ttk.Combobox(
            select_row, textvariable=self.file_select_var, state="readonly"
        )
        self.file_select_combo.pack(side="left", fill="x", expand=True)
        self.file_select_combo.bind("<<ComboboxSelected>>", self._on_select_file)
        self._export_btn = ttk.Button(
            select_row, text=self._L["batch_export_btn"], command=self._on_export_file
        )
        self._export_btn.pack(side="left", padx=(6, 0))
        self._export_btn.state(["disabled"])

        text_frame = tk.Frame(result_frame, bg=C["BG_PANEL"])
        text_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.text = tk.Text(
            text_frame,
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            font=self._font(-1),
            wrap="word",
            bd=0,
            highlightthickness=0,
            height=8,
        )
        text_sb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=text_sb.set)
        text_sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        # Markdown 整形タグ定義（OCRDialog._insert_markdown が消費するタグ名と
        # 同一・レビュー懸念5のコピペ移植方針）。
        # fmt: off
        self.text.tag_configure("md_h1", font=self._font(4, "bold"), foreground=C["ACCENT"])  # noqa: E501
        self.text.tag_configure("md_h2", font=self._font(2, "bold"), foreground=C["ACCENT"])  # noqa: E501
        self.text.tag_configure("md_bullet", lmargin1=20, lmargin2=36)
        self.text.tag_configure("md_code", background=C["BG_PANEL"], font=("Consolas", self._font_size))  # noqa: E501
        self.text.tag_configure("md_bold", font=self._font(-1, "bold"))
        # fmt: on

        self._summary_btn = ttk.Button(
            result_frame,
            text=self._L["batch_summary_btn"],
            style="Accent.TButton",
            command=self._on_batch_summary,
        )
        self._summary_btn.pack(anchor="w", pady=(8, 0))

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

    # ── ファイルループコントローラ ──────────────────────────
    def _widget_alive(self):
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _set_running_ui(self, running):
        """レビュー懸念3: 実行中/停止でボタン活性を切り替える。

        running=True で「▶ 実行」「+ ファイル追加」「削除」を disabled・
        「バッチ中止」を enabled にする。running=False で逆へ戻す。
        """
        self._running = running
        add_remove_start_state = ["disabled"] if running else ["!disabled"]
        cancel_state = ["!disabled"] if running else ["disabled"]
        self._start_btn.state(add_remove_start_state)
        self._add_btn.state(add_remove_start_state)
        self._remove_btn.state(add_remove_start_state)
        self._cancel_btn.state(cancel_state)

    def _build_provider_once(self):
        """バッチ開始時に1回だけ provider/concurrency/prompt を構築する（A2）。

        `ocr.py:_start_ocr` と同型のロジック（プロバイダ設定はファイル間で
        不変のため使い回す）。APIキー文字列は Engine へ渡さず、構築済み
        provider インスタンスのみを渡す（T-04-02 情報漏洩防止）。
        """
        s = self.app.settings
        name = s.get("ocr_provider", "")
        api_key = None
        _cloud_providers = {"claude", "gemini", "runpod"}
        if name in _cloud_providers:
            from pagefolio.ocr import _resolve_api_key
            from pagefolio.ocr_providers import OCRAPIKeyError

            session_keys = getattr(self.app, "_session_api_keys", {})
            try:
                api_key = _resolve_api_key(name, session_keys)
            except OCRAPIKeyError:
                api_key = None
        self.provider = build_provider(
            s, api_key=api_key, plugin_manager=getattr(self.app, "plugin_manager", None)
        )
        self.concurrency = max(
            1,
            min(
                self.provider.max_concurrency,
                int(s.get("ocr_concurrency", DEFAULT_OCR_CONCURRENCY)),
            ),
        )
        preset = s.get("ocr_prompt_preset", "text")
        custom_prompt = load_custom_prompt(s)
        self._ocr_prompt = resolve_ocr_prompt(preset, name, custom_prompt)
        self._ocr_scale = float(s.get("ocr_scale", DEFAULT_OCR_SCALE))

    def _on_start_batch(self):
        """バッチ実行開始。D-03（集約コスト確認）→ BatchState 構築 → ファイル
        ループ起動（レビュー懸念3・6）。
        """
        if self._running:
            return
        if count_pending(self._entries) == 0:
            messagebox.showinfo(
                self._L["info_title"], self._L["batch_empty_queue_msg"], parent=self
            )
            return
        if not self._check_cloud_api_key():
            return
        if not self._confirm_batch_cost():
            return

        # レビュー懸念6・04-01連携: STATUS_ERROR を実行対象＝分母から除外する。
        self._batch_state = BatchState(total_files=count_pending(self._entries))
        self._batch_cancel_flag.clear()
        self._file_cancel_flag.clear()
        self._build_provider_once()
        self._set_running_ui(True)
        self._update_overall_progress()
        self._advance_to_next_file()

    def _next_pending_entry(self):
        for e in self._entries:
            if e.status == STATUS_PENDING:
                return e
        return None

    def _advance_to_next_file(self):
        """次ファイルへ進む前に必ずバッチ全体キャンセルを確認する（Pitfall 2）。"""
        if self._batch_cancel_flag.is_set():
            self._set_running_ui(False)
            return
        next_entry = self._next_pending_entry()
        if next_entry is None:
            self._set_running_ui(False)
            return
        self._start_file_engine(next_entry)

    def _record_page_success(self, entry, page_idx, text, truncated):
        entry.results[page_idx] = text

    def _record_page_error(self, entry, page_idx, msg):
        entry.errors[page_idx] = msg

    def _on_engine_progress_for(self, entry, gen):
        def _on_progress(done, page_idx):
            if gen != self._run_gen:
                return
            try:
                self.after(0, lambda d=done: self._update_file_progress(entry, d))
            except tk.TclError:
                pass

        return _on_progress

    def _update_file_progress(self, entry, done):
        if not self._widget_alive():
            return
        self._file_progress[entry.path] = f"{done}/{entry.page_count}"
        self._refresh_queue_row(entry)

    def _start_file_engine(self, entry):
        """ファイルごとに `OCRRunEngine` を新規生成する（D-11 外挿・使い回さない）。"""
        entry.status = STATUS_RUNNING
        self._file_progress[entry.path] = f"0/{entry.page_count}"
        self._refresh_queue_row(entry)

        self._file_cancel_flag.clear()
        self._render_idx = 0
        self._run_gen += 1
        gen = self._run_gen
        run_pages = list(range(entry.page_count))

        engine = OCRRunEngine(
            provider=self.provider,
            prompt=self._ocr_prompt,
            run_pages=run_pages,
            concurrency=self.concurrency,
            cancel_flag=self._file_cancel_flag,
            on_success=lambda p, t, tr, e=entry: self._record_page_success(e, p, t, tr),
            on_page_error=lambda p, msg, e=entry: self._record_page_error(e, p, msg),
            on_progress=self._on_engine_progress_for(entry, gen),
            on_complete=lambda e=entry, g=gen: self._on_file_complete(e, g),
            on_cancelled=lambda e=entry, g=gen: self._on_file_cancelled(e, g),
            on_fatal=lambda msg, kind, e=entry, g=gen: self._on_file_fatal(
                e, msg, kind, g
            ),
            breaker_threshold=CB_CONSECUTIVE_FAILURES,
        )
        self._current_entry = entry
        self._current_engine = engine
        # fitz はファイル間もメインスレッド逐次（Pitfall 1・落とし穴3）。
        self._current_doc = fitz.open(entry.path)
        engine.start()
        self._render_next_page_for(entry, gen)

    def _retry_sentinels_for(self, entry, gen, remaining):
        if gen != self._run_gen:
            return
        if not self._widget_alive():
            return
        engine = self._current_engine
        sent = send_sentinels(engine.queue, remaining)
        if sent < remaining:
            left = remaining - sent
            self.after(
                50,
                lambda _g=gen, n=left, _e=entry: self._retry_sentinels_for(_e, _g, n),
            )

    def _render_next_page_for(self, entry, gen):
        """producer（メインスレッド）: 1ページ render → キューに積む（after(0) 連鎖）。

        `ocr_dialog.py:_render_next_page` と同型。fitz アクセスはここのみ
        （落とし穴3）。b64 のみをワーカーへ渡す。
        """
        if gen != self._run_gen:
            return
        if not self._widget_alive():
            return

        engine = self._current_engine
        if self._file_cancel_flag.is_set():
            sent = send_sentinels(engine.queue, self.concurrency)
            if sent < self.concurrency:
                self._retry_sentinels_for(entry, gen, self.concurrency - sent)
            return

        if engine.is_fatal():
            sent = send_sentinels(engine.queue, self.concurrency)
            if sent < self.concurrency:
                self._retry_sentinels_for(entry, gen, self.concurrency - sent)
            return

        total = len(engine.run_pages)
        idx = self._render_idx

        if idx >= total:
            sent = send_sentinels(engine.queue, self.concurrency)
            if sent < self.concurrency:
                self.after(
                    100,
                    lambda _g=gen, _e=entry: self._render_next_page_for(_e, _g),
                )
            return

        page_idx = engine.run_pages[idx]
        try:
            page = self._current_doc[page_idx]
            if has_embedded_text(page):
                extracted = page.get_text()
                entry.results[page_idx] = extracted
                engine.note_skip(page_idx)
                done_disp = engine.progress_count()
                self.after(0, lambda d=done_disp: self._update_file_progress(entry, d))
            else:
                b64 = page_to_png_b64(page, scale=self._ocr_scale)
                if not try_enqueue(engine.queue, (page_idx, b64)):
                    self.after(
                        100,
                        lambda _g=gen, _e=entry: self._render_next_page_for(_e, _g),
                    )
                    return
        except Exception as e:
            logger.exception(
                "バッチOCR: ページ処理失敗 (%s p.%d): %s",
                entry.display_name,
                page_idx,
                e,
            )
            entry.errors[page_idx] = f"image conversion error: {e}"
            engine.note_render_failed(page_idx)
            done_disp = engine.progress_count()
            self.after(0, lambda d=done_disp: self._update_file_progress(entry, d))

        self._render_idx += 1
        self.after(0, lambda _g=gen, _e=entry: self._render_next_page_for(_e, _g))

    def _close_current_doc(self):
        if self._current_doc is not None:
            try:
                self._current_doc.close()
            except Exception:
                logger.debug("バッチOCR: ドキュメントクローズ失敗（無視）")
            self._current_doc = None
        self._current_engine = None
        self._current_entry = None

    def _on_file_complete(self, entry, gen):
        """完了理由別アダプタ（正常完了）。世代ガード + after(0, ...) 投函のみ。"""
        if gen != self._run_gen:
            return
        try:
            self.after(0, lambda e=entry: self._finish_file_complete(e))
        except tk.TclError:
            pass

    def _on_file_cancelled(self, entry, gen):
        """完了理由別アダプタ（キャンセル）。_on_file_complete と同型。"""
        if gen != self._run_gen:
            return
        try:
            self.after(0, lambda e=entry: self._finish_file_cancelled(e))
        except tk.TclError:
            pass

    def _on_file_fatal(self, entry, msg, kind, gen):
        """完了理由別アダプタ（fatal）。D-09: 確認を挟まず自動スキップ。"""
        if gen != self._run_gen:
            return
        try:
            self.after(
                0, lambda e=entry, m=msg, k=kind: self._finish_file_fatal(e, m, k)
            )
        except tk.TclError:
            pass

    def _finish_file_complete(self, entry):
        if not self._widget_alive():
            return
        self._close_current_doc()
        entry.status = STATUS_DONE
        if self._batch_state is not None:
            self._batch_state.mark_completed()
        self._refresh_queue_row(entry)
        self._update_overall_progress()
        self._refresh_file_select_options()
        self._advance_to_next_file()

    def _finish_file_cancelled(self, entry):
        if not self._widget_alive():
            return
        self._close_current_doc()
        # キャンセルされたファイルは STATUS_PENDING へ戻し、後続の再実行
        # （count_pending 経由）で処理対象として残す（バッチ中止後の完了済み
        # ファイルは STATUS_DONE のまま保持され再送信されない・D-11）。
        entry.status = STATUS_PENDING
        if self._batch_state is not None:
            self._batch_state.mark_cancelled()
        self._refresh_queue_row(entry)
        self._update_overall_progress()
        self._advance_to_next_file()

    def _finish_file_fatal(self, entry, msg, kind):
        if not self._widget_alive():
            return
        self._close_current_doc()
        entry.status = STATUS_FAILED
        if self._batch_state is not None:
            self._batch_state.mark_failed()
        self._refresh_queue_row(entry)
        self._update_overall_progress()
        self._advance_to_next_file()

    def _on_batch_cancel(self):
        """D-10: 「バッチ中止」1ボタンで2階層フラグを同時に set する。"""
        self._batch_cancel_flag.set()
        self._file_cancel_flag.set()
        self._set_running_ui(False)

    def _on_close(self):
        """WM_DELETE_WINDOW ハンドラ（レビュー懸念1・HIGH。04-03 でサマリ対象へ拡張）。

        バッチ実行中またはサマリ生成中なら3フラグ（batch/file/summary）を
        同時に set してから世代を無効化し、孤児ワーカーの fitz 操作・
        クラウド API 送信・破棄後ウィジェットへの after 更新（tk.TclError
        多発）を防ぐ（`ocr_dialog.py:_on_close` 1959-1978 の踏襲。
        `OCRDialog._on_close` が `_cancel_flag`/`_summary_cancel_flag` を
        同時 set するのと同型）。
        """
        if self._running or self._summary_running:
            self._batch_cancel_flag.set()
            self._file_cancel_flag.set()
            self._summary_cancel_flag.set()
        self._run_gen += 1
        self.destroy()

    # ── ファイル別結果閲覧・統合サマリ（D-15/D-16・OCRDialog コピペ移植）──
    def _insert_markdown(self, text):
        """`ocr_dialog.py:_insert_markdown`（1800-1819行）と同一挙動の独立実装。

        `md_render.parse_markdown` の戻り値を `self.text` へ整形挿入する。
        `OCRDialog` を継承・import 流用せず同一シグネチャ・同一挙動で
        コピペ移植する（レビュー懸念5）。
        """
        for kind, spans in parse_markdown(text):
            line_start = self.text.index("end-1c")
            for span_text, inline_tag in spans:
                if inline_tag:
                    self.text.insert("end", span_text, inline_tag)
                else:
                    self.text.insert("end", span_text)
            self.text.insert("end", "\n")
            if kind:
                self.text.tag_add(kind, line_start, "end-1c")

    def _format_pages_text(self, entry):
        """`ocr_dialog.py:_format_pages_text`（1980-1993行）と同一挙動の独立実装。

        BatchOCRDialog は複数ファイルを扱うため `entry`（`BatchFileEntry`）を
        明示引数に取る（OCRDialog は単一ファイルの self.page_indices/results
        を暗黙参照するが、本ダイアログにファイル単位の等価な単一属性がない
        ための必然的差分。挙動＝「セパレータ付きページ本文連結」は同一）。
        """
        parts = []
        for page_idx in range(entry.page_count):
            if page_idx not in entry.results:
                continue
            sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
            parts.append(sep)
            parts.append(entry.results[page_idx])
        return "\n".join(parts)

    def _format_batch_summary_input(self):
        """D-15: 完了済み（STATUS_DONE）ファイルのみを対象に、ファイル名見出し
        （`batch_summary_file_header`）+ 全ページ本文を連結して1本の文字列を
        返す。完了ファイル0件なら空文字を返す（zero-completed エッジ）。
        """
        parts = []
        for entry in self._entries:
            if entry.status != STATUS_DONE:
                continue
            parts.append(
                self._L["batch_summary_file_header"].format(name=entry.display_name)
            )
            parts.append(self._format_pages_text(entry))
        return "\n".join(parts)

    def _confirm_summary_cost(self, char_count, settings=None):
        """`ocr_dialog.py:_confirm_summary_cost`（1237-1265行）と同一挙動の独立実装。"""
        s = settings if settings is not None else self.app.settings
        name = s.get("ocr_provider", "")
        if name == "gemini":
            host = "generativelanguage.googleapis.com"
        elif name == "runpod":
            host = s.get("runpod_url", "") or self._L["llm_runpod_host_unset"]
        else:
            host = "api.anthropic.com"
        msg = self._L["ocr_summary_cost_confirm_msg"].format(
            host=host, chars=char_count
        )
        return messagebox.askyesno(self._L["ocr_cost_confirm_title"], msg, parent=self)

    def _refresh_file_select_options(self):
        """完了済み（STATUS_DONE）ファイルの表示名一覧でファイル選択欄を更新する。"""
        names = [e.display_name for e in self._entries if e.status == STATUS_DONE]
        self.file_select_combo.configure(values=names)

    def _entry_by_display_name(self, name):
        for e in self._entries:
            if e.status == STATUS_DONE and e.display_name == name:
                return e
        return None

    def _on_select_file(self, event=None):
        """ファイル選択切替（D-16）: 選択ファイルの結果を `_insert_markdown` で描画。"""
        entry = self._entry_by_display_name(self.file_select_var.get())
        if entry is None:
            return
        self.text.delete("1.0", "end")
        self._insert_markdown(self._format_pages_text(entry))
        self.text.see("1.0")
        self._export_btn.state(["!disabled"])

    def _on_export_file(self):
        """ファイル単位エクスポート（D-16・raw 維持・コピー/保存は整形前テキスト）。"""
        entry = self._entry_by_display_name(self.file_select_var.get())
        if entry is None:
            return
        raw_text = self._format_pages_text(entry)
        default_name = os.path.splitext(entry.display_name)[0] + ".txt"
        path = filedialog.asksaveasfilename(
            parent=self,
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[(self._L["filetypes_all"], "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw_text)
        except OSError as e:
            logger.warning("バッチOCR: 結果エクスポート失敗: %s", e)
            messagebox.showerror(self._L["err_title"], str(e), parent=self)

    def _on_batch_summary(self, settings=None):
        """「📊 サマリ作成」手動トリガー（D-13）。

        `ocr_dialog.py:_on_summary`（2006-2074行）のゲート構造を踏襲する:
        完了ファイル0件は no-op・text 非対応プロバイダはエラー表示・クラウド
        時はコスト確認（D-14）・入力過大時は追加警告。承認後はワーカー
        スレッド1本 + 世代ガード + `_summary_cancel_flag` で実行する。
        バッチ完了時の自動生成はしない（D-13）。
        """
        if self._running or self._summary_running:
            return
        full_text = self._format_batch_summary_input()
        if not full_text:
            return
        if not getattr(self.provider, "supports_text_prompt", False):
            name = self.app.settings.get("ocr_provider", "")
            messagebox.showerror(
                self._L["err_title"],
                self._L["ocr_summary_unsupported"].format(name=name),
                parent=self,
            )
            return

        s = settings if settings is not None else dict(self.app.settings)
        name = s.get("ocr_provider", "")
        prompt = resolve_summary_prompt(name, load_summary_prompt(s))

        if self._is_cloud_provider(settings=s):
            if not self._check_cloud_api_key(settings=s):
                return
            if not self._confirm_summary_cost(len(full_text), settings=s):
                return

        if len(full_text) > SUMMARY_TOO_LONG_CHARS:
            proceed = messagebox.askyesno(
                self._L["ocr_cost_confirm_title"],
                self._L["ocr_summary_too_long_confirm"].format(chars=len(full_text)),
                parent=self,
            )
            if not proceed:
                return

        self._summary_running = True
        self._summary_cancel_flag.clear()
        self._summary_btn.state(["disabled"])
        self.status_var.set(self._L["ocr_summary_running"])
        self._run_gen += 1
        gen = self._run_gen
        threading.Thread(
            target=self._batch_summary_worker,
            args=(gen, full_text, prompt),
            daemon=True,
        ).start()

    def _batch_summary_worker(self, gen, full_text, prompt):
        """バックグラウンドスレッド: `complete_text_ex` を単発呼び出しする
        （`ocr_dialog.py:_summary_worker` と同型のリトライ規約）。
        """
        result = None
        error_msg = None
        for attempt in range(1, MAX_RETRIES + 1):
            if self._summary_cancel_flag.is_set():
                break
            try:
                result = self.provider.complete_text_ex(full_text, prompt)
                break
            except OCRRetryableError as e:
                if attempt >= MAX_RETRIES:
                    error_msg = str(e)
                    break
                raw_delay = (
                    e.retry_after
                    if e.retry_after is not None
                    else 1.0 * (2 ** (attempt - 1))
                )
                delay = clamp_retry_after(raw_delay)
                interruptible_sleep(delay, self._summary_cancel_flag)
            except Exception as e:
                logger.exception("バッチOCR: サマリ生成呼び出し失敗: %s", e)
                error_msg = str(e)
                break

        if gen != self._run_gen:
            return
        try:
            if self._summary_cancel_flag.is_set():
                self.after(0, self._on_batch_summary_cancelled)
            elif result is not None:
                text, truncated = result
                self.after(
                    0, lambda t=text, tr=truncated: self._on_batch_summary_done(t, tr)
                )
            else:
                self.after(0, lambda m=error_msg or "": self._on_batch_summary_error(m))
        except tk.TclError:
            pass

    def _on_batch_summary_done(self, text, truncated):
        if not self._widget_alive():
            return
        self.text.insert("end", f"\n{self._L['ocr_summary_separator']}\n")
        self._insert_markdown(text)
        if truncated:
            self.text.insert("end", self._L["ocr_summary_truncated"] + "\n")
        self.text.see("end")
        self.status_var.set(self._L["ocr_summary_complete"])
        self._summary_ui_reset()

    def _on_batch_summary_cancelled(self):
        if not self._widget_alive():
            return
        self.status_var.set(self._L["ocr_summary_cancelled"])
        self._summary_ui_reset()

    def _on_batch_summary_error(self, msg):
        if not self._widget_alive():
            return
        self.status_var.set(self._L["ocr_summary_failed"].format(error=msg))
        self._summary_ui_reset()

    def _summary_ui_reset(self):
        self._summary_running = False
        try:
            self._summary_btn.state(["!disabled"])
        except tk.TclError:
            pass
