# ARCHITECTURE.md
_Generated: 2026-05-23_
_Focus: arch_

<!-- refreshed: 2026-05-23 -->

**Analysis Date:** 2026-05-23

---

## システム概要

```text
┌──────────────────────────────────────────────────────────────────┐
│                       Tkinter GUI (root)                          │
│   Header (status/mode)  │  PanedWindow (3-pane)                  │
└──────────────┬───────────────────────────────────────────────────┘
               │
   ┌───────────┼───────────────────┐
   ▼           ▼                   ▼
Left Pane   Center Pane        Right Pane
サムネイル    プレビュー          ツールパネル
`viewer.py`  `viewer.py`       `ui_builder.py`
`dnd.py`     `page_ops.py`     `file_ops.py`
                                `page_ops.py`
               │
               ▼
┌─────────────────────────────────────┐
│         PDFEditorApp                │
│  UIBuilderMixin + FileOpsMixin      │
│  + PageOpsMixin + ViewerMixin       │
│  + DnDMixin                         │
│  `pagefolio/app.py`                 │
└──────────────┬──────────────────────┘
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
   fitz.Document   PluginManager   settings dict
  (in-memory PDF)  `plugins.py`    `settings.py`
```

---

## アーキテクチャパターン

**全体パターン:** Mixin 多重継承による単一クラス構成

`PDFEditorApp` は5つの Mixin クラスを多重継承し、すべての機能を1つのクラスインスタンスとして提供する。Mixin はメソッドを提供するだけで、状態は `PDFEditorApp.__init__` が一元的に管理する。

```python
# pagefolio/app.py
class PDFEditorApp(UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin):
    MAX_UNDO = 20
    def __init__(self, root): ...
```

---

## コンポーネント責務

| コンポーネント | 責務 | ファイル |
|--------------|------|---------|
| `PDFEditorApp` | 状態管理・キーバインド・ユーティリティ・初期化 | `pagefolio/app.py` |
| `UIBuilderMixin` | ttk スタイル定義・3ペインレイアウト・ツールボタン構築 | `pagefolio/ui_builder.py` |
| `FileOpsMixin` | ファイルの開閉・保存・Undo/Redo | `pagefolio/file_ops.py` |
| `PageOpsMixin` | 回転・削除・複製・トリミング・挿入・結合・分割 | `pagefolio/page_ops.py` |
| `ViewerMixin` | プレビュー描画・ズーム・サムネイル生成・ページ選択・ポップアップ | `pagefolio/viewer.py` |
| `DnDMixin` | サムネイルの D&D によるページ並び替え | `pagefolio/dnd.py` |
| `PluginManager` | プラグインの検出・読込・有効/無効・イベント発火 | `pagefolio/plugins.py` |
| `PDFEditorPlugin` | プラグイン基底クラス（フック定義） | `pagefolio/plugins.py` |
| `dialogs` モジュール | About / Settings / Plugin / MergeOrder / MergeResize の各ダイアログ | `pagefolio/dialogs.py` |
| `file_drop` モジュール | tkinterdnd2 によるファイルドロップ登録 | `pagefolio/file_drop.py` |
| `constants` モジュール | テーマ辞書 `THEMES`・実行時辞書 `C`・言語辞書 `LANG`・定数 | `pagefolio/constants.py` |
| `settings` モジュール | 設定ファイルの読み書き・テーマ適用ユーティリティ | `pagefolio/settings.py` |

---

## 状態管理

すべての状態は `PDFEditorApp.__init__` で初期化され、インスタンス属性として保持される。Mixin はこれらの属性を直接読み書きする。

### ドキュメント状態

| 属性 | 型 | 説明 |
|------|----|------|
| `self.doc` | `fitz.Document` or `None` | 現在開いている PDF。未開時は `None` |
| `self.filepath` | `str` or `None` | 現在のファイルパス。結合等の場合は `None` |
| `self.current_page` | `int` | 0始まりの現在ページインデックス |
| `self.selected_pages` | `set[int]` | 複数選択ページのインデックス集合 |

### UI 状態

