# Phase 1: 基盤分割（肥大モジュールリファクタリング） - Pattern Map

**Mapped:** 2026-07-13
**Files analyzed:** 13 新規/変更ファイル
**Analogs found:** 13 / 13（全ファイルに既存前例あり — 純粋リファクタリングフェーズのため新規パターンなし）

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pagefolio/ocr_providers/__init__.py` | config（re-export集約） | request-response | `pagefolio/dialogs/__init__.py` | exact |
| `pagefolio/ocr_providers/base.py` | service（抽象基底+共有ヘルパー） | request-response | `pagefolio/ocr_providers.py:1-246`（現行の共有基盤部） | exact（同一ファイルの分割元） |
| `pagefolio/ocr_providers/errors.py` | utility（例外クラス+純関数） | transform | `pagefolio/ocr_providers.py:138-246`（例外3種+ヘルパー） | exact |
| `pagefolio/ocr_providers/registry.py` | utility（宣言的レジストリ・新設） | transform | `pagefolio/pagination.py`（純ロジック層の前例） / `pagefolio/settings.py:23-34`（現行 _SENSITIVE_KEYS） | role-match（新設だが層の前例あり） |
| `pagefolio/ocr_providers/lmstudio.py` | service（OCRProvider実装） | request-response | `pagefolio/ocr_providers.py:249-424`（LMStudioProvider） | exact |
| `pagefolio/ocr_providers/claude.py` | service（OCRProvider実装） | request-response | `pagefolio/ocr_providers.py:425-752`（ClaudeProvider） | exact |
| `pagefolio/ocr_providers/gemini.py` | service（OCRProvider実装） | request-response | `pagefolio/ocr_providers.py:753-1022`（GeminiProvider） | exact |
| `pagefolio/ocr_providers/tesseract.py` | service（OCRProvider実装+検出関数） | request-response | `pagefolio/ocr_providers.py:1023-1168`（_detect_tesseract+TesseractProvider） | exact |
| `pagefolio/ocr_providers/ollama.py` | service（OCRProvider実装） | request-response | `pagefolio/ocr_providers.py:1169-1345`（OllamaProvider） | exact |
| `pagefolio/ocr_providers/runpod.py` | service（OCRProvider実装） | request-response | `pagefolio/ocr_providers.py:1346-1537`（RunPodProvider） | exact |
| `pagefolio/dialogs/llm_config/__init__.py` | config（re-export+多重継承統合） | request-response | `pagefolio/app.py:107-117`（PDFEditorApp 8 Mixin 構成） | exact |
| `pagefolio/dialogs/llm_config/dialog.py` | component（DialogMixin: __init__/_apply/_on_*） | event-driven | `pagefolio/dialogs/llm_config.py:36-101,1097-1300,1554-1659` | exact（同一ファイルの分割元） |
| `pagefolio/dialogs/llm_config/sections.py` | component（SectionsMixin: _build UI構築） | event-driven | `pagefolio/dialogs/llm_config.py:177-1096`（_build） | exact |
| `pagefolio/dialogs/llm_config/model_fetch.py` | component（ModelFetchMixin: 非同期取得） | event-driven | `pagefolio/dialogs/llm_config.py:1301-1553`（_fetch_models_async+probe/refresh群） | exact |
| `pagefolio/settings.py`（変更） | config | transform | 同ファイル現行 `_SENSITIVE_KEYS`（settings.py:23-34） | exact |
| `pagefolio/ocr.py`（変更） | service | request-response | 同ファイル現行 `_resolve_api_key`（ocr.py:208-267） | exact |
| `pagefolio/ocr_dialog.py`（変更） | component | request-response | 同ファイル現行 `_check_cloud_api_key`（ocr_dialog.py:1244-1280付近） | exact |
| `tests/test_imports.py`（拡張） | test | request-response | 同ファイル `TestDialogsImports`（test_imports.py:84-175） | exact |
| `tests/test_settings_keyguard.py`（拡張） | test | request-response | 同ファイル `TestSensitiveKeysConstant`（test_settings_keyguard.py:12-34） | exact |

## Pattern Assignments

### `pagefolio/ocr_providers/__init__.py`（config, request-response）

**Analog:** `pagefolio/dialogs/__init__.py`（DEBT-01 前例・完成済み）

**現物パターン（全文・17行）:**
```python
# Source: pagefolio/dialogs/__init__.py
"""pagefolio.dialogs — 後方互換の再エクスポート集約

既存の `from pagefolio.dialogs import AboutDialog, SettingsDialog, ...` を
サブパッケージ化後も維持するための再エクスポートモジュール。
"""

