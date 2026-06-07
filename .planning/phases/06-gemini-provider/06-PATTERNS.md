# Phase 6: Gemini Provider + 逐次レンダリング最適化 — パターンマップ

**作成日:** 2026-06-07
**分析対象ファイル数:** 8（新規追加: 2、改修: 6）
**アナログ発見:** 8 / 8

---

## ファイル分類

| 新規/改修ファイル | ロール | データフロー | 最近傍アナログ | 一致品質 |
|-----------------|------|------------|-------------|--------|
| `pagefolio/ocr_providers.py`（GeminiProvider 追加） | service | request-response | 同ファイル `ClaudeProvider`（line 203-425） | 完全一致 |
| `pagefolio/ocr.py`（gemini 分岐・producer-consumer） | service / utility | request-response + event-driven | 同ファイル `build_provider` / `_resolve_api_key`（line 53-287） | 完全一致 |
| `pagefolio/ocr_dialog.py`（producer-consumer 化） | component | event-driven | 同ファイル `_render_next_page` / `_worker`（line 808-923） | 完全一致 |
| `pagefolio/settings.py`（ocr_scale 変更・gemini_model 追加） | config | CRUD | 同ファイル `_load_settings` defaults ブロック（line 35-53） | 完全一致 |
| `pagefolio/dialogs/llm_config.py`（gemini 分岐追加） | component | request-response | 同ファイル `_on_provider_change` / claude 固有欄（line 439-491） | ロール一致 |
| `pagefolio/lang.py`（文言追加） | config | transform | 同ファイル `ocr_provider_name_claude` / `ocr_api_key_missing`（line 292-349） | 完全一致 |
| `tests/test_ocr_providers.py`（GeminiProvider テスト追加） | test | — | 同ファイル `TestLMStudioProviderBasic` / `TestLMStudioProviderOcrImage`（line 115-218） | 完全一致 |
| `tests/test_ocr.py`（producer-consumer メモリテスト追加） | test | — | 同ファイル `FakeProvider` / `TestLMStudioProviderPayload`（line 23-100） | ロール一致 |

---

## パターン割り当て

---

### `pagefolio/ocr_providers.py` — `GeminiProvider` 追加（service, request-response）

**アナログ:** `pagefolio/ocr_providers.py` の `ClaudeProvider`（line 203-425）

**インポートパターン**（line 1-13）:
```python
import abc
import json
import logging
import socket
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
```

**クラス属性・`__init__` パターン**（`ClaudeProvider` line 210-251 を踏襲）:
```python
class GeminiProvider(OCRProvider):
    default_concurrency = 1   # D-07: Gemini=1（ClaudeProvider は 2）
    max_concurrency = 1       # D-07: クラウド並列度制限

    GENERATE_CONTENT_ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent"
    )
    MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
    RECOMMENDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]  # D-08

    def __init__(self, api_key, model, timeout=120, max_tokens=4096, temperature=0.1):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
```

**`_build_payload` パターン**（ClaudeProvider line 268-299 の構造をそのまま踏襲・内容は差し替え）:
```python
def _build_payload(self, b64_png, prompt):
    return {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": b64_png}},
                    {"text": prompt},   # 画像→テキストの順（公式推奨）
                ]
            }
        ],
        "generationConfig": {
            "temperature": self.temperature,
            "maxOutputTokens": self.max_tokens,
            # thinkingConfig は generationConfig の直下（トップレベルではない・D-09/Pitfall-C）
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
```

**認証ヘッダーパターン**（ClaudeProvider line 319-327 と対比。ヘッダーキー名のみ異なる）:
```python
# ClaudeProvider: "x-api-key" + "anthropic-version" ヘッダー
# GeminiProvider: "x-goog-api-key" のみ（URL クエリ ?key= は禁止・D-05/Pitfall ログ漏洩回避）
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": self.api_key,
}
```

