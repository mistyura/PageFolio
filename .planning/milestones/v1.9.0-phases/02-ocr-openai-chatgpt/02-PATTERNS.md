# Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 12（新設 2 / 修正 10）
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pagefolio/ocr_providers/catalog.py`（新設） | config/utility（データ層） | request-response（メタデータ解決の純関数群） | `pagefolio/ocr_providers/registry.py` | 役割一致（独立性制約付きデータモジュール） |
| `pagefolio/ocr_providers/openai_provider.py`（新設・discretion で名称確定） | service（OCR プロバイダクラス） | request-response（HTTP client） | `pagefolio/ocr_providers/lmstudio.py` | exact（OpenAI 互換 Vision API 形状） |
| `pagefolio/ocr_providers/registry.py`（1行追加のみ） | config | — | 自身が既存パターン | exact（差分は `PROVIDER_ENV_KEYS` に1エントリ） |
| `pagefolio/ocr_providers/__init__.py`（re-export 追加） | config | — | 自身が既存パターン | exact |
| `pagefolio/ocr.py`（`build_provider`／`_cloud_providers`） | factory/controller | request-response | 同ファイル内 claude/gemini 分岐（468-499行） | exact |
| `pagefolio/ocr_dialog.py`（表示名・クラウド判定・host分岐・APIキー欠落マップ） | controller/UI | request-response | 同ファイル内 claude/gemini 既存分岐 | exact |
| `pagefolio/dialogs/batch_ocr.py`（同型の catalog 移行 + openai 分岐） | controller/UI（独立実装） | request-response | `ocr_dialog.py` の対応メソッド（意図的に非共有・データのみ catalog 経由） | exact（ロジックはコピペ移植方針を継続） |
| `pagefolio/dialogs/llm_config/sections.py`（OpenAI セクション新設 + `_base_providers` catalog 化） | component（Tkinter ウィジェット構築） | request-response | Claude セクション（411-510行） | exact |
| `pagefolio/dialogs/llm_config/dialog.py`（`_on_provider_change` openai 分岐・推論系判定 UI 連動） | controller/UI | event-driven | Claude/Gemini 分岐（218-245行）・`_model_supports_effort`（294行〜） | exact |
| `pagefolio/dialogs/llm_config/model_fetch.py`（`_refresh_openai_models` 新設） | service（非同期モデル取得） | request-response（バックグラウンドスレッド） | `_refresh_claude_models`（206-243行） | exact |
| `pagefolio/lang.py`（ja/en キー追加） | config（i18n） | — | 既存 claude/gemini 用キー群 | exact |
| `tests/test_ocr_providers.py` または `tests/test_ocr_provider_catalog.py`（discretion） | test | — | `TestClaudeProviderBasic`/`TestClaudeProviderSupportsEffort`/`TestLMStudioProviderOcrImage` 等 | exact |

## Pattern Assignments

### `pagefolio/ocr_providers/catalog.py`（新設）

**Analog:** `pagefolio/ocr_providers/registry.py`（独立性制約のあるデータモジュールという性格の直接の前例）

**独立性制約パターン**（`registry.py:4-13`）:
```python
"""OCR プロバイダ → 環境変数 中央レジストリ（V180-ROBUST-02）。

独立性制約: registry.py は Python 標準ライブラリ（`os`）のみに依存し、
pagefolio 内部の他モジュール（特に `settings.py` や UI 関連モジュール）を
import しない。これは settings.py 等がこのモジュールを参照する際の循環
import を構造的に防ぐための制約であり、将来の変更でも内部モジュールへの
import 依存を追加してはならない。
"""
import os
```
`catalog.py` はこの直後に置かれる「軽量データモジュール」として、`registry.py` のみを import する一方向依存を守る（D-06）。`registry.py` 自身は逆方向 import を持たない（`import os` のみ、実測 74 行全体で確認済み）。

**公開関数パターン**（`registry.py:26-73`。`env_vars_for`/`primary_env_var`/`resolve_env_key`/`sensitive_keys` の 4 関数はいずれも「dict 参照 → 単純変換 → 返却」の同型構造）:
```python
def env_vars_for(provider_name):
    return PROVIDER_ENV_KEYS.get(provider_name, ())

def primary_env_var(provider_name):
    env_vars = env_vars_for(provider_name)
    return env_vars[0] if env_vars else ""
