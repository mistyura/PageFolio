# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR ダイアログ — 進行表示・キャンセル・結果エクスポート"""

import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pagefolio.constants import LANG, C
from pagefolio.ocr import (
    DEFAULT_OCR_CONCURRENCY,
    MAX_OCR_CONCURRENCY,
    MAX_OCR_MAX_TOKENS,
    OCR_PROMPTS,
    has_embedded_text,
    page_to_png_b64,
    run_parallel,
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
        # OCRProvider インスタンス（D-03: メインスレッド側でのみ使用）
        self.provider = provider
        self.results = {}  # page_idx -> text
        self.errors = {}  # page_idx -> message
        # 埋め込みテキスト検出によりスキップされたページ集合
        self._skipped_pages = set()
        self._cancel_flag = threading.Event()
        self._worker_thread = None
        self._done = False
        self._started = False
        self._images = {}  # page_idx -> b64（メインスレッドでレンダリング済み）
        self._ocr_page_indices = []  # スキップ除外後の Vision OCR 対象ページリスト

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
        sf = tk.Frame(self, bg=C["BG_DARK"])
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

        # モデル選択
        mf = tk.Frame(self, bg=C["BG_DARK"])
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
        params_row = tk.Frame(self, bg=C["BG_DARK"])
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

        # 進行表示
        self.progress_var = tk.StringVar(value=self._L["ocr_run_first"])
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
        self._images.clear()
        self._ocr_page_indices.clear()
        self.progress_bar["value"] = 0
        self.progress_var.set(self._L["ocr_run_first"])
        self.copy_btn.state(["disabled"])
        self.save_btn.state(["disabled"])
        self.cancel_btn.state(["disabled"])
        self.run_btn.state(["!disabled"])
        self._started = False
        self._done = False
        self._cancel_flag.clear()

    # ── ワーカー ──
    def _on_run(self):
        """読み取り実行ボタン: OCR を開始する。

        メインスレッドでレンダリング/埋め込み判定後にワーカーを起動する。
        """
        if self._started:
            return
        self._started = True
        self.run_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.progress_var.set(self._L["ocr_progress_init"])
        # 結果テキストエリアをクリア
        self.text.delete("1.0", "end")

        # UI パラメータをここで取得（メインスレッド）
        try:
            self._ocr_scale = max(1.0, min(4.0, float(self.scale_var.get())))
        except (tk.TclError, ValueError):
            self._ocr_scale = 2.0
        try:
            self._ocr_timeout = max(10, min(600, int(self.timeout_var.get())))
        except (tk.TclError, ValueError):
            self._ocr_timeout = 120
        self._effective_timeout = self._ocr_timeout
        self._ocr_prompt = OCR_PROMPTS.get(self.preset_var.get(), OCR_PROMPTS["text"])

        # CR-02: ダイアログ UI の live 値で self.provider を再生成する
        # ワーカースレッド起動前に実行（run_parallel に反映される・メインスレッドのみ）
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

        from pagefolio.ocr_providers import LMStudioProvider

        self.provider = LMStudioProvider(
            url=url,
            model=model,
            timeout=self._effective_timeout,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # D-01/D-03/D-05: フェーズ1はメインスレッドで after() 小分け実行
        # レンダリング完了後にワーカースレッドを起動する
        self._render_idx = 0
        self._render_next_page()

    def _render_next_page(self):
        """メインスレッドで1ページずつレンダリング/埋め込み判定する。

        after() 小分けで UI フリーズを回避する（D-01/D-03/D-05）。
        """
        if self._cancel_flag.is_set():
            self._finish_cancelled()
            return

        total = len(self.page_indices)
        idx = self._render_idx

        if idx >= total:
            # 全ページのレンダリング/判定完了 → ワーカースレッドを起動
            self._start_worker_thread()
            return

        page_idx = self.page_indices[idx]
        self.progress_var.set(
            self._L["ocr_progress_render"].format(cur=idx + 1, total=total)
        )

        try:
            page = self.doc[page_idx]
            # D-05: has_embedded_text はメインスレッドで実行
            if has_embedded_text(page):
                # 埋め込みテキストあり: results に直接投入（成功基準2・D-07）
                # T-04-09: 抽出テキストをログへ混入させない
                extracted = page.get_text()
                self.results[page_idx] = extracted
                self._skipped_pages.add(page_idx)
            else:
                # 埋め込みテキストなし: Vision OCR のためレンダリング
                b64 = page_to_png_b64(page, scale=self._ocr_scale)
                self._images[page_idx] = b64
                self._ocr_page_indices.append(page_idx)
        except Exception as e:
            logger.exception("ページ処理失敗 (p.%d): %s", page_idx, e)
            self.errors[page_idx] = f"image conversion error: {e}"

        self._render_idx += 1
        # 次のページを after(0) で連鎖（UI フリーズ回避）
        self.after(0, self._render_next_page)

    def _start_worker_thread(self):
        """レンダリング完了後にワーカースレッドを起動する"""
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def _worker(self):
        """フェーズ2: API 並列送信のみを担う（fitz アクセスゼロ・D-03）"""
        total = len(self.page_indices)
        # スキップ済みページ数を進捗バー初期値に反映
        skipped_count = len(self._skipped_pages)

        if self._cancel_flag.is_set():
            self.after(0, self._finish_cancelled)
            return

        # フェーズ2: run_parallel で Vision OCR（スキップ除外済みページのみ）
        def on_progress(done, page_idx, status):
            self.after(
                0,
                lambda d=done + skipped_count, p=page_idx: self.progress_var.set(
                    self._L["ocr_progress_ocr"].format(done=d, total=total, page=p + 1)
                ),
            )
            self.after(0, lambda d=done + skipped_count: self._on_progress_bar(d))

        # スキップ済みページが存在する場合、進捗バーをスキップ数分先行させる
        if skipped_count > 0:
            self.after(0, lambda: self._on_progress_bar(skipped_count))

        results, errors, fatal_msg, fatal_kind = run_parallel(
            self.provider,
            self._images,
            self._ocr_page_indices,
            concurrency=self.concurrency,
            prompt=self._ocr_prompt,
            on_progress=on_progress,
            is_cancelled=self._cancel_flag.is_set,
        )
        self.results.update(results)
        self.errors.update(errors)

        # フェーズ3: 結果をページ順にまとめて UI へ流し込む
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
        self._done = True
        self.progress_var.set(self._L["ocr_cancelled"])
        self.cancel_btn.state(["disabled"])
        if self.results or self.errors:
            self._render_results_ordered()
        if self.results:
            self.copy_btn.state(["!disabled"])
            self.save_btn.state(["!disabled"])

    def _finish_error(self, msg, kind):
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