**HTTPError → OCRRetryableError パターン**（ClaudeProvider line 332-351 をそのままコピー）:
```python
except urllib.error.HTTPError as e:
    if e.code == 429 or e.code >= 500:
        retry_after = None
        raw_retry = e.headers.get("Retry-After") if e.headers else None
        if raw_retry:
            try:
                retry_after = float(raw_retry)
            except (ValueError, TypeError):
                retry_after = None
        raise OCRRetryableError(
            f"HTTP {e.code}: レート制限またはサーバエラー（リトライ可能）",
            retry_after=retry_after,
        ) from e
    try:
        err_body = e.read().decode("utf-8", errors="replace")
    except Exception:
        err_body = ""
    raise RuntimeError(f"HTTP {e.code}: {err_body or e.reason}") from e
except socket.timeout as e:
    raise TimeoutError(f"timed out after {self.timeout}s") from e
except urllib.error.URLError as e:
    reason = getattr(e, "reason", e)
    if isinstance(reason, socket.timeout):
        raise TimeoutError(f"timed out after {self.timeout}s") from e
    raise ConnectionError(str(reason)) from e
```

**`_parse_response` パターン**（Gemini 固有。`candidates` 空チェック必須・Pitfall-D）:
```python
def _parse_response(self, body):
    # candidates 空チェック（安全フィルタ・RECITATION ブロック対策・Pitfall-D）
    candidates = body.get("candidates", [])
    if not candidates:
        reason = body.get("promptFeedback", {}).get("blockReason", "unknown")
        raise RuntimeError(f"Gemini blocked: {reason}")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [p["text"] for p in parts if "text" in p]
    if not texts:
        raise RuntimeError(f"Gemini: no text in response: {body}")
    return "\n".join(texts)
    # ※ ClaudeProvider の同等パターン（line 362-373）: content[].type=="text" を走査して "\n".join
```

**`list_models` パターン**（ClaudeProvider line 375-425 を踏襲）:
```python
def list_models(self):
    if not self.api_key:
        return list(self.RECOMMENDED_MODELS)   # キー未設定時は静的リスト（D-08）
    timeout = 10
    req = urllib.request.Request(  # noqa: S310
        self.MODELS_ENDPOINT,
        headers={"x-goog-api-key": self.api_key},
        method="GET",
    )
    # ... 例外ハンドリングは ClaudeProvider line 406-417 と同一構造 ...
    return [
        m.get("name", "").replace("models/", "")  # "models/gemini-2.5-flash" → "gemini-2.5-flash"
        for m in data.get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
        and m.get("name", "")
    ]
    # ※ ClaudeProvider の同等パターン（line 420-425）:
    # capabilities.image_input.supported フィルタを使用（フィルタ条件のみ異なる）
```

---

### `pagefolio/ocr.py` — `build_provider` gemini 分岐・`_resolve_api_key` gemini 対応（service, request-response）

**アナログ:** 同ファイル `claude` 分岐（line 273-285 / line 74-88）

**`build_provider` への gemini 分岐追加パターン**（line 273-285 の `claude` 分岐直後）:
```python
# 既存の claude 分岐（line 273-285）:
elif name == "claude":
    from pagefolio.ocr_providers import ClaudeProvider
    return ClaudeProvider(
        api_key=api_key or "",
        model=settings.get("claude_model", "claude-sonnet-4-6"),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
        max_tokens=int(settings.get("ocr_max_tokens", 4096)),
        temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        effort=settings.get("ocr_effort", "low"),
    )

# 追加する gemini 分岐（同パターン・effort なし・gemini_model キー使用）:
elif name == "gemini":
    from pagefolio.ocr_providers import GeminiProvider
    return GeminiProvider(
        api_key=api_key or "",
        model=settings.get("gemini_model", "gemini-2.5-flash"),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
        max_tokens=int(settings.get("ocr_max_tokens", 4096)),
        temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
    )
```

