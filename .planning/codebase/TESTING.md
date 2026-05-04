# テストパターン

**分析日:** 2026-05-04

## テストフレームワーク

**ランナー:**
- pytest
- 設定: `pyproject.toml` の `[tool.pytest.ini_options]`
- `testpaths = ["tests"]`, `pythonpath = ["src"]`

**アサーションライブラリ:**
- pytest 組み込みの `assert` 文（標準）

**実行コマンド:**
```bash
pytest                   # 全テスト実行
pytest tests/test_utils.py   # ファイル指定実行
pytest -q                # 簡易出力
pytest --collect-only -q # テスト一覧確認のみ
```

**リント（テスト実行前に必ず実施）:**
```bash
ruff check . && ruff format .
```

## テストファイル構成

**配置場所:** プロジェクトルートの `tests/` ディレクトリ（ソースと分離）

```
tests/
├── conftest.py       # 共有フィクスチャ定義
├── test_utils.py     # 設定・テーマ・フォント・ページ範囲パース（35件）
├── test_pdf_ops.py   # PDF読み込み・保存・操作ロジック（26件）
└── test_plugins.py   # PluginManager（47件）
```

**合計:** 108件（`pytest --collect-only` で確認済み）

**`pyproject.toml` の `tests/` 向け Ruff 除外ルール:**
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # assert 文の使用を許可
```

## 各テストファイルの概要

### `tests/conftest.py` — 共有フィクスチャ

| フィクスチャ | 返り値 | 用途 |
|------------|--------|------|
| `tmp_settings` | `(Path, write_fn)` タプル | 一時ディレクトリへの設定ファイル作成・管理 |
| `sample_pdf` | PDF ファイルパス `str` | 3ページの A4 テスト PDF（ファイルとして保存） |
| `sample_pdf_doc` | `fitz.Document` | 3ページの A4 テスト PDF（メモリ上、yield で自動クローズ） |
| `multi_pdf_files` | `[path1, path2, path3]` | 結合・挿入テスト用（1/2/3ページの PDF 群） |

### `tests/test_utils.py` — ユーティリティ関数テスト（35件）

| テストクラス | テスト対象 | 件数 |
|------------|----------|------|
| `TestLoadSettings` | `_load_settings()` — デフォルト値・既存ファイル・キー補完・不正JSON | 4 |
| `TestSaveSettings` | `_save_settings()` — 保存・再読み込み・新規作成 | 2 |
| `TestResolveTheme` | `_resolve_theme()` — dark/light/不明/system の解決 | 4 |
| `TestApplyTheme` | `_apply_theme()` — テーマ辞書 C への適用 | 3 |
| `TestMakeFont` | `_make_font()` — delta・最小サイズ・weight あり/なし | 6 |
| `TestParsePageRanges` | `PDFEditorApp._parse_page_ranges()` — 正常系8件・異常系8件 | 16 |
| `TestGetSettingsPath` | `_get_settings_path()` — frozen/通常モード | 2 |
| `TestSaveSettingsError` | `_save_settings()` — 不正パスへの保存（例外なし） | 1 |
| `TestDetectSystemThemeError` | `_detect_system_theme()` — winreg エラー時のフォールバック | 1 |

### `tests/test_pdf_ops.py` — PDF操作テスト（26件）

| テストクラス | テスト対象 | 件数 |
|------------|----------|------|
| `TestPdfOpen` | `fitz.open()` — 正常開封・ページ数・テキスト内容・存在しないファイル | 4 |
| `TestPdfSave` | `fitz.Document.save()` — 新規保存・内容保持・incremental 保存 | 3 |
| `TestPageRotate` | `page.set_rotation()` — 90/180/360度・複数ページ | 4 |
| `TestPageDelete` | `doc.delete_page()` — 1件・残存確認・逆順複数削除 | 3 |
| `TestPageInsert` | `doc.insert_pdf()` — 先頭挿入・末尾挿入 | 2 |
| `TestPdfMerge` | `doc.insert_pdf()` — 複数ファイル結合・ページ数検証 | 1 |
| `TestPdfSplit` | `fitz.open()` + `insert_pdf()` — 範囲分割・1ページずつ・単一抽出 | 3 |
| `TestPageCrop` | `page.set_cropbox()` — 設定・MediaBox クランプ・リセット・サイズ検出 | 4 |
| `TestUndoRedoLogic` | `doc.tobytes()` + `fitz.open("pdf", bytes)` — 状態保存復元・Redo | 2 |
| `TestCheckSplitOverwrite` | `PDFEditorApp._check_split_overwrite()` — ファイルなし・Yes/No | 3 |

**設計方針:** PDF 操作ロジックは Tkinter に強く結合しているため、`fitz` API を直接使い、アプリと同等の操作が正しく動くことを検証する方針。

### `tests/test_plugins.py` — PluginManagerテスト（47件）

| テストクラス | テスト対象 | 件数 |
|------------|----------|------|
| `TestPluginManagerInit` | 初期化 — `plugins`, `all_plugins`, `get_disabled_ids()` | 2 |
| `TestPluginDiscovery` | `discover_plugins()` — 検出・空ディレクトリ・存在しないディレクトリ | 3 |
| `TestPluginLoadUnload` | `load_plugin()`, `unload_plugin()` — 読み込み・同一インスタンス・非サブクラス・不正ファイル・アンロード | 5 |
| `TestPluginEnableDisable` | `disable_plugin()`, `enable_plugin()`, `get_disabled_ids()` | 3 |
| `TestPluginFireEvent` | `fire_event()` — メソッド呼び出し・disabled スキップ・存在しないイベント | 3 |
| `TestLoadAll` | `load_all(disabled_ids=[...])` — 有効/無効の一括ロード | 1 |
| `TestGetPluginsDir` | `_get_plugins_dir()` — frozen/通常モード | 2 |
| `TestPDFEditorPluginBase` | 基底クラスの全メソッド呼び出し可能性（parametrize: 11メソッド） | 11 |
| `TestPluginLifecycleWithApp` | `load/unload/enable/disable` + `app` 引数 — ライフサイクルフック検証 | 5 |
| `TestFireEventException` | 例外プラグインが他のプラグインをブロックしないことを確認 | 2 |
| `TestLifecycleExceptionHandling` | `unload/enable/disable` での例外ハンドリング | 3 |

## テスト構造パターン

**クラスベース構成:**
```python
class TestXxx:
    """機能名のテスト"""

    def test_正常ケース(self, フィクスチャ):
        """日本語で何をテストするかを説明"""
        # アレンジ
        ...
        # アクト
        result = 対象関数()
        # アサート
        assert result == 期待値
