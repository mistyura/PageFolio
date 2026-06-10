# Testing Patterns

**Analysis Date:** 2026-06-10

## Test Framework

**Runner:**
- pytest (v9.0.2)
- Config location: `pyproject.toml` (under `[tool.pytest.ini_options]`)
- Config:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["src"]
  ```

**Assertion Library:**
- Built-in `assert` statements (standard Python unittest style)
- Also uses `pytest.raises()` for exception testing

**Run Commands:**
```bash
pytest                    # Run all tests
pytest tests/test_*.py    # Run specific test file
pytest -v                 # Verbose output with test names
pytest -x                 # Stop on first failure
pytest --cov=pagefolio    # Run with coverage (requires pytest-cov)
```

## Test File Organization

**Location:**
- Test files co-located in `tests/` directory (separate from source)
- Tests import from `pagefolio` package using sys.path manipulation for portability

**Naming:**
- Pattern: `test_<module>.py` matching source modules
- Example mappings:
  - `tests/test_pdf_ops.py` tests PDF operations via fitz API
  - `tests/test_ocr.py` tests OCR utilities and parallel execution
  - `tests/test_plugins.py` tests PluginManager
  - `tests/test_utils.py` tests utility functions (settings, fonts)
  - `tests/test_imports.py` tests backward compatibility and import paths

**File Count:**
- 11 test files total
- 412+ test methods across all files
- Estimated coverage: Core functionality and regression tests

## Test Structure

**Suite Organization:**

Test classes use the pattern `Test<Feature>` to group related tests. Each class tests one component or feature:

```python
class TestPdfOpen:
    """PDF ファイルの読み込みテスト"""
    def test_open_valid_pdf(self, sample_pdf):
        ...
    def test_open_nonexistent_file_raises(self, tmp_path):
        ...

class TestPageRotate:
    """ページ回転テスト（_rotate_selected と同等のロジック）"""
    def test_rotate_90(self, sample_pdf_doc):
        ...
```

**Fixtures (Shared Setup):**

Defined in `tests/conftest.py`. Available to all test files:

```python
@pytest.fixture()
def tmp_settings(tmp_path):
    """一時ディレクトリに設定ファイルを作成・管理するフィクスチャ。
    返り値は (settings_path, write_fn) のタプル。
    write_fn(data) で設定を書き込む。
    """
    settings_path = tmp_path / "pagefolio_settings.json"
    def write_fn(data):
        settings_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return settings_path, write_fn

@pytest.fixture()
def sample_pdf(tmp_path):
    """テスト用の3ページPDFをメモリ上で生成し、tmp_pathに保存して返す。
    返り値は PDF ファイルパス (str)。
    """
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    pdf_path = str(tmp_path / "test_sample.pdf")
    doc.save(pdf_path)
    doc.close()
    return pdf_path

@pytest.fixture()
def sample_pdf_doc():
    """テスト用の3ページPDFをメモリ上で生成し、fitz.Document として返す。
    テスト終了後に自動でクローズされる。
    """
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc
    doc.close()

@pytest.fixture()
def multi_pdf_files(tmp_path):
    """結合・挿入テスト用に複数のPDFファイルを生成する。
    返り値は [path1, path2, path3] のリスト。
    """
    # Creates 3 PDFs with 1, 2, 3 pages respectively
    ...
    return paths
```

**Setup and Teardown:**

- Fixtures use `yield` for resource cleanup (preferred over setup/teardown methods)
- Example: `sample_pdf_doc` fixture closes document after test via `yield`
- Temporary files created via pytest's `tmp_path` fixture (auto-cleaned)

## Test Structure Example

From `tests/test_pdf_ops.py`:

```python
"""PDF 操作のテスト。
pagefolio.py のPDF操作ロジックは Tkinter に強く結合しているため、
fitz API を直接使ってアプリと同等の操作が正しく動くことを検証する。
"""

import os
from unittest.mock import patch
import fitz
import pytest
import pagefolio