```
`catalog.py` の `provider_names()`/`is_cloud_provider()`/`host_for()`/`default_model_for()` もこの「dict.get → 分岐なしの単純変換」の粒度を踏襲する（CONTEXT.md D-01 の設計イメージがそのまま雛形）。

**移行対象の重複箇所（実在箇所・全列挙）:**

| 種別 | 箇所 | 内容 |
|---|---|---|
| クラウド判定集合 `{"claude","gemini","runpod"}` | `pagefolio/ocr_dialog.py:924`（`_is_cloud_provider`） | `if name in ("claude", "gemini", "runpod"): return True` |
| クラウド判定 isinstance フォールバック | `pagefolio/ocr_dialog.py:927`（`_is_cloud_provider`） | `isinstance(self.provider, (ClaudeProvider, GeminiProvider, RunPodProvider))` — D-04 でこの経路は維持 |
| クラウド判定集合（独立コピー） | `pagefolio/dialogs/batch_ocr.py:496`（`_is_cloud_provider`） | `if name in ("claude", "gemini", "runpod"): return True`（`ocr_dialog.py` と同一挙動の独立実装とコメントで明記・487行） |
| クラウド判定集合（変数名違い） | `pagefolio/ocr.py:592-597`（`_start_ocr`） | `_cloud_providers = {"claude", "gemini", "runpod"}  # Phase 6: gemini 追加, runpod 追加` |
| クラウド判定集合（変数名違い） | `pagefolio/dialogs/batch_ocr.py:602-603`（`_build_provider_once`） | `_cloud_providers = {"claude", "gemini", "runpod"}` |
| 表示名解決（if 連鎖） | `pagefolio/ocr_dialog.py:812-839`（`_provider_display_name`） | claude/gemini/tesseract/runpod/lmstudio の5分岐 if 連鎖 |
| 表示名解決（dict 版） | `pagefolio/ocr_dialog.py:2329-2351`（`_provider_key_to_display_name`） | 同じキー→表示名対応を dict で再実装（isinstance を伴わない版） |
| host 分岐 | `pagefolio/ocr_dialog.py:1235-1244`（`_confirm_cost`） | gemini→`generativelanguage.googleapis.com`／runpod→`runpod_url`／else claude→`api.anthropic.com` |
| host 分岐（同型再掲） | `pagefolio/ocr_dialog.py:1272-1278`（`_confirm_summary_cost`） | 同一 if/elif/else 構造の再実装 |
| host 分岐（フォールバック候補用） | `pagefolio/ocr_dialog.py:2360-2364`（`_fallback_candidate_host`） | `if candidate == "claude": return "api.anthropic.com"` 等の個別 if |
| host 分岐（独立コピー） | `pagefolio/dialogs/batch_ocr.py:515-523`（`_confirm_cost`） | `ocr_dialog.py:1235-1244` と同一構造 |
| host 分岐（独立コピー・別メソッド） | `pagefolio/dialogs/batch_ocr.py:974, 978` 付近 | 同型の gemini/claude host 分岐（`_confirm_summary_cost` 相当） |
| APIキー欠落 LANG キーマップ | `pagefolio/ocr_dialog.py:1298-1301`（`_check_cloud_api_key` 内） | `{"claude": "ocr_api_key_missing", "gemini": "ocr_api_key_missing_gemini", "runpod": "ocr_api_key_missing_runpod"}.get(name, "ocr_api_key_missing")` |
| APIキー欠落 LANG キーマップ（同一 dict の二重定義） | `pagefolio/dialogs/batch_ocr.py:548-552`（`_check_cloud_api_key`） | `ocr_dialog.py:1298-1301` と完全に同一の dict リテラル |
| 一覧リスト | `pagefolio/dialogs/llm_config/sections.py:85-93`（`_base_providers`） | `["off", "lmstudio", "ollama", "runpod", "claude", "gemini", "tesseract"]` |
| 一覧リスト（フォールバック候補） | `pagefolio/dialogs/llm_config/sections.py:1022`（`_base_fallback_providers`） | 同型の基本プロバイダ一覧（フォールバック用サブセット） |

**D-04 の安全側フォールバック（isinstance 判定は維持）:**
```python
# pagefolio/ocr_dialog.py:916-929（_is_cloud_provider）
from pagefolio.ocr_providers import (
    ClaudeProvider,
    GeminiProvider,
    RunPodProvider,
)
s = settings if settings is not None else self.app.settings
name = s.get("ocr_provider", "")
if name in ("claude", "gemini", "runpod"):
    return True
# isinstance ガード（provider インスタンスが差し替わっていても対応）
if isinstance(self.provider, (ClaudeProvider, GeminiProvider, RunPodProvider)):
    return True
return False
```
catalog 移行後もこの2段構成（`catalog.is_cloud_provider(name)` の集合判定 + isinstance フォールバック）は維持する。catalog に未登録のプラグインプロバイダは `is_cloud_provider()` が False を返す設計（D-04）。