```

**pytest フィクスチャの使い方:**
```python
# conftest.py フィクスチャをパラメータで受け取る
def test_open_valid_pdf(self, sample_pdf):
    doc = fitz.open(sample_pdf)
    assert len(doc) == 3
    doc.close()

# tmp_path（pytest 組み込み）は一時ディレクトリ
def test_save_new_file(self, sample_pdf_doc, tmp_path):
    save_path = str(tmp_path / "saved.pdf")
    ...

# autouse フィクスチャでテストクラス全体のセットアップ
@pytest.fixture(autouse=True)
def _setup(self):
    class FakeApp:
        ...
    self.app = FakeApp()
```

**parametrize の使い方（`test_plugins.py`）:**
```python
@pytest.mark.parametrize(
    "method_name, args",
    [
        ("on_load", ("app",)),
        ("on_file_open", ("app", "/path.pdf")),
        # ...
    ],
)
def test_base_method_callable(self, method_name, args):
    plugin = pagefolio.PDFEditorPlugin()
    method = getattr(plugin, method_name)
    result = method(*args)
    assert result is None
```

## モックの使用状況

**使用ライブラリ:** `unittest.mock` (`MagicMock`, `patch`)

**パターン1: `patch.object` で内部関数を差し替え（`test_utils.py`）:**
```python
from unittest.mock import patch
import pagefolio.settings as _settings_mod

with patch.object(_settings_mod, "_get_settings_path", return_value=fake_path):
    settings = pagefolio._load_settings()