| 属性 | 型 | 説明 |
|------|----|------|
| `self.zoom` | `float` | プレビューのズーム倍率（0.3〜3.0）|
| `self.edit_mode` | `bool` | `True` = 編集モード / `False` = 閲覧モード |
| `self.crop_mode` | `bool` | トリミング範囲選択モードの ON/OFF |
| `self.crop_rect` | `tuple` or `None` | 選択中のトリミング矩形（キャンバス座標）|
| `self.crop_drag_start` | `tuple` or `None` | ドラッグ開始座標 |
| `self._mode_btn` | `ttk.Button` or `None` | モード切替ボタンの参照 |
| `self._doc_buttons` | `list[ttk.Button]` | ファイル依存ボタンの一覧 |
| `self._edit_only_buttons` | `list[ttk.Button]` | 編集モード専用ボタンの一覧 |
| `self._paned` | `tk.PanedWindow` | メイン3ペイン分割ウィジェット |
| `self._right_panel` | `tk.Frame` | 右ツールパネルの参照 |

### Undo/Redo 状態

| 属性 | 型 | 説明 |
|------|----|------|
| `self._undo_stack` | `list[dict]` | Undo 履歴（最大 `MAX_UNDO=20` 件）|
| `self._redo_stack` | `list[dict]` | Redo 履歴 |

**Undo スタックのエントリ形式（差分保存）:**
```python
{
    "op": "rotate" | "crop" | "delete" | "move" | "duplicate" | "insert" | "merge" | "bulk_move" | "bulk_crop",
    "current_page": int,
    "selected_pages": set[int],
    "data": ...,  # op ごとに異なる差分データ
}
```

**Redo スタックのエントリ形式（スナップショット保存）:**
```python
{
    "pdf_bytes": bytes,  # doc.tobytes() の全バイト
    "current_page": int,
    "selected_pages": set[int],
}
```

### キャッシュ・レンダリング状態

| 属性 | 型 | 説明 |
|------|----|------|
| `self.thumb_cache` | `dict[int, ImageTk.PhotoImage]` | サムネイル画像キャッシュ |
| `self.thumb_images` | `list` | GC 防止用のサムネイル参照保持リスト |
| `self._preview_gen` | `int` | プレビューレンダリング世代カウンター（キャンセル用）|
| `self._thumb_gen` | `int` | サムネイルレンダリング世代カウンター（キャンセル用）|
| `self._pending_click` | `int` or `None` | ダブルクリック競合防止用の遅延クリックID |

### 設定・言語状態

| 属性 | 型 | 説明 |
|------|----|------|
| `self.settings` | `dict` | 設定辞書（テーマ・フォント・ジオメトリ等）|
| `self.font_size` | `int` | ベースフォントサイズ（8〜16）|
| `self.lang` | `str` | 現在の言語コード（`"ja"` または `"en"`）|

### プラグイン状態

| 属性 | 型 | 説明 |
|------|----|------|
| `self.plugin_manager` | `PluginManager` | プラグインマネージャーインスタンス |
| `self._plugin_ui_frame` | `tk.Frame` or `None` | プラグイン UI を配置するフレーム |

---

## 各 Mixin の責務と依存関係

### UIBuilderMixin (`pagefolio/ui_builder.py`)

**責務:** ttk スタイル定義、3ペインレイアウト構築、ツールボタン配置。

**主要メソッド:**
- `_build_styles()` — ttk スタイル（TButton / Accent.TButton / Danger.TButton / CropOn.TButton）を定義
- `_build_ui()` — ヘッダー + `PanedWindow` + 左(サムネイル) / 中(プレビュー) / 右(ツール)の3ペインを構築
- `_build_tools(parent)` — 右ペインにすべての操作ボタンを配置し `_doc_buttons` / `_edit_only_buttons` を初期化
- `_build_tools_scrollable(parent)` — 右ペインをスクロール可能な Canvas でラップ

**依存:** `pagefolio/constants.py` の `C` 辞書。実行時に `dialogs.AboutDialog` を遅延インポート。

---

### FileOpsMixin (`pagefolio/file_ops.py`)

**責務:** ファイルの開閉・保存・Undo/Redo の実装。

**主要メソッド:**
- `_save_undo(op, **kwargs)` — 操作前に差分データを `_undo_stack` に積む
- `_undo()` / `_redo()` — スタックから状態を復元
- `_restore_state(state)` — Undo/Redo エントリから `fitz.Document` を復元
- `_open_pdf_path(path)` — 単一ファイルを開く（画像→PDF変換含む）
- `_do_open_merged(ordered_paths)` — 複数ファイルを結合して開く
- `_save_file()` / `_save_as()` / `_save_compressed()` — 保存処理
- `_close_file()` — ファイルを閉じる（アプリは終了しない）