**`_resolve_api_key` への gemini 分岐追加パターン**（line 74-88 の `claude` 分岐を踏襲）:
```python
# 既存の claude 分岐（line 74-88）:
if provider_name == "claude":
    env_var = "ANTHROPIC_API_KEY"
    key = os.environ.get(env_var)
    if key:
        return key
    key = session_keys.get("claude", "")
    if key:
        return key
    raise OCRAPIKeyError(env_var)

# 追加する gemini 分岐（dual env var フォールバック付き・D-06）:
if provider_name == "gemini":
    env_var_primary = "GEMINI_API_KEY"
    key = os.environ.get(env_var_primary) or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    key = session_keys.get("gemini", "")
    if key:
        return key
    raise OCRAPIKeyError(env_var_primary)  # 主変数名でエラー表示
```

**`_start_ocr` の `_cloud_providers` 集合への gemini 追加**（line 328）:
```python
# 既存（line 328）:
_cloud_providers = {"claude"}  # Phase 6 で gemini を追加

# Phase 6 で変更:
_cloud_providers = {"claude", "gemini"}
```

**producer-consumer キュー変数の `ocr.py` 切り出しパターン**（D-13・テスト可能化):
```python
import queue  # 標準ライブラリ（新規 pip 依存なし）

def run_with_bounded_buffer(render_fn, ocr_fn, page_indices, maxsize, is_cancelled, on_done):
    """Tk 非依存の producer-consumer ループ（D-13: テストで直接呼び出せる）。

    render_fn(page_idx) -> b64_png: メインスレッドで呼ぶ前提（テストでは直接呼ぶ）
    ocr_fn(b64_png) -> str:         API 呼び出し（テストでは FakeProvider を渡す）
    """
    buf = queue.Queue(maxsize=maxsize)
    # producer / consumer 実装（RESEARCH.md Pattern 6 参照）
```

---

### `pagefolio/ocr_dialog.py` — producer-consumer 化（component, event-driven）

**アナログ:** 同ファイル `_render_next_page` / `_worker` 現状実装（line 808-923）

**現状の問題箇所**（改修の起点）:
```python
# line 80: 全ページ base64 を辞書に蓄積（メモリ逼迫の元凶・OCR-PERF-02）
self._images = {}  # page_idx -> b64（メインスレッドでレンダリング済み）

# line 820-843: 全ページ render 完了後に _start_worker_thread を呼ぶ直列フロー
if idx >= total:
    self._start_worker_thread()  # ← 全 render 完了後に起動
    return
# ...
self._images[page_idx] = b64  # ← 全ページを辞書に蓄積
```

**改修後の `_on_run` キュー初期化パターン**:
```python
import queue  # 標準ライブラリ追加

def _on_run(self):
    ...
    # バッファ上限 = 並列度 + 1（余裕係数 1 で飢え防止・D-02）
    self._render_queue = queue.Queue(maxsize=self.concurrency + 1)
    self._render_idx = 0
    self._start_worker_thread()   # worker を先に起動（producer と重なり実行）
    self._render_next_page()      # producer 開始
```

**改修後の `_render_next_page` パターン**（line 808-850 の改修版）:
```python
def _render_next_page(self):
    """メインスレッド（生産者）: 1 ページ render → キューに積む（after(0) 連鎖）"""
    if self._cancel_flag.is_set():
        self._render_queue.put(None)   # キャンセル時は完了シグナルで worker を終わらせる
        self._finish_cancelled()
        return

    total = len(self.page_indices)
    idx = self._render_idx

    if idx >= total:
        # 全ページ完了: ワーカーに終了シグナルを送る（worker が _finish_complete を呼ぶ）
        self._render_queue.put(None)
        return

    page_idx = self.page_indices[idx]
    # 統合プログレス表示（D-03: レンダリング完了数ではなく OCR 完了数を主軸に）
    # レンダリングフェーズの進捗は簡易表示のみ（レンダリング中 cur/total は廃止）

    try:
        page = self.doc[page_idx]
        if has_embedded_text(page):
            extracted = page.get_text()
            self.results[page_idx] = extracted
            self._skipped_pages.add(page_idx)
            # スキップ: キューに積まず次ページへ直接進む
        else:
            b64 = page_to_png_b64(page, scale=self._ocr_scale)
            # キャンセル検出付きブロッキング put（Pitfall-B 対策）
            while True:
                try:
                    self._render_queue.put((page_idx, b64), timeout=0.1)
                    break
                except queue.Full:
                    if self._cancel_flag.is_set():
                        self._render_queue.put(None)
                        return
    except Exception as e:
        logger.exception("ページ処理失敗 (p.%d): %s", page_idx, e)
        self.errors[page_idx] = f"image conversion error: {e}"

    self._render_idx += 1
    self.after(0, self._render_next_page)   # 次ページを連鎖（UI フリーズ回避）
```

