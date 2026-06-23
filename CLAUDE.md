# CLAUDE.md — PageFolio AI 開発指示書

このファイルは Claude (AI) がこのプロジェクトを編集・拡張する際に参照する指示書です。
エンドユーザー向けの情報は [README.md](README.md)、変更履歴は [開発履歴.md](開発履歴.md) を参照してください。

---

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| アプリ名 | PageFolio |
| 言語 | Python 3.8+ |
| UI フレームワーク | Tkinter（標準ライブラリ） |
| PDF ライブラリ | pymupdf (fitz) |
| 画像ライブラリ | Pillow (PIL) |
| 対象 OS | Windows 11 |
| 現在バージョン | `pagefolio/constants.py` の `APP_VERSION` を参照 |

> バージョン番号は `pagefolio/constants.py` の `APP_VERSION` を真の情報源とする。
> README.md のバッジ・開発履歴.md の最新エントリと同期させること。

---

## ファイル構成

```
PageFolio/
├── pagefolio.py               # エントリーポイント（python pagefolio.py で起動）
├── pagefolio/                 # メインパッケージ
│   ├── __init__.py            # 公開API（後方互換 import 用）
│   ├── __main__.py            # python -m pagefolio エントリーポイント
│   ├── constants.py           # バージョン・ファイル名・拡張子定数（APP_VERSION）+ themes/lang 再エクスポート
│   ├── themes.py              # カラーテーマ定義（THEMES, 実行時辞書 C）
│   ├── lang.py                # 言語辞書（LANG: ja / en）
│   ├── settings.py            # 設定ユーティリティ関数
│   ├── plugins.py             # プラグインシステム（PDFEditorPlugin, PluginManager）
│   ├── app.py                 # PDFEditorApp 本体（Mixin 統合 + 状態管理）
│   ├── ui_builder.py          # UI構築 Mixin（スタイル・レイアウト）
│   ├── file_ops.py            # ファイル操作 Mixin（open/save/undo/redo）
│   ├── page_ops.py            # ページ操作 Mixin（回転/削除/トリミング/挿入/結合/分割）
│   ├── print_ops.py           # 印刷 Mixin（PrintOpsMixin / write_print_tempfile）
│   ├── viewer.py              # 表示 Mixin（プレビュー/ズーム/サムネイル/ポップアップ）
│   ├── dnd.py                 # D&D Mixin（サムネイルのドラッグ並び替え）
│   ├── pagination.py          # サムネイル窓計算 / local↔global インデックス変換（Tk・fitz 非依存の純関数群）
│   ├── ocr.py                 # OCR Mixin + ヘルパー（build_provider / 並列実行 / リトライ制御 / resolve_ocr_prompt）
│   ├── ocr_providers.py       # OCR プロバイダ（LMStudio / Claude / Gemini / Tesseract）
│   ├── md_render.py           # Markdown→(行種別, インライン span) 変換の純関数（parse_markdown・Tk/fitz 非依存）
│   ├── ocr_dialog.py          # OCRDialog（複数ページ OCR 結果ビューア / エクスポート / Markdown 整形描画）
│   ├── dialogs/               # ダイアログパッケージ
│   │   ├── __init__.py        # 後方互換 re-export（from pagefolio.dialogs import ...）
│   │   ├── about.py           # AboutDialog
│   │   ├── settings.py        # SettingsDialog
│   │   ├── plugin.py          # PluginDialog
│   │   ├── merge.py           # MergeOrderDialog / MergeResizeDialog
│   │   ├── llm_config.py      # LLMConfigDialog（OCR プロバイダ / モデル設定）
│   │   ├── export_images.py   # ExportImagesDialog（ページ→画像変換 / 範囲・スケール指定）
│   │   └── password.py        # SetPasswordDialog（パスワード付与の入力 UI）
│   └── file_drop.py           # ファイル D&D（tkinterdnd2 連携）
├── pagefolio.ico              # アプリアイコン
├── PageFolio.spec             # PyInstaller ビルド定義（onedir 形式）
├── README.md                  # エンドユーザー向け使用概要
├── CLAUDE.md                  # 本ファイル（AI 向け開発指示書）
├── 開発履歴.md                # 機能追加・変更の履歴
├── LICENSE                    # MITライセンス
├── pyproject.toml             # Ruff・pytest 設定
├── requirements.txt           # 依存パッケージ（バージョン固定）
├── plugins/                   # プラグインディレクトリ
│   └── page_info.py           # サンプルプラグイン（ページ情報表示）
├── tests/                     # テストスイート（pytest）
│   ├── conftest.py            # テスト用共通フィクスチャ
│   ├── test_imports.py        # パッケージ import / 後方互換テスト
│   ├── test_utils.py          # ユーティリティ関数テスト
│   ├── test_pdf_ops.py        # PDF 操作テスト
│   ├── test_plugins.py        # PluginManager テスト
│   ├── test_viewer.py         # プレビュー / サムネイル描画テスト
│   ├── test_settings_keyguard.py  # API キー非保存ガードテスト
│   ├── test_ocr.py            # OCR ヘルパー / 並列実行テスト
│   ├── test_ocr_providers.py  # OCR プロバイダ単体テスト
│   ├── test_provider_ui.py    # プロバイダ UI（ダイアログ連携）/ resolve_ocr_prompt テスト
│   ├── test_pagination.py     # ページネーション純ロジック（窓計算 / local↔global / 境界値）テスト
│   ├── test_md_render.py      # parse_markdown 純関数（行種別 / インライン span）テスト
│   ├── test_export_images.py  # ページ→画像変換（範囲パース / スケール計算 / 出力）テスト
│   ├── test_save_overwrite.py # 縮小して保存（上書き）ヘルパーのテスト
│   ├── test_password.py       # PDF パスワード付与/解除・暗号化保存ヘルパーのテスト
│   ├── test_print.py          # 印刷一時ファイル生成 / OS 分岐のテスト
│   ├── test_lang_parity.py    # ja/en LANG キー一致 / プレースホルダ整合の回帰テスト
│   └── test_source_keyguard.py  # pagefolio/ ソースの実 API キーパターン不在スキャン
└── docs/                      # スクリーンショット画像

（実行時に自動生成）
└── pagefolio_settings.json    # ユーザー設定（テーマ・フォントサイズ等）
```

