# Testing Patterns

**Analysis Date:** 2026-07-22

## Test Framework

**Runner:**
- pytest (configured in `pyproject.toml`)
- Test path: `tests/`
- Python path: `["src"]` in pytest config

**Assertion Library:**
- Python's built-in `assert` statements
- S101 (assert usage) disabled in `tests/**/*.py` via ruff config

**Run Commands:**
```bash
pytest                          # Run all 1109 tests
pytest tests/test_ocr.py        # Run specific test file
pytest -v                       # Verbose output
pytest --collect-only           # List tests without running
pytest -k "test_window"         # Run tests matching pattern
```

**Coverage:**
```bash
# Generate coverage report
pytest --cov=pagefolio --cov-report=html

# View .coverage file created after test run
# Coverage tracking enabled via .coverage file in repo root
```

## Test File Organization

**Location:**
- Co-located in `tests/` directory (separate from `pagefolio/` source)
- Test discovery via `tests` directory specified in `pyproject.toml`

**Naming:**
- Test files: `test_*.py` (e.g., `test_ocr.py`, `test_pagination.py`)
- Test classes: `Test*` (e.g., `TestWindowBounds`, `TestPdfOpen`)
- Test methods: `test_*` (e.g., `test_returns_valid_base64_png`, `test_connection_error_raises_connection_error`)

**File Structure:**
```
tests/
├── conftest.py                  # Shared fixtures
├── test_ocr.py
├── test_pagination.py
├── test_pdf_ops.py
├── test_password.py
├── test_plugins.py
├── test_batch_ocr_dialog.py
└── ... (35 test files total, 1109 tests)
```

## Test Structure

**Suite Organization (from `conftest.py`):**
```python
class TestPageToPngB64:
    """page_to_png_b64 が有効な base64 PNG を返すか"""

    def test_returns_valid_base64_png(self, sample_pdf_doc):
        page = sample_pdf_doc[0]
        b64 = ocr.page_to_png_b64(page, scale=1.0)
        assert isinstance(b64, str)
        raw = base64.b64decode(b64)
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
```

**Patterns:**
- Test classes group related tests (one logical area)
- Docstrings explain test purpose at class level
- Fixtures injected as method parameters
- Arrange-Act-Assert structure (implicit via test flow)

**Setup/Teardown:**
- Setup via fixtures (preferring fixtures over `setup_method()`)
- Teardown via pytest fixture `yield` pattern (e.g., `sample_pdf_doc` fixture yields then closes document)
- Temporary files via `tmp_path` fixture (automatic cleanup)

**Example with yield (cleanup):**
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
    yield doc
    doc.close()
```

## Mocking

**Framework:** `monkeypatch` (pytest fixture)

**Patterns:**
```python
def test_success_returns_content(self, monkeypatch):
    import pagefolio.ocr_providers as op
    
    p = LMStudioProvider(url="http://localhost:1234", model="m", timeout=5)
    
    def fake_urlopen(req, timeout=None):
        captured = {}
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        body = json.dumps({"choices": [{"message": {"content": "hello world"}}]})
        return _FakeResponse(body)
    
    monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
    text = p.ocr_image("Zg==", "p")
    assert text == "hello world"
```

**What to Mock:**
- External network calls (urllib.request, API clients)
- File system operations (when testing logic, not file I/O)
- Time-dependent operations (via mocking time module)
- Platform-specific behavior (e.g., Windows API calls)

**What NOT to Mock:**
- fitz Document/Page objects (use real test PDFs from fixtures instead)
- Tkinter widgets (tests avoid UI layer when possible; use headless fixtures)
- Pure functions that have no side effects
- Standard library functions (except for network/time)

**Test Double Pattern:**
```python
class FakeProvider(OCRProvider):
    """run_parallel テスト用の偽 Provider。ocr_image は b64 をもとにテキストを返す。"""

    default_concurrency = 2
    max_concurrency = 4

    def __init__(self, side_effect=None):
        """side_effect が None なら f"text-{b64}" を返す。callable なら呼び出す。"""
        self._side_effect = side_effect

    def ocr_image(self, b64_png, prompt, **kwargs):
        if self._side_effect is not None:
            return self._side_effect(b64_png, prompt)
        return f"text-{b64_png}"

    def list_models(self):
        return ["fake-model"]