---

### `pagefolio/ocr_providers/openai_provider.py`（新設）

**Analog:** `pagefolio/ocr_providers/lmstudio.py`（OpenAI 互換 Vision API の一次実装）。対比・部品取り対象は `claude.py`（`_apply_gen_params` パターン）・`gemini.py`（`_is_legacy_gemini` 安全側パターン）・`errors.py`（共通リトライ基盤）。

**Imports パターン**（`lmstudio.py:1-12`）:
```python
import json
import socket
import urllib.error
import urllib.request

from pagefolio.ocr_providers.base import OCRProvider, _require_http_scheme
from pagefolio.ocr_providers.errors import _raise_mapped_http_error
```
OpenAI 版は固定 https エンドポイントのため `_require_http_scheme`（ユーザー入力 URL のスキーム検証）は不要。`re`（推論系モデル判定の正規表現）を追加 import する（`gemini.py:7` の `import re` と同型）。

**コアペイロード構造（画像+base64 data URI）** — `lmstudio.py:42-63` を土台に、差分箇所のみ置換する:
```python
# lmstudio.py:42-63（土台・そのまま流用できる部分）
def _build_payload(self, b64_png, prompt):
    return {
        "model": self.model or "local-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_png}",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": self.max_tokens,     # ← OpenAI版は max_completion_tokens に置換（D-10）
        "temperature": self.temperature,    # ← OpenAI版は推論系モデルなら省略（D-11）
        "stream": False,                    # ← OpenAI版は不要（Chat Completions非streaming時は省略可）
    }
```
`image_url.url` に加え、OpenAI 版は `image_url.detail`（D-16・既定 `"high"`）を追加する必要がある点が LM Studio との差分。

**固定エンドポイント・認証差分（`Authorization: Bearer` + org/project ヘッダ）** — 対比元は `lmstudio.py:87-101`（URL 由来の動的エンドポイント・認証ヘッダなし）:
```python
# lmstudio.py:93-101（動的URL・無認証。OpenAI版との差分ポイント）
_require_http_scheme(self.url)
endpoint = self.url.rstrip("/") + "/v1/chat/completions"
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(  # noqa: S310
    endpoint,
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
```
OpenAI 版はこの `headers` 部分のみ差し替える。org/project は空なら一切ヘッダを付与しない（D-17）:
```python
# openai_provider.py 実装イメージ（D-17: 空ならヘッダ非付与）
def _headers(self):
    h = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
    if self.organization:
        h["OpenAI-Organization"] = self.organization
    if self.project:
        h["OpenAI-Project"] = self.project
    return h
```
エンドポイントは固定文字列（`CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"`）とし、`_require_http_scheme` は不要（ユーザー入力 URL ではないため）。

**`max_completion_tokens`／推論系モデル判定によるパラメータ省略（D-10/D-11/D-13）** — 直接の設計根拠は `claude.py:114-130`（`_apply_gen_params` の3分岐パターン）と `gemini.py:117-126`（`_is_legacy_gemini` の安全側世代判定）:
```python
# claude.py:114-130（「モデル種別に応じてパラメータを出し分ける」設計の前例）
def _apply_gen_params(self, payload):
    if self._supports_effort():
        payload["output_config"] = {"effort": self.effort}
    elif self._supports_temperature():
        payload["temperature"] = self.temperature
    # それ以外（未知モデル）: 両方省略（最も安全な前方互換）
    return payload
```
```python
# gemini.py:117-126（「世代判定→パラメータ省略」の安全側パターンの前例）
def _is_legacy_gemini(self):
    gen = self._model_generation(self.model)
    return gen is not None and gen <= 2
```
OpenAI 版はこの2つを合成した単一判定関数（D-13）を持つ:
```python
# openai_provider.py 実装イメージ
_REASONING_MODEL_RE = re.compile(r"^o\d")  # D-09: 実キーで /v1/models 確認後に確定

def _is_reasoning_model(self):
    return bool(self._REASONING_MODEL_RE.match(self.model or ""))

def _apply_gen_params(self, payload):
    payload["max_completion_tokens"] = self.max_tokens  # D-10: 常時 max_completion_tokens
    if not self._is_reasoning_model():
        payload["temperature"] = self.temperature        # D-11: 非推論系のみ temperature
    elif self.reasoning_effort:
        payload["reasoning_effort"] = self.reasoning_effort  # D-15: 推論系のみ effort
    return payload
```