**依存:** `fitz` (PyMuPDF)、`pagefolio/constants.py` の `SUPPORTED_EXTENSIONS` / `IMAGE_EXTENSIONS`。

---

### PageOpsMixin (`pagefolio/page_ops.py`)

**責務:** ページレベルのすべての編集操作。

**主要メソッド:**
- `_rotate_selected(deg)` — 選択ページを回転
- `_delete_selected()` — 選択ページを削除
- `_duplicate_page()` — 現在ページを直後に複製
- `_toggle_crop_mode()` / `_crop_drag_start/move/end()` / `_crop_page()` — トリミング
- `_insert_from_file(mode)` / `_do_insert(ordered_paths, insert_at)` — ファイルの挿入
- `_merge_pdf()` / `_do_merge(ordered_paths)` — 末尾結合
- `_merge_resize_pages()` / `_do_merge_resize(targets, direction, out_w, out_h)` — ページ結合・リサイズ
- `_split_by_range()` / `_split_each_page()` — 分割保存

**依存:** `fitz`、`pagefolio/constants.py`。ダイアログは遅延インポート（循環参照回避）。

---

### ViewerMixin (`pagefolio/viewer.py`)

**責務:** プレビュー描画・サムネイル生成・ページナビゲーション・ポップアップ。

**主要メソッド:**
- `_show_preview()` — バックグラウンドスレッドでプレビューをレンダリング（`_preview_gen` で世代管理）
- `_build_thumbnails()` — `after_idle` ループでサムネイルを逐次生成（`_thumb_gen` で世代管理）
- `_get_thumb_photo(i)` — キャッシュ付きサムネイル取得
- `_refresh_all()` — サムネイル + プレビュー + ボタン状態を一括更新
- `_refresh_thumbs_selection_only()` — 選択状態の変更のみ反映（再レンダリングなし）
- `_add_thumb_placeholder(i)` — サムネイルフレームを作成しクリック / D&D イベントをバインド
- `_show_page_popup(idx)` — `tk.Toplevel` でページ拡大表示

**レンダリングスケール:**
- プレビュー: `fitz.Matrix(zoom * 1.5, zoom * 1.5)`
- サムネイル: `fitz.Matrix(0.22, 0.22)`（キャッシュ対象）

**バックグラウンド処理:**
`_show_preview()` は `threading.Thread` でピクセルデータを生成し、`root.after(0, callback)` でメインスレッドに反映する。世代カウンター `_preview_gen` でレース条件を防ぐ。

**依存:** `fitz`、`PIL` (Pillow)、`threading`、`pagefolio/constants.py`。

---

### DnDMixin (`pagefolio/dnd.py`)

**責務:** サムネイルパネル内でのページ並び替え D&D。

**主要メソッド:**
- `_dnd_start_ghost(idx)` — ドラッグ中のゴースト（`tk.Toplevel`）を表示
- `_dnd_move_ghost(event)` / `_dnd_destroy_ghost()` — ゴースト位置更新・破棄
- `_dnd_show_indicator(event)` / `_dnd_clear_indicator()` — 挿入位置インジケーター
- `_dnd_dest_index(event)` — マウス位置から挿入先インデックスを計算
- `_dnd_drop(event)` — 単一/複数ページの移動を実行

**複数ページ移動:** `self.selected_pages` に選択ページが複数ある場合、`fitz.Document.select(new_order)` を使ってページ順を一括置換する。

**依存:** `pagefolio/constants.py` の `C`。

---

## イベントフロー

### 標準的なページ操作

