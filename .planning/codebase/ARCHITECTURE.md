<!-- refreshed: 2026-05-04 -->
# アーキテクチャ

**分析日:** 2026-05-04

---

## システム概要

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        エントリーポイント層                           │
│   pagefolio.py  /  pagefolio/__main__.py                            │
│   TkinterDnD.Tk() または tk.Tk() を生成して PDFEditorApp を起動      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       PDFEditorApp（Mixin 統合クラス）               │
│   `pagefolio/app.py`                                                │
│                                                                     │
│  ┌─────────────┐ ┌────────────┐ ┌───────────┐ ┌────────┐ ┌──────┐ │
│  │UIBuilderMixin│ │FileOpsMixin│ │PageOpsMixin│ │Viewer  │ │DnD   │ │
│  │ui_builder.py │ │file_ops.py │ │page_ops.py │ │Mixin   │ │Mixin │ │
│  │スタイル・    │ │open/save/  │ │回転/削除/  │ │viewer  │ │dnd   │ │
│  │レイアウト    │ │Undo/Redo   │ │crop/挿入   │ │.py     │ │.py   │ │
│  └─────────────┘ └────────────┘ └───────────┘ └────────┘ └──────┘ │
└────────────┬────────────────────────────┬───────────────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐   ┌─────────────────────────────────────┐
│    サポートモジュール    │   │           ダイアログ群               │
│  `pagefolio/constants` │   │   `pagefolio/dialogs.py`            │
│  `pagefolio/settings`  │   │   AboutDialog / SettingsDialog      │
│  `pagefolio/plugins`   │   │   PluginDialog / MergeOrderDialog   │
│  `pagefolio/file_drop` │   └─────────────────────────────────────┘
└────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        外部ライブラリ                                 │
│   fitz (pymupdf) — PDF 操作                                         │
│   PIL / ImageTk  — 画像変換・表示                                    │
│   tkinterdnd2    — ファイル D&D（オプション）                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## アーキテクチャパターン

**全体パターン:** Mixin 合成パターン（Mixin Composition）

`PDFEditorApp` は 5 つの Mixin クラスを多重継承で組み合わせている。各 Mixin は独立した責務を持ち、`self` を通じて `PDFEditorApp` の状態（`self.doc`, `self.current_page` 等）を共有する。

```python
# pagefolio/app.py
class PDFEditorApp(UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin):
    ...
```

**解決順序（MRO）:** `PDFEditorApp → UIBuilderMixin → FileOpsMixin → PageOpsMixin → ViewerMixin → DnDMixin`

Mixin 間に継承関係はなく、すべてが `PDFEditorApp` の単一状態ストアを参照する。

---

## コンポーネント責務表

| コンポーネント | クラス / 関数 | ファイル | 責務 |
|--------------|--------------|---------|------|
| アプリ本体 | `PDFEditorApp` | `pagefolio/app.py` | Mixin 統合・状態保持・キーバインド・ユーティリティ |
| UI構築 | `UIBuilderMixin` | `pagefolio/ui_builder.py` | ttk スタイル定義・3ペインレイアウト構築 |
| ファイル操作 | `FileOpsMixin` | `pagefolio/file_ops.py` | PDF 開閉・保存（上書き/名前付け/圧縮）・Undo/Redo |
| ページ操作 | `PageOpsMixin` | `pagefolio/page_ops.py` | 回転・削除・複製・トリミング・挿入・結合・分割 |
| 表示制御 | `ViewerMixin` | `pagefolio/viewer.py` | プレビュー描画・ズーム・サムネイル・ページ選択・ポップアップ |
| D&D並び替え | `DnDMixin` | `pagefolio/dnd.py` | サムネイルのドラッグ&ドロップによるページ移動 |
| ダイアログ群 | 各 Dialog クラス | `pagefolio/dialogs.py` | About / 設定 / プラグイン管理 / 結合順 の各モーダル |
| プラグイン | `PDFEditorPlugin`, `PluginManager` | `pagefolio/plugins.py` | プラグインの検出・読込・有効化・イベント配信 |
| 設定 | 関数群 | `pagefolio/settings.py` | JSON 設定の読み書き・テーマ解決・フォント生成 |
| 定数 | `THEMES`, `C`, `LANG` | `pagefolio/constants.py` | テーマカラー・バージョン・言語辞書 |
| ファイルD&D | `_setup_file_drop` | `pagefolio/file_drop.py` | tkinterdnd2 によるファイルドロップ登録（オプション） |

