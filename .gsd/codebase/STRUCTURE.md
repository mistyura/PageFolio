---
last_mapped_commit: fb41c422035fa9d4fac753920909da56e068555c
---

# PageFolio — ディレクトリ構成 (Structure)

## ディレクトリ構成全体図

```text
PageFolio/
├── pagefolio.py               # エントリーポイント（python pagefolio.py で起動）
├── pagefolio/                 # アプリケーションパッケージ
│   ├── __init__.py            # 公開API（後方互換 import 用）
│   ├── __main__.py            # python -m pagefolio エントリーポイント
│   ├── app.py                 # PDFEditorApp（メインクラス。Mixinを統合）
│   ├── constants.py           # バージョン情報、外部ファイル名などの定数
│   ├── themes.py              # カラーテーマ辞書（THEMES, C）
│   ├── lang.py                # 日英言語辞書（LANG: ja / en）
│   ├── settings.py            # 設定ファイルの読み書き・フォント・プロンプト外部ファイル読み込み
│   ├── plugins.py             # プラグインのインターフェースと管理（PluginManager）
│   │
│   ├── ui_builder.py          # Mixin: UIスタイル定義・レイアウト構築
│   ├── file_ops.py            # Mixin: ファイルオープン・保存・パスワード・Undo/Redo
│   ├── page_ops.py            # Mixin: ページ回転・削除・トリミング・挿入・結合・分割
│   ├── redact_ops.py          # Mixin: 黒塗り（Redaction）・モザイク・page_edit undo
│   ├── viewer.py              # Mixin: プレビュー・サムネイル・拡大ポップアップ
│   ├── dnd.py                 # Mixin: サムネイル D&D 並び替え
│   ├── ocr.py                 # Mixin: OCR 起動・プロバイダ生成・並列 OCR
│   ├── print_ops.py           # Mixin: 印刷（一時ファイル生成・OS分岐）
│   │
│   ├── undo_store.py          # 純ロジック: Undo Blob 退避ストア（MemBlob/FileBlob/UndoBlobStore）
│   ├── pagination.py          # 純ロジック: サムネイル窓計算・ローカル ↔ グローバル位置変換
│   ├── ocr_pipeline.py        # 純ロジック: OCR 実行状態管理・キュー操作・1アイテム消費
│   ├── ocr_providers.py       # 各 OCR 接続プロバイダ（LMStudio, Claude, Gemini 等）
│   ├── md_render.py           # 純ロジック: OCR 結果 Markdown のパース
│   ├── ocr_dialog.py          # UI: 複数ページ OCR の実行・進捗結果・要約表示ダイアログ
│   ├── file_drop.py           # ファイルのドラッグ＆ドロップ（tkinterdnd2 連携）
│   │
│   └── dialogs/               # 個別ダイアログパッケージ
│       ├── __init__.py        # ダイアログの re-export
│       ├── about.py           # AboutDialog (アプリ情報)
│       ├── settings.py        # SettingsDialog (テーマ・フォント設定)
│       ├── plugin.py          # PluginDialog (プラグイン管理)
│       ├── merge.py           # MergeOrderDialog / MergeResizeDialog (PDF結合/リサイズ)
│       ├── llm_config.py      # LLMConfigDialog (プロバイダ・モデル設定、非同期API)
│       ├── shortcuts.py       # ShortcutsDialog (キーバインド設定)
│       ├── export_images.py   # ExportImagesDialog (画像書き出し)
│       └── password.py        # SetPasswordDialog (パスワード設定)
│
├── plugins/                   # サードパーティ製プラグインディレクトリ
│   └── page_info.py           # サンプルプラグイン（ページ情報表示）
├── tests/                     # pytest テストスイート
│   ├── conftest.py            # テスト共通フィクスチャ
│   └── test_*.py              # 各モジュールのテストコード
│
├── docs/                      # マニュアルや画像などのドキュメント
├── PageFolio.spec             # PyInstaller ビルド定義（onedir 形式）
├── pyproject.toml             # Ruff および pytest の設定ファイル
└── requirements.txt           # 依存パッケージリスト
```

---

## 重要なエントリーポイント (Entry Points)

### 1. `pagefolio.py` (開発時・通常起動用)
プロジェクトルートに配置され、以下のコードでアプリケーションを初期化・起動します。
```python
from pagefolio.__main__ import main
if __name__ == "__main__":
    main()
```

### 2. `pagefolio/__main__.py` (パッケージ起動用)
`python -m pagefolio` コマンドで起動される際のエントリーポイントです。
Tkinter の `TkinterDnD.Tk()` をルートウィンドウとして作成し、`PDFEditorApp` インスタンスを生成して `mainloop()` を開始します。

---

## テストの配置 (Where Tests Live)

- すべてのテストコードは `tests/` ディレクトリ配下に `test_<module_name>.py` という命名で格納されています。
- テストコードの中には、機能別のユニットテストだけでなく、`test_undo_stress.py` (大容量 PDF を用いた Undo/Redo のストレス・リークテスト) や、`test_source_keyguard.py` (ソースコード中に秘密鍵が漏えいしていないかを検証するテスト) などの重要な回帰・防御テストが含まれています。
