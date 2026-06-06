# Phase 4: プロバイダ抽象化 - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 5（新規 1 + 改修 4）
**Analogs found:** 5 / 5

---

## File Classification

| 新規/改修ファイル | Role | Data Flow | 最近傍アナログ | 一致度 |
|-----------------|------|-----------|--------------|--------|
| `pagefolio/ocr_providers.py` | service（抽象基底 + Provider 実装） | request-response | `pagefolio/plugins.py`（基底クラス + 具体実装パターン） | role-match |
| `pagefolio/ocr.py` | service + mixin（リファクタ） | request-response / event-driven | `pagefolio/ocr.py`（自身の現行実装） | exact |
| `pagefolio/ocr_dialog.py` | dialog（スレッド境界リファクタ） | event-driven / request-response | `pagefolio/ocr_dialog.py`（自身の現行 _worker） | exact |
| `pagefolio/settings.py` | utility（デフォルト値追加） | transform | `pagefolio/settings.py`（自身の `_load_settings`） | exact |
| `pagefolio/lang.py` | config（文言キー追加） | transform | `pagefolio/lang.py`（自身の `ocr_*` キー群） | exact |

---

## Pattern Assignments

### `pagefolio/ocr_providers.py`（新規 — service, request-response）

**アナログ:** `pagefolio/plugins.py`（抽象基底 + 具体クラスの構造）

**インポートパターン（ocr.py lines 1-16 を参考）:**
```python
# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ抽象基底クラスと各プロバイダ実装"""

import abc
import json
import logging
import socket
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
```

**抽象基底クラスパターン（plugins.py lines 27-77 の PDFEditorPlugin を参考）:**
```python
class PDFEditorPlugin:
    """プラグイン基底クラス。プラグインはこのクラスを継承して作成する。"""
    name = "Unnamed Plugin"
    version = "0.0.0"

    def on_load(self, app):
        """プラグインがロードされた時に呼ばれる"""
        pass
    # ... フックメソッド群（pass で空実装）
```
→ `OCRProvider` は `abc.ABC` を使う点が異なるが、クラス属性（`default_concurrency`, `max_concurrency`）と抽象メソッド（`ocr_image`, `list_models`）の宣言構造を踏襲する。

**例外規約パターン（ocr.py lines 84-133 の `call_lm_studio`）:**
```python
def call_lm_studio(url, model, b64_png, prompt, timeout=..., ...):
    """LM Studio Chat Completions API を呼び出して結果テキストを返す。

    例外:
      ConnectionError: 接続失敗（LM Studio 未起動等）
      TimeoutError: タイムアウト
      RuntimeError: APIエラー（Vision 非対応モデル等）
    """
    ...
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {err_body or e.reason}") from e
    except socket.timeout as e:
        raise TimeoutError(f"timed out after {timeout}s") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"timed out after {timeout}s") from e
        raise ConnectionError(str(reason)) from e
    ...
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
```
→ `LMStudioProvider.ocr_image()` はこの例外マッピングをそのまま継承する。
→ `OCRProvider` docstring の「例外規約」セクションに `ConnectionError` / `TimeoutError` / `RuntimeError` / `OCRAPIKeyError` を明記する。

**urllib 直叩きパターン（ocr.py lines 100-133）:**
```python
endpoint = url.rstrip("/") + "/v1/chat/completions"
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(  # noqa: S310
    endpoint,
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        body = resp.read().decode("utf-8")
except urllib.error.HTTPError as e:
    ...
```
→ ClaudeProvider / GeminiProvider も同じ `urllib.request` 直叩きパターンを踏襲（`# noqa: S310` 必須）。

**モデル一覧取得パターン（ocr.py lines 236-263 の `fetch_lm_studio_models`）:**
```python
def fetch_lm_studio_models(url, timeout=10):
    endpoint = url.rstrip("/") + "/v1/models"
    req = urllib.request.Request(endpoint, method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except socket.timeout as e:
        raise TimeoutError(f"timed out after {timeout}s") from e
    ...
    return [m.get("id") for m in data.get("data", []) if m.get("id")]
```
→ `LMStudioProvider.list_models()` はこのロジックを `self.url` / `self.timeout` を使って内包する形で移植する。

---

### `pagefolio/ocr.py`（改修 — service + mixin）

**アナログ:** `pagefolio/ocr.py`（自身の現行実装 — 骨格を維持しつつリファクタ）