---

## モジュール構成

### `pagefolio/constants.py`

バージョン（`APP_VERSION`）・ファイル名・対応拡張子の定数を定義。
`themes.py` の `THEMES` / `C`、`lang.py` の `LANG` を再エクスポートし後方互換 import 表面を維持。

### `pagefolio/themes.py` / `pagefolio/lang.py`

`themes.py` はカラーテーマ（`THEMES`）と実行時テーマ辞書（`C`）、`lang.py` は言語辞書（`LANG`、ja / en）を定義。
LANG の新規キーは **ja / en 両方に同一キーで追加**しキー数の左右一致を維持すること。

### `pagefolio/settings.py`

設定ファイルの読み書き・テーマ解決・フォント生成のユーティリティ関数群。
API キーは `_SENSITIVE_KEYS` ガードにより `pagefolio_settings.json` へ保存されない。

### `pagefolio/plugins.py`

`PDFEditorPlugin` 基底クラスと `PluginManager` クラス。プラグインの検出・読込・有効/無効管理。
`register_ocr_provider` フックによる OCR プロバイダ登録に対応。

### `pagefolio/app.py`

`PDFEditorApp` メインクラス。7つの Mixin を統合し、`__init__`・キーバインド・ユーティリティメソッドを持つ。

### Mixin モジュール群

| モジュール | Mixin クラス | 責務 |
|-----------|-------------|------|
| `ui_builder.py` | `UIBuilderMixin` | スタイル定義・レイアウト構築 |
| `file_ops.py` | `FileOpsMixin` | ファイル操作・Undo/Redo・パスワード付与/解除 |
| `page_ops.py` | `PageOpsMixin` | ページ回転・削除・トリミング・挿入・結合・分割 |
| `viewer.py` | `ViewerMixin` | プレビュー・ズーム・サムネイル・ポップアップ |
| `dnd.py` | `DnDMixin` | サムネイル D&D 並び替え |
| `ocr.py` | `OCRMixin` | OCR 起動・プロバイダ生成（`build_provider`）・ボタン状態管理 |
| `print_ops.py` | `PrintOpsMixin` | 印刷（既定 PDF ハンドラへ送信・`write_print_tempfile`） |

