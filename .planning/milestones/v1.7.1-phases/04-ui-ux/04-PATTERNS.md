# Phase 4: UI/UX 磨き込み + 既知バグ棚卸し - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 9 (新規1・修正8)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pagefolio/dialogs/shortcuts.py`（新設） | component (Tkinter dialog) | event-driven（KeyPress キャプチャ） | `pagefolio/dialogs/settings.py` | role-match（モーダルダイアログの起動元パターンとして最良） |
| `pagefolio/app.py`（`_bind_shortcuts` 抽出・keysym変換/重複検出の純関数追加） | utility + controller（Tk bind 配線） | transform / event-driven | `pagefolio/app.py:35-50`（`merge_shortcuts`/`shift_variant_keysym`） | exact（同一ファイル内の既存純関数パターンを横展開） |
| `pagefolio/dialogs/settings.py`（ボタン追加・3セクション再編・on_apply修正） | component (dialog) | request-response（設定適用） | 自身の既存コード（`_open_llm_config`/`_apply`） | exact |
| `pagefolio/dialogs/llm_config.py`（共通/固有再グルーピング・Ollama重複解消） | component (dialog) | request-response / CRUD-like（設定保存） | 自身の既存コード（`_probe_lm_provider`・`_fetch_ollama_models`） | exact |
| `pagefolio/viewer.py`（`_show_page_popup` のハードコード文言修正） | component (Tk popup) | request-response | 同ファイル内の他ラベル生成箇所（`self._t()` 使用パターン） | exact |
| `pagefolio/page_ops.py`（messagebox種別/タイトル統一） | controller (page operation handler) | request-response | 同ファイル内 `_do_split` の隣接 showerror 呼び出し（:958） | exact |
| `pagefolio/lang.py`（未使用9キー削除・新規キー追加） | config/i18n dict | transform | 既存 LANG 辞書構造そのもの | exact |
| `tests/test_v150_regression.py`（keysym変換・重複検出テスト追加） | test | unit | 同ファイル内の既存 `merge_shortcuts`/`shift_variant_keysym` テスト | exact |
| `tests/test_lang_parity.py`（未使用キー検出テスト追加） | test | unit（静的解析） | 同ファイルの既存キー数一致テスト | exact |
| `tests/test_provider_ui.py`（ネスト同期・Ollama重複解消テスト追加、または新設 `test_dialog_cascade.py`） | test | unit（SimpleNamespace スタブ） | 同ファイルの既存 unbound method テスト方式 | exact |

## Pattern Assignments

### `pagefolio/dialogs/shortcuts.py`（新設・D-01/D-02/D-03/D-08）

**Analog:** `pagefolio/dialogs/settings.py` + `pagefolio/dialogs/merge.py`（Toplevel 構築の型）

**モジュールヘッダ/import パターン**（`dialogs/settings.py:1-12`）:
```python
# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Settings ダイアログ"""

import logging
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import LANG, C

logger = logging.getLogger(__name__)
```