from pagefolio.dialogs.about import AboutDialog  # noqa: F401
from pagefolio.dialogs.export_images import ExportImagesDialog  # noqa: F401
from pagefolio.dialogs.llm_config import LLMConfigDialog  # noqa: F401
from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog  # noqa: F401
from pagefolio.dialogs.password import SetPasswordDialog  # noqa: F401
from pagefolio.dialogs.plugin import PluginDialog  # noqa: F401
from pagefolio.dialogs.settings import SettingsDialog  # noqa: F401
from pagefolio.dialogs.shortcuts import ShortcutsDialog  # noqa: F401
```

**このファイルへの適用（RESEARCH.md で全17シンボル精査済み・そのままコピー可）:**
```python
from pagefolio.ocr_providers.base import (  # noqa: F401
    OCRProvider,
    _ALLOWED_URL_SCHEMES,
    _require_http_scheme,
)
from pagefolio.ocr_providers.errors import (  # noqa: F401
    OCRAPIKeyError,
    OCRRetryableError,
    OCRContextLengthError,
    _CONTEXT_ERROR_MARKERS,
    _retryable_http_message,
    parse_retry_after,
    looks_like_context_error,
    _raise_mapped_http_error,
)
from pagefolio.ocr_providers.lmstudio import LMStudioProvider  # noqa: F401
from pagefolio.ocr_providers.claude import ClaudeProvider  # noqa: F401
from pagefolio.ocr_providers.gemini import GeminiProvider  # noqa: F401
from pagefolio.ocr_providers.tesseract import (  # noqa: F401
    TesseractProvider,
    _detect_tesseract,
)
from pagefolio.ocr_providers.ollama import OllamaProvider  # noqa: F401
from pagefolio.ocr_providers.runpod import RunPodProvider  # noqa: F401
```

**重要:** 主要クラスだけでなく private ヘルパー（`_require_http_scheme`・`parse_retry_after`・`looks_like_context_error`・`_raise_mapped_http_error`・`_detect_tesseract` 等）も全て re-export すること。`tests/test_ocr_providers.py` がこれらを直接 `from pagefolio.ocr_providers import ...` している（D-03 により無修正のまま通す必要あり）。

---

### `pagefolio/ocr_providers/base.py` / `errors.py`（service/utility, request-response/transform）

**Analog:** `pagefolio/ocr_providers.py:1-246`（現行の共有基盤部・分割元そのもの）

**移動元マッピング（機械的移動・Claude's Discretion の配置以外は固定）:**
- `base.py`: `_ALLOWED_URL_SCHEMES`（20行）・`_require_http_scheme`（23-38行）・`OCRProvider` ABC（41-135行）
- `errors.py`: `OCRAPIKeyError`（138-143行）・`OCRRetryableError`（146-156行）・`_retryable_http_message`（159-167行）・`OCRContextLengthError`（170-176行）・`_CONTEXT_ERROR_MARKERS`（182-191行）・`parse_retry_after`（194-206行）・`looks_like_context_error`（209-218行）・`_raise_mapped_http_error`（221-246行）

**imports パターン（現行ファイル冒頭・両ファイルで必要な分だけ分配）:**
```python
# Source: pagefolio/ocr_providers.py:1-16
import abc
import base64
import json
import logging
import socket
import subprocess
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit

logger = logging.getLogger(__name__)
```

**エラー変換パターン（`_raise_mapped_http_error`・全プロバイダ共通）:**
```python
# Source: pagefolio/ocr_providers.py:221-246
def _raise_mapped_http_error(e):
    if e.code == 429 or e.code >= 500:
        raise OCRRetryableError(
            _retryable_http_message(e.code),
            retry_after=parse_retry_after(e.headers),
            code=e.code,
        ) from e
    try:
        err_body = e.read().decode("utf-8", errors="replace")
    except Exception:
        err_body = ""
    err_body = err_body[:500]
    message = f"HTTP {e.code}: {err_body or e.reason}"
    if looks_like_context_error(e.code, err_body):
        raise OCRContextLengthError(message) from e
    raise RuntimeError(message) from e