### OCR モジュール群

| モジュール | 主要クラス / 関数 | 責務 |
|-----------|------------------|------|
| `ocr.py` | `OCRMixin`, `build_provider`, `run_parallel`, `clamp_retry_after`, `interruptible_sleep`, `PROVIDER_OCR_PROMPTS`, `resolve_ocr_prompt` | プロバイダ生成・並列 OCR 実行・リトライ/キャンセル制御・プロバイダ別プロンプト解決（custom>provider別>汎用） |
| `ocr_providers.py` | `OCRProvider`(ABC), `LMStudioProvider`, `ClaudeProvider`, `GeminiProvider`, `TesseractProvider` | 各バックエンドへの OCR リクエスト実装（`ocr_image_ex` で stop_reason/finishReason 途切れ検出） |
| `md_render.py` | `parse_markdown`, `_split_inline` | OCR 結果 Markdown を (行種別, インライン span) へ変換する純関数（Tk/fitz 非依存・`ocr_dialog.py` の整形描画が消費） |
| `ocr_dialog.py` | `OCRDialog` | 複数ページ OCR の実行 UI・進捗・結果表示/エクスポート（`_run_gen` 世代ガード）・`preset=="markdown"` 整形描画（`_insert_markdown`）・コピー/保存は raw 維持 |

### ページネーション

`pagination.py` はサムネイル一覧の窓表示（既定 20・範囲 10〜100）の純ロジック層。窓計算・件数クランプ・ローカル位置 ↔ 全ページインデックス変換（`to_global` 等）を Tk/fitz 非依存の純関数群として集約する。`selected_pages` は全ページインデックスのまま保持し、描画・D&D・選択照合の側で窓変換する（散在による窓またぎバグを構造的に防止）。

### `pagefolio/dialogs/`（パッケージ）

`about.py`（`AboutDialog`）・`settings.py`（`SettingsDialog`）・`plugin.py`（`PluginDialog`）・
`merge.py`（`MergeOrderDialog` / `MergeResizeDialog`）・`llm_config.py`（`LLMConfigDialog`）に分割。
`__init__.py` が re-export するため `from pagefolio.dialogs import SettingsDialog` 等の既存 import は維持される。

---

## カラーテーマ

テーマは `pagefolio/themes.py` の `THEMES` 辞書で定義。実行時は `C` 辞書経由で参照。

```python
THEMES = {
    "dark": {
        "BG_DARK": "#1a1a2e",  "BG_PANEL": "#16213e",  "BG_CARD": "#0f3460",
        "ACCENT": "#e94560",   "TEXT_MAIN": "#eaeaea",  "TEXT_SUB": "#a0a0b0",
        "SUCCESS": "#4ecca3",  "WARNING": "#ffd460",    "PREVIEW_BG": "#111122",
        ...
    },
    "light": {
        "BG_DARK": "#f0f0f5",  "BG_PANEL": "#e0e0ea",  "BG_CARD": "#d0d0dd",
        "ACCENT": "#d63050",   "TEXT_MAIN": "#1a1a2e",  "TEXT_SUB": "#555566",
        "SUCCESS": "#2a9d6a",  "WARNING": "#b8860b",    "PREVIEW_BG": "#c8c8d0",
        ...
    },
}
C = dict(THEMES["dark"])  # 実行時に _apply_theme() で更新
```

---

## コマンド

| コマンド | 用途 |
|---------|------|
| `pytest` | テスト実行 |
| `ruff check . && ruff format .` | リント・フォーマット |

---

## コーディング規約

### 構造・命名

- **パッケージ構成を維持する**: `pagefolio/` パッケージにモジュール分割済み。Mixin パターンで PDFEditorApp を構成。
- **メソッド名**: `_` プレフィックスで内部メソッドを示す。
- **テーマ色の参照**: グローバル定数ではなく `C["BG_DARK"]` 等のテーマ辞書を使う。
- **フォントサイズ**: ハードコードせず `self._font(delta)` ヘルパーを使う（ベース + delta）。

### ボタンスタイル

- 通常操作 → `"TButton"`
- 主要アクション → `"Accent.TButton"`
- 破壊的操作（削除・終了） → `"Danger.TButton"`
- トリミングモード ON → `"CropOn.TButton"`