**改修後の `_worker` パターン**（line 857-923 の改修版）:
```python
def _worker(self):
    """バックグラウンドスレッド（消費者）: キューから取り出して API 送信（fitz アクセスゼロ・D-03）"""
    done = 0
    total = len(self.page_indices)

    while True:
        try:
            item = self._render_queue.get(timeout=1.0)
        except queue.Empty:
            # タイムアウト: キャンセル確認（Pitfall-E 対策）
            if self._cancel_flag.is_set():
                break
            continue

        if item is None:
            break   # 完了シグナル

        page_idx, b64 = item
        try:
            text = self.provider.ocr_image(b64, self._ocr_prompt)
            self.results[page_idx] = text
            done += 1
        except Exception as e:
            self.errors[page_idx] = str(e)
            done += 1
        finally:
            del b64   # 送信直後に破棄（D-01 メモリ保証・成功基準2）
            self._render_queue.task_done()

        # 進捗通知（after(0) 経由でメインスレッドへ・スレッドセーフ Pitfall 3）
        skipped_count = len(self._skipped_pages)
        self.after(
            0,
            lambda d=done + skipped_count, p=page_idx: self.progress_var.set(
                self._L["ocr_progress_ocr"].format(done=d, total=total, page=p + 1)
            ),
        )
        self.after(0, lambda d=done + skipped_count: self._on_progress_bar(d))

    self.after(0, self._render_results_ordered)
    self.after(0, self._finish_complete)
```

**`_is_cloud_provider` / `_needs_session_key` の gemini 分岐追加**（line 513-562・Pitfall-F）:
```python
# 既存（line 513-526）:
def _is_cloud_provider(self):
    from pagefolio.ocr_providers import ClaudeProvider
    name = self.app.settings.get("ocr_provider", "")
    if name == "claude":
        return True
    if isinstance(self.provider, ClaudeProvider):
        return True
    return False

# 改修後（gemini 追加）:
def _is_cloud_provider(self):
    from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider
    name = self.app.settings.get("ocr_provider", "")
    if name in ("claude", "gemini"):
        return True
    if isinstance(self.provider, (ClaudeProvider, GeminiProvider)):
        return True
    return False

# _needs_session_key も同様に gemini 用 env var を確認する
def _needs_session_key(self):
    if not self._is_cloud_provider():
        return False
    name = self.app.settings.get("ocr_provider", "")
    if name == "gemini":
        import os
        return not bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return not bool(os.environ.get("ANTHROPIC_API_KEY"))
```

**`_apply_llm_settings` の gemini 分岐追加**（line 600-628・Pitfall-G）:
```python
# 既存（line 601-628）の name == "claude" 分岐の隣に追加:
elif name == "gemini":
    from pagefolio.ocr import _resolve_api_key, build_provider
    from pagefolio.ocr_providers import OCRAPIKeyError

    session_keys = getattr(self.app, "_session_api_keys", {})
    try:
        api_key = _resolve_api_key("gemini", session_keys)
    except OCRAPIKeyError:
        api_key = ""
    self.provider = build_provider(self.app.settings, api_key=api_key)
```