**エラーハンドリング（`_raise_mapped_http_error` をそのまま流用・D-12）** — `lmstudio.py:102-113` と完全に同一の try/except 構造をそのまま複製する:
```python
# lmstudio.py:102-113（変更不要でそのまま複製できる部分）
try:
    with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8")
except urllib.error.HTTPError as e:
    _raise_mapped_http_error(e)
except socket.timeout as e:
    raise TimeoutError(f"timed out after {self.timeout}s") from e
except urllib.error.URLError as e:
    reason = getattr(e, "reason", e)
    if isinstance(reason, socket.timeout):
        raise TimeoutError(f"timed out after {self.timeout}s") from e
    raise ConnectionError(str(reason)) from e
```
`errors.py:106-131`（`_raise_mapped_http_error`）は 429/5xx→`OCRRetryableError`・コンテキスト長超過→`OCRContextLengthError`（`_CONTEXT_ERROR_MARKERS` に既に `"context_length_exceeded"` を含む・`errors.py:67-76`）・その他4xx→`RuntimeError` の3分岐に既に対応済みであり、OpenAI 専用の変更は不要（D-12）。

**レスポンスパース** — `lmstudio.py:115-136`（`ocr_image`）をそのまま複製可能（`choices[0]["message"]["content"]` 構造が同一）:
```python
# lmstudio.py:131-136
body = self._post_chat(self._build_payload(b64_png, prompt))
try:
    result = json.loads(body)
    return result["choices"][0]["message"]["content"]
except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
    raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
```

**モデル一覧取得（D-07/D-08 ヒューリスティックフィルタ＋0件フォールバック）** — 構造の雛形は `claude.py:304-341`（`list_models`。キー未設定時は `RECOMMENDED_MODELS` を返す・カーソルページング）:
```python
# claude.py:320-322（D-08 の直接の前例）
if not self.api_key:
    return list(self.RECOMMENDED_MODELS)
```
OpenAI 版は `GET /v1/models` 取得後にヒューリスティックフィルタ（embedding/tts/whisper/dall-e/moderation 等除外）を適用し、フィルタ結果が0件なら同じく `RECOMMENDED_MODELS` へ合流させる（D-08）。フィルタ関数は Tk/ネットワーク非依存の純関数として切り出す（D-07）。

**並列度・タイムアウトのクラス属性（D-14）** — `claude.py:23-28`:
```python
default_concurrency = 2
max_concurrency = 2
supports_text_prompt = True
model_list_timeout = 30
```
OpenAI 版はこの値をそのまま踏襲する（Claude 相当）。

---

### `pagefolio/ocr_providers/registry.py`（1行追加のみ・D-06/D-18）

**Analog:** 自身（既存3エントリと同型）

**追加パターン**（`registry.py:19-23`）:
```python
PROVIDER_ENV_KEYS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "runpod": ("RUNPOD_API_KEY",),
    # 追加: "openai": ("OPENAI_API_KEY",),
}
```
この1行追加のみで `env_vars_for`/`primary_env_var`/`resolve_env_key`/`sensitive_keys()`（`registry.py:56-73`）が自動的に `openai_api_key`／`OPENAI_API_KEY`／`openai_api_key`(lower) を導出する。**それ以外のコードは変更しない**（D-06）。

---

### `pagefolio/ocr_providers/__init__.py`（re-export 追加）

**Analog:** 自身（既存5プロバイダの re-export パターン）

```python
# __init__.py:30, 42-45（既存パターン）
from pagefolio.ocr_providers.claude import ClaudeProvider  # noqa: F401
...
from pagefolio.ocr_providers.gemini import GeminiProvider  # noqa: F401
from pagefolio.ocr_providers.lmstudio import LMStudioProvider  # noqa: F401
from pagefolio.ocr_providers.ollama import OllamaProvider  # noqa: F401
from pagefolio.ocr_providers.runpod import RunPodProvider  # noqa: F401
```
`from pagefolio.ocr_providers.openai_provider import OpenAIProvider  # noqa: F401` を同一アルファベット順位置に追加する。`catalog` サブモジュールは registry と同様に re-export しない方針を踏襲する（`__init__.py:9-11` のコメント「registry サブモジュールはここでは re-export しない」と同じ理由）。

---

### `pagefolio/ocr.py`（`build_provider` の openai 分岐・`_cloud_providers` catalog 化）

**Analog:** 同ファイル内 claude/gemini 分岐（`ocr.py:468-499`）