class TestPdfOpen:
    """PDF ファイルの読み込みテスト"""

    def test_open_valid_pdf(self, sample_pdf):
        """正常な PDF を開ける"""
        doc = fitz.open(sample_pdf)
        assert len(doc) == 3
        doc.close()

    def test_open_nonexistent_file_raises(self, tmp_path):
        """存在しないファイルを開くとエラー"""
        with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
            fitz.open(str(tmp_path / "nonexistent.pdf"))

    def test_page_text_content(self, sample_pdf):
        """各ページのテキスト内容が正しい"""
        doc = fitz.open(sample_pdf)
        for i in range(3):
            text = doc[i].get_text()
            assert f"Page {i + 1}" in text
        doc.close()
```

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**

1. **Monkeypatch (pytest built-in):**
   ```python
   def test_discover_plugins(self, tmp_path, monkeypatch):
       plugins_dir = tmp_path / "plugins"
       plugins_dir.mkdir()
       (plugins_dir / "my_plugin.py").write_text("# dummy", encoding="utf-8")
       monkeypatch.setattr(_plugins_mod, "_get_plugins_dir", lambda: str(plugins_dir))
       pm = pagefolio.PluginManager()
       found = pm.discover_plugins()
       assert "my_plugin" in [pid for pid, _ in found]
   ```

2. **unittest.mock.patch():**
   ```python
   from unittest.mock import patch
   
   def test_load_settings(self, tmp_settings):
       path, write_fn = tmp_settings
       write_fn({"theme": "light", "font_size": 14})
       with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
           settings = pagefolio._load_settings()
       assert settings["theme"] == "light"
   ```

3. **Test Doubles (Custom Fakes):**
   ```python
   class FakeProvider(OCRProvider):
       """run_parallel テスト用の偽 Provider。"""
       default_concurrency = 2
       max_concurrency = 4
   
       def __init__(self, side_effect=None):
           self._side_effect = side_effect
   
       def ocr_image(self, b64_png, prompt, **kwargs):
           if self._side_effect is not None:
               return self._side_effect(b64_png, prompt)
           return f"text-{b64_png}"
   
       def list_models(self):
           return ["fake-model"]
   ```

**What to Mock:**
- External API calls (LM Studio, Claude, Gemini)
- File system paths (to use `tmp_path` instead of real files)
- Plugin discovery (to avoid loading real plugins during tests)
- Settings file I/O (to use temporary settings)

**What NOT to Mock:**
- PDF operations via fitz (test real PDF functionality)
- Core business logic (test actual algorithms)
- Data structures (test real collections, not mocks)
- Dialog classes (verify symbol existence only, don't instantiate in headless tests)

## Fixtures and Factories

**Test Data:**

Fixtures create realistic test PDFs in memory:
```python
@pytest.fixture()
def sample_pdf_doc():
    """テスト用の3ページPDFをメモリ上で生成"""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc
    doc.close()
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Test-specific fixtures: Defined within test classes with `@pytest.fixture(autouse=True)`
- Example from `tests/test_pdf_ops.py`:
  ```python
  @pytest.fixture(autouse=True)
  def setup_test(self, tmp_path, monkeypatch):
      """Each test method gets fresh temp directory"""
      self.tmp_dir = tmp_path
  ```

## Coverage

**Requirements:** No hard coverage target enforced. Testing follows pragmatic approach:
- Core business logic (PDF operations, undo/redo): thorough coverage
- UI state management: targeted tests for complex state machines
- External integrations: mocked to avoid flaky network tests
- Plugin system: comprehensive regression tests

**View Coverage:**
```bash
pytest --cov=pagefolio --cov-report=html
# Opens htmlcov/index.html in browser
```

## Test Types

**Unit Tests:**
- Focus: Individual functions and methods in isolation
- Scope: `_load_settings()`, `page_to_png_b64()`, `clamp_retry_after()`, utility functions
- Approach: Use fixtures and mocks to isolate units
- Location: Most of `tests/test_utils.py`, `tests/test_ocr.py`, `tests/test_ocr_providers.py`

**Integration Tests:**
- Focus: Multi-component workflows (file open → page rotate → save)
- Scope: Undo/redo state reconstruction, plugin lifecycle, PDF merge operations
- Approach: Use real fitz.Document and temporary files
- Location: `tests/test_pdf_ops.py`, `tests/test_plugins.py`, `tests/test_viewer.py`