**`_clear_text` への `_render_queue` リセット追加**（line 483-494 の改修）:
```python
def _clear_text(self):
    ...
    # 既存のクリア処理に加えて:
    self._render_queue = None   # キュー参照をリセット（再実行時に再生成）
```

---

### `pagefolio/settings.py` — `DEFAULT_SETTINGS` 変更（config, CRUD）

**アナログ:** 同ファイル `_load_settings` の `defaults` ブロック（line 35-53）

**変更パターン**（line 43 と line 51-53 の変更）:
```python
# 既存（line 43）:
"ocr_scale": 2.0,

# D-11 変更後:
"ocr_scale": 1.5,   # 新規ユーザー向け既定値（既存ユーザーの保存値は据え置き）

# 追加（Phase 5 の claude_model と同パターン・line 51-52 の直後に追加）:
# 既存:
"claude_model": "claude-sonnet-4-6",
"ocr_effort": "low",
# Phase 6 追加:
"gemini_model": "gemini-2.5-flash",   # D-08: Gemini 推奨デフォルトモデル
```

---

### `pagefolio/dialogs/llm_config.py` — gemini 分岐・ocr_scale ヒント（component, request-response）

**アナログ:** 同ファイル claude 固有欄（line 183-215）・`_on_provider_change`（line 439-491）

**provider Combobox への gemini 追加**（line 100）:
```python
# 既存（line 100）:
values=["off", "lmstudio", "claude"],

# 変更後:
values=["off", "lmstudio", "claude", "gemini"],
```

**Gemini 固有欄（claude_section_frame と同パターンで新規作成）**:
```python
# claude_section_frame（line 183-215）と同じ構造でフレームを作成
self.gemini_section_frame = tk.Frame(self, bg=C["BG_DARK"])

# gemini_model_var + Combobox（claude_model_var line 195-206 と同パターン）
self.gemini_model_var = tk.StringVar(
    value=self.current_settings.get("gemini_model", "gemini-2.5-flash"),
)
self.gemini_model_combo = ttk.Combobox(
    ...,
    values=GeminiProvider.RECOMMENDED_MODELS,  # ["gemini-2.5-flash", "gemini-2.5-pro"]
)
# モデル更新ボタン（claude_btn_row line 209-215 と同パターン）
```

**`_on_provider_change` への gemini 分岐追加**（line 439-458 の改修）:
```python
# 既存（line 450-458）:
if provider == "claude":
    self.claude_section_frame.pack(fill="x", padx=24, pady=(4, 2))
    self._on_model_change()
else:
    self.claude_section_frame.pack_forget()
    self.effort_frame.pack_forget()
    self.temperature_frame.pack(fill="x", padx=24, pady=2)

# 改修後:
if provider == "claude":
    self.claude_section_frame.pack(fill="x", padx=24, pady=(4, 2))
    self.gemini_section_frame.pack_forget()
    self._on_model_change()
elif provider == "gemini":
    self.gemini_section_frame.pack(fill="x", padx=24, pady=(4, 2))
    self.claude_section_frame.pack_forget()
    self.effort_frame.pack_forget()
    self.temperature_frame.pack(fill="x", padx=24, pady=2)   # temperature のみ表示（D-09）
else:
    self.claude_section_frame.pack_forget()
    self.gemini_section_frame.pack_forget()
    self.effort_frame.pack_forget()
    self.temperature_frame.pack(fill="x", padx=24, pady=2)
```

**`ocr_scale` Spinbox 近傍へのヒント追加**（line 291-306 の `scale_row` の直後）:
```python
# 既存（line 291-306）の scale_row pack 後に追加:
tk.Label(
    scale_row,  # または scale_row の直後の別 Frame
    text=self._L["ocr_scale_tradeoff_hint"],   # lang.py に追加するキー（D-12）
    bg=C["BG_DARK"],
    fg=C["TEXT_SUB"],
    font=self._font(-2),
).pack(side="left", padx=4)
# 参考: 同様のヒントパターンは ocr_temperature_hint（line 271-277）や
# ocr_max_tokens_hint（line 365-371）で使われている
```