```
ユーザー操作（ボタンクリック / キーボードショートカット）
    │
    ▼
1. Tkinter イベントループ → コマンドコールバック呼び出し
   例: btn(f2, "btn_delete", self._delete_selected)  [ui_builder.py]

2. _check_doc() で self.doc 存在確認  [app.py]

3. _save_undo(op, ...) で差分を _undo_stack に積む  [file_ops.py]

4. fitz.Document を直接変更  [page_ops.py 等]
   例: self.doc.delete_page(i)

5. _invalidate_thumb_cache(targets) でキャッシュ無効化  [viewer.py]

6. _refresh_all() を呼んで UI を再描画  [viewer.py]
   ├── _build_thumbnails() — サムネイルを再生成
   ├── _show_preview()    — プレビューを再描画（バックグラウンドスレッド）
   └── _update_doc_buttons_state() — ボタン活性状態を更新

7. _set_status(msg) でヘッダーにステータスを表示  [app.py]

8. plugin_manager.fire_event("on_page_*", ...) でプラグイン通知  [plugins.py]
```

### ファイルオープンフロー

```
Ctrl+O / D&D / ボタン
    │
    ▼
_open_file() または _on_dnd_drop()  [file_ops.py / app.py]
    │
    ▼
単一ファイル → _open_pdf_path(path)
複数ファイル → MergeOrderDialog → _do_open_merged(ordered_paths)
    │
    ▼
fitz.open(path) または fitz.open(stream=...) → self.doc 更新
    │
    ▼
_undo_stack / _redo_stack をクリア
_preview_gen / _thumb_gen をインクリメント
_refresh_all()
    │
    ▼
plugin_manager.fire_event("on_file_open", self, path)
```

### Undo フロー

```
Ctrl+Z → _undo()  [file_ops.py]
    │
    ├── Redo スタックに現在の全バイトスナップショットを保存
    │
    ├── Undo スタックから state を pop
    │
    └── _restore_state(state)
            ├── "pdf_bytes" キーあり → fitz.open(stream=bytes) で全復元
            └── op キーあり → 差分適用（rotate / crop / delete / move 等）
                    │
                    └── _refresh_all()
```

### プレビュー非同期レンダリング

```
_show_preview() 呼び出し
    │
    ├── _preview_gen をインクリメント（gen = self._preview_gen）
    ├── ローディングプレースホルダーを即時描画
    │
    └── threading.Thread(target=worker).start()
            │
            worker():
            ├── fitz.open(stream=doc_bytes) で独立した Document を開く
            ├── page.get_pixmap(matrix) でピクセルデータ生成
            └── root.after(0, lambda: _apply(samples, w, h))
                    │
                    _apply():
                    ├── self._preview_gen != gen なら中断（世代が変わっていたらキャンセル）
                    └── ImageTk.PhotoImage を生成して Canvas に描画
```

---

## プラグインアーキテクチャ

### 構造

```
plugins/                    # プロジェクトルートの plugins/ ディレクトリ
└── page_info.py            # サンプルプラグイン

pagefolio/plugins.py        # PDFEditorPlugin 基底クラス + PluginManager
```

### プラグインライフサイクル

1. **検出:** `PluginManager.discover_plugins()` が `plugins/` ディレクトリの `.py` ファイルを列挙
2. **読込:** `importlib.util.spec_from_file_location()` で動的インポート。`PDFEditorPlugin` のサブクラスを自動検出
3. **有効化/無効化:** `enable_plugin()` / `disable_plugin()` でオンザフライ切替。設定 `disabled_plugins` リストに保存
4. **イベント通知:** `fire_event(event_name, *args)` で有効な全プラグインの同名メソッドを呼び出し
5. **UI 構築:** `plugin.build_ui(app, parent_frame)` で右ペイン下部にカスタム UI を配置

### プラグインフック一覧

| メソッド | 呼ばれるタイミング | 定義箇所 |
|---------|---------------|---------|
| `on_load(app)` | プラグイン有効化時 | `plugins.py` |
| `on_unload(app)` | プラグイン無効化時 | `plugins.py` |
| `on_file_open(app, path)` | ファイルを開いた後 | `file_ops.py` |
| `on_file_save(app, path)` | ファイルを保存した後 | `file_ops.py` |
| `on_page_rotate(app, pages, degrees)` | ページ回転後 | `page_ops.py` |
| `on_page_delete(app, pages)` | ページ削除後 | `page_ops.py` |
| `on_page_crop(app, page_index)` | トリミング後 | `page_ops.py` |
| `on_page_change(app, page_index)` | 表示ページ変更時 | `viewer.py` |
| `on_insert(app, paths, insert_at)` | ページ挿入後 | `page_ops.py` |
| `on_merge(app, paths)` | PDF 結合後 | `page_ops.py` |
| `build_ui(app, parent)` | UI 構築時 | `app.py` (`_build_plugin_ui`) |

