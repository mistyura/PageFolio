<!-- refreshed: 2026-05-04 -->
# コードベース構造

**分析日:** 2026-05-04

---

## ディレクトリツリー

```
PageFolio/                          # プロジェクトルート
├── pagefolio.py                    # エントリーポイント（python pagefolio.py）
├── pagefolio/                      # メインパッケージ
│   ├── __init__.py                 # 後方互換の公開 API（主要クラス・関数を re-export）
│   ├── __main__.py                 # python -m pagefolio エントリーポイント
│   ├── app.py                      # PDFEditorApp 本体（Mixin 統合・状態管理）
│   ├── ui_builder.py               # UIBuilderMixin（スタイル・レイアウト構築）
│   ├── file_ops.py                 # FileOpsMixin（open/save/Undo/Redo）
│   ├── page_ops.py                 # PageOpsMixin（回転/削除/crop/挿入/結合/分割）
│   ├── viewer.py                   # ViewerMixin（プレビュー/ズーム/サムネイル/ポップアップ）
│   ├── dnd.py                      # DnDMixin（サムネイルD&D並び替え）
│   ├── dialogs.py                  # ダイアログ群（About/Settings/Plugin/MergeOrder）
│   ├── plugins.py                  # プラグインシステム（PDFEditorPlugin, PluginManager）
│   ├── settings.py                 # 設定ユーティリティ（読み書き・テーマ解決）
│   ├── constants.py                # 定数（THEMES, C, APP_VERSION, LANG, PLUGINS_DIR）
│   └── file_drop.py                # ファイルD&D登録（tkinterdnd2 ラッパー）
├── plugins/                        # プラグインディレクトリ（実行時に検索）
│   └── page_info.py                # サンプルプラグイン（ページ情報表示）
├── tests/                          # テストスイート（pytest）
│   ├── conftest.py                 # 共通フィクスチャ
│   ├── test_utils.py               # ユーティリティ関数テスト（35件）
│   ├── test_pdf_ops.py             # PDF 操作テスト（26件）
│   └── test_plugins.py             # PluginManager テスト（17件）
├── docs/                           # スクリーンショット画像
├── pagefolio.ico                   # アプリアイコン
├── pyproject.toml                  # Ruff・pytest 設定
├── requirements.txt                # 依存パッケージリスト
├── README.md                       # エンドユーザー向け説明
├── CLAUDE.md                       # AI 開発指示書
├── 開発履歴.md                     # 機能追加・変更の履歴
└── LICENSE                         # MIT ライセンス
（実行時に自動生成）
└── pagefolio_settings.json         # ユーザー設定（テーマ・フォントサイズ等）
```

---

## 各ファイルの役割

### エントリーポイント

| ファイル | 役割 |
|---------|------|
| `pagefolio.py` | `python pagefolio.py` で起動するシェルラッパー。`pagefolio/__main__.py` の `main()` を呼ぶだけ |
| `pagefolio/__main__.py` | `python -m pagefolio` のエントリーポイント。tkinterdnd2 の有無に応じて `TkinterDnD.Tk()` または `tk.Tk()` を選択して `PDFEditorApp` を生成 |

### アプリケーション本体

| ファイル | クラス | 役割 |
|---------|--------|------|
| `pagefolio/app.py` | `PDFEditorApp` | 5つの Mixin を多重継承で統合。`__init__` で全状態変数を初期化し、キーバインドを登録。ユーティリティメソッド（`_check_doc`, `_get_targets`, `_set_status`, `_font`, `_t`）も定義 |
| `pagefolio/ui_builder.py` | `UIBuilderMixin` | `_build_styles()` で ttk スタイルを定義。`_build_ui()` で 3ペイン（左:サムネイル / 中:プレビュー / 右:ツール）のレイアウトを構築 |
| `pagefolio/file_ops.py` | `FileOpsMixin` | PDF の開閉・保存（上書き/名前付き/圧縮）と Undo/Redo スタック管理 |
| `pagefolio/page_ops.py` | `PageOpsMixin` | ページ回転・削除・複製・トリミング（座標変換含む）・別PDF挿入・結合・分割保存 |
| `pagefolio/viewer.py` | `ViewerMixin` | fitz → PIL → ImageTk 変換によるプレビュー・サムネイル描画。ページナビゲーション・ズーム・サムネイルキャッシュ・ポップアップ拡大表示 |
| `pagefolio/dnd.py` | `DnDMixin` | サムネイルのマウスドラッグによるページ並び替え（ゴースト表示・挿入位置インジケーター） |

