# CLAUDE.md — PageFolio AI 開発指示書

このファイルは Claude (AI) がこのプロジェクトを編集・拡張する際に参照する指示書です。

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
| 現在バージョン | v0.9.6 |

---

## 開発について

本プロジェクトは **Claude Code**（Anthropic）を活用して開発されています。
`CLAUDE.md` による構造化された AI 開発指示書の運用、`開発履歴.md` による変更管理など、
AI との協調開発のユースケースとして公開しています。

---

## ファイル構成

```
PageFolio/
├── pagefolio.py               # エントリーポイント（python pagefolio.py で起動）
├── pagefolio/                 # メインパッケージ
│   ├── __init__.py            # 公開API（後方互換 import 用）
│   ├── __main__.py            # python -m pagefolio エントリーポイント
│   ├── constants.py           # テーマ・バージョン・言語辞書（THEMES, C, LANG）
│   ├── settings.py            # 設定ユーティリティ関数
│   ├── plugins.py             # プラグインシステム（PDFEditorPlugin, PluginManager）
│   ├── app.py                 # PDFEditorApp 本体（Mixin 統合 + 状態管理）
│   ├── ui_builder.py          # UI構築 Mixin（スタイル・レイアウト）
│   ├── file_ops.py            # ファイル操作 Mixin（open/save/undo/redo）
│   ├── page_ops.py            # ページ操作 Mixin（回転/削除/トリミング/挿入/結合/分割）
│   ├── viewer.py              # 表示 Mixin（プレビュー/ズーム/サムネイル/ポップアップ）
│   ├── dnd.py                 # D&D Mixin（サムネイルのドラッグ並び替え）
│   ├── dialogs.py             # ダイアログ群（About/Settings/Plugin/MergeOrder）
│   └── file_drop.py           # ファイル D&D（tkinterdnd2 連携）
├── pagefolio.ico              # アプリアイコン
├── README.md                  # エンドユーザー向け使用概要
├── CLAUDE.md                  # 本ファイル（AI 向け開発指示書）
├── 開発履歴.md                # 機能追加・変更の履歴
├── LICENSE                    # MITライセンス
├── pyproject.toml             # Ruff・pytest 設定
├── plugins/                   # プラグインディレクトリ
│   └── page_info.py           # サンプルプラグイン（ページ情報表示）
├── tests/                     # テストスイート（pytest）
│   ├── conftest.py            # テスト用共通フィクスチャ
│   ├── test_utils.py          # ユーティリティ関数テスト（35件）
│   ├── test_pdf_ops.py        # PDF 操作テスト（26件）
│   └── test_plugins.py        # PluginManager テスト（17件）
└── docs/                      # スクリーンショット画像
（実行時に自動生成）
└── pagefolio_settings.json    # ユーザー設定（テーマ・フォントサイズ）
```

---

## モジュール構成

### `pagefolio/constants.py`
テーマカラー（`THEMES`）、実行時テーマ辞書（`C`）、バージョン（`APP_VERSION`）、言語辞書（`LANG`）を定義。

### `pagefolio/settings.py`
設定ファイルの読み書き・テーマ解決・フォント生成のユーティリティ関数群。

### `pagefolio/plugins.py`
`PDFEditorPlugin` 基底クラスと `PluginManager` クラス。プラグインの検出・読込・有効/無効管理。

### `pagefolio/app.py`
`PDFEditorApp` メインクラス。5つの Mixin を統合し、`__init__`・キーバインド・ユーティリティメソッドを持つ。

### Mixin モジュール群
| モジュール | Mixin クラス | 責務 |
|-----------|-------------|------|
| `ui_builder.py` | `UIBuilderMixin` | スタイル定義・レイアウト構築 |
| `file_ops.py` | `FileOpsMixin` | ファイル操作・Undo/Redo |
| `page_ops.py` | `PageOpsMixin` | ページ回転・削除・トリミング・挿入・結合・分割 |
| `viewer.py` | `ViewerMixin` | プレビュー・ズーム・サムネイル・ポップアップ |
| `dnd.py` | `DnDMixin` | サムネイル D&D 並び替え |

### `pagefolio/dialogs.py`
`AboutDialog`・`SettingsDialog`・`PluginDialog`・`MergeOrderDialog` の4ダイアログクラス。

---

## カラーテーマ

テーマは `THEMES` 辞書で定義。実行時は `C` 辞書経由で参照。

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

- テスト実行: `pytest`
- リント: `ruff check . && ruff format .`

---

## コーディング規約