**関数内 import + API キー引数注入パターン**（`ocr.py:468-483`。claude 分岐全文）:
```python
elif name == "claude":
    # api_key は settings から読まず引数のみ・settings へ書き込まない（D-01/D-05）
    from pagefolio.ocr_providers import ClaudeProvider

    # H-1: -1 は LM Studio 専用の「モデル最大値委譲」値。
    # Anthropic API は正の整数必須のため mt <= 0 のとき 4096 にクランプする。
    mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
    mt = 4096 if mt <= 0 else mt
    return ClaudeProvider(
        api_key=api_key or "",
        model=settings.get("claude_model", "claude-sonnet-4-6"),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
        max_tokens=mt,
        temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        effort=settings.get("ocr_effort", "low"),
    )
```
OpenAI 分岐はこの構造を複製し、`effort=` の代わりに `detail=settings.get("openai_detail", "high")`（D-16）・`reasoning_effort=settings.get("openai_reasoning_effort")`（D-15）・`organization=settings.get("openai_organization", "")`・`project=settings.get("openai_project", "")`（D-17）を渡す。`max_tokens <= 0` クランプ値は claude/gemini と同じ 4096 に揃える（Claude's Discretion 事項だが RESEARCH.md は 4096 を推奨）。

**`_cloud_providers` catalog 移行対象**（`ocr.py:592-597`。`_start_ocr` 内）:
```python
_cloud_providers = {
    "claude",
    "gemini",
    "runpod",
}  # Phase 6: gemini 追加, runpod 追加
if name in _cloud_providers:
```
→ `catalog.is_cloud_provider(name)` に置換する（D-03 の段階移行対象6箇所の1つ）。openai 追加後、catalog 側の `PROVIDERS["openai"].is_cloud = True` により自動的にクラウド扱いになる。

---

### `pagefolio/ocr_dialog.py`（表示名・クラウド判定・host分岐・APIキー欠落マップ・catalog移行 + openai 追加）

**Analog:** 同ファイル内 claude/gemini の既存分岐（複数メソッドに分散）

対応箇所と改修内容（D-03 の段階移行対象）:

| メソッド | 行番号 | 現状 | 改修 |
|---|---|---|---|
| `_provider_display_name` | 812-839 | if 連鎖（claude→gemini→tesseract→runpod→lmstudio） | `catalog` 経由の表示名解決に統一しつつ isinstance フォールバックは維持（D-04） |
| `_provider_key_to_display_name` | 2329-2351 | dict リテラルによる別実装 | 同上（2つの判定経路を1本の catalog 参照へ統合） |
| `_is_cloud_provider` | 908-929 | 集合 `("claude","gemini","runpod")` + isinstance | `catalog.is_cloud_provider(name)` + isinstance フォールバック維持（D-04） |
| `_confirm_cost` | 1216-1257 | if/elif/else の host 分岐（1235-1244） | `catalog.host_for(name, s)` に置換。openai 分岐（`gpt` 系モデル + `api.openai.com`）を追加 |
| `_confirm_summary_cost` | 1259-1287 | 同型 host 分岐（1272-1278） | 同上 |
| `_fallback_candidate_host` | 2353-2364+ | 候補名ごとの個別 if | `catalog.host_for()` を使う形へ統一 |
| `_check_cloud_api_key` | 1289-1304+ | APIキー欠落 LANG キーマップ（1298-1301相当） | `catalog.PROVIDERS[name].api_key_missing_lang_key` から解決。openai 用 `ocr_api_key_missing_openai` を lang.py に追加 |

**APIキー欠落メッセージの既存パターン**（`_check_cloud_api_key` 内・行1289-1304 で確認した構造。batch_ocr.py:548-559 と同一挙動）:
```python
s = settings if settings is not None else self.app.settings
if not self._is_cloud_provider(settings=s):
    return True
from pagefolio.ocr import _resolve_api_key
from pagefolio.ocr_providers import OCRAPIKeyError
from pagefolio.ocr_providers.registry import primary_env_var
```
（以降 `_resolve_api_key` 呼び出し・`OCRAPIKeyError` 捕捉・`primary_env_var(name)` によるメッセージ組み立て・`messagebox.showerror` という構造。catalog 移行後もこの外枠は変えず、LANG キー解決部分のみ catalog 経由にする。）

---

### `pagefolio/dialogs/batch_ocr.py`（同型の catalog 移行 + openai 分岐・ロジックは独立実装のまま）

**Analog:** `ocr_dialog.py` の対応メソッド（意図的コピペ移植・DRY化しない）