```

## Fixtures and Factories

**Test Data (from `conftest.py`):**

**`sample_pdf` fixture:**
```python
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
```

**`sample_pdf_doc` fixture:**
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
    yield doc
    doc.close()
```

**`large_pdf_doc` fixture (for pagination boundary tests):**
```python
@pytest.fixture()
def large_pdf_doc():
    """窓化境界値テスト用の 47 ページ PDF を fitz.Document として返す。
    件数 20 → 最終窓 41–47（端数最終窓・D-10）の境界値検証に対応する。
    """
    doc = fitz.open()
    for i in range(47):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc
    doc.close()
```

**`multi_pdf_files` fixture:**
```python
@pytest.fixture()
def multi_pdf_files(tmp_path):
    """結合・挿入テスト用に複数のPDFファイルを生成する。
    返り値は [path1, path2, path3] のリスト。
    """
    paths = []
    for idx in range(3):
        doc = fitz.open()
        n_pages = idx + 1  # 1ページ, 2ページ, 3ページ
        for p in range(n_pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"File{idx + 1} Page{p + 1}", fontsize=20)
        path = str(tmp_path / f"file_{idx + 1}.pdf")
        doc.save(path)
        doc.close()
        paths.append(path)
    return paths
```

**`tmp_settings` fixture:**
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
```

**Location:**
- All fixtures defined in `tests/conftest.py`
- Auto-discovered by pytest; available to all test modules

## Coverage

**Requirements:** No explicit coverage threshold enforced

**View Coverage:**
```bash
pytest --cov=pagefolio --cov-report=html
# Opens htmlcov/index.html in browser
```

**Current state:** 1109 tests collected, .coverage file tracked in `.gitignore`

## Test Types

**Unit Tests:**
- Scope: Individual functions/methods in isolation
- Approach: Test with fixtures, mocking external dependencies
- Examples: `test_pagination.py` (pure functions), `test_pdf_ops.py` (fitz operations)
- Patterns:
  ```python
  def test_to_global_basic(self):
      assert to_global(3, 20) == 23
      assert to_global(0, 0) == 0
  ```

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Use real fitz documents and settings files
- Examples: `test_ocr_pipeline.py` (OCR flow), `test_batch_ocr_dialog.py` (batch operations)
- Pattern: Test full workflows (open PDF → rotate → crop → save)

**E2E Tests:**
- Scope: Full application workflows
- Framework: Not formalized (Tkinter UI testing is complex)
- Approach: Primarily integration tests serve as pseudo-E2E tests
- Note: UI interactions tested manually or via plugin system

## Common Patterns

**Async Testing:**
Tk applications use `root.after()` for deferred callbacks; testing doesn't explicitly use async but:
```python
# Generation counters prevent stale results
if self._preview_gen < generation:
    return  # Discard if newer result came in

# Tests verify logic without UI thread
```

**Error Testing:**
```python
def test_connection_error_raises_connection_error(self, monkeypatch):
    import pagefolio.ocr_providers as op

    p = LMStudioProvider(url="http://x", model="m")

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ConnectionError):
        p.ocr_image("Zg==", "p")
```

**Boundary/Property Testing:**
```python
class TestWindowBounds:
    """SC1: 件数で窓を区切り、最終窓の端数を実ページ数でクランプする（D-10）。"""

    def test_invariant_lo_hi_range(self):
        # 0 <= lo <= hi <= n_pages、hi - lo <= page_size
        for n in (0, 1, 20, 40, 47, 100):
            for size in (10, 20, 50):
                for start in (0, size, size * 2, size * 3):
                    lo, hi = window_bounds(start, size, n)
                    assert 0 <= lo <= hi <= n
                    assert hi - lo <= size
```

**Round-trip Testing (Invariants):**
```python
def test_round_trip_global_local_global(self):
    # 任意 g（0..n-1）と任意 start で to_global(to_local(g, start), start) == g
    n = 47
    for g in range(n):
        for start in (0, 20, 40):
            assert to_global(to_local(g, start), start) == g
```

---

*Testing analysis: 2026-07-22*