**`call_lm_studio_parallel` → `run_parallel()` 一般化のコア骨格（ocr.py lines 136-233）:**
```python
def call_lm_studio_parallel(
    url, model, prompt, images_b64, page_indices,
    concurrency=DEFAULT_OCR_CONCURRENCY,
    ...
    on_progress=None,
    is_cancelled=None,
):
    workers = max(1, min(MAX_OCR_CONCURRENCY, int(concurrency)))
    targets = [(p, images_b64[p]) for p in page_indices if p in images_b64]
    if not targets:
        return {}, {}, None, None
    workers = min(workers, len(targets))

    results = {}
    errors = {}
    fatal = {"msg": None, "kind": None}

    def _is_cancelled():
        return bool(is_cancelled and is_cancelled())

    def _call(page_idx, b64):
        if _is_cancelled() or fatal["msg"] is not None:
            return ("cancel", page_idx, None)
        try:
            text = call_lm_studio(url, model, b64, prompt, ...)
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

    done = 0
    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        future_to_page = {executor.submit(_call, p, b64): p for p, b64 in targets}
        for future in as_completed(future_to_page):
            if _is_cancelled():
                break
            status, page_idx, payload = future.result()
            if status == "ok":
                results[page_idx] = payload
            elif status == "err":
                errors[page_idx] = payload
            elif status in ("fatal_conn", "fatal_timeout"):
                if fatal["msg"] is None:
                    fatal["msg"] = payload
                    fatal["kind"] = (
                        "connection" if status == "fatal_conn" else "timeout"
                    )
                break
            elif status == "cancel":
                continue
            done += 1
            if on_progress is not None:
                try:
                    on_progress(done, page_idx, status)
                except Exception as e:
                    logger.debug("on_progress コールバック失敗: %s", e)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return results, errors, fatal["msg"], fatal["kind"]
```
→ `run_parallel(provider, images_b64, page_indices, concurrency, ...)` へのリファクタでは、
  `_call` 内の `call_lm_studio(url, model, b64, ...)` を `provider.ocr_image(b64, prompt)` に置き換える。
  `workers` のクランプを `MAX_OCR_CONCURRENCY` 定数から `provider.max_concurrency` に変更する。

**`OCRMixin._start_ocr` 設定読み出しパターン（ocr.py lines 284-320）:**
```python
def _start_ocr(self, page_indices):
    from pagefolio.ocr_dialog import OCRDialog

    url = self.settings.get("lm_studio_url", DEFAULT_LM_STUDIO_URL)
    model = self.settings.get("lm_studio_model", "")
    preset = self.settings.get("ocr_prompt_preset", "text")
    scale = float(self.settings.get("ocr_scale", DEFAULT_OCR_SCALE))
    timeout = int(self.settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT))
    max_tokens = int(self.settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
    temperature = float(
        self.settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)
    )
    concurrency = max(
        1,
        min(
            MAX_OCR_CONCURRENCY,
            int(self.settings.get("ocr_concurrency", DEFAULT_OCR_CONCURRENCY)),
        ),
    )

    OCRDialog(
        self.root,
        app=self,
        doc=self.doc,
        page_indices=page_indices,
        url=url,
        model=model,
        ...
    )
```
→ `build_provider(settings)` を呼んで `provider` オブジェクトを生成し、`OCRDialog` に `provider=provider` として渡す形に変更する。
→ `concurrency` のクランプ上限は `provider.max_concurrency` を使う（D-10）。

**`page_to_png_b64` — 汎用ユーティリティとして残置（ocr.py lines 46-51）:**
```python
def page_to_png_b64(page, scale=DEFAULT_OCR_SCALE):
    """fitz.Page を PNG → base64 文字列に変換する（プロバイダ非依存）"""
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    return base64.b64encode(png_bytes).decode("ascii")
```
→ D-13 通りそのまま `ocr.py` に残置する。Provider 内には置かない。

---

### `pagefolio/ocr_dialog.py`（改修 — dialog, event-driven）

**アナログ:** `pagefolio/ocr_dialog.py`（自身の現行 `_worker` — スレッド境界を整理）

**`self.after(0, ...)` スレッド安全 UI 更新パターン（ocr_dialog.py lines 464-521）:**
```python
# ワーカースレッド内から UI を更新する正しい方法
def on_progress(done, page_idx, status):
    self.after(
        0,
        lambda d=done, p=page_idx: self.progress_var.set(
            self._L["ocr_progress_ocr"].format(done=d, total=total, page=p + 1)
        ),
    )
    self.after(0, lambda d=done: self._on_progress_bar(d))
```
→ 新しいコールバック・進捗更新はすべて同じ `self.after(0, lambda: ...)` パターンを使う。
→ `on_progress` の呼び出しは `try/except` で囲む（ocr.py line 228-229 参照）。