### 状態管理（`self.*` 主要属性）

| 属性 | 説明 |
|------|------|
| `self.doc` | 現在開いている `fitz.Document`（未開時は `None`） |
| `self.current_page` | 0 始まりのページインデックス |
| `self.selected_pages` | `set` で複数選択を管理 |
| `self._undo_stack` / `self._redo_stack` | Undo/Redo スタック |
| `self.thumb_cache` | サムネイルキャッシュ辞書 |
| `self._doc_buttons` | ファイル依存ボタンのリスト（doc 未開時に disabled） |
| `self._pending_click` | ダブルクリック競合防止用の遅延クリックID |
| `self.settings` | 設定辞書（テーマ、フォントサイズ、ウィンドウジオメトリ、モード） |
| `self.font_size` | 現在のベースフォントサイズ（8〜16） |
| `self.edit_mode` | 編集モード True / 閲覧モード False（設定に永続化） |
| `self._paned` | メインの `tk.PanedWindow`（横分割）参照 |
| `self._right_panel` | 右ツールパネルの `tk.Frame` |
| `self._mode_btn` | モード切替 `ttk.Button` 参照 |

### 操作後の作法

- **再描画**: ページ変更後は必ず `self._refresh_all()` を呼ぶ。
- **ステータス表示**: 操作完了後は `self._set_status(msg)` でヘッダーに表示。
- **ファイル操作前の確認**: `self._check_doc()` で `self.doc` の存在を確認する。
- **トリミング安全処理**: CropBox は必ず MediaBox 内にクランプしてから `set_cropbox` を呼ぶ。
- **設定保存**: `pagefolio_settings.json` に JSON で永続化（`_save_settings()`）。

### 作業フロー

- **1タスクずつ完了させてから次のタスクへ進むこと**
- **リント必須**: py ファイルを編集したら必ず `ruff check . && ruff format .` が通ることを確認すること
- **テスト必須**: コミット前に `pytest` を通すこと

### 禁止事項

- `pyproject.toml` の編集
- 裸の `except:` 句（必ず `except Exception as e:` の形で）
- `# type: ignore` の無断使用

---

## 言語ルール

タスクリスト（TodoWrite）の内容を含め、**すべての返答を日本語で行うこと**。

以下の出力も**原則日本語**で記述する。

| 対象 | 例 |
|------|-----|
| コミットメッセージ | `ページ回転機能のバグを修正` |
| ブランチ説明・PR タイトル / 本文 | `サムネイルD&Dの末尾ドロップ対応` |
| GitHub Issue のタイトル / コメント | `トリミング後にプレビューが更新されない` |
| コードレビューのフィードバック | `この条件分岐は不要では？` |
| `開発履歴.md` の記載 | 既存ルール通り |
| セッション終了時の申し送り | 後述のフォーマット |
| ユーザーへの応答・説明 | 会話はすべて日本語 |

**例外（英語のまま）**:

- ソースコード中の変数名・関数名・クラス名
- ライブラリ名・コマンド名（`pymupdf`, `git push` など）
- エラーメッセージの引用（原文ママ）

---

## 既知の制限・注意事項

- トリミングは **選択中のページ全体** に一括適用（複数選択時は相対座標変換で各ページに適用）
- D&D による複数ページ一括移動は **選択ページをまとめて移動**（単一ページ D&D も引き続き動作）
- パスワード保護 PDF は開く際にパスワード入力を求める（`_authenticate_doc`）。パスワードの付与（AES-256）/解除は「🔒 パスワード」セクションから別名保存で行う
- 印刷は OS の既定 PDF ハンドラへ送る方式（Windows: `os.startfile(path, "print")`）。Windows 以外は未対応で情報通知に留める
- `set_cropbox` によるトリミングはメタデータ上の cropbox 変更であり、PDF の物理的なページサイズは変わらない
- サムネイルは `fitz.Matrix(0.22, 0.22)` のスケールで生成（変更時はパフォーマンスに注意）
- プレビューは `self.zoom * 1.5` のスケールで生成
- 右ペインはスクロール可能な Canvas 構成（`_build_tools_scrollable` で実装）
- クラウド OCR（Claude / Gemini）はページ画像を base64 で外部 API へ https 送信する（Tesseract / LM Studio はローカル完結）
- API キーは設定ファイルに保存されず、環境変数またはセッションメモリ（`app._session_api_keys`）のみ
- OCR のリトライ待機は `Retry-After` を 60 秒上限にクランプし、0.5 秒刻みでキャンセルを確認する（`clamp_retry_after` / `interruptible_sleep`）
- `fitz.Document` はスレッド間で共有しない（OCR はメインスレッドでレンダリングした base64 のみワーカーへ渡す）

