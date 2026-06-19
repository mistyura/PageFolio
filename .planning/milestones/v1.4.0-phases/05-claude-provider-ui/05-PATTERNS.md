# Phase 5: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI — Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 6 新規/変更対象ファイル
**Analogs found:** 6 / 6

---

## File Classification

| 新規/変更ファイル | Role | Data Flow | 最近接アナログ | 一致度 |
|-----------------|------|-----------|--------------|--------|
| `pagefolio/ocr_providers.py`（ClaudeProvider・OCRRetryableError 追加） | service | request-response | `pagefolio/ocr_providers.py` LMStudioProvider（既存） | exact |
| `pagefolio/ocr.py`（build_provider claude 分岐・run_parallel バックオフ層） | service | request-response / concurrent | `pagefolio/ocr.py` build_provider・run_parallel（既存） | exact |
| `pagefolio/ocr_dialog.py`（コスト確認・セッションキー入力・待機中表示） | dialog/UI | event-driven | `pagefolio/ocr_dialog.py` OCRDialog（既存） | exact |
| `pagefolio/dialogs/llm_config.py`（provider DD・モデル更新・effort/temperature 切替） | dialog/UI | request-response | `pagefolio/dialogs/llm_config.py` LLMConfigDialog（既存） | exact |
| `pagefolio/settings.py`（キーガード観点確認・DEFAULT_SETTINGS 追加） | utility/config | transform | `pagefolio/settings.py` _load_settings・_save_settings（既存） | exact |
| `pagefolio/lang.py`（最小文言追加） | config | transform | `pagefolio/lang.py` ocr_provider_unsupported キー（既存） | exact |

---

## Pattern Assignments

### `pagefolio/ocr_providers.py` — ClaudeProvider・OCRRetryableError 追加

**アナログ:** `pagefolio/ocr_providers.py` の `LMStudioProvider`（同ファイル内）

**インポートパターン**（行 1–13）:
```python
import abc
import json
import logging
import socket
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
```
ClaudeProvider も同じインポートブロックを使う。`os` を追加して環境変数読み取りに使用。

**新規例外クラスパターン**（行 58–63、OCRAPIKeyError を参照）:
```python
class OCRAPIKeyError(RuntimeError):
    """APIキー未設定を示す専用例外。環境変数名を保持する。"""

    def __init__(self, env_var):
        self.env_var = env_var
        super().__init__(f"環境変数 {env_var} が設定されていません")
```
`OCRRetryableError` も同じ形で追加する。`retry_after: float | None` を保持する属性を加える:
```python
class OCRRetryableError(RuntimeError):
    """429/5xx リトライ可能エラー。retry_after（秒）を保持する。"""

    def __init__(self, message, retry_after=None):
        self.retry_after = retry_after
        super().__init__(message)
```

**Provider クラス宣言・並列度クラス属性パターン**（行 66–76、LMStudioProvider を参照）:
```python
class LMStudioProvider(OCRProvider):
    default_concurrency = 2
    max_concurrency = 8

    def __init__(self, url, model, timeout=120, max_tokens=-1, temperature=0.1):
        self.url = url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
```
ClaudeProvider は `default_concurrency = 2` / `max_concurrency = 2`（OCR-PERF-03 の Claude=2 制約）。
`__init__` は `api_key, model, timeout=120, max_tokens=4096, temperature=0.1` を受け取る。

**_build_payload パターン**（行 92–113）:
```python
def _build_payload(self, b64_png, prompt):
    return {
        "model": self.model or "local-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_png}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": self.max_tokens,
        "temperature": self.temperature,
        "stream": False,
    }
```
Claude 版は content フォーマットが異なる（STACK.md §Claude 画像フォーマット）:
```python
def _build_payload(self, b64_png, prompt):
    payload = {
        "model": self.model,
        "max_tokens": self.max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_png,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    # effort 対応モデルのみ output_config を付加（D-16）
    if self._supports_effort():
        payload["output_config"] = {"effort": self.effort}
    else:
        payload["temperature"] = self.temperature
    return payload
```