---

## 状態管理

`PDFEditorApp.__init__` で初期化されるインスタンス変数が唯一の状態ストアとなる。グローバル状態は `C`（テーマ辞書）のみ。

### 主要な状態変数（`pagefolio/app.py`）

| 変数 | 型 | 初期値 | 意味 |
|------|----|--------|------|
| `self.doc` | `fitz.Document \| None` | `None` | 現在開いている PDF。未開時は `None` |
| `self.filepath` | `str \| None` | `None` | 現在ファイルのパス。結合開きは `None` |
| `self.current_page` | `int` | `0` | 表示中ページのインデックス（0始まり） |
| `self.selected_pages` | `set[int]` | `set()` | 複数選択されているページのインデックス集合 |
| `self.thumb_images` | `list[ImageTk.PhotoImage]` | `[]` | サムネイル画像参照（GC防止用） |
| `self.thumb_cache` | `dict[int, ImageTk.PhotoImage]` | `{}` | ページインデックス→サムネイル画像のキャッシュ |
| `self._undo_stack` | `list[dict]` | `[]` | Undo 用状態スナップショットのスタック（最大20件） |
| `self._redo_stack` | `list[dict]` | `[]` | Redo 用状態スナップショットのスタック |
| `self.zoom` | `float` | `1.0` | プレビューのズーム倍率（0.3〜3.0） |
| `self.crop_mode` | `bool` | `False` | トリミングモードの ON/OFF |
| `self.crop_rect` | `tuple \| None` | `None` | キャンバス座標でのトリミング矩形 |
| `self.edit_mode` | `bool` | `False` | 編集モード（True）/ 閲覧モード（False） |
| `self.settings` | `dict` | 設定ファイルから | テーマ・フォント・ジオメトリ等の設定辞書 |
| `self.font_size` | `int` | `10` | ベースフォントサイズ（8〜16） |
| `self.lang` | `str` | `"ja"` | 表示言語（`"ja"` または `"en"`） |
| `self._doc_buttons` | `list[ttk.Button]` | `[]` | doc 未開時に disabled にするボタンのリスト |
| `self._edit_only_buttons` | `list[ttk.Button]` | `[]` | 閲覧モード時に disabled にするボタンのリスト |
| `self._pending_click` | `int \| None` | `None` | ダブルクリック競合防止用の `after()` ID |
| `self._paned` | `tk.PanedWindow` | — | 3ペイン分割の参照 |
| `self._right_panel` | `tk.Frame` | — | 右ツールパネルの参照 |
| `self._mode_btn` | `ttk.Button \| None` | `None` | モード切替ボタンの参照 |
| `self.plugin_manager` | `PluginManager` | — | プラグイン管理オブジェクト |

### グローバル状態

| 変数 | ファイル | 意味 |
|------|---------|------|
| `C` | `pagefolio/constants.py` | 実行時テーマ辞書。`_apply_theme()` で書き換え |
| `_current_font_size` | `pagefolio/settings.py` | ダイアログが参照するフォントサイズ |

---

## データフロー

### PDF 読み込みフロー

```
ユーザー操作（ファイル選択 / D&D）
    │
    ▼
FileOpsMixin._open_file()              # pagefolio/file_ops.py
    │  filedialog.askopenfilenames()
    ▼
FileOpsMixin._open_pdf_path(path)      # pagefolio/file_ops.py
    │  fitz.open(path) → self.doc
    │  self.filepath = path
    │  self.current_page = 0
    │  self.selected_pages.clear()
    │  self._undo_stack.clear()
    │  self._redo_stack.clear()
    │  self._invalidate_thumb_cache()
    ▼
ViewerMixin._refresh_all()             # pagefolio/viewer.py
    │  ├── _build_thumbnails()         # サムネイル全再構築
    │  ├── _show_preview()             # プレビュー描画
    │  └── _update_doc_buttons_state() # ボタン活性化
    ▼
PluginManager.fire_event("on_file_open", ...)  # pagefolio/plugins.py
```