冒頭の設計方針コメント（`batch_ocr.py:12` 付近・`_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key` を指す）:
```python
# ── コスト確認（OCRDialog からのコピペ移植・レビュー懸念5）────────
def _is_cloud_provider(self, settings=None):
    """`ocr_dialog.py:_is_cloud_provider` と同一挙動の独立実装。"""
```
この「同一挙動の独立実装」というコメント規約を openai 対応時も維持する。`_is_cloud_provider`（486-500行）・`_confirm_cost`（511-532行、host 分岐は515-523行）・`_check_cloud_api_key`（534-560行、APIキー欠落マップは548-552行）・`_build_provider_once`（592-603行、`_cloud_providers` 集合は602行）の4箇所すべてが `ocr_dialog.py`/`ocr.py` と同型の catalog 移行対象になる。**ロジックの共通化（継承・メソッド import）は行わない**（Out of Scope・冒頭コメント4-16行目で明示的に否定）。

---

### `pagefolio/dialogs/llm_config/sections.py`（OpenAI セクション新設 + `_base_providers` catalog 化）

**Analog:** Claude セクション（`sections.py:411-510`）

**一覧リスト catalog 移行対象**（`sections.py:85-100`）:
```python
_base_providers = [
    "off",
    "lmstudio",
    "ollama",
    "runpod",
    "claude",
    "gemini",
    "tesseract",
]
_plugin_extras = (
    self._plugin_manager.list_ocr_providers() if self._plugin_manager else []
)
self.provider_combo = ttk.Combobox(
    provider_row,
    textvariable=self.provider_var,
    values=_base_providers + _plugin_extras,
    ...
)
```
→ `_base_providers = catalog.provider_names()` へ置換し、リストへ `"openai"` を追加する（catalog.PROVIDERS に登録するだけで自動反映）。`_base_fallback_providers`（1022行）も同様に `catalog.fallback_candidate_names()` へ。

**セクション構築パターン**（Claude セクション全体・`sections.py:411-510`。モデル combobox・APIキー欄・トグルボタン・注記ラベル・モデル更新ボタンの5要素）:
```python
self.claude_section_frame = tk.Frame(body, bg=C["BG_DARK"])

claude_model_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
claude_model_row.pack(fill="x", padx=0, pady=2)
tk.Label(
    claude_model_row, text=self._L["settings_lm_model"],
    bg=C["BG_DARK"], fg=C["TEXT_MAIN"], font=self._font(-1),
    width=20, anchor="w",
).pack(side="left")
self.claude_model_var = tk.StringVar(
    value=self.current_settings.get("claude_model", "claude-sonnet-4-6"),
)
self.claude_model_combo = ttk.Combobox(
    claude_model_row, textvariable=self.claude_model_var,
    font=self._font(-1), values=ClaudeProvider.RECOMMENDED_MODELS,
)
self.claude_model_combo.pack(side="left", fill="x", expand=True, padx=4)
self.claude_model_combo.bind("<<ComboboxSelected>>", self._on_model_change)

# APIキー欄（セッション限定・マスク表示切替あり）
claude_key_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
...
self.claude_api_key_var = tk.StringVar(value=self._session_api_keys.get("claude", ""))
self.claude_api_key_entry = tk.Entry(
    claude_key_row, show="*", textvariable=self.claude_api_key_var,
    font=self._font(-1), bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
    insertbackground=C["TEXT_MAIN"], relief="flat",
)
self._claude_key_shown = False

def _toggle_claude_key():
    self._claude_key_shown = not self._claude_key_shown
    self.claude_api_key_entry.configure(show="" if self._claude_key_shown else "*")
    claude_key_toggle_btn.configure(
        text=self._L["llm_key_toggle_hide"] if self._claude_key_shown
        else self._L["llm_key_toggle_show"]
    )

claude_key_toggle_btn = ttk.Button(
    claude_key_row, text=self._L["llm_key_toggle_show"], width=4,
    command=_toggle_claude_key,
)
claude_key_toggle_btn.pack(side="right", padx=(2, 0))
self.claude_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)

claude_note = self._L["llm_key_session_note"]
_claude_env_set, _claude_env_var = _configured_env_var("claude")
if _claude_env_set:
    claude_note += " " + self._L["llm_key_env_set_note"].format(env_var=_claude_env_var)
tk.Label(
    self.claude_section_frame, text=claude_note,
    bg=C["BG_DARK"], fg=C["TEXT_SUB"], font=self._font(-2),
    wraplength=460, justify="left",
).pack(anchor="w", pady=(0, 2))

claude_btn_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
claude_btn_row.pack(fill="x", padx=0, pady=(4, 2))
ttk.Button(
    claude_btn_row, text=self._L["ocr_model_refresh"],
    command=self._refresh_claude_models,
).pack(side="left", padx=2)
```
`openai_section_frame` はこの5要素構成をそのまま複製し、次を追加する（折りたたみ UI は導入しない・D-17）:
- org/project 2欄（任意入力・通常の `tk.Entry` 行として Claude セクションと同じ構成）
- detail レベル combobox（既定 `"high"`・D-16・永続化）
- reasoning_effort 欄（OpenAI 専用ウィジェット・専用 settings キー `openai_reasoning_effort`・D-15。Claude の `effort_frame` は流用しない）

