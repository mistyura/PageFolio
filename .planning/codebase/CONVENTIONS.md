# CONVENTIONS.md
_Generated: 2026-05-23_
_Focus: quality_

# Coding Conventions

**Analysis Date:** 2026-05-23

## Naming Patterns

**Files:**
- モジュールはスネークケース: `file_ops.py`, `page_ops.py`, `ui_builder.py`
- テストファイルは `test_` プレフィックス: `test_utils.py`, `test_pdf_ops.py`, `test_plugins.py`

**Classes:**
- PascalCase: `PDFEditorApp`, `FileOpsMixin`, `PageOpsMixin`, `PluginManager`, `PDFEditorPlugin`
- Mixin クラスには `Mixin` サフィックスを付ける: `UIBuilderMixin`, `ViewerMixin`, `DnDMixin`

**Functions / Methods:**
- スネークケース: `_rotate_selected()`, `_delete_selected()`, `_check_doc()`
- 内部メソッドには `_` プレフィックス必須（パブリック API との区別）
- ユーティリティ関数はモジュールレベルでも `_` プレフィックス: `_load_settings()`, `_save_settings()`, `_apply_theme()`

**Variables:**
- スネークケース: `thumb_cache`, `current_page`, `selected_pages`
- インスタンス変数は `self.` で参照
- モジュールレベルのロガーは常に `logger = logging.getLogger(__name__)`

**Constants:**
- アッパースネークケース: `MAX_UNDO`, `APP_VERSION`, `SETTINGS_FILE`, `THEMES`

## Button Style Rules

TTK スタイルはボタンの意味に応じて選択する。

| スタイル名 | 用途 | 例 |
|-----------|------|-----|
| `"TButton"` | 通常操作全般 | 回転、ズーム、ページ移動 |
| `"Accent.TButton"` | 主要アクション / 強調操作 | ファイルを開く、保存、編集モード ON |
| `"Danger.TButton"` | 破壊的操作 | 削除、アプリ終了 |
| `"CropOn.TButton"` | トリミングモードが ON の状態 | トリミング切替ボタン（アクティブ時） |

スタイル定義は `pagefolio/ui_builder.py` の `_build_styles()` に集約されている。
テーマ変更後に `_build_styles()` を再実行すること。

## State Management Patterns

主要な状態変数はすべて `PDFEditorApp.__init__` で初期化される（`pagefolio/app.py`）。

| 変数 | 型 | 役割 |
|------|----|------|
| `self.doc` | `fitz.Document \| None` | 現在開いている PDF。未開時は `None` |
| `self.filepath` | `str \| None` | 開いているファイルのパス |
| `self.current_page` | `int` | 0 始まりのアクティブページインデックス |
| `self.selected_pages` | `set[int]` | 複数選択中のページインデックスセット |
| `self._undo_stack` | `list[dict]` | Undo スタック（最大 `MAX_UNDO=20` 件） |
| `self._redo_stack` | `list[dict]` | Redo スタック |
| `self.thumb_cache` | `dict` | サムネイルキャッシュ（インデックス → PhotoImage） |
| `self._doc_buttons` | `list` | doc 依存ボタンのリスト（未開時に `disabled`） |
| `self._pending_click` | `str \| None` | ダブルクリック競合防止用の遅延クリックタイマーID |
| `self.settings` | `dict` | テーマ・フォントサイズ等の設定辞書 |
| `self.font_size` | `int` | 現在のベースフォントサイズ（8〜16） |
| `self.edit_mode` | `bool` | 編集モード `True` / 閲覧モード `False` |
| `self._paned` | `tk.PanedWindow` | メインの横分割ペイン参照 |
| `self._right_panel` | `tk.Frame` | 右ツールパネル（閲覧モード時は paned から外す） |
| `self._mode_btn` | `ttk.Button` | モード切替ボタン参照 |
| `self.crop_mode` | `bool` | トリミングモードの ON/OFF |

**状態変更の必須手順:**
1. ページ内容を変更する → `self._invalidate_thumb_cache(targets)` でキャッシュ破棄
2. 再描画が必要 → `self._refresh_all()` を呼ぶ
3. ユーザーへの通知 → `self._set_status(msg)` でヘッダーに表示

**操作前のガード:**
```python
def _some_operation(self):
    if not self._check_doc():  # self.doc が None なら警告ダイアログを出して return False
        return
    targets = self._get_targets()  # selected_pages があればそれを使い、なければ current_page
    ...
```

## Error Handling Patterns

**必須ルール:** 裸の `except:` は禁止。必ず `except Exception as e:` を使う。

```python
# 正しい書き方
try:
    path = _get_settings_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    logger.debug("設定ファイル読み込み失敗: %s", e)
    return dict(defaults)
```

**ログ出力パターン:**
- デバッグ情報・回復可能エラー → `logger.debug("メッセージ: %s", e)`
- 警告 → `logger.warning("...")`
- UI からユーザーに知らせる場合は `messagebox.showinfo` / `messagebox.showwarning`

**プラグインイベント内の例外:**
- `fire_event()` 内で発生した例外はすべて飲み込み、後続プラグインの処理を継続する
- (`pagefolio/plugins.py` 参照)