### ページ操作フロー（回転を例に）

```
ユーザー: ボタンクリック or キーボード
    │
    ▼
PageOpsMixin._rotate_selected(deg)     # pagefolio/page_ops.py
    │  self._check_doc()               # self.doc の存在確認
    │  self._save_undo()               # Undo スタックに現状態を保存
    │  self._get_targets()             # selected_pages or [current_page]
    │  page.set_rotation(...)          # fitz API で回転
    │  self._invalidate_thumb_cache(targets)
    ▼
ViewerMixin._refresh_all()             # サムネイル・プレビュー再描画
    ▼
PDFEditorApp._set_status(msg)          # ヘッダーにステータス表示
    ▼
PluginManager.fire_event("on_page_rotate", ...)
```

### Undo/Redo スタック設計

```
操作前: FileOpsMixin._save_undo() を呼ぶ
    │
    │  スナップショット = {
    │      "pdf_bytes": self.doc.tobytes(),   # PDF 全体をバイト列化
    │      "current_page": self.current_page,
    │      "selected_pages": set(self.selected_pages),
    │  }
    │  self._undo_stack.append(スナップショット)
    │  len(self._undo_stack) > MAX_UNDO(20) なら先頭を削除
    │  self._redo_stack.clear()
    │
Undo 実行: FileOpsMixin._undo()
    │  現在状態を _redo_stack にプッシュ
    │  _undo_stack から pop
    │  self.doc = fitz.open(stream=bytes, filetype="pdf")  ← メモリから復元
    │  _refresh_all() で再描画
    │
Redo 実行: FileOpsMixin._redo()
    │  現在状態を _undo_stack にプッシュ
    │  _redo_stack から pop
    │  同様に復元
```

**設計上の特徴:** PDF 全体をバイト列としてスナップショット保存するため、任意の変更を完全に巻き戻せる。メモリコストは PDF サイズ × スタック件数。

### トリミングフロー（座標変換）

```
canvas 座標 (sx, sy, ex, ey)   ← マウスドラッグで記録
    │
    │  scale = self.zoom * 1.5  ← プレビュー描画時の倍率
    │  img_offset = 10          ← キャンバス内パディング
    │
    ▼
PDF 座標 (x0_pdf, y0_pdf, x1_pdf, y1_pdf)
    │  x0_pdf = (sx - img_offset) / scale
    │
    ▼
fitz.Rect に変換、MediaBox 内にクランプ（EPS=0.01）
    │
    ▼
page.set_cropbox(new_rect)     # pagefolio/page_ops.py: _crop_page()
```

### UI 再構築フロー（テーマ変更時）

```
SettingsDialog._apply() → PDFEditorApp._apply_settings()
    │  _apply_theme(new_theme)    # C 辞書を更新
    │  _save_settings()
    │  _rebuild_ui()
    │      ├── root.winfo_children() を全 destroy
    │      ├── thumb_images / thumb_cache をクリア
    │      ├── _build_styles()
    │      ├── _build_ui()
    │      └── _refresh_all() または _show_preview()
    │  _setup_file_drop(self)     # D&D 再登録
```

---

## イベント駆動の仕組み

### Tkinter イベント

| イベント | バインド先 | ハンドラ |
|---------|-----------|---------|
| `<Control-o>` | `root` | `_open_file()` |
| `<Control-s>` | `root` | `_save_file()` |
| `<Control-z>` | `root` | `_undo()` |
| `<Control-y>` | `root` | `_redo()` |
| `<Control-Shift-s>` | `root` | `_save_as()` |
| `<Delete>` | `root` | `_delete_selected()` |
| `<F5>` | `root` | `_toggle_edit_mode()` |
| `<ButtonPress-1>` | `preview_canvas` | `_crop_drag_start()` |
| `<B1-Motion>` | `preview_canvas` | `_crop_drag_move()` |
| `<ButtonRelease-1>` | `preview_canvas` | `_crop_drag_end()` |
| `<ButtonPress-1>` | サムネイル frame/label | `on_press()` (D&D 開始) |
| `<B1-Motion>` | サムネイル frame/label | `on_motion()` (D&D 移動) |
| `<ButtonRelease-1>` | サムネイル frame/label | `on_release()` (D&D ドロップ/クリック) |
| `<Double-Button-1>` | サムネイル frame/label | `_show_page_popup()` |
| `WM_DELETE_WINDOW` | `root` | `_quit()` |

