<!-- generated-by: gsd-doc-writer -->
# テストガイド

## テストフレームワークとセットアップ

PageFolio は **pytest** を使用してテストを実行します。

| ツール | バージョン | 用途 |
|--------|-----------|------|
| pytest | 9.0.2 | テストランナー |
| pytest-cov | 7.1.0 | カバレッジ計測 |

テスト実行前に依存パッケージをインストールしてください。

```bash
pip install -r requirements.txt
```

pytest の設定は `pyproject.toml` に記述されています。

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

テストは GUI（Tkinter）のウィジェットを実際には生成せず、ロジック層のみをヘッドレスで検証するため、
ディスプレイのない CI 環境やリモート開発環境でもそのまま実行できます。

## テストの実行

### 全テストの実行

```bash
pytest
```

現在、`tests/` 配下には 18 個のテストファイルがあり、合計 707 件のテストが収集されます
（`pytest --collect-only -q` で確認可能）。

### 詳細出力付き

```bash
pytest -v
```

### カバレッジ付き実行

```bash
pytest --cov=pagefolio --cov-report=term-missing
```

### 特定ファイルのテスト

```bash
pytest tests/test_pdf_ops.py
```

### 特定クラス・メソッドのテスト

```bash
pytest tests/test_pdf_ops.py::TestPageRotate
pytest tests/test_pdf_ops.py::TestPageRotate::test_rotate_90
```

## テストファイル一覧

| ファイル | 対象モジュール | 内容 |
|----------|--------------|------|
| `tests/test_imports.py` | `pagefolio/__init__.py`, `pagefolio/constants.py`, `pagefolio/dialogs/` 他 | パッケージ import・後方互換 import パスの回帰テスト |
| `tests/test_utils.py` | `pagefolio/settings.py`, `pagefolio/page_ops.py` | 設定読み書き・テーマ解決・フォント生成・ページ範囲パースのユーティリティ |
| `tests/test_pdf_ops.py` | `pagefolio/file_ops.py`, `pagefolio/page_ops.py` | PDF 操作（開く/保存/回転/削除/挿入/結合/分割/トリミング）・Undo/Redo ロジック |
| `tests/test_plugins.py` | `pagefolio/plugins.py` | `PluginManager` の検出・読込・有効/無効・イベント発火・例外分離 |
| `tests/test_viewer.py` | `pagefolio/viewer.py` | プレビューレンダリング・回転反映の純関数テスト |
| `tests/test_settings_keyguard.py` | `pagefolio/settings.py` | API キー非保存ガード（`_SENSITIVE_KEYS`） |
| `tests/test_source_keyguard.py` | `pagefolio/`（ソース全体） | ソースコード中に実 API キーパターンが埋め込まれていないことのスキャン |
| `tests/test_ocr.py` | `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py` | OCR ヘルパー・並列実行・リトライ/バックオフ・サーキットブレーカー・サマリ生成 |
| `tests/test_ocr_providers.py` | `pagefolio/ocr_providers.py` | OCR プロバイダ（`OCRProvider` 基底・LMStudio/Claude/Gemini/Tesseract/Ollama/RunPod 各実装） |
| `tests/test_provider_ui.py` | `pagefolio/dialogs/llm_config.py`, `pagefolio/ocr.py` | LLM 設定ダイアログのロジック層・`resolve_ocr_prompt` / `resolve_summary_prompt` |
| `tests/test_pagination.py` | `pagefolio/pagination.py` | サムネイル窓計算・local⇄global 変換・D&D 換算・境界値の純ロジックテスト |
| `tests/test_md_render.py` | `pagefolio/md_render.py` | `parse_markdown` の行種別/インライン span 分類テスト |
| `tests/test_export_images.py` | `pagefolio/page_ops.py` | ページ→画像変換（範囲パース・スケール計算・出力・対象ページ解決） |
| `tests/test_save_overwrite.py` | `pagefolio/file_ops.py` | 「縮小して保存（上書き）」ヘルパー（`_is_current_file` / `_overwrite_current_file`） |
| `tests/test_password.py` | `pagefolio/file_ops.py` | PDF パスワード付与/解除・暗号化保存ヘルパー |
| `tests/test_print.py` | `pagefolio/print_ops.py` | 印刷一時ファイル生成（`write_print_tempfile`）・OS 分岐（`_send_to_printer`） |
| `tests/test_undo_stress.py` | `pagefolio/file_ops.py`, `pagefolio/undo_store.py` | 大規模 PDF（100 ページ超）での Undo/Redo 連続ストレス・メモリ増分・Blob 不変条件 |
| `tests/test_lang_parity.py` | `pagefolio/lang.py` | ja/en の `LANG` キー一致・プレースホルダ（`{sec}` / `{page}` 等）整合の回帰テスト |