## Theme Color References

テーマカラーは必ず `C` 辞書経由で参照する。グローバル定数やハードコードは禁止。

```python
# 正しい書き方
from pagefolio.constants import C

widget.configure(bg=C["BG_DARK"])
style.configure("TFrame", background=C["BG_PANEL"])
label = tk.Label(frame, fg=C["ACCENT"])
```

**主要カラーキー:**

| キー | 用途 |
|------|------|
| `C["BG_DARK"]` | ウィンドウ背景 |
| `C["BG_PANEL"]` | パネル背景 |
| `C["BG_CARD"]` | カード・ボタン背景 |
| `C["ACCENT"]` | アクセントカラー（強調・ホバー） |
| `C["TEXT_MAIN"]` | 本文テキスト |
| `C["TEXT_SUB"]` | 補助テキスト |
| `C["SUCCESS"]` | 成功・ステータス |
| `C["WARNING"]` | 警告 |
| `C["PREVIEW_BG"]` | プレビューキャンバス背景 |

`C` の実体は `pagefolio/constants.py` で定義された `THEMES` 辞書を `_apply_theme()` で更新したもの。
テーマ定義: `pagefolio/constants.py`
テーマ適用: `pagefolio/settings.py` の `_apply_theme()`

## Font Size Management

フォントサイズはハードコードせず、インスタンスメソッド `self._font(delta, weight)` を使う。

```python
# 正しい書き方
tk.Label(header, font=self._font(6, "bold"))   # base + 6
ttk.Button(frame, text="OK", font=self._font(0))  # base サイズそのまま
```

`_font()` は `_make_font(delta, weight, base_size=self.font_size)` を呼ぶ内部ヘルパー。
`_make_font` は `pagefolio/settings.py` に定義され、最小サイズを 7 にクランプする。

フォントファミリーは常に `"Segoe UI"`（ハードコード可）。

## Settings Persistence

設定は JSON ファイル `pagefolio_settings.json` に永続化する。

```python
# 設定の読み込み
self.settings = _load_settings()  # pagefolio/settings.py

# 設定の保存
self.settings["theme"] = new_theme
_save_settings(self.settings)
```

**保存タイミング:**
- テーマ変更時 (`SettingsDialog`)
- フォントサイズ変更時
- ウィンドウ終了時（ジオメトリ保存）
- 編集/閲覧モード切替時

**デフォルト値:**
```python
defaults = {"theme": "dark", "font_size": 12, "lang": "ja"}
```

設定ファイルが壊れていた場合は `except Exception as e:` でキャッチしてデフォルト値を返す（`pagefolio/settings.py:_load_settings`）。

## Import Organization

```python
# 1. 標準ライブラリ
import logging
import os
from tkinter import messagebox

# 2. サードパーティ
import fitz  # pymupdf

# 3. プロジェクト内モジュール
from pagefolio.constants import C, LANG
from pagefolio.settings import _load_settings, _save_settings
```

## Undo/Redo Pattern

操作前に差分データを保存してスタックに積む。

```python
def _rotate_selected(self, deg):
    if not self._check_doc():
        return
    targets = self._get_targets()
    self._save_undo("rotate", targets=targets)  # 操作前に保存
    for i in targets:
        page = self.doc[i]
        page.set_rotation((page.rotation + deg) % 360)
    self._invalidate_thumb_cache(targets)
    self._refresh_all()
    self._set_status(self._t("status_rotated").format(count=len(targets), deg=deg))
    self.plugin_manager.fire_event("on_page_rotate", self, targets, deg)
```

Undo スタックの上限は `MAX_UNDO = 20`（`pagefolio/app.py`）。

## CropBox Safety Rule

CropBox を設定するときは必ず MediaBox 内にクランプする。

```python
eps = 0.01
new_rect = fitz.Rect(
    max(round(x0, 2), mb.x0 + eps),
    max(round(y0, 2), mb.y0 + eps),
    min(round(x1, 2), mb.x1 - eps),
    min(round(y1, 2), mb.y1 - eps),
)
page.set_cropbox(new_rect)
```

width または height が 1 未満の場合は操作を中断する（`pagefolio/page_ops.py`）。

## Internationalization

UI テキストは直接ハードコードせず `self._t(key)` で取得する。

```python
self._set_status(self._t("status_rotated").format(count=len(targets), deg=deg))
messagebox.showinfo(self._t("info_title"), self._t("info_no_page_sel"))
```

言語辞書は `pagefolio/constants.py` の `LANG` に定義。
現在サポートする言語: `"ja"` (日本語), `"en"` (英語)。

## Ruff Configuration

設定ファイル: `pyproject.toml`

```toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "S", "B"]
fixable = ["ALL"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # テストでの assert は許可
```

**有効なルールセット:**
- `E` / `W`: pycodestyle エラー・警告
- `F`: Pyflakes（未使用インポート等）
- `I`: isort（インポート順序）
- `S`: flake8-bandit（セキュリティ）
- `B`: flake8-bugbear（バグパターン）

**コミット前の必須コマンド:**
```bash
ruff check . && ruff format .
```

---

*Convention analysis: 2026-05-23*