**フェーズ1 → フェーズ2 → フェーズ3 の構造（ocr_dialog.py lines 439-522）:**
```python
def _worker(self, prompt):
    # ... パラメータ検証（try/except (tk.TclError, ValueError): ... のパターン）
    total = len(self.page_indices)

    # フェーズ1: 全ページの画像を直列で変換
    # （fitz の同一 Document 並行アクセスを回避するためここは並列化しない）
    images = {}
    for i, page_idx in enumerate(self.page_indices, start=1):
        if self._cancel_flag.is_set():
            self.after(0, self._finish_cancelled)
            return
        self.after(0, lambda cur=i, tot=total: self.progress_var.set(...))
        try:
            b64 = page_to_png_b64(self.doc[page_idx], scale=scale)
            images[page_idx] = b64
        except Exception as e:
            logger.exception("ページ画像変換失敗: %s", e)
            self.errors[page_idx] = f"image conversion error: {e}"

    # フェーズ2: API 呼び出しを並列化
    results, errors, fatal_msg, fatal_kind = call_lm_studio_parallel(...)
    self.results.update(results)
    self.errors.update(errors)

    # フェーズ3: UI へ反映
    if fatal_msg is not None:
        self.after(0, lambda m=fatal_msg, k=fatal_kind: self._finish_error(m, kind=k))
        return
    if self._cancel_flag.is_set():
        self.after(0, self._finish_cancelled)
        return
    self.after(0, self._render_results_ordered)
    self.after(0, self._finish_complete)
```
→ Phase 4 の改修では、フェーズ1に `has_embedded_text()` 判定を追加し、スキップページを
  `images` に積まずに結果辞書へ直接投入する。フェーズ2の `call_lm_studio_parallel(...)` を
  `run_parallel(provider, images, self.page_indices, ...)` に置き換える。

**パラメータ検証パターン（ocr_dialog.py lines 443-458）:**
```python
try:
    scale = max(1.0, min(4.0, float(self.scale_var.get())))
except (tk.TclError, ValueError):
    scale = 2.0
try:
    timeout = max(10, min(600, int(self.timeout_var.get())))
except (tk.TclError, ValueError):
    timeout = 120
```
→ 新しいパラメータ（`provider` から取得するものは不要）も同パターンで検証する。

---

### `pagefolio/settings.py`（改修 — utility, transform）

**アナログ:** `pagefolio/settings.py`（自身の `_load_settings` の defaults dict）

**既存デフォルト値追加パターン（settings.py lines 29-44）:**
```python
def _load_settings():
    defaults = {
        "theme": "dark",
        "font_size": 12,
        "lang": "ja",
        # OCR (LM Studio) 関連デフォルト値
        "lm_studio_url": "http://localhost:1234",
        "lm_studio_model": "",
        "ocr_prompt_preset": "text",
        "ocr_scale": 2.0,
        "ocr_timeout": 120,
        "ocr_max_tokens": -1,
        "ocr_temperature": 0.1,
        "ocr_concurrency": 2,
    }
    try:
        path = _get_settings_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        logger.debug("設定ファイル読み込み失敗: %s", e)
    return dict(defaults)
```
→ `defaults` に以下を追加する（D-09, ARCHITECTURE.md §settings.py の変更）:
  - `"ocr_provider": "off"`

**`_save_settings` — APIキーガードパターン（PITFALLS.md Pitfall #1 対策）:**
```python
# 現行の _save_settings（settings.py lines 58-65）をベースにガードを追加する
NEVER_PERSIST_KEYS = {"anthropic_api_key", "gemini_api_key"}  # Phase 5 以降で必要

def _save_settings(settings):
    try:
        path = _get_settings_path()
        safe = {k: v for k, v in settings.items() if k not in NEVER_PERSIST_KEYS}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug("設定ファイル保存失敗: %s", e)
```
→ Phase 4 では APIキー項目が `settings` に入ることはまだないが、PITFALLS.md の指摘通り
  ガードを事前に組み込んでおくことを推奨する。

---

### `pagefolio/lang.py`（改修 — config, transform）

**アナログ:** `pagefolio/lang.py`（自身の `ocr_*` キー群の追記パターン）

