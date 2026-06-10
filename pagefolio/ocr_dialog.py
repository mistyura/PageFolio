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
from pagefolio.ocr import (
    DEFAULT_OCR_CONCURRENCY,
    MAX_OCR_CONCURRENCY,
    MAX_OCR_MAX_TOKENS,
    MAX_RETRIES,
    OCR_PROMPTS,
    build_provider,
    has_embedded_text,
    page_to_png_b64,
)

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
        max_tokens=-1,
        temperature=0.1,
        concurrency=DEFAULT_OCR_CONCURRENCY,
        provider=None,
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
        self._font = font_func or self._default_font

        self.url_var = tk.StringVar(value=url)
        self.model_var = tk.StringVar(value=model)
        self.preset_var = tk.StringVar(value=preset)
        self.scale_var = tk.DoubleVar(value=float(scale))
        self.timeout_var = tk.IntVar(value=int(timeout))
        self.max_tokens_var = tk.IntVar(value=int(max_tokens))
        self.temperature_var = tk.DoubleVar(value=float(temperature))
        self.concurrency = max(1, min(MAX_OCR_CONCURRENCY, int(concurrency)))
        # セッションキー入力用（マスク表示・D-04）
        self.api_key_var = tk.StringVar()
        # OCRProvider インスタンス（D-03: メインスレッド側でのみ使用）
        self.provider = provider
        self.results = {}  # page_idx -> text
        self.errors = {}  # page_idx -> message
        # 埋め込みテキスト検出によりスキップされたページ集合
        self._skipped_pages = set()
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
        # クリア/コピー/保存/読み取り実行/キャンセル/閉じる の6ボタンが収まる横幅
        w = max(1060, int(fs * 84))
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
        self._llm_config_btn = ttk.Button(
            prov_row,
            text=self._L["ocr_open_llm_config"],
            command=self._open_llm_config,
        )
        self._llm_config_btn.pack(side="left", padx=(12, 0))

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
        self.model_combo = ttk.Combobox(
            mf,
            textvariable=self.model_var,
            font=self._font(-1),
            values=[],
        )
        self.model_combo.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(
            mf,
            text=self._L["ocr_fetch_models"],
            command=self._fetch_models,
        ).pack(side="left", padx=2)

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
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
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
            to=600,
            increment=10,
            textvariable=self.timeout_var,
            width=5,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
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
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
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
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
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

    # ── サーバ・モデル設定 ──
    def _fetch_models(self):
        """provider から利用可能モデル一覧を取得して Combobox に反映"""
        if self.provider is None:
            self.progress_var.set(
                self._L["ocr_models_fetch_fail"].format(error="provider not set")
            )
            return
        url = self.url_var.get().strip()
        # 押下直後に「取得中…」を即時表示（HTTP 同期呼び出しによる UI 凍結対策）
        self.progress_var.set(self._L["ocr_models_fetching"].format(url=url))
        try:
            self.update_idletasks()
        except tk.TclError:
            pass
        try:
            models = self.provider.list_models()
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            self.progress_var.set(self._L["ocr_models_fetch_fail"].format(error=str(e)))
            return
        self.model_combo["values"] = models
        self.progress_var.set(self._L["ocr_models_fetched"].format(count=len(models)))

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
        self.copy_btn.state(["disabled"])
        self.save_btn.state(["disabled"])
        self.cancel_btn.state(["disabled"])
        self.run_btn.state(["!disabled"])
        self._llm_config_btn.state(["!disabled"])
        self._started = False
        self._done = False
        self._cancel_flag.clear()

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

    def _is_cloud_provider(self):
        """現在の ocr_provider 設定がクラウド系か判定する。

        claude / gemini であれば True を返す（D-13・Pitfall-F）。
        """
        from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider

        name = self.app.settings.get("ocr_provider", "")
        if name in ("claude", "gemini"):
            return True
        # isinstance ガード（provider インスタンスが差し替わっていても対応）
        if isinstance(self.provider, (ClaudeProvider, GeminiProvider)):
            return True
        return False

    def _estimate_cost(self, model, page_count):
        """ページ数とモデルから概算コスト文字列を返す（D-10）。

        Claude STACK.md 価格表: haiku $1/$5・sonnet $3/$15・opus $5/$25 MTok。
        Gemini: gemini-2.5-flash $0.075/$0.30 MTok（参考値・従量課金警告が重要）。
        Vision 入力: 1枚あたり最大 1600 トークン相当を仮定。
        OCR 出力: 1ページあたり平均 500 トークンを想定した粗い見積もり。
        正確性より「課金が発生する」警告の存在が重要（D-10・Pitfall 8）。
        """
        # Gemini モデル判定
        if "gemini" in model:
            if "pro" in model:
                # gemini-2.5-pro 系: $1.25/$10 MTok（参考値）
                input_price = 1.25
                output_price = 10.0
            else:
                # gemini-2.5-flash 系: $0.075/$0.30 MTok（参考値）
                input_price = 0.075
                output_price = 0.30
        # Claude モデル別 input 単価（$/MTok）— STACK.md 価格表
        elif "haiku" in model:
            input_price = 1.0  # haiku: $1/MTok
            output_price = 5.0  # haiku: $5/MTok
        elif "sonnet" in model:
            input_price = 3.0  # sonnet: $3/MTok
            output_price = 15.0  # sonnet: $15/MTok
        else:
            # opus（または不明モデル）
            input_price = 5.0  # opus: $5/MTok
            output_price = 25.0  # opus: $25/MTok

        # Vision 入力トークン見積もり: 約 1600 tokens/page（Anthropic/Google 参考値）
        # 出力トークン見積もり: 約 500 tokens/page（OCR 結果テキスト）
        input_tokens = page_count * 1600
        output_tokens = page_count * 500
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        return f"約 ${cost:.3f} 程度"

    def _needs_session_key(self):
        """クラウドかつ API キー環境変数が未設定のときに True を返す。

        claude: ANTHROPIC_API_KEY が未設定なら True。
        gemini: GEMINI_API_KEY/GOOGLE_API_KEY 両方未設定なら True（D-06/Pitfall-G）。
        環境変数が設定済みであれば入力欄を表示しない（D-02/D-03）。
        """
        if not self._is_cloud_provider():
            return False
        name = self.app.settings.get("ocr_provider", "")
        if name == "gemini":
            # dual env var: GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバック（D-06）
            return not bool(
                os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            )
        # claude（デフォルト）: ANTHROPIC_API_KEY を確認
        return not bool(os.environ.get("ANTHROPIC_API_KEY"))

    # ── LLM 設定ボタン・ライブ更新 ──────────────────────────────────────────

    def _open_llm_config(self):
        """プロバイダ表示行の「⚙ LLM 設定…」ボタンから LLMConfigDialog を開く。

        実行中（_started かつ未完了）は即 return してプロバイダ変更を阻止する
        （T-CCZ-02）。
        """
        if self._started and not self._done:
            return
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        lang = self.app.settings.get("lang", "ja")
        LLMConfigDialog(
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
        # (c)〜(g) UI 更新
        self._refresh_provider_dependent_ui()
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
        except (ValueError, Exception) as e:
            logger.error("provider 再生成に失敗しました: %s", e)
            self.progress_var.set(f"プロバイダ再生成エラー: {e}")

    def _refresh_provider_dependent_ui(self):
        """プロバイダ依存 UI（表示ラベル・LM Studio 欄・セッションキー欄）を再評価する。

        _apply_llm_settings から呼ばれる。テストでは no-op に差し替え可能。
        """
        # (c) プロバイダ表示ラベル更新
        self._provider_value_label.configure(text=self._provider_display_name())
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

    def _confirm_cost(self):
        """クラウド送信前のコスト確認ダイアログを表示し、ユーザーの選択を bool で返す。

        毎回表示する（「今後表示しない」は設けない・D-11）。
        ダイアログ内容（D-12 の3点）:
          1. 送信先ホスト（プロバイダ別: claude→api.anthropic.com/gemini→googleapis）
          2. 対象ページ数と概算コスト
          3. 「ページ画像が外部 API に送信されます」「従量課金が発生します」
        OK で True・キャンセルで False を返す（成功基準5）。
        """
        name = self.app.settings.get("ocr_provider", "")
        if name == "gemini":
            model = self.app.settings.get("gemini_model", "gemini-2.5-flash")
            host = "generativelanguage.googleapis.com"
        else:
            # claude（デフォルト）
            model = self.app.settings.get("claude_model", "claude-sonnet-4-6")
            host = "api.anthropic.com"
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
    def _on_run(self):
        """読み取り実行ボタン: OCR を開始する。

        メインスレッドでレンダリング/埋め込み判定後にワーカーを起動する。
        クラウドプロバイダ時は実行前にコスト確認ゲートを挟む（成功基準5・D-13）。
        """
        if self._started:
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

            # コスト確認ダイアログ（毎回・D-11・D-12）
            if not self._confirm_cost():
                # キャンセル → OCR を始めない（成功基準5）
                return

        self._started = True
        self.run_btn.state(["disabled"])
        self._llm_config_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.progress_var.set(self._L["ocr_progress_init"])
        # 結果テキストエリアをクリア
        self.text.delete("1.0", "end")

        # UI パラメータをここで取得（メインスレッド）
        try:
            self._ocr_scale = max(1.0, min(4.0, float(self.scale_var.get())))
        except (tk.TclError, ValueError):
            self._ocr_scale = 1.5  # WR-01: D-11 整合（例外フォールバック統一）
        try:
            self._ocr_timeout = max(10, min(600, int(self.timeout_var.get())))
        except (tk.TclError, ValueError):
            self._ocr_timeout = 120
        self._effective_timeout = self._ocr_timeout
        self._ocr_prompt = OCR_PROMPTS.get(self.preset_var.get(), OCR_PROMPTS["text"])

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

        name = self.app.settings.get("ocr_provider", "")
        if name == "claude":
            # claude: build_provider 経由でキー注入（D-01/D-05）
            from pagefolio.ocr import _resolve_api_key
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
            # gemini: build_provider 経由でキー注入（D-01/D-05/T-06-11）
            from pagefolio.ocr import _resolve_api_key
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
        # consumer（ワーカー）を先に起動してから producer（レンダリング）を開始する
        self._start_worker_thread()
        self._render_next_page()

    def _render_next_page(self):
        """メインスレッド（生産者）: 1 ページ render → キューに積む（after(0) 連鎖）。

        fitz アクセスはここのみ（D-04 必達）。キャンセル検出付き put で Pitfall-B 対策。
        全ページ完了またはキャンセル時に None 終了シグナルで worker を終わらせる。
        """
        if self._cancel_flag.is_set():
            # キャンセル: 全ワーカー分の終了シグナルを送る（CR-01 Pitfall-E）
            for _ in range(self.concurrency):
                try:
                    self._render_queue.put_nowait(None)
                except queue.Full:
                    pass
            self._finish_cancelled()
            return

        total = len(self.page_indices)
        idx = self._render_idx

        if idx >= total:
            # 全ページ完了: 全ワーカー分の終了シグナルを送る（CR-01 Pitfall-E）
            for _ in range(self.concurrency):
                self._render_queue.put(None)
            return  # _finish_complete は最終ワーカーが呼ぶ

        page_idx = self.page_indices[idx]

        try:
            page = self.doc[page_idx]
            # D-05: has_embedded_text / get_text / page_to_png_b64 はメインスレッドのみ
            if has_embedded_text(page):
                # 埋め込みテキストあり: results に直接投入しスキップ（D-03 統合対象）
                # T-04-09: 抽出テキストをログへ混入させない
                extracted = page.get_text()
                self.results[page_idx] = extracted
                self._skipped_pages.add(page_idx)
                # スキップはキューに積まず次ページへ（progress bar を after で更新）
                skipped_count = len(self._skipped_pages)
                total_pages = len(self.page_indices)
                self.after(
                    0,
                    lambda d=skipped_count, t=total_pages: self.progress_var.set(
                        self._L["ocr_progress_ocr"].format(
                            done=d, total=t, page=page_idx + 1
                        )
                    ),
                )
                self.after(0, lambda d=skipped_count: self._on_progress_bar(d))
            else:
                # 埋め込みテキストなし: Vision OCR のためレンダリングしてキューへ積む
                b64 = page_to_png_b64(page, scale=self._ocr_scale)
                # キャンセル検出付きブロッキング put（Pitfall-B）
                while True:
                    if self._cancel_flag.is_set():
                        # キャンセル: 全ワーカー分の終了シグナルを送る（CR-01）
                        for _ in range(self.concurrency):
                            try:
                                self._render_queue.put_nowait(None)
                            except queue.Full:
                                pass
                        return
                    try:
                        self._render_queue.put((page_idx, b64), timeout=0.1)
                        break
                    except queue.Full:
                        continue
        except Exception as e:
            logger.exception("ページ処理失敗 (p.%d): %s", page_idx, e)
            self.errors[page_idx] = f"image conversion error: {e}"

        self._render_idx += 1
        # 次のページを after(0) で連鎖（UI フリーズ回避）
        self.after(0, self._render_next_page)

    def _start_worker_thread(self):
        """consumer（ワーカー）スレッドを self.concurrency 本起動する（CR-01）。

        producer 開始前に先行起動する。全ワーカー終了後に最終ワーカーが
        終了処理（_render_results_ordered / _finish_complete 等）を一度だけ呼ぶ。
        """
        self._worker_threads = []
        self._workers_remaining = self.concurrency
        for _ in range(self.concurrency):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self._worker_threads.append(t)

    def _worker(self):
        """バックグラウンドスレッド（消費者）: キューから取り出して API 送信。

        fitz/get_pixmap/page_to_png_b64/self.doc[ は一切使用しない（D-04 必達）。
        キューから取り出した b64 は送信後に即座に del する（成功基準2・T-06-06）。
        統合プログレス（処理済み done+skipped/total）で進捗を表示する（D-03）。
        CR-01: 複数ワーカーが共有 done カウンタを Lock 配下で更新する。
               最終ワーカーのみ終了処理（_render_results_ordered / _finish_*）を呼ぶ。
        """
        import time as _time  # ループ外でインポート（IN-02 修正）

        total = len(self.page_indices)

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
                        text = self.provider.ocr_image(b64, self._ocr_prompt)
                        self.results[page_idx] = text
                        with self._done_lock:
                            self._done_count += 1
                        break
                    except OCRRetryableError as e:
                        if attempt >= MAX_RETRIES:
                            self.errors[page_idx] = str(e)
                            with self._done_lock:
                                self._done_count += 1
                            break
                        # リトライ待機中の進捗表示（D-15）
                        n = attempt
                        self.after(
                            0,
                            lambda p=page_idx, _n=n: self.progress_var.set(
                                self._L["ocr_waiting_retry"].format(
                                    page=p + 1, n=_n, max=MAX_RETRIES
                                )
                            ),
                        )
                        delay = (
                            e.retry_after
                            if e.retry_after is not None
                            else 1.0 * (2 ** (attempt - 1))
                        )
                        _time.sleep(delay)
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

            # 統合プログレス更新（処理済み = done + skipped・D-03）
            # after(0) 経由でメインスレッドへ（スレッドセーフ・Pitfall 3）
            skipped_count = len(self._skipped_pages)
            with self._done_lock:
                total_done = self._done_count + skipped_count
            self.after(
                0,
                lambda d=total_done, p=page_idx: self.progress_var.set(
                    self._L["ocr_progress_ocr"].format(done=d, total=total, page=p + 1)
                ),
            )
            self.after(0, lambda d=total_done: self._on_progress_bar(d))

        # CR-01: 残ワーカー数を減らし、最終ワーカーのみ終了処理を実行する
        with self._done_lock:
            self._workers_remaining -= 1
            is_last = self._workers_remaining == 0
            fatal_msg = self._fatal_msg
            fatal_kind = self._fatal_kind

        if not is_last:
            return  # 最終ワーカー以外は何もしない

        # 最終ワーカーが終了処理を一度だけ実行
        if fatal_msg is not None:
            self.after(
                0,
                lambda m=fatal_msg, k=fatal_kind: self._finish_error(m, kind=k),
            )
            return
        if self._cancel_flag.is_set():
            self.after(0, self._finish_cancelled)
            return
        self.after(0, self._render_results_ordered)
        self.after(0, self._finish_complete)

    # ── UI 更新（メインスレッド） ──
    def _on_progress_bar(self, done):
        """進捗バーの値だけを更新する（テキスト挿入なし）"""
        self.progress_bar["value"] = done

    def _render_results_ordered(self):
        """results / errors をページ順に text へ流し込む（並列実行後の一括描画）"""
        for page_idx in self.page_indices:
            sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
            self.text.insert("end", f"\n{sep}\n")
            if page_idx in self._skipped_pages:
                # D-08: 埋め込みテキストスキップをスキップ通知と共に表示
                skip_notice = self._L["ocr_text_skip_notice"].format(page=page_idx + 1)
                self.text.insert("end", f"[{skip_notice}]\n")
                if page_idx in self.results:
                    self.text.insert("end", self.results[page_idx] + "\n")
            elif page_idx in self.results:
                self.text.insert("end", self.results[page_idx] + "\n")
            elif page_idx in self.errors:
                self.text.insert(
                    "end",
                    self._L["ocr_page_error"].format(error=self.errors[page_idx])
                    + "\n",
                )
        self.text.see("end")

    def _finish_complete(self):
        if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
            return
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
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

    def _finish_cancelled(self):
        if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
            return
        self._done = True
        self.progress_var.set(self._L["ocr_cancelled"])
        self.cancel_btn.state(["disabled"])
        if self.results or self.errors:
            self._render_results_ordered()
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

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
        else:
            user_msg = msg
        self.progress_var.set(self._L["ocr_failed"])
        if self.results or self.errors:
            self._render_results_ordered()
        self.text.insert("end", "\n" + user_msg + "\n")
        self.text.see("end")
        self.cancel_btn.state(["disabled"])
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

    # ── 操作 ──
    def _on_cancel(self):
        # キャンセルボタンは実行中のみ有効
        self._cancel_flag.set()
        self.cancel_btn.state(["disabled"])
        self.progress_var.set(self._L["ocr_cancelling"])

    def _on_close(self):
        # 未開始または完了済みなら確認なしで閉じる
        if not self._started or self._done:
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