**`_apply` での gemini_model 収集追加**（line 598-649 の claude_model 収集パターンを踏襲）:
```python
# 既存（line 610-611）:
llm_settings["claude_model"] = (
    self.claude_model_var.get().strip() or "claude-sonnet-4-6"
)
# 追加（同パターン）:
llm_settings["gemini_model"] = (
    self.gemini_model_var.get().strip() or "gemini-2.5-flash"
)
```

---

### `pagefolio/lang.py` — Gemini 文言追加（config, transform）

**アナログ:** 同ファイル `ocr_provider_name_claude` / `ocr_api_key_missing`（line 292-349・日英同構造）

**追加パターン**（`ocr_provider_name_claude`（line 308/656）の直後に追加）:
```python
# 日本語辞書（line 308 付近の直後）に追加:
"ocr_provider_name_gemini": "Gemini (Google AI)",

# 英語辞書（line 656 付近の直後）に追加:
"ocr_provider_name_gemini": "Gemini (Google AI)",
```

```python
# dual env var エラー文言（ocr_api_key_missing（line 293/641）と同パターン）
# 日本語:
"ocr_api_key_missing_gemini": (
    "APIキーが設定されていません（GEMINI_API_KEY / フォールバック: GOOGLE_API_KEY）。"
    "環境変数を設定するか、入力欄にキーを入力してください。"
),
# 英語:
"ocr_api_key_missing_gemini": (
    "API key is not configured (GEMINI_API_KEY / fallback: GOOGLE_API_KEY). "
    "Set the environment variable or enter the key in the input field."
),
```

```python
# ocr_scale トレードオフヒント文言（ocr_temperature_hint 等の短文パターン踏襲）
# 日本語:
"ocr_scale_tradeoff_hint": "低=速い/安い・高=精度、低スペックは 1.5 推奨",
# 英語:
"ocr_scale_tradeoff_hint": "Low=fast/cheap, High=accuracy. 1.5 recommended for low-spec PCs.",
```

---

### `tests/test_ocr_providers.py` — `TestGeminiProvider*` 追加（test）

**アナログ:** 同ファイル `TestLMStudioProviderBasic` / `TestLMStudioProviderOcrImage`（line 115-218）

**テストクラス構造パターン**（LMStudioProvider テストをそのまま踏襲）:
```python
class _FakeResponse:
    """既存（test_ocr_providers.py line 100-111）をそのまま再利用"""
    def __init__(self, body): ...
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self._body

class TestGeminiProviderBasic:
    """GeminiProvider の基本属性（TestLMStudioProviderBasic line 115-141 と同パターン）"""

    def test_is_ocr_provider_subclass(self): ...
    def test_instantiation(self): ...
    def test_default_concurrency(self):
        assert GeminiProvider.default_concurrency == 1   # LMStudio は 2
    def test_max_concurrency(self):
        assert GeminiProvider.max_concurrency == 1       # LMStudio は 8

class TestGeminiProviderBuildPayload:
    """D-14 ①: payload 構築テスト（inline_data・x-goog-api-key・thinkingBudget=0）"""

    def test_inline_data_format(self):
        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        payload = p._build_payload("ZmFrZQ==", "describe")
        parts = payload["contents"][0]["parts"]
        assert parts[0]["inline_data"]["mime_type"] == "image/png"
        assert parts[0]["inline_data"]["data"] == "ZmFrZQ=="
        assert parts[1]["text"] == "describe"

    def test_thinking_budget_zero(self):
        """generationConfig.thinkingConfig.thinkingBudget == 0（D-09/Pitfall-C）"""
        p = GeminiProvider(api_key="k", model="m")
        payload = p._build_payload("b64", "p")
        assert payload["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0

    def test_x_goog_api_key_header(self, monkeypatch):
        """x-goog-api-key ヘッダーに api_key が設定される（D-05）"""
        from pagefolio import ocr_providers
        captured = {}
        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            body = json.dumps({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
            return _FakeResponse(body)
        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="test-key", model="m")
        p.ocr_image("Zg==", "describe")
        # ヘッダーキー名は Request 内部で capitalize される場合があるため contains 確認
        header_keys_lower = {k.lower(): v for k, v in captured["headers"].items()}
        assert header_keys_lower.get("x-goog-api-key") == "test-key"

class TestGeminiProviderOcrImage:
    """D-14 ②: レスポンス解析テスト（candidates[].content.parts[].text 結合）"""

    def test_success_returns_joined_text(self, monkeypatch): ...
    def test_empty_candidates_raises_runtime_error(self, monkeypatch):
        """candidates が空のとき RuntimeError（安全フィルタ・Pitfall-D）"""
        ...
    def test_retryable_429(self, monkeypatch): ...   # TestLMStudioProviderOcrImage と同パターン

class TestGeminiProviderListModels:
    """D-14 ③: list_models（supportedGenerationMethods フィルタ）"""

    def test_returns_recommended_when_no_key(self): ...
    def test_filters_by_generate_content_method(self, monkeypatch): ...
```