**ocr_image パターン（urllib POST + 例外変換）**（行 115–160）:
```python
def ocr_image(self, b64_png, prompt, **kwargs):
    endpoint = self.url.rstrip("/") + "/v1/chat/completions"
    payload = self._build_payload(b64_png, prompt)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
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
    try:
        result = json.loads(body)
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
```
Claude 版は以下を変更する:
- `endpoint = "https://api.anthropic.com/v1/messages"`
- ヘッダーに `x-api-key: self.api_key` / `anthropic-version: 2023-06-01` を追加
- HTTPError 429 を `OCRRetryableError` に変換（`Retry-After` ヘッダを読む）
- HTTPError 5xx を `OCRRetryableError` に変換
- レスポンス解析: `content[]` を走査して `type=="text"` ブロックを結合

**list_models パターン**（行 162–192）:
```python
def list_models(self):
    timeout = 10
    endpoint = self.url.rstrip("/") + "/v1/models"
    req = urllib.request.Request(endpoint, method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except socket.timeout as e:
        raise TimeoutError(f"timed out after {timeout}s") from e
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"timed out after {timeout}s") from e
        raise ConnectionError(str(reason)) from e
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Unexpected response: {body[:500]}") from e
    return [m.get("id") for m in data.get("data", []) if m.get("id")]
```
Claude 版は `GET https://api.anthropic.com/v1/models`、`x-api-key` ヘッダーを付加、
`data[].capabilities.image_input.supported` が True のモデルのみ返す（ビジョン対応フィルタ）。
キー未設定の場合は静的リスト（haiku-4-5 / sonnet-4-6 / opus-4-8）を返して例外を出さない（D-08）。

---

### `pagefolio/ocr.py` — build_provider claude 分岐・run_parallel バックオフ層

**アナログ:** `pagefolio/ocr.py` の `build_provider`（行 179–205）・`run_parallel`（行 83–176）

**build_provider 拡張点**（行 190–205）:
```python
def build_provider(settings):
    from pagefolio.ocr_providers import LMStudioProvider

    name = settings.get("ocr_provider", "lmstudio")

    if name in ("lmstudio", "", "off"):
        return LMStudioProvider(...)
    # Phase 5/6/7 で追加するプロバイダはここに分岐を追加する
    raise ValueError(f"未対応のプロバイダ: {name}")
```
`claude` 分岐を追加する。`api_key` は `settings` には入れず、引数として受け取るか
`os.environ.get("ANTHROPIC_API_KEY", "")` で解決する。**キーを settings に格納しない**（D-01・D-05）:
```python
    elif name == "claude":
        from pagefolio.ocr_providers import ClaudeProvider
        # api_key は settings には持たせない（D-01）
        # 呼び出し元（_start_ocr）からキーを注入するか、ここで env 解決する
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        return ClaudeProvider(
            api_key=api_key,
            model=settings.get("claude_model", "claude-sonnet-4-6"),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            max_tokens=int(settings.get("ocr_max_tokens", 4096)),
            temperature=float(settings.get("ocr_temperature", 0.1)),
        )
```

**run_parallel バックオフ拡張点**（行 129–144、`_call` 内部関数）:
```python
def _call(page_idx, b64):
    if _is_cancelled() or fatal["msg"] is not None:
        return ("cancel", page_idx, None)
    try:
        text = provider.ocr_image(b64, prompt)
        return ("ok", page_idx, text)
    except ConnectionError as e:
        return ("fatal_conn", page_idx, str(e))
    except TimeoutError as e:
        return ("fatal_timeout", page_idx, str(e))
    except RuntimeError as e:
        return ("err", page_idx, str(e))
    except Exception as e:
        logger.exception("OCR 呼び出し失敗: %s", e)
        return ("err", page_idx, str(e))
```
`OCRRetryableError` を追加して指数バックオフ（最大3回・`Retry-After` 優先）を組み込む:
```python
    except OCRRetryableError as e:
        return ("retryable", page_idx, str(e), e.retry_after)
```
`as_completed` ループで `"retryable"` ステータスを受け取ったら `time.sleep` してリトライ。
`on_progress` コールバックで「待機中（リトライ n/3）」を `"waiting"` ステータスとして渡す（D-15）。

