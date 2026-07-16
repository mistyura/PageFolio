# Phase 2: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 8
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pagefolio/settings.py`（テンプレート CRUD 関数追加） | utility / config | CRUD | `pagefolio/settings.py`（既存 `load_prompt_file`/`_load_settings`/`_save_settings`） | exact（同一ファイル拡張） |
| `pagefolio/ocr_fallback.py`（新規・純ロジック層） | utility | transform | `pagefolio/ocr_pipeline.py`（`PipelineState`・Tk/fitz 非依存の純関数層） | role-match（同格の純ロジック層） |
| `pagefolio/ocr_dialog.py`（`_propose_fallback`/`_switch_to_fallback_provider` 等追加） | controller（Tk ダイアログ） | event-driven | `pagefolio/ocr_dialog.py`（既存 `_finish_error`/`_confirm_cost`/`_check_cloud_api_key`） | exact（同一ファイル拡張） |
| `pagefolio/ocr.py`（`load_custom_prompt`/`load_summary_prompt` 呼び出し元の解決順拡張） | utility | transform | `pagefolio/ocr.py`（既存 `resolve_ocr_prompt`） | exact（同一ファイル・変更不要ロジック） |
| `pagefolio/dialogs/llm_config/sections.py`（テンプレートセクション追加） | component（Tk セクション Mixin） | request-response | `pagefolio/dialogs/llm_config/sections.py`（既存 `provider_combo` ブロック） | exact（同一ファイル拡張） |
| `pagefolio/dialogs/llm_config/sections.py`（フォールバックセクション追加） | component（Tk セクション Mixin） | request-response | `pagefolio/dialogs/merge.py`（`MergeOrderDialog` の Listbox+上下ボタン） | role-match（Toplevel→埋め込みセクションへ移植） |
| `pagefolio/dialogs/llm_config/dialog.py`（`_apply` にテンプレート/フォールバック収集追加、必要なら） | controller（Tk ダイアログ） | request-response | `pagefolio/dialogs/shortcuts.py`（`_on_save` の重複拒否パターン） | role-match |
| `tests/test_prompt_templates.py`（新規） / `tests/test_ocr_fallback.py`（新規） | test | CRUD / transform | `tests/test_ocr_pipeline.py`（純ロジック層テストの型） | role-match |

## Pattern Assignments

### `pagefolio/settings.py`（テンプレート CRUD 関数追加）（utility, CRUD）

**Analog:** 同一ファイル内の既存 `load_prompt_file`/`_load_settings`/`_save_settings`

**Imports pattern**（`pagefolio/settings.py:1-23`）:
```python
import json
import logging
import os

from pagefolio.constants import (
    CUSTOM_PROMPT_FILE,
    SETTINGS_FILE,
    SUMMARY_PROMPT_FILE,
    THEMES,
    C,
)
from pagefolio.ocr_providers.registry import sensitive_keys

logger = logging.getLogger(__name__)
_SENSITIVE_KEYS = sensitive_keys()
```

**デフォルト値パターン**（`pagefolio/settings.py:129-158`、`_load_settings` の `defaults` 辞書）:
```python
defaults = {
    "theme": "dark",
    ...
    "thumb_page_size": 20,
    # ▼ 新規追加イメージ（Claude's Discretion・A1 参照）
    "prompt_templates": {"active": "", "items": {}},
    "ocr_fallback_enabled": False,
    "ocr_fallback_chain": [],
}
...
for k, v in defaults.items():
    data.setdefault(k, v)