### サポートモジュール

| ファイル | 役割 |
|---------|------|
| `pagefolio/dialogs.py` | `AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog` の4ダイアログ。いずれも `tk.Toplevel` を継承し `grab_set()` でモーダル動作 |
| `pagefolio/plugins.py` | `PDFEditorPlugin`（プラグイン基底クラス）と `PluginManager`（検出・読込・有効化・イベント配信） |
| `pagefolio/settings.py` | `pagefolio_settings.json` の読み書き・テーマ名解決（`system` → OS 判定）・テーマ辞書 `C` の更新 |
| `pagefolio/constants.py` | `THEMES`（カラー辞書）、`C`（実行時テーマ辞書）、`APP_VERSION`、`LANG`（ja/en 言語辞書）、`SETTINGS_FILE`、`PLUGINS_DIR` |
| `pagefolio/file_drop.py` | tkinterdnd2 の有無を `try/import` で検出し、`preview_canvas` への D&D ドロップ登録を行う薄いラッパー |

### 公開 API（`pagefolio/__init__.py`）

```python
# 後方互換のために re-export しているシンボル群
from pagefolio.app import PDFEditorApp
from pagefolio.constants import APP_VERSION, LANG, THEMES, C
from pagefolio.dialogs import AboutDialog, MergeOrderDialog, PluginDialog, SettingsDialog
from pagefolio.plugins import PDFEditorPlugin, PluginManager
from pagefolio.settings import _apply_theme, _detect_system_theme, _get_settings_path,
                                _load_settings, _make_font, _resolve_theme, _save_settings
```

---

## モジュール間の依存関係

```
pagefolio.py
    └── pagefolio/__main__.py
            ├── pagefolio/app.py
            │       ├── pagefolio/constants.py    (LANG, C)
            │       ├── pagefolio/settings.py     (_apply_theme, _load_settings, _save_settings)
            │       ├── pagefolio/plugins.py      (PluginManager)
            │       ├── pagefolio/dialogs.py      (PluginDialog, SettingsDialog)
            │       ├── pagefolio/ui_builder.py   (UIBuilderMixin)
            │       │       └── pagefolio/constants.py
            │       ├── pagefolio/file_ops.py     (FileOpsMixin)
            │       ├── pagefolio/page_ops.py     (PageOpsMixin)
            │       │       └── pagefolio/constants.py
            │       ├── pagefolio/viewer.py       (ViewerMixin)
            │       │       └── pagefolio/constants.py
            │       ├── pagefolio/dnd.py          (DnDMixin)
            │       │       └── pagefolio/constants.py
            │       └── pagefolio/file_drop.py   (_setup_file_drop)
            └── pagefolio/file_drop.py

pagefolio/dialogs.py
    ├── pagefolio/constants.py   (APP_VERSION, LANG, PLUGINS_DIR, C)
    ├── pagefolio/plugins.py     (_get_plugins_dir)
    └── pagefolio/settings.py   (_current_font_size)

pagefolio/plugins.py
    └── pagefolio/constants.py   (PLUGINS_DIR)

pagefolio/settings.py
    └── pagefolio/constants.py   (SETTINGS_FILE, THEMES, C)
```

**依存の方向性:** `constants` と `settings` が最下層。Mixin モジュールは `constants` のみに依存し、互いに依存しない。`app.py` がすべての Mixin と上位モジュールを統合する頂点となる。

---

## エントリーポイントからの実行フロー

```
1. python pagefolio.py
       └── pagefolio/__main__.py::main()

2. tkinterdnd2 の有無を確認
       ├── あり: TkinterDnD.Tk() を root として使用
       └── なし: tk.Tk() を root として使用（D&D 無効）

3. PDFEditorApp(root) の __init__
       ├── logging.basicConfig()
       ├── _load_settings()             ← pagefolio_settings.json を読む
       ├── _apply_theme(settings)       ← C 辞書を更新
       ├── root.geometry() を復元       ← 前回終了時の位置・サイズ
       ├── self.doc = None 等の状態初期化
       ├── PluginManager.load_all()     ← plugins/ をスキャン
       ├── _build_styles()              ← UIBuilderMixin: ttk スタイル定義
       ├── _build_ui()                  ← UIBuilderMixin: 3ペインレイアウト構築
       ├── root.protocol("WM_DELETE_WINDOW", self._quit)
       └── root.bind() でキーボードショートカット登録

4. _setup_file_drop(app)               ← tkinterdnd2 D&D 登録

5. root.mainloop()                     ← イベントループ開始
```