**Regression Tests:**
- Focus: Backward compatibility and import paths
- Scope: Verify dialogs can be imported, constants re-exported correctly
- Approach: Explicit import statements + hasattr checks
- Location: `tests/test_imports.py` (comprehensive import compatibility suite)

**E2E Tests:**
- Status: Not yet implemented
- Note: Would require Tkinter event simulation or GUI automation
- Future: Consider `pytest-qt` equivalent for Tkinter if needed

## Common Patterns

**Async Testing (Threading):**

From `tests/test_ocr.py`:
```python
def test_run_parallel_concurrent(self):
    """複数ページを並列 OCR する"""
    provider = FakeProvider()
    pages = [f"page{i}" for i in range(4)]
    
    def render_fn(idx):
        return f"b64-page{idx}"
    
    results = list(ocr.run_parallel(
        pages, render_fn, provider, "prompt", concurrency=2
    ))
    assert len(results) == 4
    assert all("text-" in r for r in results)
```

**Handling Async Render Threads:**
- Generation counters (`_preview_gen`, `_thumb_gen`) prevent race conditions
- Stale results automatically discarded if counter advances
- No explicit thread mocking needed—tests run synchronously

**Error Testing:**

1. **Exception Type Verification:**
   ```python
   def test_open_nonexistent_file_raises(self, tmp_path):
       with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
           fitz.open(str(tmp_path / "nonexistent.pdf"))
   ```

2. **Exception Message Matching (pytest 7+):**
   ```python
   with pytest.raises(ValueError, match="API key required"):
       _resolve_api_key("unknown_provider", {})
   ```

3. **Custom Exception Handling:**
   ```python
   def test_api_key_error_on_missing_key(self):
       from pagefolio.ocr_providers import OCRAPIKeyError
       
       with pytest.raises(OCRAPIKeyError):
           # Trigger missing API key path
           provider.ocr_image(b64, prompt)
   ```

## Special Test Concerns

**Headless Mode (No Tkinter Root):**
- Dialog classes NOT instantiated in tests (would require event loop)
- Instead: verify class existence via `hasattr()` and import statements
- Rationale: `test_imports.py` ensures dialog classes are importable and exist
- Example from `tests/test_imports.py`:
  ```python
  def test_dialogs_subpackage_about(self):
      """pagefolio.dialogs から AboutDialog を import できる"""
      from pagefolio.dialogs import AboutDialog
      assert AboutDialog is not None
  ```

**Settings Persistence:**
- Use `tmp_settings` fixture to create temporary settings files
- Patch `_get_settings_path()` to point to temporary location
- Never test against real `pagefolio_settings.json`
- Example:
  ```python
  def test_save_settings_excludes_keys(self, tmp_settings):
      path, write_fn = tmp_settings
      with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
          settings = {"theme": "dark", "claude_api_key": "sk-..."}
          pagefolio._save_settings(settings)
          # Verify API key not in saved JSON
          saved = json.loads(path.read_text())
          assert "claude_api_key" not in saved
  ```

**Plugin Loading Isolation:**
- Plugins are discovered via monkeypatch to `_get_plugins_dir()`
- Real plugins in `plugins/` are never loaded during tests
- Each test class that uses plugins creates isolated temporary plugin directories
- Example from `tests/test_plugins.py`:
  ```python
  def test_discover_plugins(self, tmp_path, monkeypatch):
      plugins_dir = tmp_path / "plugins"
      plugins_dir.mkdir()
      (plugins_dir / "my_plugin.py").write_text("# dummy")
      monkeypatch.setattr(_plugins_mod, "_get_plugins_dir", lambda: str(plugins_dir))
      found = pm.discover_plugins()
  ```

## Language in Tests

**Test Documentation:**
- Docstrings in Japanese (e.g., `"""PDF ファイルの読み込みテスト"""`)
- Comments in Japanese
- Test method names in English (snake_case describing behavior)
- Exception messages and assertions in English (referring to code identifiers)

---

*Testing analysis: 2026-06-10*