```
`setdefault` ループが既存レコードへの後方互換マイグレーションを自動で担う点をそのまま踏襲する（新規キー追加のみで移行コード不要）。

**関数型 CRUD ヘルパーのスタイル**（`pagefolio/settings.py:84-126`、`save_prompt_file`/`load_custom_prompt` の書き方をテンプレート版へ複製）:
```python
def save_prompt_file(filename, content):
    """... 呼び出し側（prompt_file_exists）の責務 ..."""
    path = os.path.join(_get_base_dir(), filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.warning("プロンプトファイルの保存に失敗しました (%s): %s", filename, e)
        return False


def load_custom_prompt(settings):
    """有効なカスタムプロンプトを返す（外部 md ファイル > 設定欄・V174-2）。"""
    return load_prompt_file(CUSTOM_PROMPT_FILE) or settings.get("ocr_custom_prompt", "")
```
新規 `save_template(settings, name, custom_prompt, summary_prompt)` / `delete_template(settings, name)` / `rename_template(settings, old_name, new_name)` / `list_template_names(settings)` はこの「`settings` 辞書を引数に取り、`_save_settings()` は呼び出し側が担う」責務分離をそのまま踏襲する（settings.py 内で自動保存しない）。`load_custom_prompt`/`load_summary_prompt` は RESEARCH.md Pattern 4 のとおり「外部ファイル > テンプレート > 設定欄」の3段に拡張する。

**エラー処理パターン**（`pagefolio/settings.py:172-191`、`_save_settings` の機密キーガード）:
```python
leaked = [k for k in _SENSITIVE_KEYS if k in settings]
if leaked:
    for k in leaked:
        logger.error("機密キー '%s' が settings に混入しています（保存から除外します）", k)
    to_save = {k: v for k, v in settings.items() if k not in _SENSITIVE_KEYS}
else:
    to_save = settings
try:
    ...
except Exception as e:
    logger.debug("設定ファイル保存失敗: %s", e)
```
`bare except` 禁止・`except Exception as e:` + `logger` 呼び出しの型を新規関数でも厳守する。

---

### `pagefolio/ocr_fallback.py`（新規）（utility, transform）

**Analog:** `pagefolio/ocr_pipeline.py`（`PipelineState`・Tk/fitz 非依存の純ロジック層作法）

**設計方針**（`pagefolio/ocr_pipeline.py:47-135`、`PipelineState` の fatal 判定ロジックのスタイル）:
```python
class PipelineState:
    """... fatal_msg/fatal_kind（インスタンス属性群）..."""
    def __init__(self, ...):
        self.fatal_msg = None
        self.fatal_kind = None

    def note_consecutive_error(self, msg):
        """最初の 1 回だけ fatal_msg/fatal_kind を設定する ..."""
        if self.fatal_msg is None:
            self.fatal_msg = msg
            self.fatal_kind = kind
```
`ocr_fallback.py` は RESEARCH.md 提示の `next_fallback_candidate(chain, tried)` のみを純関数として持つ（fitz/tkinter を一切 import しない）。`PipelineState` と同じく「呼び出し側にオーケストレーションを一切持たせない・状態は明示的な引数/戻り値でやり取りする」設計を踏襲する。

```python
def next_fallback_candidate(chain, tried):
    """chain（設定済みフォールバック順リスト）から、まだ試していない
    最初の候補を返す。無ければ None（D-10: 連鎖は最後まで辿る）。
    """
    for name in chain:
        if name not in tried:
            return name
    return None
```

---

### `pagefolio/ocr_dialog.py`（フォールバックフック追加）（controller, event-driven）

**Analog:** 同一ファイル内の既存 `_finish_error`/`_confirm_cost`/`_check_cloud_api_key`/`_pending_pages`

**fatal 確定フックの挿入点**（`pagefolio/ocr_dialog.py:1847-1878`、`_finish_error`）:
```python
def _finish_error(self, msg, kind):
    if self._done:  # CR-02: 冪等ガード（二重呼び出し防止）
        return
    self._done = True
    if kind == "connection":
        user_msg = self._L["ocr_err_connection"].format(url=self.url_var.get(), error=msg)
    elif kind == "timeout":
        ...
    elif kind == "circuit_breaker":
        user_msg = self._L["ocr_err_circuit_breaker"].format(n=CB_CONSECUTIVE_FAILURES, error=msg)
    else:
        user_msg = msg
    ...
    self._after_run_ui_reset()
    # ▼ 新規フック挿入点（D-11・D-12）
    self._propose_fallback(kind, msg)
```
同型のフックを `_on_summary_error`（`pagefolio/ocr_dialog.py:2192`）末尾にも追加する（D-12）。

**確認ダイアログの毎回表示パターン**（`pagefolio/ocr_dialog.py:1171-1213`、`_confirm_cost`。「今後表示しない」チェックボックスを追加しないアンチパターン注記あり）:
```python
def _confirm_cost(self, page_count=None):
    """... 毎回表示する（「今後表示しない」は設けない・D-11）。"""
    name = self.app.settings.get("ocr_provider", "")
    if name == "gemini":
        model = self.app.settings.get("gemini_model", "gemini-2.5-flash")
        host = "generativelanguage.googleapis.com"
    elif name == "runpod":
        ...
    else:
        model = self.app.settings.get("claude_model", "claude-sonnet-4-6")
        host = "api.anthropic.com"
    ...
    return messagebox.askyesno(self._L["ocr_cost_confirm_title"], msg, parent=self)
```
フォールバック確認ダイアログ（`_propose_fallback` 内の `messagebox.askyesno`）はこの「毎回表示・provider 別分岐」パターンを理由コード（`fallback_reason_connection` 等）付きで踏襲する。**重要な差異:** `_confirm_cost` は `self.app.settings.get("ocr_provider", "")` を直接参照するが、フォールバック実装ではこれを踏襲してはならない（Pitfall 4）。`_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key` は「現在のプロバイダ名」をダイアログローカルなスナップショット（例: `self._active_ocr_settings`）から取得するよう一般化が必要（A3 参照）。

**APIキー未解決チェック**（`pagefolio/ocr_dialog.py:1244-1259`、`_check_cloud_api_key`）:
```python
def _check_cloud_api_key(self):
    if not self._is_cloud_provider():
        return True
    from pagefolio.ocr import _resolve_api_key
    from pagefolio.ocr_providers import OCRAPIKeyError
    from pagefolio.ocr_providers.registry import primary_env_var

    name = self.app.settings.get("ocr_provider", "")
    session_keys = getattr(self.app, "_session_api_keys", {})
    ...
```
フォールバック候補の APIキー未設定判定（D-11・D-14）にはこの関数を「プロバイダ名を明示引数で受け取れる」形へ一般化して再利用する。

**再開の既存機構**（`pagefolio/ocr_dialog.py:712` `_pending_pages`、`1880-1885` `_append_resume_hint`）:
```python
def _append_resume_hint(self):
    if not self._can_resume():
        return
    pending = self._pending_pages()
    self.text.insert("end", ...)
```
D-09「未処理ページのみ再開」はこの `_pending_pages()`/`_can_resume()` をそのまま流用する（新規実装不要）。

---

### `pagefolio/ocr.py`（プロンプト解決順拡張）（utility, transform）

**Analog:** 同一ファイル内の既存 `resolve_ocr_prompt`（変更不要・シグネチャ維持が必須）

```python
# pagefolio/ocr.py:75-101（変更禁止・アンチパターン注記: シグネチャ変更は test_provider_ui.py を全滅させる）
def resolve_ocr_prompt(preset, provider_name, custom_prompt=""):
    if custom_prompt:
        return custom_prompt
    by_provider = PROVIDER_OCR_PROMPTS.get(provider_name, {})
    if preset in by_provider:
        return by_provider[preset]
    return OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])
