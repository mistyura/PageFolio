# Testing Patterns

**Analysis Date:** 2026-07-03

## Test Framework

**Runner:**
- pytest 9.0.2
- Config: `pyproject.toml`
- Test paths: `tests/` directory
- Python path: `src` (for import resolution)

**Assertion Library:**
- Python built-in `assert` statements (enabled in tests via `# noqa: S101`)
- pytest assertions (`pytest.raises()`, `pytest.approx()`)
- Manual equality checks

**Run Commands:**

```bash
pytest                          # Run all tests
pytest -v                       # Verbose output with test names
pytest tests/test_pdf_ops.py    # Run specific test file
pytest tests/test_pdf_ops.py::TestPageRotate::test_rotate_90  # Run specific test
pytest -k "rotate"              # Run tests matching keyword
pytest --cov                    # Generate coverage report
pytest -x                       # Stop on first failure
pytest -s                       # Show print statements
```

## Test File Organization

**Location:**
- All tests in `tests/` directory at project root
- One test file per source module (e.g., `test_pdf_ops.py` for PDF operations)
- Some cross-cutting concern tests exist (e.g., `test_settings_keyguard.py`, `test_lang_parity.py`)

**Naming Convention:**
- Test files: `test_<module>.py` (e.g., `test_file_ops.py`, `test_ocr_providers.py`)
- Test classes: `Test<FeatureName>` (e.g., `TestPdfOpen`, `TestPdfSave`, `TestPageRotate`)
- Test methods: `test_<scenario>` (e.g., `test_open_valid_pdf`, `test_rotate_90`, `test_is_abc_subclass`)

**Directory Structure:**
```
tests/
├── conftest.py               # Shared fixtures (sample PDFs, temp paths)
├── test_imports.py           # Package import and backward-compat tests
├── test_utils.py             # Utility functions
├── test_pdf_ops.py           # PDF read/write operations
├── test_plugins.py           # PluginManager tests
├── test_viewer.py            # Preview/thumbnail rendering
├── test_settings_keyguard.py # Settings file API key safety checks
├── test_ocr.py               # OCR module utilities
├── test_ocr_providers.py     # OCR provider implementations
├── test_provider_ui.py       # Provider UI integration tests
├── test_pagination.py        # Page window calculation (pure functions)
├── test_md_render.py         # Markdown parsing (pure functions)
├── test_export_images.py     # Page-to-image export
├── test_save_overwrite.py    # Shrink-and-save helper
├── test_password.py          # PDF password operations
├── test_print.py             # Print temp file generation
├── test_undo_stress.py       # 120-page Undo/Redo stress test
├── test_lang_parity.py       # Language key consistency
└── test_source_keyguard.py   # Source code API key pattern scan
```

## Test Structure

**Suite Organization:**

Test classes group related test methods by feature/class:

```python
class TestPdfOpen:
    """PDF ファイルの読み込みテスト"""
    
    def test_open_valid_pdf(self, sample_pdf):
        """正常な PDF を開ける"""
    
    def test_open_nonexistent_file_raises(self, tmp_path):
        """存在しないファイルを開くとエラー"""


class TestPdfSave:
    """PDF ファイルの保存テスト"""
    
    def test_save_new_file(self, sample_pdf_doc, tmp_path):
        """新しいファイルとして保存できる"""
```

**Setup & Teardown:**
- pytest fixtures used for setup (e.g., `@pytest.fixture()`)
- Fixtures handle cleanup with `yield` pattern or context managers
- `conftest.py` defines shared fixtures available across all tests

**Example Fixture (Generator Pattern):**
```python
@pytest.fixture()
def sample_pdf_doc():
    """テスト用の3ページPDFをメモリ上で生成し、fitz.Document として返す。
    テスト終了後に自動でクローズされる。
    """
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc  # Test receives doc
    doc.close()  # Cleanup after test
```

**Assertion Patterns:**

```python
# Equality
assert len(doc) == 3
assert os.path.exists(save_path)
assert "Page 1" in text

# Exception raising
with pytest.raises(FileNotFoundError):
    fitz.open(nonexistent)

with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
    fitz.open(path)

# Membership & attributes
assert "text-abc" in result
assert issubclass(OCRProvider, abc.ABC)
assert pm.plugins == {}

# String operations
assert result.startswith("data:image/png;base64,")
assert "Modified" in text
```

## Fixtures

**Shared Fixtures (in `conftest.py`):**