---

### `tests/test_ocr.py` — `TestResolveApiKeyGemini` / `TestProducerConsumerMemory` 追加（test）

**アナログ:** 同ファイル `FakeProvider`（line 23-39）・既存の `run_parallel` テストパターン

**D-14 ④: dual env var 解決テスト**:
```python
class TestResolveApiKeyGemini:
    """GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバック（D-06）"""

    def test_gemini_api_key_priority(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "primary-key")
        monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
        key = ocr._resolve_api_key("gemini", {})
        assert key == "primary-key"

    def test_google_api_key_fallback(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
        key = ocr._resolve_api_key("gemini", {})
        assert key == "fallback-key"

    def test_session_key_used_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        key = ocr._resolve_api_key("gemini", {"gemini": "session-key"})
        assert key == "session-key"

    def test_raises_when_all_missing(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        from pagefolio.ocr_providers import OCRAPIKeyError
        with pytest.raises(OCRAPIKeyError) as exc_info:
            ocr._resolve_api_key("gemini", {})
        assert exc_info.value.env_var == "GEMINI_API_KEY"
```

**D-13: メモリ非蓄積テスト**（FakeProvider を使った in-flight 計測）:
```python
class TestProducerConsumerMemory:
    """producer-consumer の同時保持画像数がバッファ上限を超えないことを検証（D-13/成功基準2）"""

    def test_in_flight_count_never_exceeds_maxsize(self):
        """FakeProvider.ocr_image 呼び出し時点で同時保持される b64 数が maxsize 以内"""
        import threading
        import queue

        maxsize = 3
        in_flight_lock = threading.Lock()
        in_flight_count = [0]
        max_observed = [0]

        def counting_ocr_fn(b64):
            with in_flight_lock:
                in_flight_count[0] += 1
                max_observed[0] = max(max_observed[0], in_flight_count[0])
            time.sleep(0.01)  # API 処理時間を模擬
            with in_flight_lock:
                in_flight_count[0] -= 1
            return f"text-{b64}"

        # run_with_bounded_buffer（ocr.py に切り出す Tk 非依存ヘルパー）を直接呼ぶ
        page_indices = list(range(20))   # 20 ページ = 100 ページの代替（テスト速度）
        results = {}
        ocr.run_with_bounded_buffer(
            render_fn=lambda i: f"b64-page-{i}",
            ocr_fn=counting_ocr_fn,
            page_indices=page_indices,
            maxsize=maxsize,
            is_cancelled=lambda: False,
            on_done=lambda i, t: results.update({i: t}),
        )
        assert max_observed[0] <= maxsize, (
            f"同時保持数 {max_observed[0]} がバッファ上限 {maxsize} を超えた"
        )
        assert len(results) == len(page_indices)
```

---

## 共有パターン

