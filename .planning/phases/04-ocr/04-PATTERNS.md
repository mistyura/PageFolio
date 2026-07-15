# Phase 4: バッチ複数ファイルOCR - Pattern Map

**Mapped:** 2026-07-15
**Files analyzed:** 6（新規4・変更2）
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pagefolio/batch_ocr_state.py`（新規） | model（純ロジック層・状態遷移+集計） | event-driven | `pagefolio/ocr_pipeline.py`（`PipelineState`） | exact（同格の Tk/fitz 非依存 Lock 保護状態クラス系譜） |
| `pagefolio/dialogs/batch_ocr.py`（新規） | component（Toplevel ダイアログ） | request-response + streaming（producer-consumer） | `pagefolio/ocr_dialog.py`（`OCRDialog`） | exact（同じ Toplevel+Engine 駆動パターン） |
| `pagefolio/ui_builder.py`（変更・Treeview/メニュー スタイル追加） | config（ttk.Style 定義） | transform | `pagefolio/ui_builder.py:_build_styles`（既存自身） | exact（同ファイル内への追記） |
| `pagefolio/app.py`（変更・メニューバー新設・起動導線） | controller（メニュー→ダイアログ起動） | request-response | `pagefolio/app.py:_on_dnd_drop` 呼び出し元・既存ボタン起動導線 | role-match |
| `tests/test_batch_ocr_state.py`（新規） | test | transform | `tests/test_ocr_pipeline.py` | exact |
| `tests/test_batch_ocr_dialog.py`（新規） | test | event-driven | `tests/test_ocr_engine.py`（`FakeProvider`） | exact |

## Pattern Assignments

### `pagefolio/batch_ocr_state.py`（model, event-driven）

**Analog:** `pagefolio/ocr_pipeline.py`（`PipelineState`, 47-157行）+ `pagefolio/ocr_engine.py`（設計思想・docstring 規約）

**モジュール docstring / import 制約パターン**（`ocr_engine.py:1-27`）:
```python
# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR 実行エンジン — producer-consumer の consumer 駆動部（Tkinter / fitz 非依存）。
...
トップレベル import は `threading`/`queue`/`logging` と
`pagefolio.ocr_pipeline` のみに限定し、`tkinter`・`fitz`(PyMuPDF) をモジュール
レベルで import しない（D-01/D-02・落とし穴10 回避）。
"""

import logging
import queue
import threading
```
`batch_ocr_state.py` も同じ規約（トップレベルで `tkinter`/`fitz` を import しない・`threading`/`logging` のみ）を踏襲すること。

**Lock 保護カウンタパターン**（`ocr_pipeline.py:57-71` 相当・`PipelineState.__init__`）:
```python
def __init__(self, workers):
    self._lock = threading.Lock()
    # ... 共有カウンタ初期化
```
`BatchState.__init__`/`mark_completed`/`mark_failed`/`files_done` は全て `with self._lock:` で保護する（RESEARCH.md Pattern 2 のコード例をそのまま実装の出発点にする）。

**進捗集計の独立性原則**（RESEARCH.md Pattern 2 より）:
- `BatchState.files_done()`（ファイル軸）と `OCRRunEngine.progress_count()`（ページ軸、`ocr_engine.py:149-157`）は完全に独立したカウンタとして扱う。どちらかから他方を逆算しない。

**per-run 新規生成の原則**（`ocr_engine.py:50-54` docstring）:
```python
"""D-09: `results`/`errors`/`truncated_pages`/`skipped_pages`/
`render_failed_pages` は本クラスが内部状態として所有する。D-11 により
実行（run/rerun/resume）ごとに新規生成されるため、per-run のベースライン
差分計算は構造的に不要（D-12 を new-instance で満たす）。
"""
```
バッチのファイルキュー要素（`BatchFileEntry` 相当）も同じ「ファイルごとの状態は per-file dict/オブジェクトとして独立保持し、使い回さない」原則を適用する。

---

### `pagefolio/dialogs/batch_ocr.py`（component, request-response + streaming）

**Analog:** `pagefolio/ocr_dialog.py`（`OCRDialog` クラス全体）

**Toplevel 構築パターン**（`pagefolio/dialogs/merge.py:22-55`、`MergeOrderDialog.__init__`）:
```python
class MergeOrderDialog(tk.Toplevel):
    def __init__(self, parent, paths, callback, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["merge_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(True, True)
        self.grab_set()
        ...
        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        ...
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(400, 350)
```
`BatchOCRDialog` はこの「中央配置 Toplevel」パターンをそのまま踏襲する（D-04: `self.app.doc`/`filepath` は一切参照しない独立設計）。

**事前ページ数スキャンパターン**（`pagefolio/dialogs/merge.py:35-43`）:
```python
self._page_counts = {}
for p in paths:
    try:
        d = fitz.open(p)
        self._page_counts[p] = len(d)
        d.close()
    except Exception as e:
        logger.debug("ページ数取得失敗: %s", e)
        self._page_counts[p] = 0
```
D-03（集約コスト確認前のページ数取得）・Open Question 2（壊れたファイルの扱い）はこのパターンをそのまま流用。壊れたファイルは `page_count=0` の代わりに専用の「エラー」状態でキューに残すことを推奨（RESEARCH.md Recommendation 参照）。

**D&D 投入パターン**（`pagefolio/app.py:321-354`、`_on_dnd_drop`）:
```python
def _on_dnd_drop(self, event):
    raw_paths = self.preview_canvas.tk.splitlist(event.data)
    pdf_paths = [
        p
        for p in raw_paths
        if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
    ]
    if not pdf_paths:
        if raw_paths:
            messagebox.showwarning(
                self._t("confirm_title"), self._t("dnd_pdf_only")
            )
        return event.action
    ...
    return event.action
```
`BatchOCRDialog` 専用の drop ターゲット（キュー一覧 Canvas/Frame）へこのまま応用する（D-02）。`MergeOrderDialog` 起動分岐は不要（バッチは元々複数ファイル前提のキュー）。

**複数ファイル選択ダイアログパターン**（`pagefolio/file_ops.py:464-480`、`_open_file`）:
```python
def _open_file(self):
    _supported_filter = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
    ...
    paths = filedialog.askopenfilenames(
        filetypes=[
            (self._t("filetypes_supported"), _supported_filter),
            (self._t("filetypes_pdf"), "*.pdf"),
            (self._t("filetypes_image"), _image_filter),
            (self._t("filetypes_all"), "*.*"),
        ]
    )
    if not paths:
        return
```
D-02「+ ファイル追加」ボタンはこの `askopenfilenames` パターンをそのまま流用し、結果を `_enqueue_files(list(paths))` へ渡す。

**ファイルごとに Engine を新規生成する二層ループ**（`pagefolio/ocr_dialog.py:1664-1694`、`_start_worker_thread`）:
```python
def _start_worker_thread(self, gen=None):
    """D-11: 実行（run/rerun/resume）ごとに OCRRunEngine を新規生成する
    （世代ガードと同種の安全性を構造的に得る）。
    """
    self._engine = OCRRunEngine(
        provider=self.provider,
        prompt=self._ocr_prompt,
        run_pages=self._run_pages,
        concurrency=self.concurrency,
        cancel_flag=self._cancel_flag,
        on_success=lambda p, t, tr: self._record_page_success(p, t, truncated=tr),
        on_page_error=self._record_page_error,
        on_retry_wait=self._on_retry_wait_for(gen),
        on_progress=self._on_engine_progress_for(gen),
        on_complete=lambda: self._on_engine_complete(gen),
        on_cancelled=lambda: self._on_engine_cancelled(gen),
        on_fatal=lambda msg, kind: self._on_engine_fatal(gen, msg, kind),
        breaker_threshold=CB_CONSECUTIVE_FAILURES,
    )
    self._engine.start()
```
バッチ版はこの生成を「ファイルごとに繰り返す」外側ループを追加するだけ（RESEARCH.md Pattern 1）。`on_complete`/`on_fatal`/`on_cancelled` のラムダ内で「バッチ全体キャンセルフラグが立っていなければ次ファイルの `_start_file_engine` を呼ぶ」判断を挟む。

**世代ガード付き完了理由別アダプタ**（`pagefolio/ocr_dialog.py:1740-1769`）:
```python
def _on_engine_complete(self, gen):
    if gen is not None and gen != self._run_gen:
        return
    try:
        self.after(0, self._safe_finish_complete)
    except tk.TclError:
        pass
```
バッチのファイルループでも同じ世代ガード（`gen != self._run_gen` 相当のバッチ世代）+ `after(0, ...)` ディスパッチ + `try/except tk.TclError` パターンを踏襲する。

**集約コスト確認ダイアログの拡張対象**（`pagefolio/ocr_dialog.py:1194-1235`、`_confirm_cost`）:
```python
def _confirm_cost(self, page_count=None, settings=None):
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
        page_count = len(self.page_indices)
    cost = self._estimate_cost(model, page_count)
    msg = self._L["ocr_cost_confirm_msg"].format(host=host, count=page_count, cost=cost)
    return messagebox.askyesno(self._L["ocr_cost_confirm_title"], msg, parent=self)
```
D-03: `page_count=合計ページ数` を渡すだけで再利用可能。新規 lang.py キー（`batch_cost_confirm_msg` 等、ファイル数を含む文言）を ja/en 両方に追加するかは計画時に決定（`test_lang_parity.py` のキー数一致に注意）。

**ファイル横断統合サマリの連結ロジック拡張対象**（`pagefolio/ocr_dialog.py:1980-1993`、`_format_pages_text`）:
```python
def _format_pages_text(self):
    parts = []
    for page_idx in self.page_indices:
        if page_idx not in self.results:
            continue
        sep = self._L["ocr_page_separator"].format(page=page_idx + 1)
        parts.append(sep)
        parts.append(self.results[page_idx])
    return "\n".join(parts)
```
D-15: ファイル軸にもう一段適用し、各ファイル先頭に `=== ファイル名.pdf ===` 見出しを挿入して連結する（RESEARCH.md Pattern 7 の実装イメージをそのまま採用）。

**サマリ生成トリガー本体の拡張対象**（`pagefolio/ocr_dialog.py:2006-2074`、`_on_summary` 冒頭〜コスト確認〜過大警告部分）:
```python
def _on_summary(self, settings=None):
    if (self._started and not self._done) or self._summary_running:
        return
    if not self.results:
        return
    if not getattr(self.provider, "supports_text_prompt", False):
        messagebox.showerror(...)
        return
    full_text = self._format_pages_text()
    if not full_text:
        return
    s = settings if settings is not None else dict(self.app.settings)
    ...
    if self._is_cloud_provider(settings=s):
        if not self._check_cloud_api_key(settings=s):
            return
        if not getattr(self, "_fallback_resume", False):
            if not self._confirm_summary_cost(len(full_text), settings=s):
                return
    if len(full_text) > SUMMARY_TOO_LONG_CHARS:
        proceed = messagebox.askyesno(...)
        if not proceed:
            return
```
D-13/D-14: バッチ版は `full_text` をファイル横断連結版（`_format_batch_summary_input()`）に差し替えるだけで、コスト確認・過大警告のフロー自体は完全に踏襲できる。

---

### `pagefolio/ui_builder.py`（config, transform）

**Analog:** `pagefolio/ui_builder.py:_build_styles`（15-93行、既存自身の延長）

**既存スタイル定義パターン**:
```python
def _build_styles(self):
    fs = self.font_size
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background=C["BG_DARK"])
    ...
    style.configure(
        "TButton",
        background=C["BG_CARD"],
        foreground=C["TEXT_MAIN"],
        font=("Segoe UI", fs - 1, "bold"),
        borderwidth=0,
        padding=(10, 6),
    )
    style.map(
        "TButton",
        background=[("active", C["ACCENT"]), ("pressed", C["ACCENT2"])],
        foreground=[("active", "#ffffff")],
    )
```
Treeview 用の新規スタイルブロックは同じ `style.configure`/`style.map` 呼び出し規約でこのメソッド内に追記する（RESEARCH.md Pitfall 4 の回避策例）:
```python
style.configure(
    "Treeview",
    background=C["BG_PANEL"],
    foreground=C["TEXT_MAIN"],
    fieldbackground=C["BG_PANEL"],
)
style.map("Treeview", background=[("selected", C["ACCENT"])])
```
**注意:** `ttk.Treeview`・`tk.Menu` はコードベース初導入（Pitfall 4/5）。既存スタイル一切を変更せず新規ブロックとして追記のみ行うこと。D-06 の警告色行は `tree.tag_configure("failed", foreground=C["WARNING"])` + `tree.item(iid, tags=("failed",))`（Treeview API 標準機能、既存コードに前例なし）。

---

### `pagefolio/app.py`（controller, request-response）

**Analog:** 既存の単一ファイルOCR起動導線（🔍 ボタン、`ui_builder.py` 内のボタン生成箇所）+ `_on_dnd_drop` 呼び出し規約

新規メニューバー（`tk.Menu`）新設は本プロジェクト初導入。既存に前例が無いため、Tkinter 標準の最小構成（`menubar = tk.Menu(root); root.config(menu=menubar)` + 単一トップレベルメニュー→「バッチOCR」項目）を、既存の `self._t(...)`/`lang` 参照規約に合わせて実装する。アクセラレータキー設定は既存 `ShortcutsDialog` の `cmd_map`（11コマンド）との重複を避けるため、クリックのみで起動する設計を推奨（RESEARCH.md Pitfall 5・Open Question 1）。

---

## Shared Patterns

### コスト確認・送信先確認（毎回表示・明示同意）
**Source:** `pagefolio/ocr_dialog.py:1194-1265`（`_confirm_cost`/`_confirm_summary_cost`）
**Apply to:** `batch_ocr.py` の集約コスト確認（D-03）・統合サマリ過大警告（D-14）
```python
return messagebox.askyesno(self._L["ocr_cost_confirm_title"], msg, parent=self)
```
「今後表示しない」オプションは設けない（毎回表示）方針をバッチでも厳守する。

### Engine 新規生成の原則（実行/ファイルごとに使い回さない）
**Source:** `pagefolio/ocr_engine.py:42-72`（`OCRRunEngine` docstring）
**Apply to:** `batch_ocr.py` のファイルループ、`batch_ocr_state.py` のファイルエントリ状態
実行（run/rerun/resume/ファイル）ごとに新規インスタンスを生成し、per-run 状態のリークを構造的に防ぐ。

### 世代ガード + after(0) ディスパッチ + tk.TclError 握り
**Source:** `pagefolio/ocr_dialog.py:1740-1769`
**Apply to:** `batch_ocr.py` の全コールバックアダプタ（ファイル完了/失敗/キャンセル）
```python
if gen is not None and gen != self._run_gen:
    return
try:
    self.after(0, self._safe_finish_complete)
except tk.TclError:
    pass
```

### D&D + SUPPORTED_EXTENSIONS フィルタ
**Source:** `pagefolio/app.py:321-354`（`_on_dnd_drop`）
**Apply to:** `batch_ocr.py` の複数ファイル投入（D-02）
```python
raw_paths = self.preview_canvas.tk.splitlist(event.data)
pdf_paths = [p for p in raw_paths if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS]
```

### 純ロジック層の Lock 保護カウンタ（Tk/fitz 非依存）
**Source:** `pagefolio/ocr_pipeline.py:47-157`（`PipelineState`）
**Apply to:** `batch_ocr_state.py`（`BatchState`）
`threading.Lock` で全ての状態変更メソッドを保護し、トップレベル import に `tkinter`/`fitz` を含めない。

## No Analog Found

該当なし。全ファイルに codebase 内の直接的な analog が存在する（本フェーズは既存資産の再利用・薄い配線層追加が中心のため）。

## Metadata

**Analog search scope:** `pagefolio/`（ocr_engine.py, ocr_pipeline.py, ocr_dialog.py, ocr.py, app.py, file_ops.py, ui_builder.py, dialogs/merge.py, file_drop.py）
**Files scanned:** 9
**Pattern extraction date:** 2026-07-15
