# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio.ocr_providers — 後方互換の再エクスポート集約

既存の `from pagefolio.ocr_providers import ClaudeProvider, ...` を
サブパッケージ化後も維持するための再エクスポートモジュール（D-11）。

`registry` サブモジュールはここでは re-export しない。settings.py 等は
`from pagefolio.ocr_providers.registry import sensitive_keys` のように
サブモジュール直接指定で import すること（Pitfall 6・循環 import 回避）。

`urllib.request` / `subprocess` は D-03（tests/test_ocr_providers.py 凍結・
無修正）の互換のため保持する。既存テストが
`ocr_providers.urllib.request` / `ocr_providers.subprocess` の属性チェーンで
monkeypatch するため、`pagefolio.ocr_providers` モジュールがこれらの
stdlib モジュールを属性として持つ必要がある（実体は各プロバイダファイルが
import する共有モジュールオブジェクトと同一であり、monkeypatch は
グローバルに反映される）。
"""

import subprocess  # noqa: F401
import urllib.request  # noqa: F401

from pagefolio.ocr_providers.base import (  # noqa: F401
    _ALLOWED_URL_SCHEMES,
    OCRProvider,
    _require_http_scheme,
)
from pagefolio.ocr_providers.claude import ClaudeProvider  # noqa: F401
from pagefolio.ocr_providers.errors import (  # noqa: F401
    _CONTEXT_ERROR_MARKERS,
    OCRAPIKeyError,
    OCRContextLengthError,
    OCRRetryableError,
    _raise_mapped_http_error,
    _retryable_http_message,
    looks_like_context_error,
    parse_retry_after,
)
from pagefolio.ocr_providers.gemini import GeminiProvider  # noqa: F401
from pagefolio.ocr_providers.lmstudio import LMStudioProvider  # noqa: F401
from pagefolio.ocr_providers.ollama import OllamaProvider  # noqa: F401
from pagefolio.ocr_providers.runpod import RunPodProvider  # noqa: F401
from pagefolio.ocr_providers.tesseract import (  # noqa: F401
    TesseractProvider,
    _detect_tesseract,
)