**Toplevel 初期化・中央配置パターン**（`dialogs/merge.py:22-56`）:
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

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        ...
```
`ShortcutsDialog` はこの構造をそのまま踏襲（`parent`, font 関数, `lang` を受け取り `grab_set()`）。

**起動元ボタン・二重起動ガードパターン**（`dialogs/settings.py:173-207`。D-01 が明示的に「既存 LLM設定を開くボタンと同型」と指定）:
```python
def _open_llm_config(self):
    existing = getattr(self, "_llm_config_dialog", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return

    from pagefolio.dialogs.llm_config import LLMConfigDialog
    ...
    self._llm_config_dialog = LLMConfigDialog(...)
```
`_open_shortcuts_dialog` はこの二重起動ガード（`getattr` + `winfo_exists`）をそのままコピーする。

**KeyPress キャプチャハンドラ**（RESEARCH.md Architecture Patterns / Code Examples より・新規実装イメージ）:
```python
_MODIFIER_KEYSYMS = {
    "Control_L", "Control_R", "Alt_L", "Alt_R",
    "Shift_L", "Shift_R", "Caps_Lock", "Num_Lock",
}

def _on_capture_keypress(self, event):
    if event.keysym in _MODIFIER_KEYSYMS:
        return  # Pitfall 2: 修飾キー単体では確定しない
    new_keysym = build_keysym_from_event(event.state, event.keysym)
    # find_duplicate_binding(...) で重複チェック → 保存拒否 or 一時保持
```

---

### `pagefolio/app.py`（純関数追加 + `_bind_shortcuts()` 抽出・D-04/D-05/D-06/D-07）

**Analog:** 同ファイル内の既存 `merge_shortcuts`/`shift_variant_keysym`（`app.py:35-50`）

**既存の隣接純関数パターン**（そのまま横展開する型）:
```python
def merge_shortcuts(default_shortcuts, custom_shortcuts):
    """既定＋ユーザー設定のショートカット辞書をマージする（後勝ち）。"""
    return {**default_shortcuts, **custom_shortcuts}


def shift_variant_keysym(keysym):
    """Control-小文字 の keysym から Shift 補完用の大文字版 keysym を返す。"""
    if keysym.startswith("<Control-") and len(keysym) == 11 and keysym[-2].islower():
        return keysym[:-2] + keysym[-2].upper() + ">"
    return None
```

**新規純関数の推奨シグネチャ**（D-04/D-07。Tk 非依存を維持しテスト容易性を保つ）:
```python
def build_keysym_from_event(state, keysym, shift_mask=0x1, control_mask=0x4, alt_mask=0x20000):
    ...

def find_duplicate_binding(shortcuts, cmd_name, new_keysym):
    """new_keysym が cmd_name 以外の既存コマンドと重複していないか判定する（D-04）。"""
    ...

def keysym_to_display(keysym):
    """Tk keysym 文字列を人間可読表記へ変換する（D-07）。例: "<Control-o>" → "Ctrl+O" """
    ...
```

**抽出対象（現状 `__init__` 直書き・`app.py:146-186`）**:
```python
default_shortcuts = {
    "open_file": "<Control-o>", "save_file": "<Control-s>", "undo": "<Control-z>",
    "redo": "<Control-y>", "save_as": "<Control-S>", "delete": "<Delete>",
    "toggle_mode": "<F5>", "print_pdf": "<Control-p>",
}
custom_shortcuts = self.settings.get("shortcuts", {})
shortcuts = merge_shortcuts(default_shortcuts, custom_shortcuts)
cmd_map = {
    "open_file": self._open_file, ..., "rotate_right": lambda: self._rotate_selected(90),
    "rotate_left": lambda: self._rotate_selected(270), "rotate_180": lambda: self._rotate_selected(180),
}
for cmd_name, keysym in shortcuts.items():
    func = cmd_map.get(cmd_name)
    if func and keysym:
        try:
            self.root.bind(keysym, lambda e, f=func: f())
            variant = shift_variant_keysym(keysym)
            if variant is not None:
                self.root.bind(variant, lambda e, f=func: f())
        except Exception as ex:
            logger.warning(f"Failed to bind shortcut {keysym} for {cmd_name}: {ex}")
```

**抽出後の `_bind_shortcuts()`（D-05・Pitfall 1 対応：unbind してから再バインド）**:
```python
def _bind_shortcuts(self):
    for old_keysym in getattr(self, "_bound_keysyms", []):
        try:
            self.root.unbind(old_keysym)
        except Exception as e:
            logger.debug("ショートカット unbind 失敗: %s", e)
    custom_shortcuts = self.settings.get("shortcuts", {})
    shortcuts = merge_shortcuts(self._default_shortcuts, custom_shortcuts)
    bound = []
    for cmd_name, keysym in shortcuts.items():
        func = self._cmd_map.get(cmd_name)
        if func and keysym:
            try:
                self.root.bind(keysym, lambda e, f=func: f())
                bound.append(keysym)
                variant = shift_variant_keysym(keysym)
                if variant is not None:
                    self.root.bind(variant, lambda e, f=func: f())
                    bound.append(variant)
            except Exception as ex:
                logger.warning(f"Failed to bind shortcut {keysym} for {cmd_name}: {ex}")
    self._bound_keysyms = bound
```

---

### `pagefolio/dialogs/settings.py`（D-01ボタン追加・D-16セクション再編・D-14ネスト同期修正）

**Analog:** 自身の既存コード（変更対象そのもの）

**現状のセクション見出し**（`settings.py:136-151`。改称対象「LM Studio (OCR)」→「AI・OCR 設定」）:
```python
# ── LM Studio (OCR) セクション ──
sep = tk.Frame(self, bg=C["BG_CARD"], height=1)
sep.pack(fill="x", padx=24, pady=(8, 4))
tk.Label(
    self, text=self._L["settings_lm_studio_section"],
    bg=C["BG_DARK"], fg=C["WARNING"], font=self._font(0, "bold"),
).pack(anchor="w", padx=24, pady=(4, 2))

ttk.Button(
    self, text=self._L["settings_open_llm_config"], command=self._open_llm_config,
).pack(anchor="w", padx=24, pady=(2, 8))
```
D-16 で「外観」「操作（ショートカット）」「AI・OCR」の3見出しに分割。「操作」セクションに D-01 の「⌨ ショートカット設定…」ボタンを、上記と同型の `ttk.Button(..., command=self._open_shortcuts_dialog)` で追加。

**D-14 ネスト同期修正対象**（`settings.py:188-197`。現状はディスクのみ即時反映・メモリ/UI は外側 `_apply` 依存）:
```python
def on_apply(llm_settings):
    self.current_settings.update(llm_settings)
    from pagefolio.settings import _save_settings
    _save_settings(self.current_settings)
    # ← ここに apply_callback(dict(self.current_settings)) 相当の呼び出しを追加し
    #    app.settings（メモリ）・UI 再構築まで即座に反映する（Pattern 3 参照）
```
Open Question の推奨: `SettingsDialog.__init__` の後方互換を壊さないよう、新規任意引数（例 `on_llm_apply`）を追加し、`OCRDialog` 起動経路（Pitfall 5）には影響を与えない設計にする。

---

### `pagefolio/dialogs/llm_config.py`（D-15グルーピング・C2 Ollama重複解消）

**Analog:** 自身の既存 `_probe_lm_provider`（LM Studio 用共通ヘルパー・統合の型）

**棚卸し対象（活き残り確定・C2）**: `llm_config.py:1161-1183`（`_fetch_ollama_models`）・`:1185-1206`（`_test_ollama_connection`）が `_probe_lm_provider`（:1120-1150）とほぼ完全重複。統合時は `settings_lm_testing`/`settings_lm_test_ok`/`settings_lm_test_fail` を使い回している現状を維持しつつ、未配線キー `llm_fetching_ollama_models`（lang.py 未使用キー#3）をどう扱うかを1回の設計判断で確定する（Pitfall 4）。

**D-15 共通/固有分離対象**: `llm_config.py:1320-1418` の `_apply`（共通設定 max_tokens/temperature/timeout/prompt と、プロバイダ固有の URL/モデル/APIキーが混在）。見出し付きグルーピングへ再編。

---

### `pagefolio/viewer.py`（C6・ハードコード文言修正）

**Analog:** 同メソッド `_show_page_popup` 自身が持つ `self._t()` を使うべき箇所（他の LANG 経由ラベルとの対称化）

**修正対象**（`viewer.py:407,494,499,503`）:
```python
popup.title(f"ページ {i + 1} / {n}")        # → self._t("...").format(...) 等へ
...
text="🔍 縮小"                                # → self._t("popup_zoom_out") 等へ
text="🔍 拡大"                                # → self._t("popup_zoom_in") 等へ
text="✕ 閉じる"                               # → self._t("popup_close") 等へ
```
新規 LANG キーを ja/en 両方へ同一キー名で追加（`test_lang_parity.py` の既存キー数一致テストが監視）。

---

### `pagefolio/page_ops.py`（C7・messagebox種別/タイトル統一）

**Analog:** 同ファイル内 :958 の `showerror`+`err_title` 呼び出し（対称化の型）

**修正対象と統一先**（`page_ops.py:945-961`）:
```python
if not range_str.strip():
    messagebox.showinfo(self._t("info_title"), self._t("err_split_no_range"))  # 修正: showerror+err_title へ
    return
ranges = self._parse_page_ranges(range_str, n)
if ranges is None:
    messagebox.showerror(
        self._t("err_title"), self._t("err_split_range").format(n=n)
    )  # このパターンに揃える
    return
```

**messagebox種別統一基準**（D-12b、RESEARCH.md Pattern 4 で確定・全ダイアログ呼び出しに適用）:
- `showerror`+`err_title`: 操作失敗・入力/状態を正す必要がある場合
- `showwarning`+個別タイトル（`warn_del_all_title`等）: 破壊的操作の実行前確認
- `showinfo`+`info_title`: 破壊的でない案内・状態通知
- `askyesno`+`confirm_title`: Yes/No の意思決定

---

### `pagefolio/lang.py`（D-09/D-10 未使用キー削除・新規キー追加）

**Analog:** 既存 LANG 辞書のキー追加/削除パターン（ja/en 同一キー同時追加が鉄則）

**削除対象9キー**（確定済み・根拠は RESEARCH.md 未使用キー監査表）:
`ocr_provider_off_hint`・`tesseract_not_installed`・`llm_fetching_ollama_models`・`ocr_fetch_models`・`ocr_models_fetched`・`ocr_models_fetch_fail`・`ocr_models_fetching`・`sec_compress`・`warn_title`
（4〜7番は C2 の Ollama 重複解消の設計次第で「削除」ではなく「配線」も選択肢——Pitfall 4 参照）

**新規キー追加が必要な箇所**: ShortcutsDialog の全文言（タイトル・コマンド名一覧・変更/解除/保存/既定に戻すボタン・重複エラーメッセージ）、D-16 の見出し改称（`settings_lm_studio_section`→「AI・OCR 設定」等）、viewer.py C6 修正用の3キー。

---

## Shared Patterns

### ダイアログ共通骨格
**Source:** `pagefolio/dialogs/settings.py` / `pagefolio/dialogs/merge.py`
**Apply to:** `dialogs/shortcuts.py`（新設）
```python
class XxxDialog(tk.Toplevel):
    def __init__(self, parent, ..., lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["xxx_title"])
        self.configure(bg=C["BG_DARK"])
        self.grab_set()
        self._build()
        self.update_idletasks()
        # 親ウィンドウ中央配置 + geometry 計算
```

### 二重起動ガード
**Source:** `pagefolio/dialogs/settings.py:173-182`
**Apply to:** `dialogs/settings.py` の `_open_shortcuts_dialog`（新設）
```python
existing = getattr(self, "_shortcuts_dialog", None)
if existing is not None and existing.winfo_exists():
    existing.lift()
    existing.focus_force()
    return
```

### Tk 非依存の純関数 + テスト（既存確立パターン）
**Source:** `pagefolio/app.py:35-50`（`merge_shortcuts`/`shift_variant_keysym`）、同型が `pagination.py`/`md_render.py`/`ocr_pipeline.py` にも存在
**Apply to:** `app.py` の新規 keysym 変換・重複検出関数、`test_v150_regression.py` の追加テスト
- ロジックは `tkinter` を import せず、bool/str/dict の入出力のみで完結させる
- テストは unbound function 呼び出し + アサーションのみ（実 Tk ウィジェット生成不要）

### LANG キー ja/en 同時追加・キー数一致
**Source:** `tests/test_lang_parity.py`（既存）
**Apply to:** `lang.py` への全ての新規/削除キー変更
```python
# 既存: ja/en のキー集合が完全一致することを検証
assert set(LANG["ja"].keys()) == set(LANG["en"].keys())
```
D-11 で「全キーがソースのどこかで参照されている」検査を同ファイルに追加（grep/AST ベース・動的参照許可リスト付き）。

## No Analog Found

該当なし。全ファイルについて同一ファイル内の既存コード、または隣接ファイル（`dialogs/settings.py` ↔ `dialogs/merge.py`）に十分近い分析対象が存在する。

## Metadata

**Analog search scope:** `pagefolio/app.py`, `pagefolio/dialogs/`, `pagefolio/viewer.py`, `pagefolio/page_ops.py`, `pagefolio/lang.py`, `tests/test_v150_regression.py`, `tests/test_lang_parity.py`, `tests/test_provider_ui.py`（04-RESEARCH.md の既存照合結果を一次情報として活用し、`dialogs/merge.py`・`dialogs/settings.py` を追加で直接 Read して裏取り）
**Files scanned:** 7（直接 Read）+ RESEARCH.md 記載の既存コード引用多数
**Pattern extraction date:** 2026-07-05
