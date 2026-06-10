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

## テストの実行

### 全テストの実行

```bash
pytest
```

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
| `tests/test_imports.py` | `pagefolio/__init__.py` 他 | パッケージ import・後方互換テスト |
| `tests/test_utils.py` | `pagefolio/settings.py` | 設定読み書き・テーマ解決・フォント生成ユーティリティ |
| `tests/test_pdf_ops.py` | `pagefolio/file_ops.py`, `pagefolio/page_ops.py` | PDF 操作・Undo/Redo ロジック |
| `tests/test_plugins.py` | `pagefolio/plugins.py` | `PluginManager` の検出・読込・有効/無効・イベント発火 |
| `tests/test_viewer.py` | `pagefolio/viewer.py` | プレビューレンダリング |
| `tests/test_settings_keyguard.py` | `pagefolio/settings.py` | API キー非保存ガード |
| `tests/test_ocr.py` | `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py` | OCR ヘルパー・並列実行・リトライ・バックオフ |
| `tests/test_ocr_providers.py` | `pagefolio/ocr_providers.py` | OCR プロバイダ（`OCRProvider` 基底・各実装） |
| `tests/test_provider_ui.py` | `pagefolio/dialogs/llm_config.py` | LLM 設定ダイアログのロジック層 |

## テストの書き方

### ファイル命名規則

テストファイルは `tests/` ディレクトリに `test_<対象モジュール名>.py` 形式で配置します。

```
tests/
├── conftest.py          # 共通フィクスチャ
├── test_pdf_ops.py      # pagefolio/page_ops.py 対応
└── test_ocr.py          # pagefolio/ocr.py 対応
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
| `tmp_settings` | `tuple[Path, Callable]` | 一時ディレクトリに設定ファイルを作成・管理 |
| `sample_pdf` | `str` | テスト用 3 ページ PDF のファイルパス |
| `sample_pdf_doc` | `fitz.Document` | テスト用 3 ページ PDF の `fitz.Document`（自動クローズ） |
| `multi_pdf_files` | `list[str]` | 結合・挿入テスト用の複数 PDF ファイルリスト（1, 2, 3 ページ） |

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

Mixin メソッドのテストは `types.SimpleNamespace` で必要な属性だけを持つスタブを作り、未束縛メソッドとしてバインドして呼び出す方法を使います。

```python
import types
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

## カバレッジ要件

現在、カバレッジしきい値は明示的に設定されていません。

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

`tests/**/*.py` では `S101`（assert の使用）が許可されています。

## CI 統合

現在、GitHub Actions などの CI パイプラインは設定されていません。
ローカルで `pytest` を実行して確認してください。

コミット前のチェックリスト:

1. `ruff check . && ruff format .` でリント・フォーマット確認
2. `pytest` でテスト確認
