# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR ダイアログ — 進行表示・キャンセル・結果エクスポート"""

import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pagefolio.constants import LANG, C
from pagefolio.md_render import parse_markdown
from pagefolio.ocr import (
    DEFAULT_OCR_CONCURRENCY,
    MAX_OCR_CONCURRENCY,
    MAX_OCR_MAX_TOKENS,
    MAX_RETRIES,
    build_provider,
    has_embedded_text,
    page_to_png_b64,
    resolve_ocr_prompt,
)

logger = logging.getLogger(__name__)

# M-6: モデル別単価テーブル（$/MTok, 入力, 出力）
# キーに完全一致しない場合は suffix ルールで判定するフォールバックへ進む
OCR_PRICE_TABLE: dict[str, tuple[float, float]] = {
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
# フォールバック単価（不明モデル）
_PRICE_FALLBACK = (5.0, 25.0)

# サーキットブレーカー: リトライ上限到達がこのページ数連続したら実行を中断する
# （サーバ側が完全に落ちている時に全ページ × リトライ待機を消化しないための保険）
CB_CONSECUTIVE_FAILURES = 3


def _lookup_price(model: str) -> tuple[float, float]:
    """OCR_PRICE_TABLE からモデル単価を取得する（部分一致フォールバック付き）。"""
    # 完全一致優先
    for key, prices in OCR_PRICE_TABLE.items():
        if key in model:
            return prices
    return _PRICE_FALLBACK


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
        max_tokens=-1,
        temperature=0.1,
        concurrency=DEFAULT_OCR_CONCURRENCY,
        provider=None,
        lang="ja",
        font_func=None,
        custom_prompt="",
    ):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["ocr_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.grab_set()

        self.app = app
        self.doc = doc
        self.page_indices = list(page_indices)
        self._font = font_func or self._default_font

        self.url_var = tk.StringVar(value=url)
        self.model_var = tk.StringVar(value=model)
        self.preset_var = tk.StringVar(value=preset)
        self.scale_var = tk.DoubleVar(value=float(scale))
        self.timeout_var = tk.IntVar(value=int(timeout))
        self.max_tokens_var = tk.IntVar(value=int(max_tokens))
        self.temperature_var = tk.DoubleVar(value=float(temperature))
        self.concurrency = max(1, min(MAX_OCR_CONCURRENCY, int(concurrency)))
        self.provider = provider
        self.custom_prompt = custom_prompt
        # セッションキー入力用（マスク表示・D-04）
        self.api_key_var = tk.StringVar()
        # 埋め込みテキスト無視オプション（既定 OFF・クラウド課金に直結するため非永続）
        self.force_ocr_var = tk.BooleanVar(value=False)
        self._force_ocr = False
        # OCRProvider インスタンス（D-03: メインスレッド側でのみ使用）
        self.results = {}  # page_idx -> text
        self.errors = {}  # page_idx -> message
        # 埋め込みテキスト検出によりスキップされたページ集合
        self._skipped_pages = set()
        # max_tokens 超過で応答が途切れたページ集合（D-05・部分テキストは保持）
        self._truncated_pages = set()
        # 今回の実行で処理するページリスト（再開時は未処理ページのみ）
        self._run_pages = list(self.page_indices)
        # 今回の実行開始時点のスキップ済み数（再開時の進捗計算基準）
        self._skip_base = 0
        self._cancel_flag = threading.Event()
        self._worker_threads = []  # CR-01: 複数ワーカースレッドの保持
        self._done = False
        self._started = False
        self._render_queue = None  # queue.Queue（_on_run で初期化・producer-consumer）
        self._ocr_page_indices = []  # スキップ除外後の Vision OCR 対象ページリスト
        # CR-01: 共有 done カウンタ保護 Lock および調整カウンタ
        self._done_lock = threading.Lock()
        self._done_count = 0  # Lock 配下の Vision OCR 完了ページ数
        self._workers_remaining = 0  # 残ワーカー数（0 になった最終ワーカーが終了処理）
        # CR-01: 致命的エラー情報（複数ワーカーで最初に発生したもの・Lock 保護）
        self._fatal_msg = None
        self._fatal_kind = None
        # サーキットブレーカー: 連続リトライ上限到達ページ数（Lock 保護）
        self._consec_err_count = 0
        # M-2: 世代カウンタ（ダイアログ破棄後の旧ワーカー after コールバックを無効化）
        # viewer.py の _preview_gen と同じパターン（世代一致 + winfo_exists）
        self._run_gen = 0

        self._build()
        self._center(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        # クリア/コピー/保存/再開/読み取り実行/キャンセル/閉じる の7ボタンが収まる横幅
        w = max(1150, int(fs * 90))
        # 設定行(プロンプト/サーバ/モデル/詳細) + 進行表示 + 結果領域 + ボタン行
        h = max(680, int(fs * 56))
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(960, 620)

    # ── UI 構築 ──
    def _build(self):
        tk.Label(
            self,
            text=self._L["ocr_dialog_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(12, 6))

        # 実行プロバイダ表示（どのプロバイダで OCR するかを明示）
        # 左寄せ: プロバイダ名 + モデル名 / 右寄せ: LLM 設定ボタン
        prov_row = tk.Frame(self, bg=C["BG_DARK"])
        prov_row.pack(fill="x", padx=16, pady=(0, 2))
        tk.Label(
            prov_row,
            text=self._L["ocr_provider_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(side="left")
        self._provider_value_label = tk.Label(
            prov_row,
            text=self._provider_display_name(),
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(-1, "bold"),
        )
        self._provider_value_label.pack(side="left", padx=(6, 0))
        # 現在選択されているモデル名（クラウド時は LM Studio 欄が消えるため明示する）
        self._model_value_label = tk.Label(
            prov_row,
            text=self._model_display_text(),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            anchor="w",
        )
        self._model_value_label.pack(side="left", padx=(12, 0))
        # LLM 設定ボタンは行の右端に配置
        self._llm_config_btn = ttk.Button(
            prov_row,
            text=self._L["ocr_open_llm_config"],
            command=self._open_llm_config,
        )
        self._llm_config_btn.pack(side="right", padx=(10, 0))
        # LM Studio のモデル変更（Combobox 編集）を表示へ即時反映する
        self.model_var.trace_add("write", lambda *_a: self._update_model_label())

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

        # サーバ（参照のみ・設定メニューの値を表示）
        # LM Studio 固有欄: クラウドプロバイダ時は表示しない（provider 中立化）
        show_lmstudio_fields = not self._is_cloud_provider()
        self._lmstudio_server_frame = tk.Frame(self, bg=C["BG_DARK"])
        sf = self._lmstudio_server_frame
        if show_lmstudio_fields:
            sf.pack(fill="x", padx=16, pady=(6, 2))
        tk.Label(
            sf,
            text=self._L["ocr_server_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=8,
            anchor="w",
        ).pack(side="left")
        tk.Entry(
            sf,
            textvariable=self.url_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
            state="readonly",
            readonlybackground=C["BG_CARD"],
        ).pack(side="left", fill="x", expand=True, padx=4)

        # モデル選択（LM Studio 固有欄: クラウド時は非表示）
        self._lmstudio_model_frame = tk.Frame(self, bg=C["BG_DARK"])
        mf = self._lmstudio_model_frame
        if show_lmstudio_fields:
            mf.pack(fill="x", padx=16, pady=2)
        tk.Label(
            mf,
            text=self._L["ocr_model_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=8,
            anchor="w",
        ).pack(side="left")
        # 編集導線は LLMConfigDialog へ一元化済みのため、モデル欄は読み取り専用表示。
        # 4 つの数値 Spinbox と同様、disabled + 暗背景 + 可読色で編集不可にする。
        self.model_combo = tk.Entry(
            mf,
            textvariable=self.model_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
            state="disabled",
            disabledbackground=C["BG_CARD"],
            disabledforeground=C["TEXT_SUB"],
        )
        self.model_combo.pack(side="left", fill="x", expand=True, padx=4)

        # 詳細設定行（解像度 / タイムアウト / 最大トークン）
        # self 属性化: ライブ更新時に LM Studio 欄を before= でこの行の前へ戻す
        self._params_row = tk.Frame(self, bg=C["BG_DARK"])
        params_row = self._params_row
        params_row.pack(fill="x", padx=16, pady=(6, 0))
        tk.Label(
            params_row,
            text=self._L["ocr_params_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=8,
            anchor="w",
        ).pack(side="left")
        tk.Label(
            params_row,
            text=self._L["ocr_scale_short"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(side="left", padx=(0, 2))
        tk.Spinbox(
            params_row,
            from_=1.0,
            to=4.0,
            increment=0.5,
            textvariable=self.scale_var,
            width=5,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
            disabledbackground=C["BG_CARD"],
            disabledforeground=C["TEXT_SUB"],
            state="disabled",
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            params_row,
            text=self._L["ocr_timeout_short"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(side="left", padx=(0, 2))
        tk.Spinbox(
            params_row,
            from_=10,
            to=900,
            increment=10,
            textvariable=self.timeout_var,
            width=5,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
            disabledbackground=C["BG_CARD"],
            disabledforeground=C["TEXT_SUB"],
            state="disabled",
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            params_row,
            text=self._L["ocr_max_tokens_short"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(side="left", padx=(0, 2))
        tk.Spinbox(
            params_row,
            from_=-1,
            to=MAX_OCR_MAX_TOKENS,
            increment=1024,
            textvariable=self.max_tokens_var,
            width=8,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
            disabledbackground=C["BG_CARD"],
            disabledforeground=C["TEXT_SUB"],
            state="disabled",
        ).pack(side="left", padx=(0, 4))
        tk.Label(
            params_row,
            text=self._L["ocr_max_tokens_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            params_row,
            text=self._L["ocr_temperature_short"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(side="left", padx=(0, 2))
        tk.Spinbox(
            params_row,
            from_=0.0,
            to=2.0,
            increment=0.1,
            textvariable=self.temperature_var,
            width=5,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
            disabledbackground=C["BG_CARD"],
            disabledforeground=C["TEXT_SUB"],
            state="disabled",
        ).pack(side="left", padx=(0, 4))
        tk.Label(
            params_row,
            text=self._L["ocr_temperature_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left")

        tk.Label(
            self,
            text=self._L["ocr_params_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=16)

        # 埋め込みテキスト無視オプション（低品質な埋め込みを Vision OCR で再読込）
        tk.Checkbutton(
            self,
            text=self._L["ocr_force_vision"],
            variable=self.force_ocr_var,
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            selectcolor=C["BG_CARD"],
            activebackground=C["BG_DARK"],
            activeforeground=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(anchor="w", padx=16, pady=(2, 0))

        # セッションキー入力欄（クラウドかつ env 未設定時のみ表示・マスク・D-04）
        self._key_frame = tk.Frame(self, bg=C["BG_DARK"])
        if self._needs_session_key():
            self._key_frame.pack(fill="x", padx=16, pady=(4, 0))
        tk.Label(
            self._key_frame,
            text=self._L["ocr_session_key_label"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(-1),
        ).pack(side="left")
        self.api_key_entry = tk.Entry(
            self._key_frame,
            show="*",
            textvariable=self.api_key_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        )
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # 進行表示
        # self 属性化: ライブ更新時にセッションキー欄を before= でこのラベルの前へ戻す
        self.progress_var = tk.StringVar(value=self._L["ocr_run_first"])
        self._progress_label = tk.Label(
            self,
            textvariable=self.progress_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(0, "bold"),
        )
        self._progress_label.pack(pady=(4, 2))

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
            height=10,
        )
        sb = ttk.Scrollbar(result_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        # Markdown 整形タグ定義（色は C[]・フォントは _font・V16-AI-01）。
        # 受入基準の単一行 grep ゲートを満たすため fmt:off で折返しを抑止。
        # fmt: off
        self.text.tag_configure("md_h1", font=self._font(4, "bold"), foreground=C["ACCENT"])  # noqa: E501
        self.text.tag_configure("md_h2", font=self._font(2, "bold"), foreground=C["ACCENT"])  # noqa: E501
        self.text.tag_configure("md_bullet", lmargin1=20, lmargin2=36)
        self.text.tag_configure("md_code", background=C["BG_PANEL"], font=("Consolas", self._font_size()))  # noqa: E501
        self.text.tag_configure("md_bold", font=self._font(-1, "bold"))
        # fmt: on

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

        self.clear_btn = ttk.Button(
            btn_row, text=self._L["ocr_clear"], command=self._clear_text
        )
        self.clear_btn.pack(side="left", padx=4)

        self.close_btn = ttk.Button(
            btn_row,
            text=self._L["btn_close"],
            command=self._on_close,
        )
        self.close_btn.pack(side="right", padx=4)

        self.cancel_btn = ttk.Button(
            btn_row,
            text=self._L["ocr_cancel"],
            style="Danger.TButton",
            command=self._on_cancel,
        )
        self.cancel_btn.pack(side="right", padx=4)
        self.cancel_btn.state(["disabled"])

        self.run_btn = ttk.Button(
            btn_row,
            text=self._L["ocr_run"],
            style="Accent.TButton",
            command=self._on_run,
        )
        self.run_btn.pack(side="right", padx=4)

        # 続きから再実行（エラー/未処理ページのみ・成功済み結果は保持）
        self.resume_btn = ttk.Button(
            btn_row,
            text=self._L["ocr_resume"],
            command=lambda: self._on_run(resume=True),
        )
        self.resume_btn.pack(side="right", padx=4)
        self.resume_btn.state(["disabled"])

    def _clear_text(self):
        """結果テキストエリア・進行表示・実行状態を初期化する"""
        # 実行中はクリア不可（キャンセルしてから再度押す想定）
        if self._started and not self._done:
            return
        self.text.delete("1.0", "end")
        self.results.clear()
        self.errors.clear()
        self._skipped_pages.clear()
        self._render_queue = None  # キュー参照をリセット（再実行時に再生成）
        self._ocr_page_indices.clear()
        self.progress_bar["value"] = 0
        self.progress_var.set(self._L["ocr_run_first"])
        self._progress_label.configure(fg=C["SUCCESS"])
        self.copy_btn.state(["disabled"])
        self.save_btn.state(["disabled"])
        self.cancel_btn.state(["disabled"])
        self.run_btn.state(["!disabled"])
        self.resume_btn.state(["disabled"])
        self._llm_config_btn.state(["!disabled"])
        self._started = False
        self._done = False
        self._cancel_flag.clear()
        # H-6: 前回実行の致命的エラー・完了カウンタを破棄する。
        # 残留すると再実行時に全ワーカーが has_fatal=True で API 呼び出しを
        # スキップし、旧エラーで即終了してしまう（タイムアウト後の再実行バグ）。
        self._fatal_msg = None
        self._fatal_kind = None
        self._done_count = 0
        self._consec_err_count = 0
        # M-2: クリア時も旧世代を無効化する（再実行前に旧コールバックを排除）
        self._run_gen += 1

    # ── 再開（リスタート）判定 ──

    def _pending_pages(self):
        """結果が得られていないページ（エラー・未処理）の昇順リストを返す"""
        return [p for p in self.page_indices if p not in self.results]

    def _can_resume(self):
        """「続きから再実行」が可能か（部分的な結果があり未処理ページが残っている）"""
        return bool(self.results) and bool(self._pending_pages())

    def _after_run_ui_reset(self):
        """実行終了後（完了/キャンセル/エラー共通）のボタン状態リセット。

        読み取り実行はクリアを経由せず再実行（リラン）できるよう再有効化し、
        部分的な結果が残っている場合のみ「続きから再実行」を有効化する。
        """
        self._started = False
        self.run_btn.state(["!disabled"])
        self._llm_config_btn.state(["!disabled"])
        if self._can_resume():
            self.resume_btn.state(["!disabled"])
        else:
            self.resume_btn.state(["disabled"])

    # ── ページ結果記録（ワーカースレッドから呼ばれる・Lock 保護） ──

    def _record_page_success(self, page_idx, text, truncated=False):
        """ページ成功を記録し、連続失敗カウンタをリセットする。

        truncated=True のとき当該ページを _truncated_pages に登録する。
        途切れは「成功＋警告」であり部分テキストは破棄せず results に保持する
        （D-05）。途切れ通知は _render_results_ordered で当該ページに併記する。
        """
        self.results[page_idx] = text
        with self._done_lock:
            self._done_count += 1
            self._consec_err_count = 0
            if truncated:
                self._truncated_pages.add(page_idx)
            else:
                self._truncated_pages.discard(page_idx)

    def _record_retryable_failure(self, page_idx, msg):
        """リトライ上限到達ページを記録する。

        連続失敗数が CB_CONSECUTIVE_FAILURES に達したらサーキットブレーカーとして
        致命的エラー（kind="circuit_breaker"）を設定し、以降のページの API 呼び出しを
        中断させる（サーバ側が落ちている時の無駄なリトライ消化を防ぐ）。
        中断後も成功済み結果は保持され「続きから再実行」で再開できる。
        """
        self.errors[page_idx] = msg
        with self._done_lock:
            self._done_count += 1
            self._consec_err_count += 1
            if (
                self._consec_err_count >= CB_CONSECUTIVE_FAILURES
                and self._fatal_msg is None
            ):
                self._fatal_msg = msg
                self._fatal_kind = "circuit_breaker"

    # ── クラウドプロバイダ判定・コスト確認・セッションキー ──

    def _provider_display_name(self):
        """現在の ocr_provider 設定を人間可読なプロバイダ表示名に変換する。

        claude → "Claude (Anthropic)"・gemini → "Gemini (Google AI)"
        lmstudio/"" → "LM Studio"。未知の名前はそのまま返す（フォールバック）。
        """
        from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider

        name = self.app.settings.get("ocr_provider", "")
        if name == "claude" or isinstance(self.provider, ClaudeProvider):
            return self._L["ocr_provider_name_claude"]
        if name == "gemini" or isinstance(self.provider, GeminiProvider):
            return self._L["ocr_provider_name_gemini"]
        if name == "tesseract":
            return self._L["ocr_provider_name_tesseract"]
        if name in ("lmstudio", ""):
            return self._L["ocr_provider_name_lmstudio"]
        return name

    def _provider_model_name(self):
        """現在のプロバイダで使用されるモデル名を返す（表示用）。

        claude / gemini は settings の各モデルキー、lmstudio は Combobox のライブ値、
        tesseract はモデル概念がないため空文字を返す。
        プラグインプロバイダは provider.model 属性をフォールバックとして参照する。
        """
        name = self.app.settings.get("ocr_provider", "")
        if name == "claude":
            return self.app.settings.get("claude_model", "claude-sonnet-4-6")
        if name == "gemini":
            return self.app.settings.get("gemini_model", "gemini-2.5-flash")
        if name == "tesseract":
            return ""
        if name in ("lmstudio", "", "off"):
            try:
                return self.model_var.get().strip()
            except tk.TclError:
                return ""
        return getattr(self.provider, "model", "") or ""

    def _model_display_text(self):
        """プロバイダ表示行に併記するモデル名テキストを返す（モデルなしは空文字）。"""
        model = self._provider_model_name()
        if not model:
            return ""
        return f"{self._L['ocr_model_label']} {model}"

    def _update_model_label(self):
        """モデル表示ラベルを現在の選択内容で更新する。"""
        try:
            self._model_value_label.configure(text=self._model_display_text())
        except tk.TclError:
            pass

    @staticmethod
    def _retry_wait_key(e):
        """リトライ待機中の進捗表示に使う LANG キーを例外から決定する。

        HTTP 429 のみ「レート制限」と表示し、5xx や code 不明（プラグイン等）は
        「サーバエラー」と表示する（500 をレート制限と誤認させない）。
        """
        if getattr(e, "code", None) == 429:
            return "ocr_waiting_retry"
        return "ocr_waiting_retry_server"

    def _build_retry_wait_message(self, wait_key, page_idx, attempt, delay):
        """リトライ待機中の進捗表示文言を生成する純粋ヘルパー（Tk 非依存）。

        実 delay（clamp_retry_after でクランプ済の実待機秒）由来の round(delay) を
        sec として文言へ埋め込む（D-06）。delay を文言生成より前に算出して渡す
        ことで「表示する待機秒数が実待機値と一致する」順序を回帰テストで担保する
        （_worker での順序入替が崩れたら直接アサートで落ちる）。
        external I/O や after は含めず、_retry_wait_key と同じくテスト可能な純度を
        保つ（self._L 参照のためインスタンスメソッド）。
        """
        return self._L[wait_key].format(
            page=page_idx + 1, n=attempt, max=MAX_RETRIES, sec=round(delay)
        )

    def _is_cloud_provider(self):
        """現在の ocr_provider 設定がクラウド系か判定する。

        claude / gemini / runpod であれば True を返す（D-13・Pitfall-F）。
        """
        from pagefolio.ocr_providers import (
            ClaudeProvider,
            GeminiProvider,
            RunPodProvider,
        )

        name = self.app.settings.get("ocr_provider", "")
        if name in ("claude", "gemini", "runpod"):
            return True
        # isinstance ガード（provider インスタンスが差し替わっていても対応）
        if isinstance(self.provider, (ClaudeProvider, GeminiProvider, RunPodProvider)):
            return True
        return False

    def _estimate_cost(self, model, page_count):
        """ページ数とモデルから概算コスト文字列を返す（D-10）。

        OCR_PRICE_TABLE からモデル単価を取得する（M-6）。
        Vision 入力: 1枚あたり最大 1600 トークン相当を仮定。
        OCR 出力: 1ページあたり平均 500 トークンを想定した粗い見積もり。
        正確性より「課金が発生する」警告の存在が重要（D-10・Pitfall 8）。
        """
        input_price, output_price = _lookup_price(model)
        # Vision 入力トークン見積もり: 約 1600 tokens/page（Anthropic/Google 参考値）
        # 出力トークン見積もり: 約 500 tokens/page（OCR 結果テキスト）
        input_tokens = page_count * 1600
        output_tokens = page_count * 500
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        lang = self.app.settings.get("lang", "ja")
        return LANG[lang]["ocr_cost_estimate"].format(cost=cost)

    def _needs_session_key(self):
        """クラウドかつ API キー環境変数が未設定のときに True を返す。

        claude: ANTHROPIC_API_KEY が未設定なら True。
        gemini: GEMINI_API_KEY/GOOGLE_API_KEY 両方未設定なら True（D-06/Pitfall-G）。
        runpod: RUNPOD_API_KEY が未設定なら True。
        環境変数が設定済みであれば入力欄を表示しない（D-02/D-03）。
        """
        from pagefolio.ocr_providers import RunPodProvider

        if not self._is_cloud_provider():
            return False
        name = self.app.settings.get("ocr_provider", "")
        if name == "gemini":
            # dual env var: GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバック（D-06）
            return not bool(
                os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            )
        elif name == "runpod" or isinstance(self.provider, RunPodProvider):
            return not bool(os.environ.get("RUNPOD_API_KEY"))
        # claude（デフォルト）: ANTHROPIC_API_KEY を確認
        return not bool(os.environ.get("ANTHROPIC_API_KEY"))

    # ── LLM 設定ボタン・ライブ更新 ──────────────────────────────────────────

    def _open_llm_config(self):
        """プロバイダ表示行の「⚙ LLM 設定…」ボタンから LLMConfigDialog を開く。

        実行中（_started かつ未完了）は即 return してプロバイダ変更を阻止する
        （T-CCZ-02）。既に開いている場合も二重起動せず既存ウィンドウを前面へ出す。
        """
        if self._started and not self._done:
            return
        existing = getattr(self, "_llm_config_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        lang = self.app.settings.get("lang", "ja")
        self._llm_config_dialog = LLMConfigDialog(
            self,
            self.app.settings,
            on_apply=self._apply_llm_settings,
            font_func=self._font,
            lang=lang,
            plugin_manager=getattr(self.app, "plugin_manager", None),
        )

    def _apply_llm_settings(self, llm_settings):
        """LLMConfigDialog の on_apply コールバック。設定更新・永続化・ライブ更新。

        llm_settings に api_key 系キーは含まれず T-05-12 ガードは維持される。
        UI 操作は _refresh_provider_dependent_ui に委譲しテスト容易性を確保する。
        """
        # (a) 設定を app.settings に反映
        self.app.settings.update(llm_settings)
        # (b) 永続化（機密キー除外は _save_settings 内部で実施済み）
        from pagefolio.settings import _save_settings

        _save_settings(self.app.settings)
        # self.custom_prompt は __init__ 時点の値をキャッシュしているだけで
        # 以降の app.settings 更新が反映されないため、ここで明示的に同期する
        # （さもないと _on_run が 1 回前のカスタムプロンプトを使い続ける）
        self.custom_prompt = self.app.settings.get("ocr_custom_prompt", "")
        # (c)〜(g) UI 更新
        self._refresh_provider_dependent_ui()
        # 全プロバイダ共通: 読み取り専用の数値パラメータ表示を settings 値へ即時同期
        # (D-03)。LM Studio 専用 (g) ブロックの外で行い claude/gemini でも反映する。
        self._sync_param_vars_from_settings()
        # (f) provider インスタンスの再生成
        name = self.app.settings.get("ocr_provider", "")
        try:
            if name == "claude":
                from pagefolio.ocr import _resolve_api_key, build_provider
                from pagefolio.ocr_providers import OCRAPIKeyError

                session_keys = getattr(self.app, "_session_api_keys", {})
                try:
                    api_key = _resolve_api_key("claude", session_keys)
                except OCRAPIKeyError:
                    api_key = ""
                self.provider = build_provider(
                    self.app.settings,
                    api_key=api_key,
                    plugin_manager=getattr(self.app, "plugin_manager", None),
                )
            elif name == "gemini":
                # Gemini: dual env var → セッションキー → api_key=""（Pitfall-G）
                from pagefolio.ocr import _resolve_api_key, build_provider
                from pagefolio.ocr_providers import OCRAPIKeyError

                session_keys = getattr(self.app, "_session_api_keys", {})
                try:
                    api_key = _resolve_api_key("gemini", session_keys)
                except OCRAPIKeyError:
                    api_key = ""
                self.provider = build_provider(
                    self.app.settings,
                    api_key=api_key,
                    plugin_manager=getattr(self.app, "plugin_manager", None),
                )
            elif name == "ollama":
                from pagefolio.ocr_providers import OllamaProvider

                self.provider = OllamaProvider(
                    url=self.app.settings.get("ollama_url", "http://localhost:11434"),
                    model=self.app.settings.get("ollama_model", ""),
                    timeout=int(self.app.settings.get("ocr_timeout", 120)),
                    max_tokens=int(self.app.settings.get("ocr_max_tokens", -1)),
                    temperature=float(self.app.settings.get("ocr_temperature", 0.1)),
                )
                self.url_var.set(
                    self.app.settings.get("ollama_url", "http://localhost:11434")
                )
                self.model_var.set(self.app.settings.get("ollama_model", ""))
            elif name == "runpod":
                from pagefolio.ocr import _resolve_api_key, build_provider
                from pagefolio.ocr_providers import OCRAPIKeyError

                session_keys = getattr(self.app, "_session_api_keys", {})
                try:
                    api_key = _resolve_api_key("runpod", session_keys)
                except OCRAPIKeyError:
                    api_key = ""
                self.provider = build_provider(
                    self.app.settings,
                    api_key=api_key,
                    plugin_manager=getattr(self.app, "plugin_manager", None),
                )
                self.url_var.set(self.app.settings.get("runpod_url", ""))
                self.model_var.set(self.app.settings.get("runpod_model", ""))
            elif name in ("lmstudio", "", "off"):
                from pagefolio.ocr_providers import LMStudioProvider

                self.provider = LMStudioProvider(
                    url=self.app.settings.get("lm_studio_url", "http://localhost:1234"),
                    model=self.app.settings.get("lm_studio_model", ""),
                    timeout=int(self.app.settings.get("ocr_timeout", 120)),
                    max_tokens=int(self.app.settings.get("ocr_max_tokens", -1)),
                    temperature=float(self.app.settings.get("ocr_temperature", 0.1)),
                )
                # (g) LM Studio 欄の Tk 変数も settings に合わせて更新
                self.url_var.set(
                    self.app.settings.get("lm_studio_url", "http://localhost:1234")
                )
                self.model_var.set(self.app.settings.get("lm_studio_model", ""))
            else:
                # H-2: tesseract / プラグイン登録プロバイダは build_provider で再生成
                from pagefolio.ocr import build_provider

                self.provider = build_provider(
                    self.app.settings,
                    plugin_manager=getattr(self.app, "plugin_manager", None),
                )
            # H-3: provider 再生成後に concurrency を max_concurrency 以下に再クランプ
            self.concurrency = max(
                1, min(self.provider.max_concurrency, self.concurrency)
            )
        except Exception as e:
            logger.error("provider 再生成に失敗しました: %s", e)
            lang = self.app.settings.get("lang", "ja")
            self.progress_var.set(LANG[lang]["ocr_provider_rebuild_error"].format(e=e))

    def _sync_param_vars_from_settings(self):
        """読み取り専用の数値パラメータ Tk 変数を app.settings の値へ同期する。

        全プロバイダ共通（claude/gemini/lmstudio/off/tesseract）で呼ばれ、
        読み取り専用 Spinbox の表示を LLM 設定の適用結果へ即時反映する（D-03）。
        既定値は llm_config 側のフォールバックと整合させる。
        値はログに出力しない（情報露出回避・T-01-01）。
        """
        settings = self.app.settings
        self.scale_var.set(settings.get("ocr_scale", 1.5))
        self.timeout_var.set(settings.get("ocr_timeout", 120))
        self.max_tokens_var.set(settings.get("ocr_max_tokens", -1))
        self.temperature_var.set(settings.get("ocr_temperature", 0.1))

    def _refresh_provider_dependent_ui(self):
        """プロバイダ依存 UI（表示ラベル・LM Studio 欄・セッションキー欄）を再評価する。

        _apply_llm_settings から呼ばれる。テストでは no-op に差し替え可能。
        """
        # (c) プロバイダ表示ラベル更新（モデル名併記も再評価）
        self._provider_value_label.configure(text=self._provider_display_name())
        self._update_model_label()
        # (d) LM Studio 欄の可視性再評価
        # before= で元の位置（詳細設定行の前）へ戻す。素の pack() は
        # スレーブリスト末尾へ追加されダイアログ最下部に表示されてしまうため。
        show = not self._is_cloud_provider()
        if show:
            self._lmstudio_server_frame.pack(
                fill="x", padx=16, pady=(6, 2), before=self._params_row
            )
            self._lmstudio_model_frame.pack(
                fill="x", padx=16, pady=2, before=self._params_row
            )
        else:
            self._lmstudio_server_frame.pack_forget()
            self._lmstudio_model_frame.pack_forget()
        # (e) セッションキー欄の可視性再評価（before= で進行表示の前へ戻す）
        if self._needs_session_key():
            self._key_frame.pack(
                fill="x", padx=16, pady=(4, 0), before=self._progress_label
            )
        else:
            self._key_frame.pack_forget()
        # (f) 行の増減でボタン行が隠れないよう、必要に応じてウィンドウ高さを拡張
        self._grow_to_fit()

    def _grow_to_fit(self):
        """ライブ更新で行が増えた際、ボタン行が画面外へ押し出されないよう高さを拡張する。

        固定高で開いたダイアログに LM Studio 欄を再表示すると content が高さを超え、
        最下部のボタン行がクリップされるため、必要時のみ高さを広げる（縮小はしない）。
        """
        try:
            self.update_idletasks()
            req_h = self.winfo_reqheight()
            cur_h = self.winfo_height()
            if req_h > cur_h:
                self.geometry(
                    f"{self.winfo_width()}x{req_h}+{self.winfo_x()}+{self.winfo_y()}"
                )
        except tk.TclError:
            pass

    def _confirm_cost(self, page_count=None):
        """クラウド送信前のコスト確認ダイアログを表示し、ユーザーの選択を bool で返す。

        毎回表示する（「今後表示しない」は設けない・D-11）。
        ダイアログ内容（D-12 の3点）:
          1. 送信先ホスト（プロバイダ別: claude→api.anthropic.com/gemini→googleapis）
          2. 対象ページ数と概算コスト
          3. 「ページ画像が外部 API に送信されます」「従量課金が発生します」
        OK で True・キャンセルで False を返す（成功基準5）。

        引数:
          page_count: 今回送信するページ数（None なら全対象ページ数。
                      再開時は未処理ページ数を渡して過大見積もりを避ける）
        """
        name = self.app.settings.get("ocr_provider", "")
        if name == "gemini":
            model = self.app.settings.get("gemini_model", "gemini-2.5-flash")
            host = "generativelanguage.googleapis.com"
        else:
            # claude（デフォルト）
            model = self.app.settings.get("claude_model", "claude-sonnet-4-6")
            host = "api.anthropic.com"
        if page_count is None:
            page_count = len(self.page_indices)
        cost = self._estimate_cost(model, page_count)
        msg = self._L["ocr_cost_confirm_msg"].format(
            host=host,
            count=page_count,
            cost=cost,
        )
        return messagebox.askyesno(
            self._L["ocr_cost_confirm_title"],
            msg,
            parent=self,
        )

    # ── ワーカー ──
    def _on_run(self, resume=False):
        """読み取り実行 / 続きから再実行: OCR を開始する。

        メインスレッドでレンダリング/埋め込み判定後にワーカーを起動する。
        クラウドプロバイダ時は実行前にコスト確認ゲートを挟む（成功基準5・D-13）。

        引数:
          resume: True なら成功済み結果を保持し、エラー/未処理ページのみ
                  再実行する（リスタート）。False は全ページ再実行（リラン）。
        """
        if self._started:
            return

        # 今回の実行対象を決定（再開時は未処理ページのみ）
        resume = resume and self._can_resume()
        run_pages = self._pending_pages() if resume else list(self.page_indices)
        if not run_pages:
            return

        # ── クラウド実行ゲート（_started を True にする前）──
        if self._is_cloud_provider():
            name = self.app.settings.get("ocr_provider", "")
            # セッションキー入力（環境変数未設定時のみ）
            if self._needs_session_key():
                key = self.api_key_var.get().strip()
                if not key:
                    # キー未入力 → エラー表示して中止（成功基準2・T-05-19）
                    if name == "gemini":
                        # gemini: ocr_api_key_missing_gemini（dual env var 説明・D-06）
                        messagebox.showerror(
                            self._L["err_title"],
                            self._L["ocr_api_key_missing_gemini"],
                            parent=self,
                        )
                    else:
                        # claude（デフォルト）
                        messagebox.showerror(
                            self._L["err_title"],
                            self._L["ocr_api_key_missing"].format(
                                env_var="ANTHROPIC_API_KEY"
                            ),
                            parent=self,
                        )
                    return
                # _session_api_keys に格納（settings には入れない・D-01/D-03/T-06-11）
                if name == "gemini":
                    self.app._session_api_keys["gemini"] = key
                else:
                    self.app._session_api_keys["claude"] = key

            # コスト確認ダイアログ（毎回・D-11・D-12。再開時は未処理ページ数で見積）
            if not self._confirm_cost(len(run_pages)):
                # キャンセル → OCR を始めない（成功基準5）
                return

        self._started = True
        self._done = False
        # H-6: 実行開始時に前回実行の致命的エラー・完了カウンタを必ず破棄する
        # （_clear_text を経由しない再実行経路でも残留状態を持ち込まないため）
        self._fatal_msg = None
        self._fatal_kind = None
        self._done_count = 0
        self._consec_err_count = 0
        self._cancel_flag.clear()
        if resume:
            # 再実行対象の旧エラー・旧途切れ状態を破棄（再実行結果で上書きするため）
            for p in run_pages:
                self.errors.pop(p, None)
                self._truncated_pages.discard(p)
        else:
            # リラン（全体再実行）: 前回の結果・エラー・スキップ・途切れ状態を破棄
            self.results.clear()
            self.errors.clear()
            self._skipped_pages.clear()
            self._truncated_pages.clear()
        self._run_pages = run_pages
        self._skip_base = len(self._skipped_pages)
        self.run_btn.state(["disabled"])
        self.resume_btn.state(["disabled"])
        self._llm_config_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.progress_var.set(self._L["ocr_progress_init"])
        # 前回エラー完了時の警告色を通常色（SUCCESS）へ戻す
        self._progress_label.configure(fg=C["SUCCESS"])
        self.progress_bar.configure(maximum=max(1, len(run_pages)))
        self.progress_bar["value"] = 0
        # 結果テキストエリアをクリア（完了時に全ページ分を統合して再描画する）
        self.text.delete("1.0", "end")

        # UI パラメータをここで取得（メインスレッド）
        try:
            self._ocr_scale = max(1.0, min(4.0, float(self.scale_var.get())))
        except (tk.TclError, ValueError):
            self._ocr_scale = 1.5  # WR-01: D-11 整合（例外フォールバック統一）
        try:
            self._ocr_timeout = max(10, min(900, int(self.timeout_var.get())))
        except (tk.TclError, ValueError):
            self._ocr_timeout = 120
        self._effective_timeout = self._ocr_timeout
        # provider 名はプロンプト解決の前に無条件取得（下流の再生成分岐と共用）。
        name = self.app.settings.get("ocr_provider", "")
        # プロンプト解決は resolve_ocr_prompt に集約（優先順位は純関数側で担保）。
        prompt = resolve_ocr_prompt(self.preset_var.get(), name, self.custom_prompt)
        self._ocr_prompt = prompt

        try:
            self._force_ocr = bool(self.force_ocr_var.get())
        except (tk.TclError, ValueError):
            self._force_ocr = False

        # CR-02（中立化版）: プロバイダ種別に応じて provider を再生成する
        # lmstudio / off → LMStudioProvider（live 値で再生成・後方互換維持）
        # claude → build_provider 経由で ClaudeProvider（api_key は引数注入のみ・D-01）
        try:
            url = self.url_var.get().strip()
        except (tk.TclError, ValueError):
            url = getattr(self.provider, "url", "") if self.provider else ""
        try:
            model = self.model_var.get().strip()
        except (tk.TclError, ValueError):
            model = getattr(self.provider, "model", "") if self.provider else ""
        try:
            raw_mt = int(self.max_tokens_var.get())
            max_tokens = max(-1, min(MAX_OCR_MAX_TOKENS, raw_mt))
        except (tk.TclError, ValueError):
            _prov = self.provider
            max_tokens = getattr(_prov, "max_tokens", -1) if _prov else -1
        try:
            temperature = max(0.0, min(2.0, float(self.temperature_var.get())))
        except (tk.TclError, ValueError):
            _prov = self.provider
            temperature = getattr(_prov, "temperature", 0.1) if _prov else 0.1

        from pagefolio.ocr import _resolve_api_key
        from pagefolio.ocr_providers import OCRAPIKeyError

        if name == "claude":
            # claude: build_provider 経由でキー注入（D-01/D-05）
            session_keys = getattr(self.app, "_session_api_keys", {})
            try:
                api_key = _resolve_api_key("claude", session_keys)
            except OCRAPIKeyError:
                api_key = ""
            self.provider = build_provider(
                self.app.settings,
                api_key=api_key,
                plugin_manager=getattr(self.app, "plugin_manager", None),
            )
        elif name == "gemini":
            # gemini: build_provider 経由でキー注入（D-01/D-05/T-06-11）
            session_keys = getattr(self.app, "_session_api_keys", {})
            try:
                api_key = _resolve_api_key("gemini", session_keys)
            except OCRAPIKeyError:
                api_key = ""
            self.provider = build_provider(
                self.app.settings,
                api_key=api_key,
                plugin_manager=getattr(self.app, "plugin_manager", None),
            )
        elif name == "ollama":
            from pagefolio.ocr_providers import OllamaProvider

            self.provider = OllamaProvider(
                url=url,
                model=model,
                timeout=self._effective_timeout,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        elif name == "runpod":
            session_keys = getattr(self.app, "_session_api_keys", {})
            try:
                api_key = _resolve_api_key("runpod", session_keys)
            except OCRAPIKeyError:
                api_key = ""
            self.provider = build_provider(
                self.app.settings,
                api_key=api_key,
                plugin_manager=getattr(self.app, "plugin_manager", None),
            )
        elif name in ("lmstudio", "", "off"):
            # lmstudio / off: ライブ値で再生成（CR-02 後方互換）
            from pagefolio.ocr_providers import LMStudioProvider

            self.provider = LMStudioProvider(
                url=url,
                model=model,
                timeout=self._effective_timeout,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        else:
            # H-2: tesseract / プラグイン登録プロバイダは build_provider で再生成
            # （else で LMStudioProvider を生成すると tesseract 選択時に画像が
            #  LM Studio URL へ送信される重大な誤動作が発生する）
            self.provider = build_provider(
                self.app.settings,
                plugin_manager=getattr(self.app, "plugin_manager", None),
            )

        # H-3: provider 再生成後に concurrency を max_concurrency 以下に再クランプ
        # （lmstudio→gemini 切替時など max_concurrency が変わる場合に対応）
        self.concurrency = max(1, min(self.provider.max_concurrency, self.concurrency))

        # producer-consumer: バッファ初期化 → consumer 先行起動 → producer 開始
        # バッファ上限 = concurrency + 1（余裕係数 1 でワーカー飢えを防止・D-02）
        self._render_queue = queue.Queue(maxsize=self.concurrency + 1)
        self._render_idx = 0
        # M-2: 世代カウンタをインクリメントしローカルに捕捉する。
        # ワーカー起動後に旧世代の after コールバックを無効化するため。
        self._run_gen += 1
        gen = self._run_gen
        # consumer（ワーカー）を先に起動してから producer（レンダリング）を開始する
        self._start_worker_thread(gen)
        self._render_next_page(gen)

    def _render_next_page(self, gen=None):
        """メインスレッド（生産者）: 1 ページ render → キューに積む（after(0) 連鎖）。

        fitz アクセスはここのみ（D-04 必達）。M-1: put_nowait で non-blocking。
        M-2: gen 不一致または winfo_exists() False なら早期 return（世代ガード）。
        全ページ完了またはキャンセル時に None 終了シグナルで worker を終わらせる。
        """
        # M-2: 世代ガード（ダイアログ破棄後 / キャンセル→再実行の旧コールバック排除）
        if gen is not None and gen != self._run_gen:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        if self._cancel_flag.is_set():
            # キャンセル: 全ワーカー分の終了シグナルを送る（CR-01 Pitfall-E）
            for _ in range(self.concurrency):
                try:
                    self._render_queue.put_nowait(None)
                except queue.Full:
                    pass
            self._finish_cancelled()
            return

        total = len(self._run_pages)
        idx = self._render_idx

        if idx >= total:
            # 全ページ完了: 全ワーカー分の終了シグナルを送る（CR-01 Pitfall-E）
            # M-1: put_nowait で non-blocking に送信。Full なら after(100) で再試行。
            sent = 0
            for _ in range(self.concurrency):
                try:
                    self._render_queue.put_nowait(None)
                    sent += 1
                except queue.Full:
                    break
            if sent < self.concurrency:
                g = gen
                self.after(100, lambda _g=g: self._render_next_page(_g))
            return  # _finish_complete は最終ワーカーが呼ぶ

        page_idx = self._run_pages[idx]

        try:
            page = self.doc[page_idx]
            # D-05: has_embedded_text / get_text / page_to_png_b64 はメインスレッドのみ
            # _force_ocr=True なら埋め込みテキストを無視して全ページ Vision OCR する
            if not self._force_ocr and has_embedded_text(page):
                # 埋め込みテキストあり: results に直接投入しスキップ（D-03 統合対象）
                # T-04-09: 抽出テキストをログへ混入させない
                extracted = page.get_text()
                self.results[page_idx] = extracted
                self._skipped_pages.add(page_idx)
                # スキップはキューに積まず次ページへ（progress bar を after で更新）
                # 今回の実行分の処理済み数 = Vision 完了数 + 今回の新規スキップ数
                with self._done_lock:
                    done_disp = (
                        self._done_count + len(self._skipped_pages) - self._skip_base
                    )
                total_pages = len(self._run_pages)
                self.after(
                    0,
                    lambda d=done_disp, t=total_pages: self.progress_var.set(
                        self._L["ocr_progress_ocr"].format(
                            done=d, total=t, page=page_idx + 1
                        )
                    ),
                )
                self.after(0, lambda d=done_disp: self._on_progress_bar(d))
            else:
                # 埋め込みテキストなし: Vision OCR のためレンダリングしてキューへ積む
                b64 = page_to_png_b64(page, scale=self._ocr_scale)
                # M-1: put_nowait で non-blocking に積む。Full なら同一ページを
                # after(100) で再スケジュール（_render_idx を進めない）。
                try:
                    self._render_queue.put_nowait((page_idx, b64))
                except queue.Full:
                    # キューが満杯: このページを再試行（_render_idx 不変）
                    g = gen
                    self.after(100, lambda _g=g: self._render_next_page(_g))
                    return
        except Exception as e:
            logger.exception("ページ処理失敗 (p.%d): %s", page_idx, e)
            self.errors[page_idx] = f"image conversion error: {e}"

        self._render_idx += 1
        # 次のページを after(0) で連鎖（UI フリーズ回避）
        g = gen
        self.after(0, lambda _g=g: self._render_next_page(_g))

    def _start_worker_thread(self, gen=None):
        """consumer（ワーカー）スレッドを self.concurrency 本起動する（CR-01）。

        producer 開始前に先行起動する。全ワーカー終了後に最終ワーカーが
        終了処理（_render_results_ordered / _finish_complete 等）を一度だけ呼ぶ。
        M-2: gen を各ワーカーに伝搬して世代ガードを有効化する。
        """
        self._worker_threads = []
        self._workers_remaining = self.concurrency
        for _ in range(self.concurrency):
            t = threading.Thread(target=self._worker, args=(gen,), daemon=True)
            t.start()
            self._worker_threads.append(t)

    def _worker(self, gen=None):
        """バックグラウンドスレッド（消費者）: キューから取り出して API 送信。

        fitz/get_pixmap/page_to_png_b64/self.doc[ は一切使用しない（D-04 必達）。
        キューから取り出した b64 は送信後に即座に del する（成功基準2・T-06-06）。
        統合プログレス（処理済み done+skipped/total）で進捗を表示する（D-03）。
        CR-01: 複数ワーカーが共有 done カウンタを Lock 配下で更新する。
               最終ワーカーのみ終了処理（_render_results_ordered / _finish_*）を呼ぶ。
        M-2: gen 不一致時は after 投函前にガードして TclError を防ぐ。
        """

        total = len(self._run_pages)

        while True:
            try:
                item = self._render_queue.get(timeout=1.0)
            except queue.Empty:
                # タイムアウト: キャンセル確認（Pitfall-E）
                if self._cancel_flag.is_set():
                    break
                continue

            if item is None:
                break  # 完了シグナル

            page_idx, b64 = item
            try:
                with self._done_lock:
                    has_fatal = self._fatal_msg is not None
                if self._cancel_flag.is_set() or has_fatal:
                    # キャンセル or 致命的エラー後は API 呼び出しをスキップ
                    continue

                # OCRRetryableError は run_parallel と同じ指数バックオフでリトライ
                from pagefolio.ocr_providers import OCRRetryableError

                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        text, truncated = self.provider.ocr_image_ex(
                            b64, self._ocr_prompt
                        )
                        self._record_page_success(page_idx, text, truncated=truncated)
                        break
                    except OCRRetryableError as e:
                        if attempt >= MAX_RETRIES:
                            # リトライ上限到達: 連続失敗ならサーキットブレーカー発動
                            self._record_retryable_failure(page_idx, str(e))
                            break
                        # M-5: interruptible_sleep でキャンセル応答性向上
                        from pagefolio.ocr import (
                            clamp_retry_after,
                            interruptible_sleep,
                        )

                        # D-06: 実待機秒（delay）を待機文言生成より前に算出し、
                        # 表示する秒数が実待機値（クランプ後）と一致するようにする
                        raw_delay = (
                            e.retry_after
                            if e.retry_after is not None
                            else 1.0 * (2 ** (attempt - 1))
                        )
                        delay = clamp_retry_after(raw_delay)
                        # リトライ待機中の進捗表示（D-15）
                        # M-2: 世代ガード後にのみ after を投函する
                        if gen is None or gen == self._run_gen:
                            wait_key = self._retry_wait_key(e)
                            msg = self._build_retry_wait_message(
                                wait_key, page_idx, attempt, delay
                            )
                            try:
                                self.after(0, lambda m=msg: self.progress_var.set(m))
                            except tk.TclError:
                                pass
                        interruptible_sleep(delay, self._cancel_flag.is_set)
                    except ConnectionError as e:
                        with self._done_lock:
                            if self._fatal_msg is None:
                                self._fatal_msg = str(e)
                                self._fatal_kind = "connection"
                            self._done_count += 1
                        break
                    except TimeoutError as e:
                        with self._done_lock:
                            if self._fatal_msg is None:
                                self._fatal_msg = str(e)
                                self._fatal_kind = "timeout"
                            self._done_count += 1
                        break
                    except RuntimeError as e:
                        self.errors[page_idx] = str(e)
                        with self._done_lock:
                            self._done_count += 1
                        break
                    except Exception as e:
                        logger.exception("OCR 呼び出し失敗: %s", e)
                        self.errors[page_idx] = str(e)
                        with self._done_lock:
                            self._done_count += 1
                        break
            finally:
                del b64  # 送信後即座に破棄（成功基準2・T-06-06）

            # 統合プログレス更新（処理済み = done + 今回の新規スキップ・D-03）
            # M-2: 世代ガード後にのみ after を投函する
            if gen is None or gen == self._run_gen:
                skipped_count = len(self._skipped_pages) - self._skip_base
                with self._done_lock:
                    total_done = self._done_count + skipped_count
                try:
                    self.after(
                        0,
                        lambda d=total_done, p=page_idx: self.progress_var.set(
                            self._L["ocr_progress_ocr"].format(
                                done=d, total=total, page=p + 1
                            )
                        ),
                    )
                    self.after(0, lambda d=total_done: self._on_progress_bar(d))
                except tk.TclError:
                    pass

        # CR-01: 残ワーカー数を減らし、最終ワーカーのみ終了処理を実行する
        with self._done_lock:
            self._workers_remaining -= 1
            is_last = self._workers_remaining == 0
            fatal_msg = self._fatal_msg
            fatal_kind = self._fatal_kind

        if not is_last:
            return  # 最終ワーカー以外は何もしない

        # M-2: 世代ガード後にのみ終了処理 after を投函する
        if gen is not None and gen != self._run_gen:
            return

        # 最終ワーカーが終了処理を一度だけ実行
        if fatal_msg is not None:
            try:
                self.after(
                    0,
                    lambda m=fatal_msg, k=fatal_kind: self._finish_error(m, kind=k),
                )
            except tk.TclError:
                pass
            return
        if self._cancel_flag.is_set():
            try:
                self.after(0, self._finish_cancelled)
            except tk.TclError:
                pass
            return
        try:
            self.after(0, self._render_results_ordered)
            self.after(0, self._finish_complete)
        except tk.TclError:
            pass

    # ── UI 更新（メインスレッド） ──
    def _on_progress_bar(self, done):
        """進捗バーの値だけを更新する（テキスト挿入なし）"""
        self.progress_bar["value"] = done

    def _insert_markdown(self, text):
        """parse_markdown の戻り値を text へ整形挿入する薄い描画ヘルパー。

        preset == "markdown" の本文のみで呼ばれる（Pitfall 2: text/table や
        Tesseract/LMStudio 素出力には当てない構造的ガードは呼び出し側）。
        各 span を insert し inline_tag があれば tag_add、行末で行レベルタグ
        （kind）を行全体へ tag_add する（04-RESEARCH.md:137-146）。整形は表示
        専用でコピー/保存（_format_full_text）は raw 維持（Pitfall 5）。
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

    def _render_results_ordered(self):
        """results / errors をページ順に text へ流し込む（並列実行後の一括描画）"""
        # preset == "markdown" のときのみ整形描画（Pitfall 2 構造的ガード）。
        # text/table や Tesseract/LMStudio 素出力には Markdown パーサを当てない。
        markdown = self.preset_var.get() == "markdown"
        for page_idx in self.page_indices:
            sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
            self.text.insert("end", f"\n{sep}\n")
            if page_idx in self._skipped_pages:
                # D-08: 埋め込みテキストスキップをスキップ通知と共に表示
                skip_notice = self._L["ocr_text_skip_notice"].format(page=page_idx + 1)
                self.text.insert("end", f"[{skip_notice}]\n")
                if page_idx in self.results:
                    self._insert_results_body(page_idx, markdown)
            elif page_idx in self.results:
                self._insert_results_body(page_idx, markdown)
                # D-05: max_tokens 途切れページは部分テキストの後に専用文言を併記
                if page_idx in self._truncated_pages:
                    notice = self._L["ocr_err_truncated"].format(page=page_idx + 1)
                    self.text.insert("end", f"[{notice}]\n")
            elif page_idx in self.errors:
                self.text.insert(
                    "end",
                    self._L["ocr_page_error"].format(error=self.errors[page_idx])
                    + "\n",
                )
        self.text.see("end")

    def _insert_results_body(self, page_idx, markdown):
        """results 本文の挿入のみを担う。markdown のときだけ整形描画する。

        markdown == False のときは従来の素朴 insert を完全に温存（後方互換）。
        """
        if markdown:
            self._insert_markdown(self.results[page_idx])
        else:
            self.text.insert("end", self.results[page_idx] + "\n")

    def _finish_complete(self):
        if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
            return
        self._done = True
        if self._cancel_flag.is_set():
            self.progress_var.set(self._L["ocr_cancelled"])
        elif self.errors:
            # エラーページありの完了: 件数を明示し警告色で表示する
            self.progress_var.set(
                self._L["ocr_complete_with_errors"].format(
                    count=len(self.results),
                    total=len(self.page_indices),
                    err=len(self.errors),
                )
            )
            self._progress_label.configure(fg=C["WARNING"])
        else:
            self.progress_var.set(
                self._L["ocr_complete"].format(
                    count=len(self.results), total=len(self.page_indices)
                )
            )
        self.cancel_btn.state(["disabled"])
        # 一部ページがエラーのまま完了した場合は再開案内を追記する
        self._append_resume_hint()
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])
        self._after_run_ui_reset()

    def _finish_cancelled(self):
        if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
            return
        self._done = True
        self.progress_var.set(self._L["ocr_cancelled"])
        self.cancel_btn.state(["disabled"])
        if self.results or self.errors:
            self._render_results_ordered()
        self._append_resume_hint()
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])
        self._after_run_ui_reset()

    def _finish_error(self, msg, kind):
        if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
            return
        self._done = True
        if kind == "connection":
            user_msg = self._L["ocr_err_connection"].format(
                url=self.url_var.get(), error=msg
            )
        elif kind == "timeout":
            user_msg = self._L["ocr_err_timeout"].format(
                timeout=getattr(self, "_effective_timeout", self.timeout_var.get()),
                error=msg,
            )
        elif kind == "circuit_breaker":
            # サーキットブレーカー: 連続失敗による中断（成功済み結果は保持）
            user_msg = self._L["ocr_err_circuit_breaker"].format(
                n=CB_CONSECUTIVE_FAILURES, error=msg
            )
        else:
            user_msg = msg
        self.progress_var.set(self._L["ocr_failed"])
        self._progress_label.configure(fg=C["WARNING"])
        if self.results or self.errors:
            self._render_results_ordered()
        self.text.insert("end", "\n" + user_msg + "\n")
        self._append_resume_hint()
        self.text.see("end")
        self.cancel_btn.state(["disabled"])
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])
        self._after_run_ui_reset()

    def _append_resume_hint(self):
        """部分的に成功している場合、未処理ページ数と再開案内を結果欄に追記する"""
        if not self._can_resume():
            return
        pending = self._pending_pages()
        self.text.insert(
            "end",
            self._L["ocr_resume_hint"].format(n=len(pending), first=pending[0] + 1)
            + "\n",
        )
        self.text.see("end")

    # ── 操作 ──
    def _on_cancel(self):
        # キャンセルボタンは実行中のみ有効
        self._cancel_flag.set()
        self.cancel_btn.state(["disabled"])
        self.progress_var.set(self._L["ocr_cancelling"])

    def _on_close(self):
        # 未開始または完了済みなら確認なしで閉じる
        if not self._started or self._done:
            # M-2: 閉じる前に世代を無効化し旧ワーカーの after を排除する
            self._run_gen += 1
            self.destroy()
            return
        ok = messagebox.askyesno(
            self._L["confirm_title"],
            self._L["ocr_close_during_run"],
            parent=self,
        )
        if not ok:
            return
        self._cancel_flag.set()
        # M-2: 閉じる前に世代を無効化し旧ワーカーの after を排除する
        self._run_gen += 1
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