- **パッケージ構成を維持する**: `pagefolio/` パッケージにモジュール分割済み。Mixin パターンで PDFEditorApp を構成。
- **メソッド名**: `_` プレフィックスで内部メソッドを示す
- **ボタンスタイル**:
  - 通常操作 → `"TButton"`
  - 主要アクション → `"Accent.TButton"`
  - 破壊的操作（削除・終了） → `"Danger.TButton"`
  - トリミングモード ON → `"CropOn.TButton"`
- **状態管理**:
  - `self.doc` — 現在開いている `fitz.Document`（未開時は `None`）
  - `self.current_page` — 0 始まりのページインデックス
  - `self.selected_pages` — `set` で複数選択を管理
  - `self._undo_stack` / `self._redo_stack` — Undo/Redo スタック
  - `self.thumb_cache` — サムネイルキャッシュ辞書
  - `self._doc_buttons` — ファイル依存ボタンのリスト（doc未開時に disabled）
  - `self._pending_click` — ダブルクリック競合防止用の遅延クリックID
  - `self.settings` — 設定辞書（テーマ、フォントサイズ）
  - `self.font_size` — 現在のベースフォントサイズ（8〜16）
- **再描画**: ページ変更後は必ず `self._refresh_all()` を呼ぶ
- **ステータス表示**: 操作完了後は `self._set_status(msg)` でヘッダーに表示
- **ファイル操作前の確認**: `self._check_doc()` で `self.doc` の存在を確認する
- **トリミング安全処理**: CropBox は必ず MediaBox 内にクランプしてから `set_cropbox` を呼ぶ
- **テーマ色の参照**: グローバル定数ではなく `C["BG_DARK"]` 等のテーマ辞書を使う
- **フォントサイズ**: ハードコードせず `self._font(delta)` ヘルパーを使う（ベース + delta）
- **設定保存**: `pagefolio_settings.json` に JSON で永続化（`_save_settings()`）
- **作業フロー**: 1タスクずつ完了させてから次のタスクへ進むこと
- **リント必須**: py ファイルを編集したら必ず `ruff check . && ruff format .` が通ることを確認すること
- **テスト必須**: コミット前に `pytest` を通すこと

### 禁止事項

- `pyproject.toml` / `ruff.toml` の編集
- 裸の `except:` 句（必ず `except Exception as e:` の形で）
- `# type: ignore` の無断使用

---

## Language

タスクリスト（TodoWrite）の内容を含め、すべての返答を日本語で行うこと。

---

## 言語ルール

本プロジェクトでは、以下の出力を**原則日本語**で記述すること。

| 対象 | 例 |
|------|-----|
| コミットメッセージ | `ページ回転機能のバグを修正` |
| ブランチ説明・PR タイトル / 本文 | `サムネイルD&Dの末尾ドロップ対応` |
| GitHub Issue のタイトル / コメント | `トリミング後にプレビューが更新されない` |
| コードレビューのフィードバック | `この条件分岐は不要では？` |
| `開発履歴.md` の記載 | 既存ルール通り |
| セッション終了時の申し送り | 既存ルール通り |
| ユーザーへの応答・説明 | 会話はすべて日本語 |

**例外（英語のまま）**:
- ソースコード中の変数名・関数名・クラス名
- ライブラリ名・コマンド名（`pymupdf`, `git push` など）
- エラーメッセージの引用（原文ママ）

---

## 既知の制限・注意事項

- トリミングは **現在表示中のページのみ** 対象（複数ページ一括トリミング未対応）
- D&D によるページ移動は **1ページずつ**（複数選択ページの一括移動未対応）
- 暗号化・パスワード保護 PDF は開けない場合がある
- `set_cropbox` によるトリミングはメタデータ上の cropbox 変更であり、PDF の物理的なページサイズは変わらない
- サムネイルは `fitz.Matrix(0.22, 0.22)` のスケールで生成（変更時はパフォーマンスに注意）
- プレビューは `self.zoom * 1.5` のスケールで生成
- 右ペインはスクロール可能な Canvas 構成（`_build_tools_scrollable` で実装）

---

## 今後の追加予定機能（候補）

- [ ] 複数ページの一括トリミング
- [ ] 複数ページの D&D 一括移動
- [ ] ページの回転状態をプレビューに即時反映
- [ ] PDF のパスワード解除対応
- [ ] 印刷機能
- [x] ページ範囲指定での分割保存
- [x] PyInstaller による exe 化・配布対応

---

## 変更時のチェックリスト

- [ ] `ruff check . && ruff format .` でリント・フォーマット確認
- [ ] `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
- [ ] `pytest` でテスト確認
- [ ] `開発履歴.md` に変更内容を追記
- [ ] バージョン番号を更新（本ファイル・開発履歴.md）

---

## セッション終了時のルール

作業が完了したら、依頼されなくても必ず日本語で以下の形式で申し送りを出力すること。
この出力はclaude.aiに貼り付けてNotionを更新するために使用する。

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