```
`errors.py` から `base.py` の `OCRProvider` は参照しない（独立関数群）。`errors.py` → `base.py` の import 方向は不要、両者は互いに依存しない設計にできる（`base.py` の `OCRProvider.ocr_image_ex`/docstring がエラー3種の名前に言及するのみ）。

---

### `pagefolio/ocr_providers/registry.py`（utility・新設, transform）

**Analog:** `pagefolio/pagination.py`（純ロジック層・Tk/fitz非依存の前例）＋現行 `pagefolio/settings.py:23-34`（`_SENSITIVE_KEYS` の現物）

**現行 `_SENSITIVE_KEYS`（置換対象・現物）:**
```python
# Source: pagefolio/settings.py:23-34
_SENSITIVE_KEYS = {
    "claude_api_key",
    "gemini_api_key",
    "google_api_key",  # WR-03: Gemini フォールバックキー名（小文字）
    "anthropic_api_key",
    "api_key",
    "GEMINI_API_KEY",  # WR-03: 大文字バリアント
    "GOOGLE_API_KEY",  # WR-03: Gemini フォールバックキー名（大文字・D-06）
    "ANTHROPIC_API_KEY",  # WR-03: 大文字バリアント
    "runpod_api_key",  # RunPod APIキー（小文字）
    "RUNPOD_API_KEY",  # RunPod APIキー（大文字）
}
```

**registry.py の実装方針（RESEARCH.md Pattern 3 に完全実装例あり・そのまま採用可）:**
```python
PROVIDER_ENV_KEYS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "runpod": ("RUNPOD_API_KEY",),
}

def primary_env_var(provider_name): ...
def env_vars_for(provider_name): ...
def resolve_env_key(provider_name): ...
def sensitive_keys():
    keys = {"api_key"}
    for provider_name, env_vars in PROVIDER_ENV_KEYS.items():
        keys.add(f"{provider_name}_api_key")
        for var in env_vars:
            keys.add(var)
            keys.add(var.lower())
    return keys
```

**注意（Pitfall 6・循環import回避）:** `settings.py` からは `from pagefolio.ocr_providers.registry import sensitive_keys`（サブモジュール直接指定）で import し、`pagefolio.ocr_providers`（`__init__.py` 経由で全プロバイダを import する重い経路）は経由しない。

---

### `pagefolio/ocr_providers/{lmstudio,claude,gemini,tesseract,ollama,runpod}.py`（service, request-response）

**Analog:** それぞれ `pagefolio/ocr_providers.py` 内の対応クラス行範囲（上表参照）

**方針:** D-02 により**機械的移動のみ**。各ファイルは `base.py`/`errors.py` から必要なシンボルを import する（例: `from pagefolio.ocr_providers.base import OCRProvider, _require_http_scheme`・`from pagefolio.ocr_providers.errors import OCRAPIKeyError, OCRRetryableError, _raise_mapped_http_error`）。共通化・リネーム・最適化は一切行わない。`tesseract.py` のみ `_detect_tesseract()` 関数（1023-1061行）を同居させる。

---

### `pagefolio/dialogs/llm_config/__init__.py`（config, request-response）

**Analog:** `pagefolio/app.py:107-117`（PDFEditorApp 8 Mixin 構成の確立パターン）

**現物パターン:**
```python
# Source: pagefolio/app.py:107-117
class PDFEditorApp(
    UIBuilderMixin,
    FileOpsMixin,
    PageOpsMixin,
    RedactOpsMixin,
    ViewerMixin,
    DnDMixin,
    OCRMixin,
    PrintOpsMixin,
):
    MAX_UNDO = 20

    def __init__(self, root):
        ...
```

**このファイルへの適用（tk.Toplevel の MRO 注意・Pitfall 3）:**
```python
import tkinter as tk