### 認証ヘッダー非汚染パターン（全 Provider・全 API 呼び出し）
**ソース:** `pagefolio/settings.py` line 16 / `pagefolio/ocr.py` line 53-88
**適用先:** `GeminiProvider.__init__`・`_resolve_api_key`・`_apply_llm_settings`
```python
# _SENSITIVE_KEYS（settings.py line 16）—— 既に "gemini_api_key" が含まれている
_SENSITIVE_KEYS = {"claude_api_key", "gemini_api_key", "anthropic_api_key", "api_key"}
# → api_key は settings への書き込み禁止・ログ出力禁止・引数注入のみ（D-01/D-05）
```

### スレッドセーフ UI 更新パターン（全バックグラウンドスレッド）
**ソース:** `pagefolio/ocr_dialog.py` `_worker` line 876-894
**適用先:** producer-consumer 改修後の `_worker` 進捗通知
```python
# バックグラウンドスレッド → after(0) 経由でメインスレッドへ委譲（Pitfall 3）
self.after(
    0,
    lambda d=done, p=page_idx: self.progress_var.set(...),
)
self.after(0, lambda d=done: self._on_progress_bar(d))
```

### 関数内 import で循環 import 回避パターン
**ソース:** `pagefolio/ocr.py` line 72/260/275
**適用先:** `build_provider` の gemini 分岐・`_start_ocr` の gemini 追加
```python
# 既存パターン（line 275）:
from pagefolio.ocr_providers import ClaudeProvider
# Phase 6 追加（同パターン）:
from pagefolio.ocr_providers import GeminiProvider
```

### エラーハンドリング共通パターン（Provider の `ocr_image`）
**ソース:** `pagefolio/ocr_providers.py` `ClaudeProvider.ocr_image` line 329-358
**適用先:** `GeminiProvider.ocr_image` の例外処理（構造は完全に同一・ヘッダーのみ差し替え）

### テーマカラー参照パターン
**ソース:** `pagefolio/dialogs/llm_config.py` 全体
**適用先:** llm_config.py への Gemini 欄追加時（ハードコード禁止）
```python
# 正: C["BG_DARK"], C["TEXT_MAIN"], C["TEXT_SUB"], C["SUCCESS"], C["ACCENT"]
# 誤: bg="#1a1a2e"（ハードコード禁止）
```

---

## アナログなし（なし）

Phase 6 の全ファイルは既存コードベースに強力なアナログが存在する。新規外部パターンの参照が必要なファイルはない。

---

## 実装上の注意点

### Pitfall-A: LM Studio 並列度の低下（設計判断）
`_worker` の直列ループ採用により LM Studio の実効並列度が 1 になる。Phase 6 の目的（クラウドのメモリ節約）に対しては許容済み（RESEARCH.md Pattern 5 参照）。リリースノートに明記すること。

### Pitfall-B: キャンセル応答性
`queue.Queue.put()` は timeout=0.1 のループで呼び、`queue.Full` のたびに `_cancel_flag.is_set()` を確認する。

### Pitfall-C: thinkingConfig の配置
`generationConfig` の **直下**（トップレベルではない）。`generationConfig.thinkingConfig.thinkingBudget=0`。

### Pitfall-D: candidates 空チェック
`candidates[0]` への直接アクセス禁止。必ず `if not candidates: raise RuntimeError(...)` を最初に確認。

### Pitfall-E: キャンセル時の worker 終了
キャンセル検出時は必ず `self._render_queue.put(None)` で worker に完了シグナルを送る。

### Pitfall-F: `_is_cloud_provider` / `_needs_session_key` の gemini 分岐
`ocr_dialog.py` の provider 判定系メソッドすべてに `"gemini"` 分岐を追加すること。

### Pitfall-G: `_apply_llm_settings` の gemini 分岐
`ocr_dialog.py` の `_apply_llm_settings` に `elif name == "gemini":` 分岐を追加すること。

---

## メタデータ

**アナログ検索範囲:** `pagefolio/`・`tests/`
**スキャンファイル数:** 8
**パターン抽出日:** 2026-06-07
