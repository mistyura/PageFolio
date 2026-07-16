# Testing Patterns

**Analysis Date:** 2026-07-16

## Test Framework

**Runner:**
- Framework: pytest (installed, configured in `pyproject.toml`)
- Configuration file: `pyproject.toml` with section `[tool.pytest.ini_options]`
- Test discovery: All files matching `test_*.py` in `tests/` directory
- Python path: `pythonpath = ["src"]` configured for imports

**Run Commands:**
```bash
pytest                  # Run all tests in tests/ directory
pytest tests/          # Explicit test directory
pytest tests/test_ocr_engine.py  # Run specific test file
pytest -v              # Verbose output with test names
pytest -k keyword      # Run tests matching keyword pattern
pytest --tb=short      # Shorter traceback format
```

**No built-in watch mode:** Pytest doesn't have native watch/re-run; manually re-run pytest on file changes

## Test File Organization

**Location:**
- Test files co-located in `tests/` directory parallel to `pagefolio/` package
- Structure: `tests/test_<module_name>.py` mirrors `pagefolio/<module_name>.py`

**Naming Convention:**
- Test files: `test_module_name.py` (e.g., `test_ocr_engine.py`, `test_pagination.py`)
- Test classes: `Test<Feature>` (e.g., `TestOCRRunEngineUnit`, `TestWindowBounds`, `TestConsumeOne`)
- Test methods: `test_<behavior>` (e.g., `test_single_page_success_invokes_on_success()`, `test_exact_divisible_last_window()`)

**Structure by focus:**
```
tests/
├── conftest.py                    # Shared fixtures for all tests
├── test_pdf_ops.py               # PDF reading/writing/manipulation
├── test_ocr_engine.py            # OCR execution engine
├── test_ocr_pipeline.py          # Producer-consumer queue logic
├── test_pagination.py            # Window/index conversion
├── test_ocr.py                   # OCR provider selection and API
├── test_plugins.py               # Plugin system
└── ...
```

## Test Structure

**Suite Organization:**
```python
class TestFeatureName:
    """Short description of what this test class verifies.
    
    Reference: D-05, V180-ROBUST-02 (design decision or issue number)
    """

    def test_specific_behavior(self):
        """One sentence describing the assertion."""
        # Arrange
        given = setup_test_data()
        
        # Act
        result = function_under_test(given)
        
        # Assert
        assert result == expected_value
```

**Patterns:**
- **Setup:** Fixtures provide common test data (`sample_pdf`, `sample_pdf_doc`, `multi_pdf_files`)
- **Arrangement:** Use `given` or descriptive variable names for inputs
- **Execution:** Call function once per test
- **Assertion:** Use simple `assert` statements; pytest reports details

**Example from test_pagination.py:**
```python
class TestWindowBounds:
    """SC1: 件数で窓を区切り、最終窓の端数を実ページ数でクランプする（D-10）。"""

    def test_fraction_last_window(self):
        # 端数最終窓・D-10: 件数 20・全 47 → 最終窓 (40, 47)
        assert window_bounds(40, 20, 47) == (40, 47)

    def test_doc_not_open(self):
        # doc 未オープン
        assert window_bounds(0, 20, 0) == (0, 0)
```

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**
```python
from unittest.mock import patch, MagicMock

# Mock external dependencies
with patch('pagefolio.module.external_func') as mock_func:
    mock_func.return_value = expected_value
    result = function_under_test()
    assert mock_func.called

# Mock class for test doubles
class FakeProvider:
    def ocr_image(self, b64_png, prompt, **kwargs):
        return f"text-{b64_png}"
    
    def list_models(self):
        return ["fake-model"]
```

**What to Mock:**
- External API calls (Claude, Gemini, RunPod endpoints)
- File I/O operations when not testing file handling itself
- Long-running operations (use side_effect for controllable responses)
- System-level operations (os.startfile for printing)

**What NOT to Mock:**
- `fitz.Document` - Create real PDF objects via fixtures (cheaper than mocking)
- Internal pagefolio functions - Test integration paths
- Standard library modules (`logging`, `json`, `os` path operations) - Let them run
- Pure function logic - No mocking needed, just data

**Example: OCR provider testing (test_ocr_providers.py):**
```python
class FakeProvider(OCRProvider):
    """Fake OCR provider for testing.
    
    Mock side_effect can be set to simulate success, failure, or retry scenarios.
    """
    def __init__(self, side_effect=None):
        self._side_effect = side_effect

    def ocr_image(self, b64_png, prompt, **kwargs):
        if self._side_effect is not None:
            return self._side_effect(b64_png, prompt)
        return f"text-{b64_png}"

    def list_models(self):
        return ["fake-model"]

# Usage in test
def test_retry_on_retryable_error():
    def side_effect(b64, prompt):
        # Simulate API timeout
        raise OCRRetryableError("timeout")
    
    provider = FakeProvider(side_effect=side_effect)
    # Test retry logic...
```

## Fixtures and Factories

**Test Data Fixtures (in conftest.py):**

| Fixture | Purpose | Returns | Setup |
|---------|---------|---------|-------|
| `tmp_settings` | Temporary settings file | `(path, write_fn)` tuple | Creates JSON file in tmp_path |
| `sample_pdf` | 3-page test PDF | File path (str) | Generated in-memory, saved to disk |
| `sample_pdf_doc` | 3-page PDF in memory | `fitz.Document` | Yields doc, closes on cleanup |
| `large_pdf_doc` | 47-page PDF for boundary tests | `fitz.Document` | Yields doc, closes on cleanup |
| `multi_pdf_files` | Multiple PDFs for merge testing | List of 3 file paths | Each has 1–3 pages |