| Fixture | Purpose | Type |
|---------|---------|------|
| `tmp_settings` | Temp settings JSON file path + write function | Tuple `(Path, callable)` |
| `sample_pdf` | 3-page test PDF, saved to temp path | String (filepath) |
| `sample_pdf_doc` | 3-page PDF as `fitz.Document` in memory | `fitz.Document` (auto-closed) |
| `large_pdf_doc` | 47-page PDF for window boundary tests | `fitz.Document` (auto-closed) |
| `multi_pdf_files` | 3 PDFs (1/2/3 pages) in temp dir | List of paths |

**Fixture Usage:**
```python
def test_save_preserves_content(self, sample_pdf_doc, tmp_path):
    """sample_pdf_doc and tmp_path are injected by pytest"""
    save_path = str(tmp_path / "saved.pdf")
    sample_pdf_doc.save(save_path)
    # Test uses both fixtures
```

## Mocking

**Framework:** `unittest.mock` from standard library

**Patterns:**

*Monkeypatch (preferred for simple value replacement):*
```python
def test_discover_from_directory(self, tmp_path, monkeypatch):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    # Replace function with temp value
    monkeypatch.setattr(_plugins_mod, "_get_plugins_dir", lambda: str(plugins_dir))
    pm = pagefolio.PluginManager()
    found = pm.discover_plugins()
```

*Fake Response Objects (for HTTP/socket mocking):*
```python
class _FakeResponse:
    """urllib.request.urlopen の文脈マネージャーをモック"""
    
    def __init__(self, body):
        self._body = body.encode("utf-8") if isinstance(body, str) else body
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        return False
    
    def read(self):
        return self._body

def test_lmstudio_payload(self, monkeypatch):
    p = LMStudioProvider(url="http://x", model="m")
    monkeypatch.setattr("urllib.request.urlopen", 
                       lambda req, timeout=None: _FakeResponse(json_body))
```

*Subclass Mocking (for abstract base classes):*
```python
class FakeProvider(OCRProvider):
    """run_parallel テスト用の偽 Provider"""
    
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
- External services (HTTP, sockets) → use fake response classes
- File system → use `tmp_path` fixture
- Module-level functions → use `monkeypatch.setattr()`
- Abstract methods → subclass and implement

**What NOT to Mock:**
- PyMuPDF (`fitz`) operations — test with real PDF objects in memory
- Settings I/O — use real JSON write in temp directory
- Plugin loading — actually load test plugin files from temp directory
- OCR provider logic — test directly with fake data, not mocked calls

## Test Types

**Unit Tests:**
- Scope: Single function or method
- Approach: Isolate pure logic (e.g., `resolve_ocr_prompt()`, `parse_markdown()`)
- Location: `test_ocr.py` (OCR utilities), `test_pagination.py` (window calculations), `test_md_render.py` (markdown parsing)
- Example: `TestPageToPngB64.test_returns_valid_base64_png()` — verifies PNG encoding

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Test with real fixtures (actual PDFs, real settings JSON)
- Location: `test_pdf_ops.py` (open + save workflow), `test_plugins.py` (discovery + load + unload)
- Example: `TestPdfSave.test_save_preserves_content()` — open PDF, modify, save, re-open, verify

**Stress/Memory Tests:**
- Scope: Behavior under heavy load or repeated operations
- Approach: Large datasets (120-page PDFs), many cycles (25+ repeat operations)
- Location: `test_undo_stress.py` — Undo/Redo across 120 pages with memory validation
- Example: Verify Blob disposal, deque eviction, no file leaks

**Regression Tests:**
- Scope: Language key parity, API key safety, source code scans
- Approach: Automated consistency checks
- Location: `test_lang_parity.py`, `test_settings_keyguard.py`, `test_source_keyguard.py`
- Example: Ensure all `LANG["ja"]` keys exist in `LANG["en"]`

**E2E / Dialog Tests:**
- Scope: Not formally used (Tkinter makes it difficult)
- Approach: Manual testing or `test_provider_ui.py` mocking dialog state
- Note: Dialog logic tested via callback function mocking, not window interaction

## Common Patterns

**Async/Threading Testing:**

Most threading is tested via callback mocking rather than actual thread execution:

```python
def test_concurrent_calls_use_threadpool(self, monkeypatch):
    """Verify ThreadPoolExecutor.map is called with correct concurrency"""
    calls = []
    
    def fake_map(fn, items):
        calls.append(("map", len(items)))
        return [fn(item) for item in items]
    
    monkeypatch.setattr(ThreadPoolExecutor, "map", fake_map)
    # Now test actual code that uses ThreadPoolExecutor