---

## 命名規則

### ファイル

| パターン | 例 | 意味 |
|---------|-----|------|
| `snake_case.py` | `ui_builder.py` | モジュールファイル |
| `__dunder__.py` | `__init__.py` | Python 特殊ファイル |

### メソッド

| パターン | 例 | 意味 |
|---------|-----|------|
| `_メソッド名` | `_open_file()` | 内部メソッド（外部から直接呼ばない） |
| `_build_xxx` | `_build_ui()` | UI 構築系メソッド |
| `_refresh_xxx` | `_refresh_all()` | 表示更新系メソッド |
| `_on_xxx` | `_on_dnd_drop()` | イベントハンドラ |
| `_do_xxx` | `_do_merge()` | 確認後の実行処理 |

### ボタンスタイル

| スタイル | 用途 |
|---------|------|
| `"TButton"` | 通常操作 |
| `"Accent.TButton"` | 主要アクション（開く・保存等） |
| `"Danger.TButton"` | 破壊的操作（削除・終了等） |
| `"CropOn.TButton"` | トリミングモード ON 時 |

---

## 新規コード追加時の指針

### 新しいページ操作を追加する場合

1. 実装先: `pagefolio/page_ops.py` の `PageOpsMixin` にメソッドを追加
2. UI ボタン追加先: `pagefolio/ui_builder.py` の `_build_tools()` 内、適切なセクション
3. 破壊的操作は必ず `self._save_undo()` を冒頭で呼ぶ
4. 操作後は `self._refresh_all()` を呼ぶ
5. ステータス表示: `self._set_status(self._t("status_xxx"))` を使う
6. 多言語対応: `pagefolio/constants.py` の `LANG["ja"]` と `LANG["en"]` 両方にキーを追加

### 新しいダイアログを追加する場合

1. 追加先: `pagefolio/dialogs.py`
2. `tk.Toplevel` を継承し `self.grab_set()` でモーダル化
3. カラーは `C["BG_DARK"]` 等、フォントは `self._font(delta, weight)` を使う
4. 呼び出し元: `pagefolio/app.py` から `_open_xxx()` メソッド経由で呼ぶ

### 新しいプラグインを作成する場合

1. 配置先: `plugins/` ディレクトリ内の `.py` ファイル（`_` 始まり禁止）
2. `PDFEditorPlugin` を継承したクラスを定義
3. `name`, `version`, `description`, `author` クラス変数を設定
4. 必要なイベントメソッドをオーバーライド
5. カスタム UI が必要な場合は `build_ui(app, parent)` を実装

### 新しい設定項目を追加する場合

1. `pagefolio/settings.py` の `_load_settings()` 内 `defaults` にデフォルト値を追加
2. `PDFEditorApp.__init__` で `self.settings.get("key", default)` で読み込む
3. 終了時は `self._save_window_state()` 経由で保存（またはイベント後に `_save_settings()` を直接呼ぶ）
4. 設定 UI が必要な場合は `pagefolio/dialogs.py` の `SettingsDialog._build()` を拡張

### カラー・テーマを拡張する場合

1. `pagefolio/constants.py` の `THEMES["dark"]` と `THEMES["light"]` 両方に同じキーで追加
2. コード中では `C["新キー名"]` で参照（絶対にハードコードしない）

---

## 特殊ディレクトリ

| ディレクトリ | 用途 | 生成 | コミット |
|------------|------|------|---------|
| `plugins/` | プラグイン配置場所。起動時に自動スキャン | 手動 | Yes（サンプルあり） |
| `tests/` | pytest テストスイート | 手動 | Yes |
| `docs/` | スクリーンショット等のドキュメント画像 | 手動 | Yes |
| `.planning/` | GSD コードベース分析ドキュメント | 自動（GSD） | 任意 |

---

## 実行時に生成されるファイル

| ファイル | 場所 | 内容 |
|---------|------|------|
| `pagefolio_settings.json` | プロジェクトルート（または exe と同ディレクトリ） | テーマ・フォントサイズ・ウィンドウジオメトリ・言語・サッシ位置・無効プラグイン一覧 |

---

*構造分析: 2026-05-04*