**既存 OCR キーの追記パターン（lang.py lines 248-329 の構造）:**
```python
LANG = {
    "ja": {
        ...
        # OCR 関連（既存）
        "ocr_progress_render": "画像変換中… ({cur}/{total})",
        "ocr_progress_ocr": "読み取り完了 ({done}/{total}) — p.{page}",
        ...
    },
    "en": {
        ...
        # OCR 関連（既存）
        "ocr_progress_render": "Rendering images… ({cur}/{total})",
        "ocr_progress_ocr": "OCR done ({done}/{total}) — p.{page}",
        ...
    },
}
```
→ Phase 4 で最小追加するキー（D-09 / ARCHITECTURE.md §lang.py の変更）:
  - `"ocr_text_skip_notice"`: `"p.{page}: テキスト埋め込み済みのためスキップしました"` / `"p.{page}: Skipped (embedded text detected)"`
  - `"ocr_provider_off"`: OCR が無効（off）であることを示すヒント文言
  - `"ocr_apikey_missing"`: `"環境変数 {env_var} が未設定です。設定してからアプリを再起動してください。"` / `"Environment variable {env_var} is not set. Please set it and restart the app."`
  - プロバイダ名文言（`ocr_provider_label`, `ocr_provider_lmstudio` 等）は Phase 5 の UI 追加時でも可。Phase 4 では必達ではない。

---

## Shared Patterns

### スレッド安全 UI 更新
**Source:** `pagefolio/ocr_dialog.py` lines 466-493
**Apply to:** `ocr_dialog.py` の改修全体（新しい進捗通知・スキップ通知）
```python
# ワーカースレッドから UI を更新する唯一の正しい方法
self.after(0, lambda: self.progress_var.set("..."))
self.after(0, lambda m=msg: self._finish_error(m, kind=k))
```
**禁止:** `Provider` クラス内（`ocr_providers.py`）から `self.after()`・`StringVar`・Tkinter シンボルを一切参照しない（PITFALLS.md Pitfall #3）。

### fitz スレッド境界
**Source:** `pagefolio/ocr_dialog.py` lines 461-479（フェーズ1の直列ループ）
**Apply to:** `ocr_dialog.py` `_worker` 改修
```python
# fitz.Page へのアクセスはスレッド内でも「直列」に限る
# ThreadPoolExecutor に self.doc や fitz.Page を渡してはならない
for i, page_idx in enumerate(self.page_indices, start=1):
    b64 = page_to_png_b64(self.doc[page_idx], scale=scale)  # 直列・fitz操作
    images[page_idx] = b64  # 文字列のみを保持
# ここから先は文字列(images)のみを並列処理
```
→ Phase 4 成功基準3: `grep -n "get_pixmap\|self\.doc\[" pagefolio/ocr_dialog.py` の結果が
  フェーズ1ループ内の直列箇所のみであること（`ThreadPoolExecutor.submit` の target 関数内に存在しないこと）。

### 例外ロギングパターン
**Source:** `pagefolio/ocr.py` lines 199-201 / `pagefolio/plugins.py` lines 147-148
**Apply to:** `ocr_providers.py`, `ocr.py` `run_parallel()`
```python
except Exception as e:
    logger.exception("OCR 呼び出し失敗: %s", e)
    return ("err", page_idx, str(e))
```
→ 裸の `except:` 禁止（CLAUDE.md 規約）。必ず `except Exception as e:` の形で。

### fatal/error 区別パターン
**Source:** `pagefolio/ocr.py` lines 193-201（`_call` 内の status tuple）
**Apply to:** `run_parallel()` — Provider の `ConnectionError` / `TimeoutError` は fatal、`RuntimeError` は per-page error
```python
except ConnectionError as e:
    return ("fatal_conn", page_idx, str(e))
except TimeoutError as e:
    return ("fatal_timeout", page_idx, str(e))
except RuntimeError as e:
    return ("err", page_idx, str(e))
```

### コピーライトヘッダー
**Source:** `pagefolio/ocr.py` lines 1-4
**Apply to:** 新規 `ocr_providers.py`
```python
# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""<モジュール概要>"""
```

---

## No Analog Found

なし。すべてのファイルについて、自身または近傍モジュールに十分な類似実装が存在する。

---

## Metadata

**Analog search scope:** `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`, `pagefolio/plugins.py`, `pagefolio/settings.py`, `pagefolio/lang.py`
**Files scanned:** 5
**Pattern extraction date:** 2026-06-06