### シングルクリック / ダブルクリック競合防止

サムネイルの `on_release` では `root.after(250, _single_click)` で遅延実行し、`_pending_click` に ID を保存する。ダブルクリック時は `on_double` 内で `root.after_cancel(_pending_click)` を呼びシングルクリック処理をキャンセルする。

### プラグインイベントシステム

```python
# 各操作の後に fire_event を呼ぶ（pagefolio/file_ops.py, page_ops.py 等）
self.plugin_manager.fire_event("on_file_open", self, path)

# PluginManager.fire_event (pagefolio/plugins.py)
for plugin_id, plugin in self.plugins.items():  # _disabled を除外
    method = getattr(plugin, event_name, None)
    if method:
        method(*args, **kwargs)
```

利用可能なイベント: `on_load`, `on_unload`, `on_file_open`, `on_file_save`, `on_page_rotate`, `on_page_delete`, `on_page_crop`, `on_page_change`, `on_insert`, `on_merge`

---

## プラグインシステム設計

```
plugins/                       ← PLUGINS_DIR（プロジェクトルート）
└── page_info.py               ← PDFEditorPlugin を継承したクラスを定義

PluginManager.load_all()
    │  discover_plugins()      ← plugins/ 内の .py ファイルを列挙
    │  load_plugin(id, path)   ← importlib.util.spec_from_file_location
    │                            モジュール内で PDFEditorPlugin サブクラスを検索
    │  instance.on_load(app)   ← 有効なプラグインのみ
    ▼
PluginManager.plugins          ← _disabled を除外した有効プラグイン辞書
```

プラグインは `build_ui(app, parent)` を実装することで右パネルにカスタム UI を追加できる。

---

## エラー処理方針

- **すべての例外は `except Exception as e:` で捕捉**（裸の `except:` 禁止）
- ユーザー操作エラー: `messagebox.showerror()` / `messagebox.showwarning()` でダイアログ表示
- 内部エラー（ジオメトリ復元失敗等）: `logger.debug()` でログ記録し処理継続
- プラグインエラー: `logger.exception()` で記録し他プラグインへ影響させない
- ファイル保存: incremental save 失敗時は `.tmp` ファイル経由でフォールバック（`pagefolio/file_ops.py`）

---

## アーキテクチャ上の制約

- **シングルスレッド:** Tkinter のイベントループは単一スレッド。重い PDF 処理（大規模結合・分割）はブロッキング
- **グローバル `C` 辞書:** `pagefolio/constants.py` の `C` はモジュールレベルのミュータブルオブジェクト。テーマ変更時に `_apply_theme()` で一括更新
- **Mixin の状態共有:** すべての Mixin が `self` を通じて同一状態を参照するため、メソッド名の衝突に注意が必要
- **トリミングは現在ページのみ:** `_crop_page()` は `self.current_page` の 1 ページのみ対象
- **D&D は 1 ページずつ:** `_dnd_drop()` は `_dnd_src_idx`（単一）のみ処理

---

## アンチパターン（避けるべき実装）

### ハードコードされたフォントサイズの使用

**やってはいけない:** `font=("Segoe UI", 12, "bold")`
**正しい方法:** `font=self._font(2, "bold")` — `pagefolio/app.py` の `_font()` ヘルパーを使う

### C 辞書を迂回した直接カラー指定

**やってはいけない:** `fg="#e94560"`
**正しい方法:** `fg=C["ACCENT"]` — `pagefolio/constants.py` の `C` 辞書経由で参照

### _refresh_all() を省略した状態変更

**やってはいけない:** `self.doc.delete_page(i)` 後に再描画しない
**正しい方法:** ページ変更後は必ず `self._refresh_all()` を呼ぶ

### _save_undo() を省略した破壊的操作

**やってはいけない:** `_delete_selected()` 等で Undo スタックへの保存を省略
**正しい方法:** 破壊的操作の直前に `self._save_undo()` を呼ぶ

---

*アーキテクチャ分析: 2026-05-04*