**_start_ocr のキー解決結合点**（行 226–278）:
```python
def _start_ocr(self, page_indices):
    from pagefolio.ocr_dialog import OCRDialog
    ...
    try:
        provider = build_provider(self.settings)
    except ValueError as e:
        ...
```
Phase 5 では `build_provider` 呼び出し前に `_resolve_api_key(self.settings)` を実行し、
環境変数未設定かつセッション属性にもキーがない場合は `OCRAPIKeyError` を raise させる。
セッションキーは `self._session_api_keys`（プロバイダ別 dict、D-01）から取得して `build_provider` に渡す:
```python
        api_key = (
            os.environ.get("ANTHROPIC_API_KEY")
            or self._session_api_keys.get("claude", "")
        )
        provider = build_provider(self.settings, api_key=api_key)
```

---

### `pagefolio/ocr_dialog.py` — コスト確認・セッションキー入力・待機中表示

**アナログ:** `pagefolio/ocr_dialog.py` OCRDialog（同ファイル）

**self.after(0, ...) スレッド安全パターン**（行 557–563、`_worker` 内の `on_progress`）:
```python
def on_progress(done, page_idx, status):
    self.after(
        0,
        lambda d=done + skipped_count, p=page_idx: self.progress_var.set(
            self._L["ocr_progress_ocr"].format(done=d, total=total, page=p + 1)
        ),
    )
    self.after(0, lambda d=done + skipped_count: self._on_progress_bar(d))
```
「待機中」進捗（D-15）は `status == "waiting"` のとき分岐:
```python
    if status == "waiting":
        self.after(0, lambda p=page_idx, n=retry_n: self.progress_var.set(
            self._L["ocr_waiting_retry"].format(page=p + 1, n=n, max=3)
        ))
    else:
        self.after(0, lambda d=...: self.progress_var.set(...))
```

**コスト確認ダイアログの配置**（_on_run の実行開始前、クラウドプロバイダのみ）:
```python
def _on_run(self):
    if self._started:
        return
    # クラウドプロバイダの場合のみコスト確認ゲートを挟む（D-13）
    if self._is_cloud_provider():
        if not self._confirm_cost():
            return
    self._started = True
    ...
```
`_confirm_cost()` は `tk.Toplevel` のモーダルダイアログ（`grab_set()`）または `messagebox.askyesno` を使う。
ダイアログ内容（D-12）: 送信先ホスト名・「ページ画像が外部 API に送信される」・概算コスト。

**セッションキー入力欄（マスク表示、クラウドかつキー未設定時のみ）**:
```python
# Entry with show="*" — masking pattern（D-04）
self.api_key_entry = tk.Entry(
    key_frame,
    show="*",
    textvariable=self.api_key_var,
    font=self._font(-1),
    bg=C["BG_CARD"],
    fg=C["TEXT_MAIN"],
    insertbackground=C["TEXT_MAIN"],
    relief="flat",
)
```
`api_key_var` の値を `self.app._session_api_keys["claude"]` に設定するが `settings` には入れない（D-01）。

**_on_run での provider 再生成パターン**（行 481–489、現状 LMStudioProvider 固定）:
```python
from pagefolio.ocr_providers import LMStudioProvider
self.provider = LMStudioProvider(
    url=url,
    model=model,
    timeout=self._effective_timeout,
    max_tokens=max_tokens,
    temperature=temperature,
)
```
Phase 5 では `build_provider` を経由してプロバイダ種別を自動判定する形に変更し、
ClaudeProvider へのキー注入をここで行う（api_key を provider インスタンスに渡す）。

---

### `pagefolio/dialogs/llm_config.py` — provider DD・モデル更新・effort/temperature 切替

**アナログ:** `pagefolio/dialogs/llm_config.py` LLMConfigDialog（同ファイル）