```

**パターン2: `monkeypatch` で `sys` 属性を書き換え（pytest 組み込み）:**
```python
def test_frozen_mode(self, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/fake/dir/app.exe")
    result = _settings_mod._get_settings_path()
    assert os.path.dirname(result) == "/fake/dir"
```

**パターン3: `@patch` デコレータで Tkinter messagebox を差し替え（`test_pdf_ops.py`）:**
```python
@patch("pagefolio.page_ops.messagebox.askyesno", return_value=True)
def test_existing_files_user_accepts(self, mock_ask, tmp_path):
    result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf"])
    assert result is True
    mock_ask.assert_called_once()
```

**パターン4: `MagicMock` でモジュールを差し替え（`test_utils.py`）:**
```python
broken = MagicMock()
broken.OpenKey = MagicMock(side_effect=OSError("mocked"))
with patch.dict("sys.modules", {"winreg": broken}):
    result = _settings_mod._detect_system_theme()
```

**パターン5: Tkinter に依存するメソッドのテスト — FakeApp パターン:**
```python
class FakeApp:
    def _t(self, key):
        return key  # 翻訳関数のスタブ

self.app = FakeApp()
self.app._check_split_overwrite = (
    pagefolio.PDFEditorApp._check_split_overwrite.__get__(self.app)
)
```

**モックすべき対象:**
- ファイルシステムへの書き込み（`_get_settings_path` を `tmp_path` にリダイレクト）
- Tkinter の `messagebox`（GUI なしでテスト可能にする）
- Windows 固有 API（`winreg`）
- `sys.frozen`, `sys.executable`（PyInstaller 環境のシミュレーション）

**モックしない対象:**
- `fitz`（pymupdf）の PDF 操作（実際の動作を検証）
- ファイル I/O（`tmp_path` を使った実際のファイル操作）

## フィクスチャとテストデータ

**PDF テストデータ（`tests/conftest.py` で生成）:**
```python
@pytest.fixture()
def sample_pdf_doc():
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)  # A4 サイズ
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc
    doc.close()  # テスト終了後に自動クローズ
```

**動的プラグインファイル生成（`test_plugins.py` の補助メソッド）:**
```python
def _create_plugin_file(self, path, name="TestPlugin"):
    code = textwrap.dedent(f"""
        import pagefolio
        class {name}(pagefolio.PDFEditorPlugin):
            name = "{name}"
            ...
    """)
    path.write_text(code, encoding="utf-8")
```

## テストカバレッジの現状

**カバレッジ要件:** 未設定（`pyproject.toml` に coverage 設定なし）

**テスト済みの領域:**
- `pagefolio/settings.py` — `_load_settings`, `_save_settings`, `_resolve_theme`, `_apply_theme`, `_make_font`, `_get_settings_path`, `_detect_system_theme` の全関数
- `pagefolio/plugins.py` — `PluginManager` クラスの全パブリックメソッド、`PDFEditorPlugin` 基底クラス全メソッド
- `pagefolio/app.py` — `_parse_page_ranges`, `_check_split_overwrite` （部分）
- PDF 操作ロジック（fitz API 直接検証）— 読み込み・保存・回転・削除・挿入・結合・分割・トリミング・Undo/Redo

**テストが不足している領域:**

| 対象 | 理由 | 優先度 |
|------|------|--------|
| `pagefolio/ui_builder.py` | Tkinter 依存でヘッドレステスト困難 | 低 |
| `pagefolio/viewer.py` | Canvas/Image 操作で GUI 必要 | 低 |
| `pagefolio/dnd.py` | マウスイベント依存でテスト困難 | 低 |
| `pagefolio/dialogs.py` | ダイアログは GUI インタラクション依存 | 低 |
| `pagefolio/file_drop.py` | tkinterdnd2 依存 | 低 |
| `pagefolio/file_ops.py` — `_open_file` | ファイルダイアログ依存 | 中 |
| `pagefolio/page_ops.py` — `_crop_apply` | Tkinter Canvas 依存 | 中 |
| `pagefolio/app.py` — `_font`, `_t`, `_check_doc` | Mixin のヘルパーメソッド | 中 |
| ページ複製機能 (`_duplicate_page`) | 未テスト | 高 |
| PDF 縮小保存機能 | 未テスト | 高 |

**カバレッジ計測コマンド:**
```bash
pytest --cov=pagefolio --cov-report=term-missing
```
（`pytest-cov` パッケージが必要）

## テストタイプ

**単体テスト（主体）:**
- 純粋関数: 設定読み書き、テーマ解決、フォント生成、ページ範囲パース
- プラグインシステム: PluginManager の全操作

**統合テスト（擬似的）:**
- `test_pdf_ops.py` — `fitz` API を直接使ってアプリと同等の PDF 操作を検証
- プラグイン動的ロード — 実際に Python ファイルを生成・インポートして検証

**E2E テスト:** 未使用（Tkinter アプリの特性上、手動確認が主）

---

*テスト分析日: 2026-05-04*
