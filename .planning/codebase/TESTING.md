# TESTING.md
_Generated: 2026-05-23_
_Focus: quality_

# Testing Patterns

**Analysis Date:** 2026-05-23

## Test Framework

**Runner:**
- pytest
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)
- `testpaths = ["tests"]`
- `pythonpath = ["src"]`

**Assertion Library:**
- pytest 組み込みの `assert` 文
- テストファイルでの `assert` は Ruff S101 から除外済み (`tests/**/*.py` = `["S101"]`)

**Run Commands:**
```bash
pytest                    # 全テスト実行
pytest tests/test_utils.py  # 特定ファイルのみ
pytest -v                 # 詳細出力
pytest --tb=short         # 短縮スタックトレース
```

## Test File Organization

**Location:** `tests/` ディレクトリ（プロジェクトルート直下）

**Naming:**
- テストファイル: `test_<対象領域>.py`
- テストクラス: `Test<機能名>`（例: `TestLoadSettings`, `TestPageDelete`）
- テストメソッド: `test_<シナリオ説明>`（例: `test_defaults_when_no_file`）

**Structure:**
```
tests/
├── conftest.py        # 共通フィクスチャ（sample_pdf, sample_pdf_doc 等）
├── test_utils.py      # ユーティリティ関数テスト（35件）
├── test_pdf_ops.py    # PDF 操作テスト（34件）
└── test_plugins.py    # PluginManager テスト（17件）
```

**合計テスト数:** 86件（実装ファイルを直接インポートしてテスト）

## Test File Contents

### `tests/test_utils.py`（35件）

設定読み書き・テーマ解決・フォント生成・ページ範囲パースをカバー。

| クラス | テスト数 | 内容 |
|--------|---------|------|
| `TestLoadSettings` | 4件 | ファイルなし・正常読込・欠損キー補完・不正JSON |
| `TestSaveSettings` | 2件 | 保存・再読込の一致、新規ファイル作成 |
| `TestResolveTheme` | 4件 | dark/light/不明値/system |
| `TestApplyTheme` | 3件 | dark/light 適用、不明値フォールバック |
| `TestMakeFont` | 6件 | デフォルト・delta・最小サイズクランプ・weight |
| `TestParsePageRanges` | 16件 | 正常系8件（単一・範囲・複合・境界）+ 異常系8件 |
| `TestGetSettingsPath` | 2件 | frozen/通常モードのパス解決 |
| `TestSaveSettingsError` | 1件 | 存在しないディレクトリへの保存（例外を投げない） |
| `TestDetectSystemThemeError` | 1件 | winreg インポート失敗時のフォールバック |

### `tests/test_pdf_ops.py`（34件）

fitz API を直接呼び出して PDF 操作ロジックを検証（Tkinter 非依存）。

| クラス | テスト数 | 内容 |
|--------|---------|------|
| `TestPdfOpen` | 4件 | 正常読込・ページ数・不存在ファイル・テキスト内容 |
| `TestPdfSave` | 3件 | 新規保存・内容保持・incremental 上書き保存 |
| `TestPageRotate` | 4件 | 90°/180°/360°/複数ページ |
| `TestPageDelete` | 3件 | 単一削除・残存ページ確認・逆順複数削除 |
| `TestPageInsert` | 2件 | 先頭挿入・末尾挿入 |
| `TestPdfMerge` | 1件 | 複数ファイル結合・ページ数確認 |
| `TestPdfSplit` | 3件 | 範囲指定・1ページずつ・単一ページ抽出 |
| `TestPageCrop` | 4件 | CropBox 設定・MediaBox 内クランプ・リセット・最小サイズ検出 |
| `TestUndoRedoLogic` | 3件 | 回転差分・削除差分・旧フォーマット互換 |
| `TestBulkMoveLogic` | 2件 | doc.select() ラウンドトリップ・new_order 構築ロジック |
| `TestBulkCropLogic` | 2件 | 複数ページ cropbox ラウンドトリップ・相対座標変換 |
| `TestCheckSplitOverwrite` | 3件 | ファイル未存在・ユーザー許可・ユーザー拒否 |
| `TestMergeResizeLogic` | 5件 | A4×2横/縦結合・元ページ削除・3枚横結合・異サイズ混在 |