```

OCR dialog's `_run_gen()` method tested by checking state updates without actually running threads:

```python
def test_ocr_dialog_generation_guard(self, monkeypatch):
    """_run_gen prevents stale results from overwriting newer ones"""
    # Mock OCR execution
    # Verify only latest generation result is applied
```

**Error Testing:**

```python
def test_open_nonexistent_file_raises(self, tmp_path):
    """存在しないファイルを開くとエラー"""
    with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
        fitz.open(str(tmp_path / "nonexistent.pdf"))

def test_ocr_api_key_missing_raises(self):
    """API キーが見つからない場合は OCRAPIKeyError を発生"""
    from pagefolio.ocr_providers import OCRAPIKeyError
    
    with pytest.raises(OCRAPIKeyError) as exc_info:
        # Code that tries to read missing API key
    
    assert exc_info.value.env_var == "EXPECTED_KEY"
    assert "EXPECTED_KEY" in str(exc_info.value)
```

**Parametrized Tests:**

```python
@pytest.mark.parametrize("theme,expected", [
    ("dark", {"BG_DARK": "#1a1a2e", ...}),
    ("light", {"BG_DARK": "#f0f0f5", ...}),
])
def test_theme_colors(theme, expected):
    """Each theme applies correct color palette"""
    _apply_theme(theme)
    for key, val in expected.items():
        assert C[key] == val
```

**State Isolation:**

Each test starts with clean state:
- New `fitz.Document` per test (not shared)
- New temp directory per test (via `tmp_path`)
- New settings dict per test (via `tmp_settings` fixture)
- Plugin manager fresh instance per test

## Coverage

**Requirements:** No enforced minimum (project uses coverage for awareness, not gating)

**View Coverage:**
```bash
pytest --cov=pagefolio --cov-report=term-missing
pytest --cov=pagefolio --cov-report=html  # Generates htmlcov/index.html
```

**Current Focus Areas:**
- Core PDF operations: `test_pdf_ops.py` (95%+ coverage)
- Pure utility functions: `test_ocr.py`, `test_pagination.py`, `test_md_render.py` (high coverage)
- Plugin system: `test_plugins.py` (comprehensive)
- Undo/Redo: `test_undo_stress.py` (detailed stress testing)
- Settings & safety: `test_settings_keyguard.py`, `test_source_keyguard.py` (100% critical)

**Not Covered (By Design):**
- Full UI interaction (Tkinter makes this expensive; tested manually)
- Thread-heavy OCR dialog (mocked or stubbed; real integration via manual QA)
- External API integrations (Claude, Gemini, LM Studio) — tested with fake providers

## Test Data

**PDF Fixtures:**
- `sample_pdf`: 3-page A4 PDF with simple text, ~20KB
- `sample_pdf_doc`: Same as `sample_pdf` but as in-memory `fitz.Document`
- `large_pdf_doc`: 47-page PDF for pagination boundary tests
- `multi_pdf_files`: [1-page, 2-page, 3-page] PDFs for merge/insert tests
- `stress_pdf_bytes`: 120-page PDF with noise images (≈64KiB per page) for Undo/Redo stress testing

**Settings Fixtures:**
- `tmp_settings`: Tuple of (temp path to JSON, write function) for safe settings I/O testing

**Generate Test Data:**
All fixtures use `fitz.open()` to generate PDFs in memory:
```python
doc = fitz.open()  # Create blank PDF
for i in range(3):
    page = doc.new_page(width=595, height=842)  # A4 size
    page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
data = doc.tobytes()  # Serialize to bytes
doc.close()
```

## Best Practices

**1. Use Fixtures for Setup**
Always use pytest fixtures for setup, not class-level setup methods. This ensures test isolation.

**2. Name Tests Clearly**
Test names should describe the scenario and expected behavior: `test_rotate_90`, `test_open_nonexistent_file_raises`

**3. One Assertion Per Test** (where practical)
Each test should verify one specific behavior. Use multiple test methods for different scenarios.

**4. Avoid Test Interdependence**
Each test should be runnable independently; don't rely on test execution order.

**5. Use `tmp_path` for File I/O**
Never write to the actual project directory or user's home; always use `tmp_path` fixture.

**6. Mock External Services**
For HTTP/socket calls, use fake response objects; never make real network calls in tests.

**7. Test Edge Cases**
Include tests for boundary conditions (empty input, max size, error cases).

**8. Comment Complex Assertions**
If test logic is non-obvious, add a comment explaining what is being verified.

---

*Testing analysis: 2026-07-03*