ボタン・フォント規約は CLAUDE.md に準拠: 通常操作は `"TButton"`（モデル更新ボタン等）、フォントは `self._font(delta)`、色は `C["BG_DARK"]`/`C["TEXT_MAIN"]` 等のテーマ辞書参照を踏襲する。

---

### `pagefolio/dialogs/llm_config/dialog.py`（`_on_provider_change` openai 分岐・D-13 判定関数の UI 連動）

**Analog:** Claude/Gemini の既存分岐（`dialog.py:218-245`）

**プロバイダ切替パターン**（`dialog.py:218-230`。Claude 分岐全文）:
```python
if provider == "claude":
    self.claude_section_frame.pack(
        fill="x", padx=24, pady=(4, 2), before=self.scale_row
    )
    self.gemini_section_frame.pack_forget()
    self.tesseract_section_frame.pack_forget()
    self._common_section_heading.pack(
        anchor="w", padx=24, pady=(6, 2), before=self.scale_row
    )
    # モデルに応じて effort/temperature を切替
    self._on_model_change()
```
`elif provider == "openai":` 分岐を追加し、`openai_section_frame.pack(...)` + 他セクションの `pack_forget()` を同型で行う。effort 相当の表示切替は Claude の `_on_model_change`（274-291行）と同型の `_on_openai_model_change` を新設し、D-13 の単一判定関数（`_is_reasoning_model` 相当）を呼ぶ。

**effort 表示切替の判定パターン**（`dialog.py:274-298`。`_on_model_change`／`_model_supports_effort`）:
```python
def _on_model_change(self, _event=None):
    model = self.claude_model_var.get()
    if self._model_supports_effort(model):
        self.effort_frame.pack(fill="x", padx=24, pady=2, before=self.scale_row)
        self.temperature_frame.pack_forget()
    else:
        self.temperature_frame.pack(fill="x", padx=24, pady=2, before=self.scale_row)
        self.effort_frame.pack_forget()
    self._resize_to_fit()

def _model_supports_effort(self, model):
    """モデルが effort パラメータ（output_config）に対応しているか判定する。
    M-3: ocr_providers.ClaudeProvider._supports_effort と同じ判定に揃える。
    """
```
この「UI 側判定関数がプロバイダ側の判定と重複する」構造は Claude では既に2箇所（`claude.py:69-75` の `_supports_effort` と `dialog.py:294-` の `_model_supports_effort`）に存在する技術的負債（PITFALLS.md Pitfall 3 で反面教師として明記）。**OpenAI では同じ重複を作らない**: D-13 の単一純関数（`_is_reasoning_model(model)` 等）を UI 側とプロバイダ側の両方が同一箇所から参照する設計にする（配置モジュールは Claude's Discretion）。

---

### `pagefolio/dialogs/llm_config/model_fetch.py`（`_refresh_openai_models` 新設）

**Analog:** `_refresh_claude_models`（`model_fetch.py:206-243`）

**全文パターン**:
```python
# model_fetch.py:206-243
def _refresh_claude_models(self):
    self._set_lm_status(self._L["llm_fetching_claude_models"], kind="info")
    api_key = self.claude_api_key_var.get().strip() or _env_fallback("claude")
    provider = ClaudeProvider(api_key=api_key, model="")

    def _on_success(models):
        self.claude_model_combo["values"] = models
        if not api_key:
            self._set_lm_status(self._L["llm_env_key_unset_static"], kind="info")
        else:
            self._set_lm_status(
                self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
            )

    def _on_error(e):
        logger.warning(
            self._L["llm_model_fetch_failed"].format(provider="Claude", e=e)
        )
        self.claude_model_combo["values"] = ClaudeProvider.RECOMMENDED_MODELS
        self._set_lm_status(self._L["llm_env_key_unset_static"], kind="info")

    self._fetch_models_async(provider.list_models, _on_success, _on_error)
```
`_refresh_openai_models` はこの構造を完全複製し `ClaudeProvider`→`OpenAIProvider`／`claude_api_key_var`→`openai_api_key_var`／`claude_model_combo`→`openai_model_combo`／`provider="Claude"`→`provider="OpenAI"` に置換する。