from pagefolio.dialogs.llm_config.dialog import DialogMixin
from pagefolio.dialogs.llm_config.model_fetch import ModelFetchMixin
from pagefolio.dialogs.llm_config.sections import SectionsMixin


class LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel):
    """LLM 設定ダイアログ（OCR と設定で共有）— Mixin 分割後の統合クラス"""
```
`tk.Toplevel` を継承リストの**最後**に置く（既存コードは `class LLMConfigDialog(tk.Toplevel):` で `super().__init__(parent)` を呼ぶため）。`__init__` は `DialogMixin` に集約し、他の Mixin は `__init__` を持たない設計にする。

---

### `pagefolio/dialogs/llm_config/dialog.py`（component, event-driven）

**Analog:** `pagefolio/dialogs/llm_config.py:36-101`（`__init__`）・`1097-1300`（`_on_provider_change`/`_on_model_change`）・`1554-1659`（`_apply`）

**imports パターン（現行ファイル冒頭）:**
```python
# Source: pagefolio/dialogs/llm_config.py:1-27
import logging
import os
import threading
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import CUSTOM_PROMPT_FILE, LANG, SUMMARY_PROMPT_FILE, C
from pagefolio.ocr import MAX_OCR_MAX_TOKENS
from pagefolio.ocr_providers import (
    ClaudeProvider,
    GeminiProvider,
    LMStudioProvider,
    _detect_tesseract,
)
from pagefolio.settings import (
    get_current_font_size,
    load_prompt_file,
    prompt_file_exists,
    save_prompt_file,
)

logger = logging.getLogger(__name__)
```
D-10 によりこれらの import 元パス（`pagefolio.ocr_providers`・`pagefolio.ocr`・`pagefolio.settings`）は変更しない。3つの新 Mixin ファイルそれぞれが必要なサブセットを個別 import する。

**コンストラクタの核心パターン（機械的移動対象・そのまま `DialogMixin.__init__` へ）:**
```python
# Source: pagefolio/dialogs/llm_config.py:49-101
def __init__(
    self, parent, current_settings, on_apply, font_func=None,
    lang="ja", plugin_manager=None, session_api_keys=None,
):
    super().__init__(parent)
    self._L = LANG[lang]
    self.title(self._L["llm_config_title"])
    self.configure(bg=C["BG_DARK"])
    self.resizable(True, True)
    self.minsize(420, 320)
    self.grab_set()
    self.current_settings = dict(current_settings)
    self.on_apply = on_apply
    self._font = font_func or (...)
    self._plugin_manager = plugin_manager
    self._session_api_keys = session_api_keys if session_api_keys is not None else {}
    self._last_valid_provider = current_settings.get("ocr_provider", "off")
    self._tesseract_available, self._tesseract_langs = _detect_tesseract()
    ...
    self._build()  # sections.py の SectionsMixin._build を呼ぶ（Mixin 越し）
```

---

### `pagefolio/dialogs/llm_config/sections.py`（component, event-driven）

**Analog:** `pagefolio/dialogs/llm_config.py:177-1096`（`_build`・約920行）

**方針:** D-05 により機械的移動。`_build` 本体と `_build_scrollable_area`（104-176行）をこの Mixin に集約する。

---

### `pagefolio/dialogs/llm_config/model_fetch.py`（component, event-driven）

**Analog:** `pagefolio/dialogs/llm_config.py:1301-1553`（`_probe_lm_provider`/`_probe_ollama_provider`/`_fetch_models_async`/`_refresh_runpod_models`/`_refresh_claude_models`/`_refresh_gemini_models`）

**共通非同期取得パターン（`_fetch_models_async`）:**
```python
# Source: pagefolio/dialogs/llm_config.py:1386 付近（シグネチャ）
def _fetch_models_async(self, fetch_fn, on_success, on_error):
    """バックグラウンドスレッドで fetch_fn() を実行し、
    結果を self.after() 経由でメインスレッドへ橋渡しする。"""