### プラグイン実装例

```python
# plugins/my_plugin.py
from pagefolio.plugins import PDFEditorPlugin

class MyPlugin(PDFEditorPlugin):
    name = "My Plugin"
    version = "1.0.0"

    def on_file_open(self, app, path):
        print(f"Opened: {path}")

    def build_ui(self, app, parent):
        import tkinter as tk
        from pagefolio.constants import C
        tk.Label(parent, text="My Plugin UI", bg=C["BG_CARD"]).pack()
```

---

## テーマシステム

テーマは `pagefolio/constants.py` で定義し、実行時に `C` 辞書に反映される。

```python
# 定義: constants.py
THEMES = {"dark": {...}, "light": {...}}
C = dict(THEMES["dark"])  # モジュールレベルのミュータブル辞書

# 適用: settings.py
def _apply_theme(theme_name):
    resolved = _resolve_theme(theme_name)  # "system" の場合は Windows レジストリから判定
    C.update(THEMES[resolved])
```

**参照方法:** すべての UI コードで `C["BG_DARK"]` 等のキーで参照する。ハードコードした色は使用しない。

---

## 設定永続化

設定は `pagefolio_settings.json` に JSON 形式で保存される。保存先はプロジェクトルート（通常実行時）または実行ファイルと同ディレクトリ（PyInstaller ビルド時）。

**設定キー:**
- `theme`: `"dark"` / `"light"` / `"system"`
- `font_size`: `8` 〜 `16`
- `lang`: `"ja"` / `"en"`
- `edit_mode`: `bool`
- `window_geometry`: `"1200x780+100+50"` 形式の文字列
- `sash_left` / `sash_right`: PanedWindow のサッシ位置（px）
- `disabled_plugins`: 無効化プラグイン ID のリスト

---

## エラーハンドリング戦略

**方針:** 操作ごとに `try/except Exception as e:` でキャッチし、`messagebox.showerror()` でユーザーに通知。裸の `except:` は使用しない。

**バックグラウンドスレッド内エラー:** `logger.debug()` でログに記録し、UI への適用をスキップする（`_apply()` 内で世代チェック）。

**Undo/Redo のフォールバック:** `_restore_state()` は差分適用と全スナップショット復元の両方に対応。差分で復元できない場合（Redo スタック）は `pdf_bytes` から全復元する。

---

## アーキテクチャ制約

- **スレッドモデル:** Tkinter はシングルスレッド。プレビューレンダリングのみ `threading.Thread` を使用し、UI 操作は必ず `root.after()` 経由でメインスレッドに戻す
- **グローバル状態:** `pagefolio/constants.py` の `C` 辞書（ミュータブル、`_apply_theme()` で更新）および `pagefolio/settings.py` の `_current_font_size`
- **循環インポート:** `pagefolio/app.py` と `pagefolio/dialogs.py` の間に循環インポートリスクがあるため、`dialogs` は Mixin 内で遅延インポートする
- **fitz.Document の所有:** `self.doc` は常に `PDFEditorApp` が唯一の所有者。バックグラウンドスレッドでは `doc.tobytes()` からコピーを開いて操作する

---

## アンチパターン

### バックグラウンドスレッドから直接 self.doc を参照する

**問題になる例:**
```python
# 誤り — バックグラウンドスレッドで self.doc を直接参照
def worker():
    page = self.doc[page_idx]  # スレッドセーフでない
```
**正しい方法:**
```python
# 正解 — メインスレッドで bytes を取得してからスレッドへ渡す
doc_bytes = self.doc.tobytes()
def worker():
    tmp_doc = fitz.open(stream=doc_bytes, filetype="pdf")
    page = tmp_doc[page_idx]  # ローカルコピーを使用
```
実装例: `pagefolio/viewer.py` の `_show_preview()`

### テーマ色をハードコードする

```python
# 誤り
label = tk.Label(parent, bg="#1a1a2e")

# 正解
label = tk.Label(parent, bg=C["BG_DARK"])
```

### フォントサイズをハードコードする

```python
# 誤り
font=("Segoe UI", 10, "bold")

# 正解
font=self._font(0, "bold")
```

---

*Architecture analysis: 2026-05-23*
