# コーディング規約

**分析日:** 2026-05-04

## 命名規則

**クラス名:**
- PascalCase を使用
- 例: `PDFEditorApp`, `UIBuilderMixin`, `FileOpsMixin`, `PageOpsMixin`, `ViewerMixin`, `DnDMixin`
- Mixin クラスは末尾に `Mixin` を付与
- ダイアログクラスは末尾に `Dialog` を付与: `AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog`
- プラグイン基底クラス: `PDFEditorPlugin`

**メソッド名:**
- `_` プレフィックスで内部メソッドを示す（例: `_save_undo`, `_rotate_selected`, `_refresh_all`）
- snake_case を使用
- 公開メソッドには `_` を付けない（例外的に少数）

**変数名:**
- snake_case を使用
- インスタンス変数はすべて `self.xxx` 形式
- プライベート的な一時変数にも `_` プレフィックスを使用（例: `self._undo_stack`, `self._redo_stack`）
- ループ変数: `i` (インデックス), `p` (ページ), `k`/`v` (辞書キー/値)

**定数:**
- ALL_CAPS_SNAKE_CASE: `THEMES`, `APP_VERSION`, `SETTINGS_FILE`, `PLUGINS_DIR`, `LANG`

**ファイル名:**
- snake_case を使用: `app.py`, `file_ops.py`, `page_ops.py`, `ui_builder.py`, `file_drop.py`
- テストファイルは `test_` プレフィックス: `test_utils.py`, `test_pdf_ops.py`, `test_plugins.py`

## ファイル構成の規則

**モジュール先頭:**
1. ライセンスコメントブロック（3行）
2. docstring（`"""モジュール説明"""` 形式）
3. import 文（標準ライブラリ → サードパーティ → 内部モジュールの順）

**import の順序（isort/Ruff の I ルール準拠）:**
```python
# 1. 標準ライブラリ
import logging
import os
from tkinter import messagebox

# 2. サードパーティ
import fitz
from PIL import Image, ImageTk

# 3. 内部モジュール
from pagefolio.constants import C
from pagefolio.settings import _load_settings
```

**モジュール内の区切り:**
- `# ══════════════════════════════════════════` または `# ===== セクション名 =====` で論理ブロックを区切る

## コメントの書き方

**docstring:**
- モジュールレベル: `"""モジュール説明 — サブ説明"""` 形式（1行または複数行）
- クラスレベル: `"""クラスの責務を一文で説明"""` 形式
- メソッドレベル: 複雑なロジックにのみ記述（簡単なメソッドは省略可）

**インラインコメント:**
- 日本語で記述する
- 例: `# 前回終了時のウィンドウジオメトリを復元`
- 例: `# 状態保存（PDF バイト列）`

**テストコメント:**
- テストクラスに `"""機能名のテスト"""` 形式の docstring
- 各テストメソッドに日本語で `"""何をテストするかを一文で説明"""` の docstring
- 例: `"""設定ファイルがない場合はデフォルト値を返す"""`

## エラー処理パターン

**基本ルール:**
- 裸の `except:` 句は禁止。必ず `except Exception as e:` の形で使用する
- キャッチした例外は `logger.debug(...)` で記録し、静かに処理する
- ユーザー向けの処理不可エラーは `messagebox.showerror` または `messagebox.showwarning` で通知

**パターン例（`pagefolio/settings.py`）:**
```python
def _load_settings():
    try:
        path = _get_settings_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except Exception as e:
        logger.debug("設定ファイル読み込み失敗: %s", e)
    return dict(defaults)
```

**パターン例（`pagefolio/app.py`）:**
```python
try:
    self.root.geometry(saved_geom)
except Exception as e:
    logger.debug("ジオメトリ復元失敗: %s", e)
    self.root.geometry("1200x780")
```

**ロギング:**
- モジュールレベルで `logger = logging.getLogger(__name__)` を定義
- `logger.debug(...)` で内部エラー詳細を記録
- フォーマット: `logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")`

## ボタンスタイルの規則

`pagefolio/ui_builder.py` でスタイルを定義。用途に応じて使い分ける:

| スタイル | 用途 |
|----------|------|
| `"TButton"` | 通常操作ボタン |
| `"Accent.TButton"` | 主要アクション（開く・保存など） |
| `"Danger.TButton"` | 破壊的操作（削除・終了） |
| `"CropOn.TButton"` | トリミングモード ON 時のトグルボタン |

## テーマカラーの参照方法

**必ずグローバル定数 `C` 辞書を介して参照する。ハードコードしない。**

```python
# 正しい参照方法（pagefolio/constants.py で定義）
from pagefolio.constants import C

widget.configure(bg=C["BG_DARK"])
widget.configure(fg=C["TEXT_MAIN"])
widget.configure(fg=C["ACCENT"])
```

**`C` 辞書のキー一覧:**
- `C["BG_DARK"]` — メイン背景
- `C["BG_PANEL"]` — パネル背景
- `C["BG_CARD"]` — カード/アイテム背景
- `C["ACCENT"]` — アクセントカラー（強調・ボタン）
- `C["ACCENT2"]` — セカンダリアクセント
- `C["TEXT_MAIN"]` — メインテキスト色
- `C["TEXT_SUB"]` — サブテキスト色
- `C["BTN_HOVER"]` — ボタンホバー色
- `C["SUCCESS"]` — 成功・完了表示
- `C["WARNING"]` — 警告表示
- `C["CROP_ON_BG"]` — トリミングモード ON 背景
- `C["PREVIEW_BG"]` — プレビュー背景
- `C["DANGER_BG"]` / `C["DANGER_FG"]` — 危険操作ボタン背景/文字

テーマは `_apply_theme(theme_name)` で切り替え。`C` は `pagefolio/constants.py` で `dict(THEMES["dark"])` として初期化。

## フォントサイズの規則

**ハードコード禁止。必ず `self._font(delta)` ヘルパーを使用する。**

```python
# 正しい使用方法
font=self._font()        # ベースサイズ（delta=0）
font=self._font(2)       # ベース+2（やや大きく）
font=self._font(4)       # ベース+4（大きく）
font=self._font(-1)      # ベース-1（やや小さく）
font=self._font(0, "bold")  # ベースサイズ太字
```

`_make_font(delta, weight, base_size)` のグローバル版は `pagefolio/settings.py` に定義。最小フォントサイズは 7pt にクランプされる。

## 状態管理の規則

**`PDFEditorApp` の主要状態変数（`pagefolio/app.py`）:**

| 変数 | 型 | 説明 |
|------|----|------|
| `self.doc` | `fitz.Document` or `None` | 現在開いている PDF |
| `self.current_page` | `int` | 0 始まりのページインデックス |
| `self.selected_pages` | `set` | 複数選択ページのインデックス集合 |
| `self._undo_stack` | `list` | Undo スタック（最大 20 件） |
| `self._redo_stack` | `list` | Redo スタック |
| `self.thumb_cache` | `dict` | サムネイルキャッシュ |
| `self._doc_buttons` | `list` | doc 未開時に disabled にするボタンリスト |
| `self.settings` | `dict` | 設定辞書（JSON に永続化） |
| `self.font_size` | `int` | ベースフォントサイズ（8〜16） |
| `self.edit_mode` | `bool` | 編集モード（True）/ 閲覧モード（False） |

**操作パターン:**
1. `self._check_doc()` でドキュメント存在確認
2. `self._save_undo()` でアンドゥスタックに状態保存
3. 操作実行
4. `self._refresh_all()` で全体再描画
5. `self._set_status(msg)` でステータスバー更新
6. `self.plugin_manager.fire_event(...)` でプラグインイベント発火

## 禁止事項

- `pyproject.toml` / `ruff.toml` の編集
- 裸の `except:` 句（必ず `except Exception as e:` の形で）
- `# type: ignore` の無断使用
- テーマカラーのハードコード（`"#1a1a2e"` など直接埋め込み）
- フォントサイズのハードコード（`("Segoe UI", 12)` など固定値の直接使用）
- 変更後に `ruff check . && ruff format .` を実行しないこと
- コミット前に `pytest` を通さないこと

---

*規約分析日: 2026-05-04*