---

## 今後の追加予定機能

- [x] ページの回転状態をプレビューに即時反映（v1.6.0 / V16-QUAL-01）
- [x] PDF のパスワード対応（付与/解除・AES-256）（v1.6.1）
- [x] 印刷機能（Ctrl+P・既定 PDF ハンドラ送信）（v1.6.1）

> 実装済みの機能リストは [開発履歴.md](開発履歴.md) を参照。

---

## 変更時のチェックリスト

- [ ] `ruff check . && ruff format .` でリント・フォーマット確認
- [ ] `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
- [ ] `pytest` でテスト確認
- [ ] `開発履歴.md` に変更内容を追記
- [ ] バージョン番号を更新（`pagefolio/constants.py` の `APP_VERSION`、開発履歴.md、README.md のバッジ）

---

## セッション終了時のルール

作業が完了したら、依頼されなくても必ず日本語で以下の形式で申し送りを出力すること。
この出力は claude.ai に貼り付けて Notion を更新するために使用する。

### 変更内容サマリー

**修正対象**: （バグ番号・機能名など）

| ファイル | 変更内容 |
|----------|----------|
| ファイルパス | 変更内容の概要 |

### 修正内容の詳細

（バグ修正なら症状・原因・対応内容を記載）

### 次セッションへの申し送り

#### 未実施（動作確認・テスト）

- 確認が必要な事項を箇条書き

#### 注意点・潜在リスク

- 動作上の注意点や将来の改善候補

#### 実行推奨コマンド（必要な場合）

```
pytest tests/ など
```

<!-- GSD:project-start source:PROJECT.md -->

## Project

**PageFolio — コード最適化プロジェクト**

PageFolio の既存コードベースに対する最適化プロジェクト。
バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。

**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Runtime & Language

- Python 3.8+ — アプリケーション全体（型ヒントは 3.8 互換）
- 仮想環境: `venv/` (Windows 向け)
- pip（`requirements.txt` で依存管理）
- Lockfile: `requirements.txt`（バージョン固定）

## Core Frameworks & Libraries

| Name | Version | Purpose | Key usage patterns |
|------|---------|---------|-------------------|
| Tkinter | 標準ライブラリ | GUI フレームワーク | `tk.Tk`, `ttk.Button`, `tk.Canvas` でウィジェット構築 |
| PyMuPDF (fitz) | 1.27.2.2 | PDF 読み書き・レンダリング | `fitz.open()`, `page.get_pixmap()`, `doc.save()` |
| Pillow (PIL) | 12.2.0 | 画像変換・表示 | `Image`, `ImageTk.PhotoImage` でプレビュー描画 |
| tkinterdnd2 | 0.4.3 | ファイル D&D サポート | `TkinterDnD.Tk`, `DND_FILES`, `drop_target_register()` |

## Build & Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| Ruff | 0.15.7 | リント・フォーマット（E/F/W/I/S/B ルール） |
| PyInstaller | 6.19.0 | Windows 実行ファイルのビルド（`.exe` 生成） |

- `line-length = 88`
- `select = ["E", "F", "W", "I", "S", "B"]`
- `tests/**/*.py` で `S101` (assert) を除外

## Development Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 9.0.2 | テストランナー |
| pytest-cov | 7.1.0 | カバレッジ計測 |

## Standard Library Usage

- `tkinter` / `tkinter.ttk` — GUI 全般（`pagefolio/ui_builder.py`, `pagefolio/dialogs/` など）
- `tkinter.filedialog`, `messagebox`, `simpledialog` — ダイアログ操作
- `json` — 設定ファイル読み書き（`pagefolio/settings.py`）
- `os` — パス操作・ファイル検索
- `logging` — ログ出力（全モジュール）
- `threading` — バックグラウンド処理（`pagefolio/ocr_dialog.py`）
- `concurrent.futures.ThreadPoolExecutor` — OCR 並列処理（`pagefolio/ocr.py`）
- `urllib.request` — HTTP 通信（LM Studio API 呼び出し）（`pagefolio/ocr_providers.py`）
- `base64` — OCR 画像エンコード（`pagefolio/ocr.py`）
- `json`, `socket` — OCR リクエスト組み立て（`pagefolio/ocr_providers.py`）
- `importlib`, `importlib.util` — プラグイン動的読み込み（`pagefolio/plugins.py`）

## Infrastructure & Platform

- `pagefolio.py` — `python pagefolio.py` 起動
- `pagefolio/__main__.py` — `python -m pagefolio` 起動
- PyInstaller で onedir 形式（ディレクトリ配布）としてビルド
- アイコン: `pagefolio.ico`
- `pyproject.toml` で `pythonpath = ["src"]` を指定（pytest 用）

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Conventions

- Modules use `snake_case.py` (e.g., `file_ops.py`, `ui_builder.py`, `page_ops.py`)
- Test files use `test_<module>.py` prefix (e.g., `test_pdf_ops.py`, `test_plugins.py`)
- PascalCase (e.g., `PDFEditorApp`, `UIBuilderMixin`, `FileOpsMixin`, `AboutDialog`)
- Mixin classes end with `Mixin` suffix (e.g., `UIBuilderMixin`, `ViewerMixin`, `DnDMixin`)
- Dialog classes end with `Dialog` suffix (e.g., `AboutDialog`, `SettingsDialog`)
- Test classes use `Test<FeatureName>` prefix (e.g., `TestLoadSettings`, `TestPdfOpen`)
- `_` prefix for internal/private methods (e.g., `_build_styles`, `_refresh_all`, `_set_status`)
- Public API methods use plain names (e.g., `discover_plugins`, `load_plugin`, `fire_event`)
- Tkinter event handlers conventionally begin with `_on_` or `_do_` (e.g., `_do_merge`, `_do_insert`)
- `snake_case` throughout (e.g., `current_page`, `selected_pages`, `thumb_cache`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `APP_VERSION`, `THEMES`, `LANG`, `SETTINGS_FILE`)
- Theme colors accessed via `C["KEY"]` dict, never hardcoded hex strings

## Code Style

- `tests/**/*.py` exempt from S101 (assert allowed in tests)
- No bare `except:` — always `except Exception as e:`
- No `# type: ignore` without prior approval

