# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR ダイアログ — 進行表示・キャンセル・結果エクスポート"""

import logging
import queue
import threading
import time
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
    resolve_summary_prompt,
)
from pagefolio.ocr_pipeline import (
    PipelineState,
    consume_one,
    send_sentinels,
    try_enqueue,
)

logger = logging.getLogger(__name__)

# M-6: モデル別単価テーブル（$/MTok, 入力, 出力）
# キーに完全一致しない場合は suffix ルールで判定するフォールバックへ進む
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
# フォールバック単価（不明モデル）
_PRICE_FALLBACK = (5.0, 25.0)

# サーキットブレーカー: リトライ上限到達がこのページ数連続したら実行を中断する
# （サーバ側が完全に落ちている時に全ページ × リトライ待機を消化しないための保険）
CB_CONSECUTIVE_FAILURES = 3

# サマリ生成専用のタイムアウト下限（秒）。全ページ連結テキストの要約は
# OCR 1 ページより大幅に長いため、provider.timeout がこれ未満なら実行中のみ
# 引き上げる（_on_summary で退避 → _summary_ui_reset で復元）
SUMMARY_TIMEOUT_MIN = 300

# サマリ入力がこの文字数を超えたら追加確認を出す（コンテキスト長超過の事前警告。
# トークン厳密概算はモデル依存で不可能なため文字数閾値の警告に留める）
SUMMARY_TOO_LONG_CHARS = 200_000


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
        # D-01/D-02: producer-consumer 共有状態（done カウンタ・fatal 情報・
        # サーキットブレーカーカウンタ・残ワーカー数）は ocr_pipeline.PipelineState
        # へ一本化した（_start_worker_thread で concurrency 本分を渡して生成）。
        self._pstate = None
        # L-6a: レンダー失敗ページ集合（_skipped_pages と同型で進捗計上に使う）
        self._render_failed_pages = set()
        self._render_failed_base = 0  # 今回実行開始時点のレンダー失敗済み数
        # M-2: 世代カウンタ（ダイアログ破棄後の旧ワーカー after コールバックを無効化）
        # viewer.py の _preview_gen と同じパターン（世代一致 + winfo_exists）
        self._run_gen = 0
        # 全ページ統合サマリ（OCR 完了後に「サマリ作成」で手動トリガー）
        self.summary_result = None  # str | None（成功時のサマリ本文・raw）
        self._summary_truncated = False  # サマリ応答が max_tokens で途切れたか
        self._summary_running = False
        # OCR 用 _cancel_flag とは分離する。OCR キャンセル直後は旧ワーカーが
        # queue ループに残留している可能性があり、サマリ開始時に clear() すると
        # 旧ワーカーがキャンセル確認で抜けられなくなるため共有しない。
        self._summary_cancel_flag = threading.Event()
        # サマリ実行中のみ provider.timeout を引き上げるための退避値
        self._summary_prev_timeout = None
        # サマリ進捗表示（indeterminate パルス + 経過秒数ティッカー）
        self._summary_tick_id = None  # after id（ティッカー再スケジュール用）
        self._summary_base_msg = ""  # ティッカーが合成するベース文言
        self._summary_started_at = 0.0  # time.monotonic() 開始時刻

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
        # 詳細設定行 + 結果領域 + 右ペイン（縦積みボタン群）が収まる横幅
        w = max(1150, int(fs * 90))
        # 設定行(プロンプト/サーバ/モデル/詳細) + 進行表示 + 結果領域/右ペイン
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

        # 進行表示
        # self 属性化: ライブ更新時に各種欄を before= でこのラベルの前へ戻す
        self.progress_var = tk.StringVar(value=self._L["ocr_run_first"])
        self._progress_label = tk.Label(
            self,
            textvariable=self.progress_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(0, "bold"),
        )
        self._progress_label.pack(pady=(4, 2))

        # D-07: Tesseract 言語段階的縮退のフォールバック非モーダル注記
        # （WARNING 色・実行は止めない・OCR 結果 raw には混入させない）。
        # フォールバック未発生時は空文字のまま非表示（pack しない）。
        self._lang_fallback_notice_var = tk.StringVar(value="")
        self._lang_fallback_label = tk.Label(
            self,
            textvariable=self._lang_fallback_notice_var,
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        )

        self.progress_bar = ttk.Progressbar(
            self, mode="determinate", maximum=max(1, len(self.page_indices))
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))

        # 結果テキスト + 右ペイン（操作ボタン群）
        # ボタンを下部の横一列に置くと初期ウィンドウ幅次第で右端側のボタンが
        # クリップされて隠れるため、メイン画面と同じ「セクション見出し +
        # 縦積みボタン」の右ペイン構成にする（幅不足で隠れる構造を排除）。
        body = tk.Frame(self, bg=C["BG_DARK"])
        body.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        side = tk.Frame(body, bg=C["BG_PANEL"])
        side.pack(side="right", fill="y", padx=(10, 0))

        result_frame = tk.Frame(body, bg=C["BG_PANEL"])
        result_frame.pack(side="left", fill="both", expand=True)
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

        # 右ペインのセクション/ボタン生成ヘルパー（ui_builder._build_tools と同構成）
        def section(title):
            f = tk.Frame(side, bg=C["BG_CARD"], bd=0)
            f.pack(fill="x", padx=8, pady=5)
            tk.Label(
                f,
                text=title,
                bg=C["BG_CARD"],
                fg=C["WARNING"],
                font=self._font(-1, "bold"),
            ).pack(anchor="w", padx=8, pady=(6, 2))
            return f

        def side_btn(sec, text, cmd, style="TButton"):
            b = ttk.Button(sec, text=text, command=cmd, style=style)
            b.pack(fill="x", padx=8, pady=2)
            return b

        # 閉じるは右ペイン最下部に固定（セクション外・誤操作分離）
        self.close_btn = ttk.Button(
            side,
            text=self._L["btn_close"],
            command=self._on_close,
        )
        self.close_btn.pack(side="bottom", fill="x", padx=8, pady=(4, 8))

        # 実行セクション（読み取り実行 / 続きから再実行 / キャンセル）
        f_run = section(self._L["ocr_sec_run"])
        self.run_btn = side_btn(
            f_run, self._L["ocr_run"], self._on_run, "Accent.TButton"
        )
        # 続きから再実行（エラー/未処理ページのみ・成功済み結果は保持）
        self.resume_btn = side_btn(
            f_run, self._L["ocr_resume"], lambda: self._on_run(resume=True)
        )
        self.resume_btn.state(["disabled"])
        self.cancel_btn = side_btn(
            f_run, self._L["ocr_cancel"], self._on_cancel, "Danger.TButton"
        )
        self.cancel_btn.state(["disabled"])
        # セクション最下段ボタンの下余白（見出し〜ボタン列の枠内バランス）
        tk.Frame(f_run, bg=C["BG_CARD"], height=6).pack(fill="x")

        # 結果セクション（コピー / 保存 / サマリ / クリア）
        f_result = section(self._L["ocr_sec_result"])
        self.copy_btn = side_btn(f_result, self._L["ocr_copy"], self._copy_to_clipboard)
        self.copy_btn.state(["disabled"])
        self.save_btn = side_btn(f_result, self._L["ocr_save"], self._save_to_file)
        self.save_btn.state(["disabled"])
        # 全ページ統合サマリ（OCR 完了後に有効化・supports_text_prompt 必須）
        self.summary_btn = side_btn(
            f_result, self._L["ocr_summary_btn"], self._on_summary
        )
        self.summary_btn.state(["disabled"])
        self.clear_btn = side_btn(f_result, self._L["ocr_clear"], self._clear_text)
        tk.Frame(f_result, bg=C["BG_CARD"], height=6).pack(fill="x")

    def _clear_text(self):
        """結果テキストエリア・進行表示・実行状態を初期化する"""
        # 実行中（OCR / サマリ生成）はクリア不可（キャンセルしてから再度押す想定）
        if self._started and not self._done:
            return
        if self._summary_running:
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
        # サマリ状態も破棄（旧サマリを新しい実行へ持ち込まない）
        self.summary_result = None
        self._summary_truncated = False
        self._summary_cancel_flag.clear()
        self.summary_btn.state(["disabled"])
        # H-6: 前回実行の致命的エラー・完了カウンタを破棄する（PipelineState ごと）。
        # 残留すると再実行時に全ワーカーが is_fatal()=True で API 呼び出しを
        # スキップし、旧エラーで即終了してしまう（タイムアウト後の再実行バグ）。
        self._pstate = None
        self._render_failed_pages.clear()
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
        self._update_summary_btn_state()

    def _update_summary_btn_state(self):
        """サマリ作成ボタンの有効/無効を再評価する。

        OCR 結果があり、サマリ生成中でなく、かつ現在のプロバイダがテキストの
        み補完に対応している場合のみ有効化する（Tesseract 等の非 LLM
        プロバイダは構造的に無効のまま・三重ガードの 1 段目）。
        """
        ok = (
            bool(self.results)
            and not self._summary_running
            and getattr(self.provider, "supports_text_prompt", False)
        )
        self.summary_btn.state(["!disabled"] if ok else ["disabled"])

    # ── ページ結果記録（ワーカースレッドから呼ばれる・Lock 保護） ──

    def _record_page_success(self, page_idx, text, truncated=False):
        """ページ成功時の結果辞書ブックキーピング（consume_one の on_success 用）。

        truncated=True のとき当該ページを _truncated_pages に登録する。
        途切れは「成功＋警告」であり部分テキストは破棄せず results に保持する
        （D-05）。途切れ通知は _render_results_ordered で当該ページに併記する。
        done カウンタ/連続失敗カウンタのリセットは ocr_pipeline.consume_one が
        呼び出し前に PipelineState.record_success() 経由で済ませている
        （D-01/D-02・二重計上防止のためここでは触らない）。
        """
        self.results[page_idx] = text
        if truncated:
            self._truncated_pages.add(page_idx)
        else:
            self._truncated_pages.discard(page_idx)

    def _record_page_error(self, page_idx, msg):
        """非致命的ページエラー時の結果辞書ブックキーピング（consume_one の
        on_page_error コールバック）。

        リトライ上限到達（サーキットブレーカー判定含む）・RuntimeError・
        その他 Exception のいずれの経路でも呼ばれる。カウンタ更新/サーキット
        ブレーカー判定は ocr_pipeline.consume_one が呼び出し前に
        PipelineState.record_retryable_failure()/record_page_error() 経由で
        済ませている（D-01/D-02・二重計上防止のためここでは触らない）。
        """
        self.errors[page_idx] = msg

    def _done_disp(self):
        """今回実行分の「処理済み」件数（進捗バー/進捗文言表示用）を算出する。

        Vision OCR 完了数（PipelineState.done_count）+ 今回の新規スキップ数
        （埋め込みテキスト検出）+ 今回の新規レンダー失敗数、の合計。レンダー
        失敗ページも「処理済み」として計上することで、進捗が全ページ数
        （100%）に到達するようにする（L-6a）。
        """
        done_count = self._pstate.done_count if self._pstate is not None else 0
        skipped = len(self._skipped_pages) - self._skip_base
        render_failed = len(self._render_failed_pages) - self._render_failed_base
        return done_count + skipped + render_failed

    # ── クラウドプロバイダ判定・コスト確認・セッションキー ──

    def _provider_display_name(self):
        """現在の ocr_provider 設定を人間可読なプロバイダ表示名に変換する。

        claude → "Claude (Anthropic)"・gemini → "Gemini (Google AI)"
        runpod → "RunPod (Serverless)"・lmstudio/"" → "LM Studio"。
        未知の名前はそのまま返す（フォールバック）。
        """
        from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider

        name = self.app.settings.get("ocr_provider", "")
        if name == "claude" or isinstance(self.provider, ClaudeProvider):
            return self._L["ocr_provider_name_claude"]
        if name == "gemini" or isinstance(self.provider, GeminiProvider):
            return self._L["ocr_provider_name_gemini"]
        if name == "tesseract":
            return self._L["ocr_provider_name_tesseract"]
        if name == "runpod":
            return self._L["ocr_provider_name_runpod"]
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

    # ── LLM 設定ボタン・ライブ更新 ──────────────────────────────────────────

    def _open_llm_config(self):
        """プロバイダ表示行の「⚙ LLM 設定…」ボタンから LLMConfigDialog を開く。

        実行中（_started かつ未完了、またはサマリ生成中）は即 return して
        プロバイダ変更を阻止する（T-CCZ-02・スレッド安全確保）。
        既に開いている場合も二重起動せず既存ウィンドウを前面へ出す。
        """
        if self._started and not self._done:
            return
        if self._summary_running:
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
            session_api_keys=getattr(self.app, "_session_api_keys", None),
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
            # D-07: Tesseract 段階的縮退フォールバックの非モーダル注記を更新
            self._maybe_show_lang_fallback_notice()
        except Exception as e:
            logger.error("provider 再生成に失敗しました: %s", e)
            lang = self.app.settings.get("lang", "ja")
            self.progress_var.set(LANG[lang]["ocr_provider_rebuild_error"].format(e=e))
        # L-6j: "off" 切替時にメイン画面ツールバーの OCR ボタン状態を同期する。
        # provider 再生成が例外で失敗しても必ず実行されるよう try/except の
        # 外側（Pitfall 6）に置く。app 属性は既存の防御的パターン（getattr
        # フォールバック）に倣い、SimpleNamespace スタブとの後方互換を保つ。
        update_ocr_buttons = getattr(self.app, "_update_ocr_buttons_state", None)
        if callable(update_ocr_buttons):
            update_ocr_buttons()
        # provider 差し替えで supports_text_prompt が変わり得るため再評価する
        self._update_summary_btn_state()

    def _maybe_show_lang_fallback_notice(self):
        """D-07: TesseractProvider の段階的縮退フォールバックを検知したら
        非モーダル WARNING 注記を表示する（実行は止めない）。

        フォールバック非発生時（他プロバイダ選択時含む）は注記を消す。
        OCR 結果テキスト（self.text・raw コピー/保存対象）には一切書き込まない
        （V16-D-02 のコピー/保存 raw 維持方針と整合）。provider 再生成の都度
        呼ばれるだけで OCR 実行中（1ページごと）には呼ばれないため、
        同一実行内で複数ページがあっても注記は実質的に1回のみ更新される。
        """
        provider = getattr(self, "provider", None)
        fallback = bool(
            provider is not None and getattr(provider, "lang_fallback", False)
        )
        if fallback:
            requested = getattr(provider, "requested_lang", "") or ""
            effective = getattr(provider, "effective_lang", "") or ""
            msg = self._L["ocr_tesseract_lang_fallback_notice"].format(
                requested=requested, effective=effective
            )
            self._lang_fallback_notice_var.set(msg)
            if not self._lang_fallback_label.winfo_ismapped():
                self._lang_fallback_label.pack(before=self.progress_bar, pady=(0, 4))
        else:
            self._lang_fallback_notice_var.set("")
            if self._lang_fallback_label.winfo_ismapped():
                self._lang_fallback_label.pack_forget()

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
        """プロバイダ依存 UI（表示ラベル・LM Studio 欄）を再評価する。

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
          1. 送信先ホスト（プロバイダ別: claude→api.anthropic.com/gemini→googleapis
             /runpod→ユーザー設定の runpod_url）
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
        elif name == "runpod":
            model = self.app.settings.get("runpod_model", "") or "runpod"
            host = (
                self.app.settings.get("runpod_url", "")
                or self._L["llm_runpod_host_unset"]
            )
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

    def _confirm_summary_cost(self, char_count):
        """サマリ生成前のクラウド送信確認ダイアログを表示し、選択を bool で返す。

        _confirm_cost と同方針で毎回表示する（D-11）。画像ではなく OCR 結果
        テキストの送信であることと概算文字数を明示する。

        引数:
          char_count: 送信する全ページ連結テキストの文字数
        """
        name = self.app.settings.get("ocr_provider", "")
        if name == "gemini":
            host = "generativelanguage.googleapis.com"
        elif name == "runpod":
            host = (
                self.app.settings.get("runpod_url", "")
                or self._L["llm_runpod_host_unset"]
            )
        else:
            # claude（デフォルト・_confirm_cost と同じフォールバック）
            host = "api.anthropic.com"
        msg = self._L["ocr_summary_cost_confirm_msg"].format(
            host=host,
            chars=char_count,
        )
        return messagebox.askyesno(
            self._L["ocr_cost_confirm_title"],
            msg,
            parent=self,
        )

    def _check_cloud_api_key(self):
        """クラウド実行前に APIキーが解決可能か確認する（成功基準2・撤去後の代替）。

        入力 UI は LLMConfigDialog に一元化されたため、この関数は値の収集を
        一切行わず _resolve_api_key の解決可否のみを確認する（値の保持・返却は
        しない）。未解決なら3プロバイダ別の明示エラーを表示して False を返す。
        _on_run と _on_summary の共有経路。
        """
        if not self._is_cloud_provider():
            return True
        from pagefolio.ocr import _resolve_api_key
        from pagefolio.ocr_providers import OCRAPIKeyError

        name = self.app.settings.get("ocr_provider", "")
        session_keys = getattr(self.app, "_session_api_keys", {})
        try:
            _resolve_api_key(name, session_keys)
        except OCRAPIKeyError:
            msg_key = {
                "claude": "ocr_api_key_missing",
                "gemini": "ocr_api_key_missing_gemini",
                "runpod": "ocr_api_key_missing_runpod",
            }.get(name, "ocr_api_key_missing")
            env_var = {
                "claude": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "runpod": "RUNPOD_API_KEY",
            }.get(name, "")
            messagebox.showerror(
                self._L["err_title"],
                self._L[msg_key].format(env_var=env_var),
                parent=self,
            )
            return False
        return True

    # ── ワーカー ──
    def _on_run(self, resume=False):
        """読み取り実行 / 続きから再実行: OCR を開始する。

        メインスレッドでレンダリング/埋め込み判定後にワーカーを起動する。
        クラウドプロバイダ時は実行前にコスト確認ゲートを挟む（成功基準5・D-13）。

        引数:
          resume: True なら成功済み結果を保持し、エラー/未処理ページのみ
                  再実行する（リスタート）。False は全ページ再実行（リラン）。
        """
        if self._started or self._summary_running:
            return

        # 今回の実行対象を決定（再開時は未処理ページのみ）
        resume = resume and self._can_resume()
        run_pages = self._pending_pages() if resume else list(self.page_indices)
        if not run_pages:
            return

        # ── クラウド実行ゲート（_started を True にする前）──
        if self._is_cloud_provider():
            # APIキー解決確認（成功基準2・T-05-19）
            if not self._check_cloud_api_key():
                return

            # コスト確認ダイアログ（毎回・D-11・D-12。再開時は未処理ページ数で見積）
            if not self._confirm_cost(len(run_pages)):
                # キャンセル → OCR を始めない（成功基準5）
                return

        self._started = True
        self._done = False
        # H-6: 実行開始時に前回実行の致命的エラー・完了カウンタを必ず破棄する
        # （_clear_text を経由しない再実行経路でも残留状態を持ち込まないため）。
        # 実際の PipelineState は _start_worker_thread で concurrency 確定後に生成する。
        self._pstate = None
        self._cancel_flag.clear()
        # 再実行で結果セットが変わるため旧サマリは破棄する
        # （_render_results_ordered は results のみ再描画するため表示からも消える）
        self.summary_result = None
        self._summary_truncated = False
        self._summary_cancel_flag.clear()
        self.summary_btn.state(["disabled"])
        if resume:
            # 再実行対象の旧エラー・旧途切れ状態を破棄（再実行結果で上書きするため）
            for p in run_pages:
                self.errors.pop(p, None)
                self._truncated_pages.discard(p)
                self._render_failed_pages.discard(p)  # L-6a: 再開対象は再挑戦させる
        else:
            # リラン（全体再実行）: 前回の結果・エラー・スキップ・途切れ状態を破棄
            self.results.clear()
            self.errors.clear()
            self._skipped_pages.clear()
            self._truncated_pages.clear()
            self._render_failed_pages.clear()
        self._run_pages = run_pages
        self._skip_base = len(self._skipped_pages)
        self._render_failed_base = len(self._render_failed_pages)  # L-6a
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
        # D-07: Tesseract 段階的縮退フォールバックの非モーダル注記を更新
        self._maybe_show_lang_fallback_notice()

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

        fitz アクセスはここのみ（D-04 必達）。M-1: try_enqueue で non-blocking。
        M-2: gen 不一致または winfo_exists() False なら早期 return（世代ガード）。
        全ページ完了・キャンセル・fatal 確定時に None 終了シグナルで worker を
        終わらせる（enqueue/sentinel は ocr_pipeline.try_enqueue/send_sentinels
        経由・D-01/D-02）。
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
            # WR-01: 部分送出時は残り本数のみを再試行し worker のポーリング残留を防ぐ
            sent = send_sentinels(self._render_queue, self.concurrency)
            if sent < self.concurrency:
                self._retry_sentinels(gen, self.concurrency - sent)
            self._finish_cancelled()
            return

        if self._pstate is not None and self._pstate.is_fatal():
            # L-6g: fatal 確定後は producer も残ページの render を継続しない。
            # 全ワーカー分の終了シグナルを送るのみに留め、終了処理自体は
            # 最終ワーカー側（_worker の decrement_worker 判定）に委ねる。
            # ここで直接呼んでも _finish_error の冪等ガードにより二重実行しない。
            # WR-01: 部分送出時は残り本数のみを再試行し worker のポーリング残留を防ぐ
            sent = send_sentinels(self._render_queue, self.concurrency)
            if sent < self.concurrency:
                self._retry_sentinels(gen, self.concurrency - sent)
            self._finish_error(self._pstate.fatal_msg, kind=self._pstate.fatal_kind)
            return

        total = len(self._run_pages)
        idx = self._render_idx

        if idx >= total:
            # 全ページ完了: 全ワーカー分の終了シグナルを送る（CR-01 Pitfall-E）
            # M-1: 非ブロッキングで送信。部分送出なら after(100) で残りを再試行。
            sent = send_sentinels(self._render_queue, self.concurrency)
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
                done_disp = self._done_disp()
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
                # M-1: 非ブロッキングで積む。Full なら同一ページを after(100) で
                # 再スケジュール（_render_idx を進めない）。
                if not try_enqueue(self._render_queue, (page_idx, b64)):
                    g = gen
                    self.after(100, lambda _g=g: self._render_next_page(_g))
                    return
        except Exception as e:
            logger.exception("ページ処理失敗 (p.%d): %s", page_idx, e)
            self.errors[page_idx] = f"image conversion error: {e}"
            # L-6a: レンダー失敗ページも「処理済み」として進捗計上する。
            # 計上しないと進捗バーが 100% に到達しないまま完了してしまう。
            self._render_failed_pages.add(page_idx)
            done_disp = self._done_disp()
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

        self._render_idx += 1
        # 次のページを after(0) で連鎖（UI フリーズ回避）
        g = gen
        self.after(0, lambda _g=g: self._render_next_page(_g))

    def _retry_sentinels(self, gen, remaining):
        """WR-01: キュー満杯で部分送出になった終了シグナルの残り分のみを再試行する。

        cancel / fatal 経路専用のヘルパー。send_sentinels の契約
        （「戻り値が count 未満なら残り本数のみ再試行」）を守り、
        既に送信済みの本数を再送しない。世代ガードで旧世代の再試行は無視する。
        """
        if gen is not None and gen != self._run_gen:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        sent = send_sentinels(self._render_queue, remaining)
        if sent < remaining:
            left = remaining - sent
            self.after(50, lambda _g=gen, n=left: self._retry_sentinels(_g, n))

    def _start_worker_thread(self, gen=None):
        """consumer（ワーカー）スレッドを self.concurrency 本起動する（CR-01）。

        producer 開始前に先行起動する。全ワーカー終了後に最終ワーカーが
        終了処理（_render_results_ordered / _finish_complete 等）を一度だけ呼ぶ。
        M-2: gen を各ワーカーに伝搬して世代ガードを有効化する。
        D-01/D-02: 共有状態は ocr_pipeline.PipelineState へ一本化。
        """
        self._worker_threads = []
        self._pstate = PipelineState(self.concurrency)
        for _ in range(self.concurrency):
            t = threading.Thread(target=self._worker, args=(gen,), daemon=True)
            t.start()
            self._worker_threads.append(t)

    def _worker(self, gen=None):
        """バックグラウンドスレッド（消費者）: キューから取り出し ocr_pipeline へ委譲。

        fitz/get_pixmap/page_to_png_b64/self.doc[ は一切使用しない（D-04 必達）。
        1 アイテムの処理（リトライ/バックオフ/fatal 判定）は
        ocr_pipeline.consume_one に委譲する薄いラッパー（D-01/D-02 一本化）。
        キューから取り出した b64 は consume_one 呼び出し後に即座に del する
        （成功基準2・T-06-06）。統合プログレス（処理済み done+skipped+
        render_failed/total）で進捗を表示する（D-03・L-6a）。
        CR-01: 複数ワーカーが共有 PipelineState 経由で done カウンタを更新する。
               最終ワーカーのみ終了処理（_render_results_ordered / _finish_*）を呼ぶ。
        M-2: gen 不一致時は after 投函前にガードして TclError を防ぐ。
        """

        total = len(self._run_pages)

        def _on_retry_wait(page_idx, attempt, delay, exc):
            # リトライ待機中の進捗表示（D-15）。M-2: 世代ガード後にのみ after 投函。
            if gen is None or gen == self._run_gen:
                wait_key = self._retry_wait_key(exc)
                msg = self._build_retry_wait_message(wait_key, page_idx, attempt, delay)
                try:
                    self.after(0, lambda m=msg: self.progress_var.set(m))
                except tk.TclError:
                    pass

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
                consume_one(
                    self.provider,
                    item,
                    self._ocr_prompt,
                    self._pstate,
                    cancel_check=self._cancel_flag.is_set,
                    breaker_threshold=CB_CONSECUTIVE_FAILURES,
                    on_success=lambda p, t, tr: self._record_page_success(
                        p, t, truncated=tr
                    ),
                    on_page_error=self._record_page_error,
                    on_retry_wait=_on_retry_wait,
                )
            finally:
                del b64  # 送信後即座に破棄（成功基準2・T-06-06）

            # 統合プログレス更新（処理済み = done + skip + render_failed・D-03/L-6a）
            # M-2: 世代ガード後にのみ after を投函する
            if gen is None or gen == self._run_gen:
                done_disp = self._done_disp()
                try:
                    self.after(
                        0,
                        lambda d=done_disp, p=page_idx: self.progress_var.set(
                            self._L["ocr_progress_ocr"].format(
                                done=d, total=total, page=p + 1
                            )
                        ),
                    )
                    self.after(0, lambda d=done_disp: self._on_progress_bar(d))
                except tk.TclError:
                    pass

        # CR-01: 残ワーカー数を減らし、最終ワーカーのみ終了処理を実行する
        is_last, fatal_msg, fatal_kind = self._pstate.decrement_worker()

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
        # キャンセルボタンは実行中（OCR / サマリ生成）のみ有効
        self._cancel_flag.set()
        self._summary_cancel_flag.set()
        self.cancel_btn.state(["disabled"])
        self.progress_var.set(self._L["ocr_cancelling"])

    def _on_close(self):
        # 未開始または完了済み（かつサマリ生成中でない）なら確認なしで閉じる
        running = (self._started and not self._done) or self._summary_running
        if not running:
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
        self._summary_cancel_flag.set()
        # M-2: 閉じる前に世代を無効化し旧ワーカーの after を排除する
        self._run_gen += 1
        self.destroy()

    def _format_pages_text(self):
        """ページ本文のみをセパレータ付きで連結して返す（サマリは含めない）。

        サマリ生成の LLM 入力と _format_full_text の共有経路。サマリを再生成
        するとき旧サマリが入力へ混入しないよう、サマリ本文はここに含めない。
        """
        parts = []
        for page_idx in self.page_indices:
            if page_idx not in self.results:
                continue
            sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
            parts.append(sep)
            parts.append(self.results[page_idx])
        return "\n".join(parts)

    def _format_full_text(self):
        """コピー/保存用の全文（ページ本文 + サマリ・raw 維持）を返す。"""
        text = self._format_pages_text()
        if not self.summary_result:
            return text
        parts = [text] if text else []
        parts.append(self._L["ocr_summary_separator"])
        parts.append(self.summary_result)
        return "\n".join(parts)

    # ── 全ページ統合サマリ ──
    def _on_summary(self):
        """サマリ作成: 全ページの OCR 結果テキストを LLM へ送信し統合サマリを生成。

        手動トリガー（クラウドコスト配慮）。OCR 完了後（results あり）のみ実行
        できる。実行はワーカースレッド 1 本 + _run_gen 世代ガード + サマリ専用
        キャンセルフラグで制御する。プロンプトは settings["ocr_summary_prompt"]
        （カスタム）> プロバイダ別 > 既定 の順で解決する（resolve_summary_prompt）。
        """
        if (self._started and not self._done) or self._summary_running:
            return
        if not self.results:
            return
        # 三重ガードの 2 段目（1 段目はボタン無効化・3 段目は NotImplementedError）
        if not getattr(self.provider, "supports_text_prompt", False):
            messagebox.showerror(
                self._L["err_title"],
                self._L["ocr_summary_unsupported"].format(
                    name=self._provider_display_name()
                ),
                parent=self,
            )
            return

        # メインスレッドで入力を確定（ページ本文のみ・旧サマリは含めない）
        full_text = self._format_pages_text()
        if not full_text:
            return
        name = self.app.settings.get("ocr_provider", "")
        prompt = resolve_summary_prompt(
            name, self.app.settings.get("ocr_summary_prompt", "")
        )

        # ── クラウド実行ゲート（OCR 実行時と同方針・毎回確認）──
        if self._is_cloud_provider():
            if not self._check_cloud_api_key():
                return
            if not self._confirm_summary_cost(len(full_text)):
                return

        # ── 入力過大の事前警告（コンテキスト長超過しやすい規模・全プロバイダ）──
        if len(full_text) > SUMMARY_TOO_LONG_CHARS:
            proceed = messagebox.askyesno(
                self._L["ocr_cost_confirm_title"],
                self._L["ocr_summary_too_long_confirm"].format(chars=len(full_text)),
                parent=self,
            )
            if not proceed:
                return

        # サマリ専用タイムアウト: 全ページ連結テキストは OCR 1 ページより長い
        # ため、実行中のみ provider.timeout を SUMMARY_TIMEOUT_MIN まで引き上げる
        # （サマリ中は OCR 実行ボタンが disabled のため provider は共有されない。
        # _summary_ui_reset で必ず復元する）
        self._summary_prev_timeout = getattr(self.provider, "timeout", None)
        if self._summary_prev_timeout is not None:
            self.provider.timeout = max(self._summary_prev_timeout, SUMMARY_TIMEOUT_MIN)

        # 実行状態へ遷移
        self._summary_running = True
        self._summary_cancel_flag.clear()
        self.summary_result = None
        self._summary_truncated = False
        self.run_btn.state(["disabled"])
        self.resume_btn.state(["disabled"])
        self.clear_btn.state(["disabled"])
        self.copy_btn.state(["disabled"])
        self.save_btn.state(["disabled"])
        self.summary_btn.state(["disabled"])
        self._llm_config_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.progress_var.set(self._L["ocr_summary_running"])
        self._progress_label.configure(fg=C["SUCCESS"])

        # 進捗表示: サマリは単発 API 呼び出しのため determinate バーでは
        # 一切動かない。indeterminate パルス + 経過秒数ティッカーで
        # 「処理が進行している」ことを可視化する（体感フリーズ防止）
        self._summary_base_msg = self._L["ocr_summary_running"]
        self._summary_started_at = time.monotonic()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start(12)

        # M-2: 世代を進めて捕捉する（OCR 完了後のため既存ワーカーへの副作用は
        # なく、残留していた旧 after があってもここで無効化される）
        self._run_gen += 1
        gen = self._run_gen
        self._summary_tick_id = self.after(1000, lambda: self._summary_tick(gen))
        threading.Thread(
            target=self._summary_worker, args=(gen, full_text, prompt), daemon=True
        ).start()

    def _summary_tick(self, gen):
        """サマリ実行中の経過秒数を 1 秒間隔で表示する（メインスレッド）。

        世代ガード（gen != _run_gen）または実行終了で自然停止する。
        リトライ待機文言（_set_summary_base_msg）ともここで合成される。
        """
        if gen != self._run_gen or not self._summary_running:
            return
        try:
            sec = int(time.monotonic() - self._summary_started_at)
            self.progress_var.set(
                self._L["ocr_summary_elapsed"].format(
                    msg=self._summary_base_msg, sec=sec
                )
            )
            self._summary_tick_id = self.after(1000, lambda: self._summary_tick(gen))
        except tk.TclError:
            # ダイアログ破棄後に発火した場合は静かに停止する
            self._summary_tick_id = None

    def _set_summary_base_msg(self, msg):
        """ティッカーのベース文言を更新し、経過表示を即時反映する。

        _summary_worker のリトライ待機通知から after(0) で呼ばれる。
        progress_var を直接上書きしない（次のティックで消される）ための経路。
        """
        self._summary_base_msg = msg
        sec = int(time.monotonic() - self._summary_started_at)
        self.progress_var.set(self._L["ocr_summary_elapsed"].format(msg=msg, sec=sec))

    def _summary_progress_stop(self):
        """サマリ進捗表示の停止: ティッカー解除 + バーを determinate へ復元。

        バーは OCR 完了時の満杯表示（maximum=対象ページ数）に戻す。
        成功/失敗/キャンセル共通で _summary_ui_reset から呼ばれる。
        """
        if self._summary_tick_id is not None:
            try:
                self.after_cancel(self._summary_tick_id)
            except tk.TclError:
                pass
            self._summary_tick_id = None
        try:
            self.progress_bar.stop()
            maximum = max(1, len(self.page_indices))
            self.progress_bar.configure(mode="determinate", maximum=maximum)
            self.progress_bar["value"] = maximum
        except tk.TclError:
            pass

    def _summary_worker(self, gen, full_text, prompt):
        """バックグラウンドスレッド: complete_text_ex を単発呼び出しする。

        _worker と同じリトライ規約（指数バックオフ + clamp_retry_after +
        interruptible_sleep）。キャンセル判定はサマリ専用 _summary_cancel_flag
        のみを見る。終端は世代ガード後に after(0) でメインスレッドへ投函する
        （M-2 と同パターン・tk.TclError 捕捉）。urlopen の制約上、送信中の
        1 リクエストは即時中断できない（キャンセルはリトライ待機でのみ反応）。
        """
        from pagefolio.ocr import clamp_retry_after, interruptible_sleep
        from pagefolio.ocr_providers import OCRContextLengthError, OCRRetryableError

        result = None
        error_msg = None
        error_kind = None
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
                # D-06: 実待機秒（クランプ後）を文言生成より前に算出する
                raw_delay = (
                    e.retry_after
                    if e.retry_after is not None
                    else 1.0 * (2 ** (attempt - 1))
                )
                delay = clamp_retry_after(raw_delay)
                if gen is None or gen == self._run_gen:
                    msg = self._L["ocr_summary_waiting_retry"].format(
                        n=attempt, max=MAX_RETRIES, sec=round(delay)
                    )
                    try:
                        # progress_var 直接更新ではなくベース文言更新経由
                        # （経過秒数ティッカーとの表示競合を避ける）
                        self.after(0, lambda m=msg: self._set_summary_base_msg(m))
                    except tk.TclError:
                        pass
                interruptible_sleep(delay, self._summary_cancel_flag.is_set)
            except NotImplementedError as e:
                # 三重ガードの 3 段目（プロバイダ差し替え等のすり抜け対策）
                error_msg = str(e)
                break
            except OCRContextLengthError as e:
                # 入力（全ページ連結テキスト）がコンテキスト長上限を超過。
                # リトライしても解消しないため専用ガイダンスで即中断する
                error_msg = str(e)
                error_kind = "ctx"
                break
            except TimeoutError as e:
                error_msg = str(e)
                error_kind = "timeout"
                break
            except (ConnectionError, RuntimeError) as e:
                error_msg = str(e)
                break
            except Exception as e:
                logger.exception("サマリ生成呼び出し失敗: %s", e)
                error_msg = str(e)
                break

        # M-2: 世代ガード後にのみ終了処理 after を投函する
        if gen is not None and gen != self._run_gen:
            return
        try:
            if self._summary_cancel_flag.is_set():
                self.after(0, self._on_summary_cancelled)
            elif result is not None:
                text, truncated = result
                self.after(0, lambda t=text, tr=truncated: self._on_summary_done(t, tr))
            else:
                self.after(
                    0,
                    lambda m=error_msg or "", k=error_kind: self._on_summary_error(
                        m, k
                    ),
                )
        except tk.TclError:
            pass

    def _on_summary_done(self, text, truncated):
        """サマリ生成成功（メインスレッド）: 結果保持・末尾へ追記・UI 復帰。

        表示は preset=="markdown" のときのみ整形描画（_insert_results_body と
        同じ構造的ガード）。コピー/保存は raw 維持（_format_full_text）。
        途切れ（truncated）は「成功＋警告」として部分サマリを保持する（D-05）。
        """
        self.summary_result = text
        self._summary_truncated = truncated
        self.text.insert("end", f"\n{self._L['ocr_summary_separator']}\n")
        if self.preset_var.get() == "markdown":
            self._insert_markdown(text)
        else:
            self.text.insert("end", text + "\n")
        if truncated:
            self.text.insert("end", self._L["ocr_summary_truncated"] + "\n")
        self.text.see("end")
        self.progress_var.set(self._L["ocr_summary_complete"])
        self._progress_label.configure(fg=C["WARNING"] if truncated else C["SUCCESS"])
        self._summary_ui_reset()

    def _on_summary_error(self, msg, kind=None):
        """サマリ生成失敗（メインスレッド）: OCR 結果は破壊せず再実行可能に戻す。

        kind に応じて専用ガイダンスを表示する:
          "ctx"     — コンテキスト長超過（ページ数を減らして再実行の案内）
          "timeout" — タイムアウト（タイムアウト延長・対象削減の案内）
          None      — 従来の汎用文言（安全側フォールバック）
        """
        if kind == "ctx":
            display = self._L["ocr_summary_ctx_exceeded"]
        elif kind == "timeout":
            # provider.timeout は _summary_ui_reset で復元される前なので
            # ここではサマリ実行に使われた実タイムアウト値が読める
            sec = int(getattr(self.provider, "timeout", 0) or 0)
            display = self._L["ocr_summary_timeout"].format(sec=sec)
        else:
            display = self._L["ocr_summary_failed"].format(error=msg)
        self.progress_var.set(display)
        self._progress_label.configure(fg=C["WARNING"])
        self._summary_ui_reset()

    def _on_summary_cancelled(self):
        """サマリ生成キャンセル（メインスレッド）。"""
        self.progress_var.set(self._L["ocr_summary_cancelled"])
        self._summary_ui_reset()

    def _summary_ui_reset(self):
        """サマリ実行終了後（成功/失敗/キャンセル共通）の UI 復帰。

        _after_run_ui_reset が run/resume/llm_config/サマリボタンを再評価する。
        サマリ実行中に引き上げた provider.timeout もここで復元する。
        """
        prev = getattr(self, "_summary_prev_timeout", None)
        if prev is not None:
            self.provider.timeout = prev
            self._summary_prev_timeout = None
        self._summary_running = False
        self._summary_progress_stop()
        self.cancel_btn.state(["disabled"])
        self.clear_btn.state(["!disabled"])
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])
        self._after_run_ui_reset()

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