## テストの書き方

### ファイル命名規則

テストファイルは `tests/` ディレクトリに `test_<対象モジュール名>.py` 形式で配置します。

```
tests/
├── conftest.py           # 共通フィクスチャ
├── test_pdf_ops.py       # pagefolio/page_ops.py, pagefolio/file_ops.py 対応
└── test_ocr.py           # pagefolio/ocr.py 対応
```

### テストクラスとメソッドの命名

```python
class TestPageRotate:
    """ページ回転テスト"""

    def test_rotate_90(self, sample_pdf_doc):
        """90° 回転"""
        ...
```

- クラス名: `Test<機能名>` 形式
- メソッド名: `test_<動作の説明>` 形式

### 共通フィクスチャ（`tests/conftest.py`）

テストで頻繁に使われる共通フィクスチャが `conftest.py` に定義されています。

| フィクスチャ | 型 | 説明 |
|-------------|---|------|
| `tmp_settings` | `tuple[Path, Callable]` | 一時ディレクトリに設定ファイルを作成・管理する `(settings_path, write_fn)` |
| `sample_pdf` | `str` | テスト用 3 ページ（A4）PDF のファイルパス |
| `sample_pdf_doc` | `fitz.Document` | テスト用 3 ページ PDF の `fitz.Document`（テスト終了後に自動クローズ） |
| `large_pdf_doc` | `fitz.Document` | ページネーション窓の境界値検証用 47 ページ PDF（自動クローズ） |
| `multi_pdf_files` | `list[str]` | 結合・挿入テスト用の複数 PDF ファイルパス（1, 2, 3 ページ） |

使用例:

```python
def test_open_valid_pdf(self, sample_pdf):
    doc = fitz.open(sample_pdf)
    assert len(doc) == 3
    doc.close()
```

### Tkinter 非依存テストのパターン

GUI コンポーネントはヘッドレス環境でテストできるよう、Tkinter ウィジェットを生成せずにロジック層のみを検証するパターンを採用しています。

```python
# NG: ダイアログをインスタンス化しない
# dialog = SettingsDialog(root, ...)

# OK: クラスシンボルの存在確認のみ
from pagefolio.dialogs import SettingsDialog
assert SettingsDialog is not None
```

Mixin メソッドのテストは `types.SimpleNamespace` や軽量なスタブクラスで必要な属性だけを持つオブジェクトを作り、
Mixin を継承させて呼び出す方法を使います。

```python
import collections
import pagefolio.file_ops as fo

class FakeApp(fo.FileOpsMixin):
    MAX_UNDO = 20

    def __init__(self, doc):
        self.doc = doc
        self.current_page = 0
        self.selected_pages = set()
        self._undo_stack = collections.deque()
        self._redo_stack = collections.deque()
        self._preview_gen = 0
        self._thumb_gen = 0

    def _invalidate_thumb_cache(self, *a, **kw):
        pass

    def _refresh_all(self):
        pass
```

`pagination.py` / `md_render.py` / `undo_store.py` は Tk・fitz に一切依存しない純関数層として設計されているため、
`tests/test_pagination.py` や `tests/test_md_render.py` のように引数だけを渡して直接呼び出す形でテストできます。

## カバレッジ要件

現在、カバレッジしきい値（`fail_under` 等）は `pyproject.toml` や `.coveragerc` に明示的に設定されていません。

カバレッジレポートを生成するには以下を実行してください。

```bash
pytest --cov=pagefolio --cov-report=html
```

HTML レポートは `htmlcov/index.html` に出力されます。

## コードスタイル確認

テスト実行前後に Ruff でリント・フォーマットを確認してください。

```bash
ruff check . && ruff format .
```

`tests/**/*.py` では `pyproject.toml` の `[tool.ruff.lint.per-file-ignores]` により `S101`（assert の使用）が許可されています。

## CI 統合

現在、`.github/workflows/` は存在せず、GitHub Actions などの CI パイプラインは設定されていません。
プルリクエスト作成前にローカルで以下を実行して確認してください。

```bash
ruff check . && ruff format .   # リント・フォーマット
pytest                          # テスト実行
```

コミット前のチェックリスト（`CLAUDE.md` 準拠）:

1. `ruff check . && ruff format .` でリント・フォーマット確認
2. `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
3. `pytest` でテスト確認