### `tests/test_plugins.py`（17件）

PluginManager の全機能と PDFEditorPlugin 基底クラスをカバー。

| クラス | テスト数 | 内容 |
|--------|---------|------|
| `TestPluginManagerInit` | 2件 | 初期状態の空辞書・無効化セット |
| `TestPluginDiscovery` | 3件 | ディレクトリ検出・空ディレクトリ・存在しないディレクトリ |
| `TestPluginLoadUnload` | 5件 | 読込・同一インスタンス再利用・サブクラスなし・不正ファイル・アンロード |
| `TestPluginEnableDisable` | 3件 | 無効化・再有効化・disabled_ids リスト |
| `TestPluginFireEvent` | 3件 | イベント呼び出し・無効プラグインスキップ・存在しないメソッドの安全性 |
| `TestLoadAll` | 1件 | disabled_ids 指定での一括読み込み |
| `TestGetPluginsDir` | 2件 | frozen/通常モードのパス解決 |
| `TestPDFEditorPluginBase` | 11件 (parametrize) | 基底クラス全メソッドの呼び出し可能性 |
| `TestPluginLifecycleWithApp` | 5件 | app 引数付きの load/unload/enable/disable |
| `TestFireEventException` | 2件 | 例外飲み込み・後続プラグインの継続 |
| `TestLifecycleExceptionHandling` | 3件 | unload/enable/disable の例外ハンドリング |

## Fixtures (`tests/conftest.py`)

| フィクスチャ | スコープ | 返り値 | 用途 |
|-------------|---------|--------|------|
| `tmp_settings` | function | `(Path, write_fn)` | 一時設定ファイル操作 |
| `sample_pdf` | function | `str`（ファイルパス） | 3ページ A4 PDF ファイル |
| `sample_pdf_doc` | function | `fitz.Document` | 3ページ PDF オブジェクト（yield + 自動クローズ） |
| `multi_pdf_files` | function | `list[str]` | 1/2/3ページの PDF 3ファイル（結合・挿入用） |

**サンプル PDF の仕様:**
- ページ数: 3ページ
- サイズ: 595×842pt（A4）
- 各ページに `"Page N"` テキスト挿入済み（テスト内容検証用）

```python
# conftest.py の実装パターン
@pytest.fixture()
def sample_pdf_doc():
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc
    doc.close()  # テスト終了後に自動クローズ
```

## Mocking Patterns

**フレームワーク:** `unittest.mock`（`MagicMock`, `patch`, `patch.dict`, `monkeypatch`）

### `unittest.mock.patch` でモジュール内関数を差し替える

```python
# 設定ファイルパスをモック
with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
    settings = pagefolio._load_settings()
```

### `@patch` デコレーターで Tkinter のダイアログをモック

```python
@patch("pagefolio.page_ops.messagebox.askyesno", return_value=True)
def test_existing_files_user_accepts(self, mock_ask, tmp_path):
    result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf"])
    assert result is True
    mock_ask.assert_called_once()
```

### `monkeypatch` で sys 属性を操作

```python
def test_frozen_mode(self, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", os.path.join("/fake", "dir", "app.exe"))
    result = _settings_mod._get_settings_path()
    assert os.path.dirname(result) == "/fake/dir"
```

### `patch.dict` でモジュールを差し替える

```python
broken = MagicMock()
broken.OpenKey = MagicMock(side_effect=OSError("mocked"))
with patch.dict("sys.modules", {"winreg": broken}):
    result = _settings_mod._detect_system_theme()
assert result == "dark"
```

## Tkinter 非依存テストの方針