**Var + クランプ保存パターン**（行 136–152、`ocr_scale_var` を例に）:
```python
self.ocr_scale_var = tk.DoubleVar(
    value=float(self.current_settings.get("ocr_scale", 2.0)),
)
tk.Spinbox(
    scale_row,
    from_=1.0, to=4.0, increment=0.5,
    textvariable=self.ocr_scale_var,
    width=6, ...
).pack(...)
```
`_apply()` での保存（行 394–398）:
```python
try:
    llm_settings["ocr_scale"] = max(
        1.0, min(4.0, float(self.ocr_scale_var.get()))
    )
except (tk.TclError, ValueError):
    llm_settings["ocr_scale"] = 2.0
```
provider ドロップダウン・effort 欄も同じパターンで追加する:
```python
self.provider_var = tk.StringVar(
    value=self.current_settings.get("ocr_provider", "off"),
)
self.provider_combo = ttk.Combobox(
    provider_row,
    textvariable=self.provider_var,
    values=["off", "lmstudio", "claude"],  # Phase 6 で gemini 追加
    state="readonly",
    font=self._font(-1),
)
self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)
```

**provider 変更時の欄切替パターン（_on_provider_change）**:
コンボボックスの `<<ComboboxSelected>>` イベントで `pack_forget()` / `pack()` を使い、
provider に応じて URL 欄（lmstudio のみ）・effort/temperature 欄を動的に切り替える:
```python
def _on_provider_change(self, _event=None):
    provider = self.provider_var.get()
    # LM Studio 固有欄
    if provider == "lmstudio":
        self.url_section_frame.pack(...)
    else:
        self.url_section_frame.pack_forget()
    # effort / temperature 欄切替（D-17）
    model = self.model_var.get()
    if self._model_supports_effort(model):
        self.effort_frame.pack(...)
        self.temperature_frame.pack_forget()
    else:
        self.temperature_frame.pack(...)
        self.effort_frame.pack_forget()
```

**ステータス表示パターン**（行 328–344、`_set_lm_status`）:
```python
def _set_lm_status(self, text, kind="info"):
    color = {"ok": C["SUCCESS"], "fail": C["ACCENT"], "info": C["WARNING"]}.get(
        kind, C["TEXT_MAIN"]
    )
    self.lm_status_var.set(text)
    try:
        self.lm_status_label.configure(fg=color)
    except tk.TclError:
        pass
    try:
        self.update_idletasks()
    except tk.TclError:
        pass
```
モデル更新ボタン（D-08）にも同パターンを使う。キー未設定時は静的リストにフォールバックし、
`_set_lm_status` で "環境変数 ANTHROPIC_API_KEY が未設定のため静的リストを表示中" などを表示する。

---

### `pagefolio/settings.py` — キーガード観点確認

**アナログ:** `pagefolio/settings.py` `_load_settings`・`_save_settings`（同ファイル）

**_save_settings パターン**（行 60–67）:
```python
def _save_settings(settings):
    """設定を保存する"""
    try:
        path = _get_settings_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug("設定ファイル保存失敗: %s", e)
```
`settings` 辞書をそのまま JSON 化する。**キーを `settings` に入れない（D-01）が唯一のガード手段**。
Phase 5 では `_save_settings` 内に防御的アサートを追加してキー混入を検知する:
```python
_SENSITIVE_KEYS = {"claude_api_key", "gemini_api_key", "anthropic_api_key"}

def _save_settings(settings):
    # 防御: 機密キーが settings に混入していないかチェック（D-01 構造的ガード）
    for k in _SENSITIVE_KEYS:
        if k in settings:
            logger.error("機密キー '%s' が settings に混入しています（保存をスキップ）", k)
            # キーを除去してから保存する（最悪ケースへの安全フォールバック）
            settings = {key: v for key, v in settings.items() if key not in _SENSITIVE_KEYS}
    ...
```

**DEFAULT_SETTINGS への `ocr_provider: "off"` 追加確認**（行 31–46）:
```python
defaults = {
    ...
    "ocr_provider": "off",  # V14-D-03: 安全デフォルト（Phase 4 で追加済み）
}
```
Phase 5 では `claude_model` / `ocr_effort` キーも defaults に追加する（キー自体は無害な設定値）:
```python
    "claude_model": "claude-sonnet-4-6",
    "ocr_effort": "low",  # effort 対応モデル時の既定値（D-17）
```

