# Testing Patterns

**Analysis Date:** 2026-06-01

## Test Framework

**Runner:** pytest
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`
- `testpaths = ["tests"]`
- `pythonpath = ["src"]`

**Assertion Library:** pytest built-in assert

**Run Commands:**
```bash
pytest                  # Run all tests
pytest tests/test_pdf_ops.py   # Run single file
pytest -k "TestPdfOpen"        # Run single class
```

## Test File Organization

**Location:** `tests/` directory (separate from source)

**Files:**
- `tests/conftest.py` — shared fixtures (PDF generation, settings helpers)
- `tests/test_utils.py` — settings load/save, theme resolution, font helper, page range parser
- `tests/test_pdf_ops.py` — PDF open/save/rotate/delete/insert/merge/split/crop/undo-redo/bulk-move
- `tests/test_plugins.py` — PluginManager discovery, load/unload, enable/disable, event firing, lifecycle
- `tests/test_ocr.py` — OCR payload building, PNG encoding, LM Studio HTTP client (mocked), parallel execution

**Naming:**
- Test files: `test_<module>.py`
- Test classes: `Test<FeatureName>` (e.g., `TestLoadSettings`, `TestPdfMerge`, `TestPluginDiscovery`)
- Test methods: `test_<scenario>` with descriptive Japanese docstrings

## Test Structure

**Class-based grouping** — all tests are organized in classes, never bare functions:
```python
class TestLoadSettings:
    """_load_settings のテスト"""

    def test_defaults_when_no_file(self, tmp_path):
        """設定ファイルがない場合はデフォルト値を返す"""
        ...
```

**Normal + error cases pattern** — classes cover both happy path and edge/error cases:
```python
# --- 正常系 ---
def test_single_page(self): ...
def test_page_range(self): ...

# --- 異常系 ---
def test_empty_string(self): ...
def test_page_zero(self): ...
```

**Parametrize for base class methods:**
```python
@pytest.mark.parametrize(
    "method_name, args",
    [
        ("on_load", ("app",)),
        ("on_file_open", ("app", "/path.pdf")),
    ],
)
def test_base_method_callable(self, method_name, args):
    plugin = pagefolio.PDFEditorPlugin()
    result = getattr(plugin, method_name)(*args)
    assert result is None
```

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `patch`, `monkeypatch`)

**`patch.object` for module-level path injection** — used to redirect file paths to `tmp_path`:
```python
with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
    settings = pagefolio._load_settings()
```

**`monkeypatch.setattr` for pytest-style patching** — preferred for `sys` attributes and module functions:
```python
monkeypatch.setattr(sys, "frozen", True, raising=False)
monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
```

**Fake objects for Tkinter-coupled methods** — Tkinter is not instantiated; minimal `FakeApp` class used:
```python
class FakeApp:
    def _t(self, key):
        return key

self.app = FakeApp()
self.app._check_split_overwrite = (
    pagefolio.PDFEditorApp._check_split_overwrite.__get__(self.app)
)
```

**Tkinter dialogs patched directly:**
```python
@patch("pagefolio.page_ops.messagebox.askyesno", return_value=True)
def test_existing_files_user_accepts(self, mock_ask, tmp_path):
    ...
    mock_ask.assert_called_once()
```

## Fixtures and Factories

**Defined in `tests/conftest.py`:**

```python
@pytest.fixture()
def tmp_settings(tmp_path):
    """一時ディレクトリに設定ファイルを作成・管理するフィクスチャ。
    返り値は (settings_path, write_fn) のタプル。"""
    settings_path = tmp_path / "pagefolio_settings.json"
    def write_fn(data):
        settings_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return settings_path, write_fn

@pytest.fixture()
def sample_pdf(tmp_path):
    """テスト用の3ページPDF (ファイルパス str を返す)"""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    pdf_path = str(tmp_path / "test_sample.pdf")
    doc.save(pdf_path)
    doc.close()
    return pdf_path

@pytest.fixture()
def sample_pdf_doc():
    """テスト用の3ページPDF (fitz.Document を yield、終了後自動クローズ)"""
    doc = fitz.open()
    ...
    yield doc
    doc.close()

@pytest.fixture()
def multi_pdf_files(tmp_path):
    """複数PDFファイルリスト [path1(1p), path2(2p), path3(3p)]"""
```

**Inline fixtures** using `autouse=True` for per-class setup:
```python
@pytest.fixture(autouse=True)
def _setup(self):
    class FakeApp:
        pass
    self.app = FakeApp()
    ...
```

**Plugin code generation in tests** — plugin source code is written to `tmp_path` at runtime using `textwrap.dedent`:
```python
code = textwrap.dedent(f"""\
    import pagefolio
    class {name}(pagefolio.PDFEditorPlugin):
        ...
""")
(tmp_path / "my_plugin.py").write_text(code, encoding="utf-8")
```

## Coverage

**Requirements:** No enforced coverage threshold in `pyproject.toml`

**Well-covered areas:**
- `pagefolio/settings.py` — load/save/resolve/detect all exercised including error paths
- `pagefolio/plugins.py` — full lifecycle, all event hooks, exception handling in `fire_event`
- `pagefolio/page_ops.py` — rotate, delete, insert, merge, split, crop, undo/redo, bulk-move logic
- `pagefolio/ocr.py` — payload building, base64 PNG encoding, HTTP responses (success + all error types), parallel execution

**Not covered (Tkinter-bound code):**
- `pagefolio/app.py` — `PDFEditorApp.__init__`, `_build_ui`, window lifecycle (requires display)
- `pagefolio/viewer.py` — thumbnail rendering, preview canvas, popup (requires display)
- `pagefolio/dnd.py` — drag-and-drop event handlers (requires display)
- `pagefolio/dialogs.py` — dialog rendering (requires display); only logic patches like `messagebox.askyesno` are tested indirectly

**Strategy for Tkinter-bound logic:**
- Extract pure logic into standalone functions or test the fitz API directly (`test_pdf_ops.py`)
- Use `FakeApp` pattern to bind unbound methods and test without a real Tk window

## Running Tests

```bash
pytest                          # All tests
pytest tests/test_utils.py      # Utility / settings tests only
pytest tests/test_pdf_ops.py    # PDF operation logic tests only
pytest tests/test_plugins.py    # Plugin system tests only
pytest tests/test_ocr.py        # OCR client tests only
pytest -v                       # Verbose output with test names
```

Linting must pass before commit:
```bash
ruff check . && ruff format .
```

---

*Testing analysis: 2026-06-01*