```
Pitfall（研究由来）: スレッド↔メインスレッドの橋渡し部分のみこの層に残す。実際の HTTP 呼び出しは各 Provider（`ocr_providers/*.py`）の `list_models()` に既に委譲済みであり変更不要。

---

### `pagefolio/settings.py`（変更・D-09統合対象1）

**Analog:** 同ファイル現行 `_SENSITIVE_KEYS` 定義（上記 registry.py セクション参照）

**変更パターン:**
```python
# 変更後（想定）
from pagefolio.ocr_providers.registry import sensitive_keys

_SENSITIVE_KEYS = sensitive_keys()
```
既存 `test_settings_keyguard.py::TestSensitiveKeysConstant` はこの変更後もグリーンで通ること（`_SENSITIVE_KEYS` は `set` のまま・既存要素を全て含む）。

---

### `pagefolio/ocr.py`（変更・D-09統合対象2）

**Analog:** 同ファイル現行 `_resolve_api_key`（208-267行）

**現行パターン（置換対象・claude/gemini/runpod のハードコード分岐）:**
```python
# Source: pagefolio/ocr.py:229-264
if provider_name == "claude":
    env_var = "ANTHROPIC_API_KEY"
    key = session_keys.get("claude", "")
    if key:
        return key
    key = os.environ.get(env_var)
    if key:
        return key
    raise OCRAPIKeyError(env_var)

if provider_name == "gemini":
    key = session_keys.get("gemini", "")
    if key:
        return key
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    raise OCRAPIKeyError("GEMINI_API_KEY")

if provider_name == "runpod":
    env_var = "RUNPOD_API_KEY"
    key = session_keys.get("runpod", "")
    if key:
        return key
    key = os.environ.get(env_var)
    if key:
        return key
    raise OCRAPIKeyError(env_var)
```
**置換方針:** `registry.env_vars_for(provider_name)` を使った優先順ループへ統一。セッションキー優先→環境変数フォールバックの2段構造・Gemini の dual env var 優先順（GEMINI_API_KEY→GOOGLE_API_KEY）は不変で保持すること（D-09）。

---

### `pagefolio/ocr_dialog.py`（変更・D-09統合対象3）

**Analog:** 同ファイル現行 `_check_cloud_api_key`（1244行〜）内の env_var dict

**現行パターン（置換対象）:**
```python
# Source: pagefolio/ocr_dialog.py:1267-1271
env_var = {
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "runpod": "RUNPOD_API_KEY",
}.get(name, "")
```
**置換方針:** `registry.primary_env_var(name)` へ置換（try/except で未知プロバイダは `""` へフォールバック、現行 `.get(name, "")` の挙動を保持）。

---

### `tests/test_imports.py`（拡張・Wave 0 必達）

**Analog:** 同ファイル `TestDialogsImports`（84-175行・完成済みの後方互換テスト集約形式）

**現物パターン（そのまま `TestOcrProvidersImports` として複製すればよい形式）:**
```python
# Source: tests/test_imports.py:84-176
class TestDialogsImports:
    """REFAC-01 — dialogs サブパッケージ分割後の import 検証

    D-08: dialog クラスはインスタンス化せず、シンボル存在のみ確認する。
    """

    def test_dialogs_subpackage_about(self):
        """pagefolio.dialogs から AboutDialog を import できる"""
        from pagefolio.dialogs import AboutDialog
        assert AboutDialog is not None

    def test_individual_module_llm_config(self):
        """dialogs.llm_config から LLMConfigDialog を import できる"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog
        assert LLMConfigDialog is not None

    def test_llm_config_via_dialogs_subpackage(self):
        """pagefolio.dialogs 経由でも LLMConfigDialog を import できる"""
        from pagefolio.dialogs import LLMConfigDialog
        assert LLMConfigDialog is not None
```

**新規追加が必要な `TestOcrProvidersImports`（Wave 0・分割前に赤で追加 → 分割後に緑）:** 上記形式を踏襲し、`ocr_providers/__init__.py` の全17シンボル（Pattern 1参照）それぞれについて「パッケージ直下 import」＋「サブモジュール直接 import」の両方をテストするクラスを追加する。`_require_http_scheme`・`parse_retry_after`・`looks_like_context_error`・`_raise_mapped_http_error`・`_detect_tesseract` 等の private ヘルパーも必ず含める。

---

### `tests/test_settings_keyguard.py`（拡張・Wave 0 必達）

**Analog:** 同ファイル `TestSensitiveKeysConstant`（12-34行）

**現物パターン:**
```python
# Source: tests/test_settings_keyguard.py:9-34
from pagefolio.settings import _SENSITIVE_KEYS, _load_settings, _save_settings

class TestSensitiveKeysConstant:
    """_SENSITIVE_KEYS 定数の構成テスト"""

    def test_is_set(self):
        """_SENSITIVE_KEYS が set として存在する"""
        assert isinstance(_SENSITIVE_KEYS, set)

    def test_contains_claude_key(self):
        assert "claude_api_key" in _SENSITIVE_KEYS

    def test_contains_anthropic_key(self):
        assert "anthropic_api_key" in _SENSITIVE_KEYS

    def test_contains_gemini_key(self):
        assert "gemini_api_key" in _SENSITIVE_KEYS

    def test_contains_generic_api_key(self):
        assert "api_key" in _SENSITIVE_KEYS
```

**新規追加が必要なテスト（Wave 0）:** `from pagefolio.ocr_providers.registry import sensitive_keys` を import し、`sensitive_keys()` の出力が現行10エントリ（`claude_api_key, gemini_api_key, google_api_key, anthropic_api_key, api_key, GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, runpod_api_key, RUNPOD_API_KEY`）を部分集合として含むことを検証する（`set(...) >= {...}`）。

## Shared Patterns

### 後方互換 re-export（DEBT-01/DEBT-02 前例）
**Source:** `pagefolio/dialogs/__init__.py`・`pagefolio/constants.py`
**Apply to:** `ocr_providers/__init__.py`・`dialogs/llm_config/__init__.py` の両方
```python
from pagefolio.lang import LANG  # noqa: F401
from pagefolio.themes import THEMES, C  # noqa: F401
```
主要クラスだけでなく private ヘルパー・定数まで**完全列挙**する（Pitfall 1/2 の再発防止）。

### Mixin 分割（PDFEditorApp 8 Mixin 前例）
**Source:** `pagefolio/app.py:107-117`
**Apply to:** `dialogs/llm_config/__init__.py` の `LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel)`
継承リストの末尾に基底 UI クラス（`tk.Toplevel`）を置く原則を厳守。

### エラー規約（OCRProvider 共通）
**Source:** `pagefolio/ocr_providers.py:41-135`（`OCRProvider` docstring）・`221-246`（`_raise_mapped_http_error`）
**Apply to:** `ocr_providers/base.py`・`errors.py`・各プロバイダファイル
`ConnectionError`/`TimeoutError`/`OCRAPIKeyError`/`OCRRetryableError`/`OCRContextLengthError`/`RuntimeError` の例外規約を機械的移動後も維持する（挙動変更禁止）。

### プロバイダ→環境変数マッピングの一元化（D-09・4箇所統合）
**Source:** `pagefolio/settings.py:23-34`・`pagefolio/ocr.py:208-267`・`pagefolio/ocr_dialog.py:1267-1271`・`pagefolio/dialogs/llm_config.py:512,612,714`
**Apply to:** `ocr_providers/registry.py` を Single Source of Truth とし、上記4ファイルすべてがそこから `env_vars_for`/`primary_env_var`/`sensitive_keys` を参照する形へ置換。Gemini の dual env var 優先順（GEMINI_API_KEY→GOOGLE_API_KEY）は不変。

## No Analog Found

なし。本フェーズは全ファイルが既存コードの分割（機械的移動）または既存パターンの複製であり、真に新規のパターンを要するファイルは存在しない。`registry.py` のみ新設ファイルだが、設計は RESEARCH.md 内に完全な実装例（Pattern 3）が既に提供されている。

## Metadata

**Analog search scope:** `pagefolio/` 全体（`ocr_providers.py`・`dialogs/llm_config.py`・`dialogs/__init__.py`・`constants.py`・`settings.py`・`ocr.py`・`ocr_dialog.py`・`app.py`・`pagination.py`）・`tests/`（`test_imports.py`・`test_settings_keyguard.py`）
**Files scanned:** 11 ソースファイル + 2 テストファイル
**Pattern extraction date:** 2026-07-13