PDF 操作ロジックは Tkinter に強く結合しているため、インスタンスメソッドを直接テストする代わりに fitz API を直接呼び出してアプリと同等のロジックを検証する。

```python
# Tkinter なしでメソッドをテストする場合のFakeApp パターン
class FakeApp:
    def _t(self, key):
        return key  # 翻訳をパススルー

self.app = FakeApp()
self.app._check_split_overwrite = (
    pagefolio.PDFEditorApp._check_split_overwrite.__get__(self.app)
)
```

この方法で `self` を使うが Tkinter を必要としないメソッドを単独テストできる。

## Parametrize Pattern

```python
@pytest.mark.parametrize(
    "method_name, args",
    [
        ("on_load", ("app",)),
        ("on_unload", ("app",)),
        ("on_file_open", ("app", "/path.pdf")),
        ...
    ],
)
def test_base_method_callable(self, method_name, args):
    plugin = pagefolio.PDFEditorPlugin()
    method = getattr(plugin, method_name)
    result = method(*args)
    assert result is None
```

## Coverage

**Requirements:** 明示的なカバレッジ閾値の設定なし

**カバレッジの高い領域:**
- `pagefolio/settings.py` — `_load_settings`, `_save_settings`, `_resolve_theme`, `_apply_theme`, `_make_font`, `_get_settings_path`, `_detect_system_theme` を全パステスト
- `pagefolio/plugins.py` — `PluginManager` の全パブリックメソッドをカバー
- PDF 操作ロジック（回転・削除・挿入・結合・分割・トリミング・Undo/Redo）

**カバレッジの低い / 未テスト領域:**
- `pagefolio/app.py` — Tkinter `root` が必要なため `PDFEditorApp` の `__init__` 以降の UI 処理はテストなし
- `pagefolio/ui_builder.py` — UI 構築メソッド（`_build_styles`, `_build_ui`）はテストなし
- `pagefolio/viewer.py` — プレビュー・ズーム・サムネイル描画はテストなし
- `pagefolio/dnd.py` — D&D ハンドラはテストなし
- `pagefolio/dialogs.py` — 各ダイアログクラスはテストなし
- `pagefolio/file_drop.py` — tkinterdnd2 連携はテストなし
- `pagefolio/file_ops.py` の Undo/Redo 実行パス（`_undo`, `_redo`）

## Test Types

**Unit Tests:**
- 純粋な関数・ユーティリティメソッドを対象（`test_utils.py`）
- Tkinter を使わないビジネスロジックを fitz API 経由で検証（`test_pdf_ops.py`）
- プラグインシステムの動作検証（`test_plugins.py`）

**Integration Tests:**
- `test_pdf_ops.py` の一部は複数 fitz 操作を連結した統合テスト（保存→再読込、削除→Undo 等）

**E2E Tests:**
- 未実装（Tkinter GUI の自動テストツールは導入なし）

## Common Patterns

**Async Testing:**
- 非同期処理のテストは現状なし（バックグラウンドレンダリングはテスト対象外）

**Error Path Testing:**
```python
def test_invalid_json_returns_defaults(self, tmp_settings):
    path, _ = tmp_settings
    path.write_text("{invalid json!!!", encoding="utf-8")
    with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
        settings = pagefolio._load_settings()
    assert settings["theme"] == "dark"  # デフォルト値に落ちることを確認
```

**Exception Safety Testing:**
```python
def test_fire_event_exception_caught(self, tmp_path):
    pm = pagefolio.PluginManager()
    pm.load_plugin("error_plug", str(error_file))
    pm.fire_event("on_file_open", None, "/test.pdf")  # 例外が飲み込まれる
    # assert なし — 呼び出しが正常終了することを確認
```

**Roundtrip Testing:**
```python
def test_save_and_reload(self, tmp_settings):
    path, _ = tmp_settings
    data = {"theme": "light", "font_size": 16, "lang": "en"}
    with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
        pagefolio._save_settings(data)
        loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == data
```

---

*Testing analysis: 2026-05-23*