**env フォールバック解決**（`model_fetch.py:17-32`。`_env_fallback`）:
```python
def _env_fallback(provider_name):
    for var in env_vars_for(provider_name):
        val = os.environ.get(var)
        if val:
            return val
    return ""
```
`_env_fallback("openai")` は `registry.env_vars_for("openai")` が `("OPENAI_API_KEY",)` を返すことで自動対応する（registry.py への1行追加のみで完結・変更不要）。

---

## Shared Patterns

### 429/5xx リトライ・エラーマッピング（変更不要・そのまま適用）
**Source:** `pagefolio/ocr_providers/errors.py:106-131`（`_raise_mapped_http_error`）+ `67-76`（`_CONTEXT_ERROR_MARKERS`、既に `"context_length_exceeded"` を含む）
**Apply to:** `openai_provider.py` の全 HTTP 呼び出し（`_post_chat`/`list_models` 等）
```python
if e.code == 429 or e.code >= 500:
    raise OCRRetryableError(
        _retryable_http_message(e.code),
        retry_after=parse_retry_after(e.headers),
        code=e.code,
    ) from e
```
D-12 のとおり errors.py は原則未変更。OpenAI 専用のエラー分岐は新設しない。

### API キー機密判定（`registry.py` へ1行追加で完結）
**Source:** `pagefolio/ocr_providers/registry.py:19-23, 56-73`
**Apply to:** `openai_provider.py`（引数注入のみ）・`ocr.py:build_provider`・`ocr_dialog.py`/`batch_ocr.py:_check_cloud_api_key`・`settings.py:_SENSITIVE_KEYS`
```python
PROVIDER_ENV_KEYS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "runpod": ("RUNPOD_API_KEY",),
    "openai": ("OPENAI_API_KEY",),  # 追加
}
```

### モデル一覧の非同期取得基盤（変更不要）
**Source:** `pagefolio/dialogs/llm_config/model_fetch.py`（`_fetch_models_async`。UI フリーズ回避のバックグラウンドスレッド実行）
**Apply to:** `_refresh_openai_models`（新設時は既存基盤をそのまま呼ぶだけ）

### 安全側パラメータ省略パターン（設計思想の共有）
**Source:** `pagefolio/ocr_providers/gemini.py:117-126`（`_is_legacy_gemini`）・`pagefolio/ocr_providers/claude.py:114-130`（`_apply_gen_params`）
**Apply to:** `openai_provider.py`（D-10/D-11/D-13 の推論系モデル判定）
「未知の入力（新モデル）が来ても壊れない側に倒す」という設計基準を OpenAI 実装でも継続する。

### ボタン・フォント・テーマ規約（プロジェクト全体規約・CLAUDE.md）
**Source:** ルート `CLAUDE.md`「コーディング規約」
**Apply to:** `sections.py` の OpenAI セクション新設部分
- 通常操作 → `"TButton"`、主要アクション → `"Accent.TButton"`
- テーマ色は `C["BG_DARK"]` 等の辞書参照（グローバル定数直書き禁止）
- フォントサイズは `self._font(delta)` ヘルパー使用

## No Analog Found

なし。全 12 ファイルについて既存コードベース内に role + data flow が一致する強い analog が見つかった（OpenAI プロバイダ自体は `LMStudioProvider` を土台とした差分実装として実現可能）。

## Metadata

**Analog search scope:** `pagefolio/ocr_providers/`, `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/batch_ocr.py`, `pagefolio/dialogs/llm_config/`, `tests/test_ocr_providers.py`
**Files scanned:** `registry.py`, `lmstudio.py`, `claude.py`, `gemini.py`, `errors.py`, `__init__.py`, `ocr.py`（`build_provider`/`_start_ocr`）, `ocr_dialog.py`（`_provider_display_name`/`_is_cloud_provider`/`_confirm_cost`/`_confirm_summary_cost`/`_check_cloud_api_key`/`_provider_key_to_display_name`/`_fallback_candidate_host`）, `batch_ocr.py`（`_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key`/`_build_provider_once`）, `sections.py`（`_base_providers`/Claude セクション）, `dialog.py`（`_on_provider_change`/`_on_model_change`/`_model_supports_effort`）, `model_fetch.py`（`_env_fallback`/`_refresh_claude_models`）, `pagefolio/CLAUDE.md`, ルート `CLAUDE.md`
**Pattern extraction date:** 2026-08-11