**Fixture Usage:**
```python
class TestPageRotate:
    def test_rotate_90(self, sample_pdf_doc):
        """Test uses fixture by parameter name."""
        page = sample_pdf_doc[0]
        page.set_rotation((page.rotation + 90) % 360)
        assert page.rotation == 90
```

**Factories (custom generators):**
- Not used extensively; prefer fixtures
- Some tests create custom FakeProvider instances with different side_effects

## Coverage

**Requirements:** No explicit enforced target in configuration

**View Coverage:**
- Coverage reporting not configured in `pyproject.toml`
- To measure: `pip install pytest-cov && pytest --cov=pagefolio tests/`

**Gap Analysis:**
- Tkinter UI code (`app.py`, dialogs) has minimal unit test coverage (requires mocking Tk widgets)
- Pure function layers (`pagination.py`, `ocr_pipeline.py`, `md_render.py`) have high coverage
- OCR provider tests are comprehensive (mocked API responses)
- File I/O operations use real PDF fixtures (integration-style tests)

## Test Types

**Unit Tests:**
- Scope: Single function or method in isolation
- Examples: `test_pagination.py` (pure functions), `test_ocr_pipeline.py` (PipelineState logic)
- Use mocks for external dependencies and side effects
- Fast execution (no I/O, no threading)

**Integration Tests:**
- Scope: Multiple components working together
- Examples: `test_pdf_ops.py` (PDF reading/writing), `test_ocr.py` (provider selection + fallback)
- Use real `fitz.Document` objects and temporary files
- Test actual file operations, not mocked equivalents

**System/E2E Tests:**
- Scope: Full workflow (OCR dialog, batch processing, plugin loading)
- Examples: `test_batch_ocr_dialog.py` (dialog lifecycle + OCR pipeline)
- Limited coverage due to Tkinter UI complexity
- Some tests use mocking for API calls while exercising real dialog flow

**Threading Tests:**
- Scope: Concurrent operations (OCR queue consumption, sentinel signaling)
- Examples: `test_ocr_engine.py` (thread start/join), `test_ocr_pipeline.py` (queue operations)
- Use `threading.Event`, `time.sleep()`, and careful timing checks
- Timeout guards to prevent test hangs: `deadline = time.monotonic() + timeout`

## Common Patterns

**Async Testing (with threading):**
```python
def test_single_page_success_invokes_on_success(self):
    """Test callback invoked once after OCR success."""
    provider = FakeProvider()
    cancel_flag = threading.Event()
    successes = []
    engine = OCRRunEngine(
        provider=provider,
        prompt="prompt",
        run_pages=[0],
        concurrency=1,
        cancel_flag=cancel_flag,
        on_success=lambda p, t, tr: successes.append((p, t, tr)),
    )
    threads = engine.start()
    
    # Manually enqueue items (simulate producer)
    assert try_enqueue(engine.queue, (0, "b64-0")) is True
    assert send_sentinels(engine.queue, 1) == 1
    
    # Wait for consumer threads to finish
    for t in threads:
        t.join(timeout=2.0)
    
    # Assert side effect occurred
    assert len(successes) == 1
    assert successes[0] == (0, "text-b64-0", False)
```

**Error Testing:**
```python
def test_nonexistent_file_raises(self, tmp_path):
    """Verify that opening nonexistent file raises FileNotFoundError."""
    with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
        fitz.open(str(tmp_path / "nonexistent.pdf"))
```

**Parametrized Testing:**
```python
class TestIndexConvert:
    def test_invariant_lo_hi_range(self):
        """Boundary check: 0 <= lo <= hi <= n_pages, hi - lo <= page_size."""
        for n in (0, 1, 20, 40, 47, 100):
            for size in (10, 20, 50):
                for start in (0, size, size * 2, size * 3):
                    lo, hi = window_bounds(start, size, n)
                    assert 0 <= lo <= hi <= n
                    assert hi - lo <= size
```

**Fixture with cleanup:**
```python
@pytest.fixture()
def sample_pdf_doc():
    """3-page PDF: open, use in test, close automatically."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc  # Test runs here
    doc.close()  # Cleanup after test
```

## Special Test Patterns

**Decision Coverage Testing:**
- Test class names map to design decisions (e.g., `TestWindowBounds=SC1`, `TestDndIndexConvert=SC3`)
- References to decision docs (D-05, D-10, D-11, etc.) in docstrings
- Each test method verifies one acceptance criterion (one behavior, one assertion focus)
- Boundary conditions tested explicitly (e.g., "window boundary at edge", "single page", "doc not open")

**Pure Function Testing:**
- No mocks, no side effects, no state mutation
- Input → Output verification only
- Examples: `test_pagination.py`, `test_ocr_pipeline.py` (PipelineState unit tests)
- These tests are reliable and fast

**Producer-Consumer Testing:**
- Manual queue operations in test setup (simulate producer without threading)
- Consumer thread(s) started via `engine.start()` or similar
- Timeout guards to prevent hangs: `t.join(timeout=2.0)`
- Example: `test_ocr_engine.py` helper `_send_all_sentinels(q, count, timeout=5.0)`

---

*Testing analysis: 2026-07-16*