```
テンプレート層は `settings.py` の `load_custom_prompt`/`load_summary_prompt`（呼び出し元）でのみ拡張し、`resolve_ocr_prompt`/`resolve_summary_prompt` 自体・`build_provider`（`pagefolio/ocr.py:414`）・`_resolve_api_key`（`pagefolio/ocr.py:208`）は無改造で流用する。

---

### `pagefolio/dialogs/llm_config/sections.py`（テンプレートセクション新設）（component, request-response）

**Analog:** 同一ファイル内の既存 `provider_combo` ブロック

**Combobox パターン**（`pagefolio/dialogs/llm_config/sections.py:60-93`）:
```python
self.provider_var = tk.StringVar(value=self.current_settings.get("ocr_provider", "off"))
_base_providers = ["off", "lmstudio", "ollama", "runpod", "claude", "gemini", "tesseract"]
_plugin_extras = self._plugin_manager.list_ocr_providers() if self._plugin_manager else []
self.provider_combo = ttk.Combobox(
    provider_row,
    textvariable=self.provider_var,
    values=_base_providers + _plugin_extras,
    state="readonly",
    font=self._font(-1),
    width=14,
)
self.provider_combo.pack(side="left", padx=4)
self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)
```
テンプレート選択欄（`self.template_combo`）はこの型をそのまま複製する（`values=list_template_names(...)`、`state="readonly"`、`<<ComboboxSelected>>` バインド）。プロバイダ固有セクションの動的表示/非表示（`before=self.scale_row` での挿入・`pack`/`pack_forget`）パターンは D-16 のフォールバック順リスト（トグル ON 時のみ表示）にも流用できる。

**外部ファイル連動注記の流用**（`pagefolio/dialogs/llm_config/sections.py:851, 893`）:
```python
self._add_prompt_file_notice(body, CUSTOM_PROMPT_FILE)
...
self._add_prompt_file_notice(body, SUMMARY_PROMPT_FILE)
```
D-08 によりこの既存注記をそのまま流用し、専用UIは新設しない。

---

### `pagefolio/dialogs/llm_config/sections.py`（フォールバックセクション新設）（component, request-response）

**Analog:** `pagefolio/dialogs/merge.py`（`MergeOrderDialog` の Listbox + 上へ/下へボタン、`pagefolio/dialogs/merge.py:80-165`）

```python
# Listbox 構築（merge.py:83-100）
sb = ttk.Scrollbar(list_frame, orient="vertical")
self.listbox = tk.Listbox(
    list_frame,
    yscrollcommand=sb.set,
    bg=C["BG_CARD"],
    fg=C["TEXT_MAIN"],
    selectbackground=C["ACCENT"],
    selectforeground="#fff",
    font=self._font(-1),
    activestyle="none",
    bd=0,
    highlightthickness=0,
    height=list_height,
)

# 上へ/下へボタン（merge.py:108-113）
ttk.Button(btn_row, text=self._L["merge_up"], command=self._move_up).pack(side="left", padx=4)
ttk.Button(btn_row, text=self._L["merge_down"], command=self._move_down).pack(side="left", padx=4)