## Module Organization

- Takes `parent`, font function, and `lang` parameter
- Sets `self.grab_set()` for modal behavior
- Centers itself relative to parent window

## Error Handling Patterns

- Bare `except:` without exception type
- Silencing exceptions without at minimum a `logger` call

## UI Patterns

- `"TButton"` — standard operation
- `"Accent.TButton"` — primary/important action
- `"Danger.TButton"` — destructive action (delete, quit)
- `"CropOn.TButton"` — trim mode active state

## Logging & Status

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Design Patterns

```python

```

## Core Components

| Component | Responsibility | File |
|-----------|----------------|------|
| `PDFEditorApp` | Root app class; wires all Mixins, holds all state, sets up keybindings | `pagefolio/app.py` |
| `UIBuilderMixin` | Builds ttk styles, PanedWindow layout, toolbar, thumbnail panel, preview canvas, right tool panel | `pagefolio/ui_builder.py` |
| `FileOpsMixin` | Open/Save/SaveAs/Undo/Redo; delta-based undo stack (operation state dicts) | `pagefolio/file_ops.py` |
| `PageOpsMixin` | Rotate, delete, crop (CropBox), insert, merge, split | `pagefolio/page_ops.py` |
| `ViewerMixin` | Render preview (fitz→PIL→Tk), thumbnails with cache, zoom, popup preview | `pagefolio/viewer.py` |
| `DnDMixin` | Thumbnail drag-and-drop reorder (single or multi-page) | `pagefolio/dnd.py` |
| `OCRMixin` | LM Studio Vision API integration; concurrent page OCR | `pagefolio/ocr.py` |
| `PluginManager` | Discover/load/unload/enable/disable plugins; fire lifecycle events | `pagefolio/plugins.py` |
| `PDFEditorPlugin` | Abstract base for third-party plugins | `pagefolio/plugins.py` |
| Constants & Theme | `THEMES`, `C` (runtime dict), `APP_VERSION`, `LANG`, `SUPPORTED_EXTENSIONS` | `pagefolio/constants.py` |
| Settings utils | Read/write `pagefolio_settings.json`, theme application, font helpers | `pagefolio/settings.py` |
| Dialogs | `AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog`, `MergeResizeDialog` | `pagefolio/dialogs/` |
| OCR Dialog | `OCRDialog` — multi-page OCR results viewer/exporter | `pagefolio/ocr_dialog.py` |
| File Drop | tkinterdnd2 integration for drag-and-drop file open | `pagefolio/file_drop.py` |