---

### `pagefolio/lang.py` — 最小文言追加

**アナログ:** `pagefolio/lang.py` の `ocr_provider_unsupported` キー（行 288–290）:
```python
"ocr_provider_unsupported": (
    "未対応の OCR プロバイダが設定されています: {name}\n"
    "設定を確認してください。"
),
```
同じスタイルで Phase 5 の最小文言を追加する（ja/en 両方に追加必須）:

| 追加キー | 用途 |
|---------|------|
| `ocr_api_key_missing` | キー未設定エラー（D-06）例: `"APIキーが設定されていません（{env_var}）"` |
| `ocr_cost_confirm_title` | コスト確認ダイアログタイトル（D-12） |
| `ocr_cost_confirm_msg` | コスト確認本文（ページ数・概算・送信先ホスト・課金注意） |
| `ocr_session_key_label` | セッションキー入力欄ラベル（D-03） |
| `ocr_waiting_retry` | 「待機中（リトライ {n}/{max}）」進捗表示（D-15） |
| `ocr_provider_label` | provider ドロップダウンのラベル（D-07） |
| `ocr_effort_label` | effort 選択欄のラベル（D-17） |

---

## Shared Patterns

### テーマカラー参照
**Source:** `pagefolio/constants.py`（`C` 辞書）
**Apply to:** 全 UI ファイル
全ウィジェットの色は `C["BG_DARK"]` 等を使う。ハードコード文字列は禁止。

### フォントサイズ
**Source:** `pagefolio/ocr_dialog.py` `_default_font`（行 83–87）
**Apply to:** 全ダイアログ
```python
font=self._font(0)      # 標準
font=self._font(-1)     # 小
font=self._font(2, "bold")  # 見出し
```

### モーダル作法
**Source:** `pagefolio/dialogs/llm_config.py` `__init__`（行 50）
**Apply to:** コスト確認ダイアログ・セッションキー入力欄
```python
self.grab_set()
```

### スレッド安全 UI 更新
**Source:** `pagefolio/ocr_dialog.py` `_worker`（行 556–591）
**Apply to:** `run_parallel` バックオフ層の「待機中」進捗更新
```python
self.after(0, lambda: self.progress_var.set(...))
```
バックグラウンドスレッドから直接 Tkinter ウィジェットを操作しない。`after(0, ...)` を使う。

### 例外正規化（urllib）
**Source:** `pagefolio/ocr_providers.py` `LMStudioProvider.ocr_image`（行 142–154）
**Apply to:** `ClaudeProvider.ocr_image` / `ClaudeProvider.list_models`
```python
except urllib.error.HTTPError as e:
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
ClaudeProvider では `HTTPError.code == 429` または `e.code >= 500` を `OCRRetryableError` に変換する前段を追加する。

### APIキー非永続化ガード
**Source:** `pagefolio/settings.py` `_save_settings`（行 60–67）+ D-01 設計決定
**Apply to:** `pagefolio/ocr_dialog.py`・`pagefolio/ocr.py`・`pagefolio/app.py`（`_session_api_keys` 属性）
- セッションキーは `self._session_api_keys: dict[str, str]` にのみ保持する
- `settings` 辞書に API キー相当の値を入れる操作を行わない
- `_save_settings` 呼び出し前に `_SENSITIVE_KEYS` チェックを挟む（防御的ガード）

---

## No Analog Found

なし。全ファイルに既存コードベース内の近接アナログが存在する。

---

## Metadata

**Analog search scope:** `pagefolio/ocr_providers.py`・`pagefolio/ocr.py`・`pagefolio/ocr_dialog.py`・`pagefolio/dialogs/llm_config.py`・`pagefolio/settings.py`・`pagefolio/lang.py`
**Files scanned:** 6
**Pattern extraction date:** 2026-06-06