# 移動ロジック（merge.py:143-157）
def _move_up(self):
    sel = self.listbox.curselection()
    if not sel or sel[0] == 0:
        return
    i = sel[0]
    self.paths[i - 1], self.paths[i] = self.paths[i], self.paths[i - 1]
    self._reload_list(i - 1)
```
D-13 によりこの Listbox+ボタンの**ウィジェット構成のみ**を移植する（`MergeOrderDialog` は独立 `tk.Toplevel` だが、フォールバックセクションは LLM 設定ダイアログ内の埋め込みセクション・D-15）。`Toplevel` 化・`callback` 経由の親子通信は不要（同一ダイアログ内 `self` 属性で完結）。リスト対象は `paths`（ファイルパス）ではなく `self._fallback_chain`（プロバイダ名リスト）に置き換える。

---

### `pagefolio/dialogs/llm_config/dialog.py`（`_apply` 拡張、必要なら）（controller, request-response）

**Analog:** `pagefolio/dialogs/shortcuts.py`（`ShortcutsDialog._on_save` の重複拒否＋保存パターン）

```python
# pagefolio/dialogs/shortcuts.py:254-284
def _on_save(self):
    ...
    from pagefolio.app import find_duplicate_binding
    for cmd_name, keysym in self._shortcuts.items():
        dup_cmd = find_duplicate_binding(self._shortcuts, cmd_name, keysym)
        if dup_cmd is not None:
            messagebox.showerror(
                self._L["err_title"],
                self._L["shortcuts_dup_error"].format(cmd=self._label_for_cmd(dup_cmd)),
            )
            return
    ...
    self._app.settings["shortcuts"] = diff
    from pagefolio.settings import _save_settings
    _save_settings(self._app.settings)
    self.destroy()
```
D-04「テンプレート名重複は保存時に拒否」はこの型（保存直前に重複チェック→`messagebox.showerror`→`return`、問題なければ `settings` へ書き込み `_save_settings` 呼び出し）をそのまま踏襲する。テンプレート名重複判定は `settings.py` 内の純粋関数（`ShortcutsDialog` の `find_duplicate_binding` 相当）として実装し、UI 側はその結果を判定するだけに留める。

---

## Shared Patterns

### 純ロジック層の独立性作法（Tk/fitz 非依存）
**Source:** `pagefolio/ocr_pipeline.py`（`PipelineState`）・`pagefolio/pagination.py`
**Apply to:** `pagefolio/ocr_fallback.py`（新規）、`settings.py` のテンプレート CRUD ヘルパー
「fitz/tkinter を一切 import しない」設計により pytest でのユニットテストが容易になる。`ocr_fallback.py` はこの作法をそのまま踏襲する（RESEARCH.md Pattern 6 コード例で明記済み）。

### 確認ダイアログ「毎回表示・省略なし」方針
**Source:** `pagefolio/ocr_dialog.py:1171-1213`（`_confirm_cost`）
**Apply to:** `_propose_fallback` 内のフォールバック確認ダイアログ（D-10/D-11・Pitfall 2）
「今後表示しない」チェックボックスを追加しない。理由（`fallback_reason_connection` 等）を必ず明示する。

### `self.app.settings` を書き換えないローカルスナップショット方針
**Source:** RESEARCH.md Pitfall 4（本フェーズ新規発見の落とし穴）
**Apply to:** `_switch_to_fallback_provider`・`_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key` の一般化
`self._active_ocr_settings = dict(self.app.settings)` のようなダイアログローカル辞書のみを更新し、`build_provider()` にはこのローカル辞書を渡す。`_save_settings()` 呼び出し経路（`_apply`）には絶対に触れさせない。

### 重複拒否パターン
**Source:** `pagefolio/dialogs/shortcuts.py:254-270`
**Apply to:** テンプレート名の保存時重複チェック（D-04）

### 機密キー除外ガード
**Source:** `pagefolio/settings.py:172-191`（`_SENSITIVE_KEYS`/`_save_settings`）
**Apply to:** テンプレート辞書・フォールバックチェーンのキー名が `_SENSITIVE_KEYS` パターン（`*_api_key` 等）と衝突しないことの設計時確認（RESEARCH.md セキュリティ節）

## No Analog Found

なし。全ファイルに強い既存分析対象があり（`settings.py`/`ocr_pipeline.py`/`ocr_dialog.py`/`merge.py`/`shortcuts.py`/`ocr.py`）、新規パターンの発明は不要。

## Metadata

**Analog search scope:** `pagefolio/settings.py`, `pagefolio/ocr.py`, `pagefolio/ocr_pipeline.py`, `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/llm_config/sections.py`, `pagefolio/dialogs/merge.py`, `pagefolio/dialogs/shortcuts.py`
**Files scanned:** 7（grep + 直接 Read）
**Pattern extraction date:** 2026-07-14