## Data Flow

### File Open

### Page Render (Preview)

### Thumbnail Generation

### Page Operation (example: rotate)

### OCR Flow

## State Management

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.doc` | `fitz.Document \| None` | Open PDF document |
| `self.filepath` | `str \| None` | Path of the open file |
| `self.current_page` | `int` | 0-based current page index |
| `self.selected_pages` | `set[int]` | Multi-selection set |
| `self._undo_stack` | `deque[dict]` | 操作デルタ state dict（max 20） |
| `self._redo_stack` | `deque[dict]` | 逆操作デルタ state dict（max 20） |
| `self.thumb_cache` | `dict[int, ImageTk.PhotoImage]` | Thumbnail image cache |
| `self._doc_buttons` | `list[ttk.Button]` | Buttons disabled when no doc |
| `self.crop_mode` | `bool` | Whether crop selection is active |
| `self.crop_rect` | `tuple \| None` | Current crop selection rect |
| `self.edit_mode` | `bool` | Edit vs View mode |
| `self.settings` | `dict` | Persisted settings from JSON |
| `self.font_size` | `int` | Base font size (8–16) |
| `self.plugin_manager` | `PluginManager` | Plugin lifecycle manager |
| `self._preview_gen` | `int` | Generation counter for preview thread |
| `self._thumb_gen` | `int` | Generation counter for thumbnail thread |

## Extension Points

### Plugin System

| Hook | Signature | Trigger |
|------|-----------|---------|
| `on_load` | `(app)` | Plugin enabled/loaded |
| `on_unload` | `(app)` | Plugin disabled/unloaded |
| `on_file_open` | `(app, path)` | File opened |
| `on_file_save` | `(app, path)` | File saved |
| `on_page_rotate` | `(app, pages, degrees)` | Page rotated |
| `on_page_delete` | `(app, pages)` | Page deleted |
| `on_page_crop` | `(app, page_index)` | Page cropped |
| `on_page_change` | `(app, page_index)` | Current page changed |
| `on_insert` | `(app, paths, insert_at)` | Pages inserted |
| `on_merge` | `(app, paths)` | PDFs merged |
| `build_ui` | `(app, parent)` | Build custom UI in given `tk.Frame` |

### Theme Extension

## Architectural Constraints

- **Threading:** UI runs on the Tkinter main thread. Preview and thumbnail renders are processed on the main thread via `root.after()` chained calls; generation counters (`_preview_gen`, `_thumb_gen`) prevent stale results from overwriting newer ones. OCR uses `ThreadPoolExecutor`.
- **Global state:** `C` (theme dict) and `_current_font_size` in `pagefolio/settings.py` are module-level mutable singletons updated at runtime.
- **Undo limit:** Hard-coded to `MAX_UNDO = 20` in `pagefolio/app.py`. 各エントリは操作固有のデルタ dict（rotate: 回転値リスト、crop: cropbox タプル、delete: ページ単位 bytes 等）であり、full PDF シリアライズではない。
- **CropBox safety:** All crop operations must clamp the `CropBox` inside the page's `MediaBox` before calling `set_cropbox()` (`pagefolio/page_ops.py`).

## Anti-Patterns

### Accessing theme colors via raw strings instead of `C` dict

### Hardcoding font sizes

## Error Handling

- File operations use `messagebox.showerror()` for user-visible failures
- Plugin callbacks are individually wrapped so one plugin failure cannot crash others
- Preview/thumbnail `root.after()` callbacks silently discard results when generation counter has advanced

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
