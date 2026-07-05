# Phase 2: OCR 磨き込み - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 10 (new: 2 / modified: 8)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `pagefolio/ocr_pipeline.py` (新設) | utility（純ロジック層） | event-driven / streaming（producer-consumer） | `pagefolio/pagination.py`（Tk/fitz 非依存の純関数集約パターン） | role-match（同格の新設パターン） |
| `tests/test_ocr_pipeline.py` (新設) | test | transform | `tests/test_pagination.py`（純ロジック層のテスト構成） / `tests/test_ocr.py`（移設元テスト） | role-match |
| `pagefolio/ocr.py` (修正: `run_with_bounded_buffer` 削除) | utility | event-driven | 自身（既存コード） | exact |
| `pagefolio/ocr_dialog.py` (修正: `_render_next_page`/`_worker` を `ocr_pipeline` 呼び出しへ縮小・L-6a/L-6j 修正) | component（Tk ダイアログ） | event-driven / request-response | 自身（既存コード。producer/consumer の「実戦仕様」そのもの） | exact |
| `pagefolio/ocr_providers.py` (修正: Tesseract lang 尊重・URL スキーム検証共通ヘルパー・Gemini quote・エラー body 切り詰め) | service（外部 API クライアント群） | request-response | 自身（`_raise_mapped_http_error` / `_detect_tesseract` / `TesseractProvider.ocr_image`） | exact |
| `pagefolio/plugins.py` (修正: `register_ocr_provider` 堅牢化・`unload_plugin` 解除・`get_ocr_provider`/`list_ocr_providers` 追加) | service（プラグインライフサイクル管理） | CRUD（registry 登録/解除/参照） | 自身（既存 `PluginManager`） | exact |
| `pagefolio/dialogs/llm_config.py` (修正: `_provider_registry` 私有アクセス置換・`_fetch_models`/`_test_connection` 重複解消) | component（設定ダイアログ） | request-response | 自身（`_fetch_ollama_models`/`_test_ollama_connection` が重複解消後の同型ターゲット） | exact |
| `pagefolio/lang.py` (修正: フォールバック注記キー追加) | config（言語辞書） | CRUD | 自身（既存 `tesseract_lang_fallback` キー・ja/en 対） | exact |
| `CLAUDE.md` (修正: ファイル構成表に `ocr_pipeline.py` 追記) | config（プロジェクト文書） | transform | 自身（既存モジュール構成表の行フォーマット） | exact |
| `tests/test_ocr_providers.py` / `tests/test_plugins.py` / `tests/test_ocr.py` (修正: 新仕様に合わせテスト更新) | test | transform | 自身（既存テストファイル） | exact |

## Pattern Assignments

### `pagefolio/ocr_pipeline.py`（新設・utility・event-driven）

**Analog:** `pagefolio/pagination.py`（Tk/fitz 非依存の純ロジック層パターン）と `pagefolio/ocr_dialog.py`（一本化対象の実戦仕様）

**モジュールdocstring・純関数集約パターン**（`pagination.py` lines 1-23）:
```python
# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ページネーション純ロジック層 — Tkinter / fitz 非依存。

「表示窓のローカル位置 ↔ 全ページインデックス」変換と窓計算を、
引数→戻り値・状態非依存の純関数に集約する（02-CONTEXT.md integration point）。
...
ここには `fitz` / `tkinter` を一切 import しない（viewer.py:40-49 の純関数作法に倣う）。
```
→ `ocr_pipeline.py` も同型の docstring（Tk/fitz 非依存の明言・参照決定の記載・確定名の固定）で始めること。

**共有状態クラスの型（新設イメージ・CONTEXT/RESEARCH 由来・そのまま流用可）:**
```python
# ocr_dialog.py:135-143 の Tk 依存版を Tk 非依存クラスへ抽出する対象
self._done_lock = threading.Lock()
self._done_count = 0
self._workers_remaining = 0
self._fatal_msg = None
self._fatal_kind = None
self._consec_err_count = 0
```
RESEARCH.md「Pattern 1」の `PipelineState` 実装イメージ（`record_success`/`record_retryable_failure`）をそのまま出発点にする。

**consumer 中核ロジック（Tk 非依存で移設可能な部分・そのまま抽出対象）**（`ocr_dialog.py` lines 1466-1528, 特に retry/fatal 分岐）:
```python
for attempt in range(1, MAX_RETRIES + 1):
    try:
        text, truncated = self.provider.ocr_image_ex(b64, self._ocr_prompt)
        self._record_page_success(page_idx, text, truncated=truncated)
        break
    except OCRRetryableError as e:
        if attempt >= MAX_RETRIES:
            self._record_retryable_failure(page_idx, str(e))
            break
        raw_delay = (
            e.retry_after if e.retry_after is not None
            else 1.0 * (2 ** (attempt - 1))
        )
        delay = clamp_retry_after(raw_delay)
        interruptible_sleep(delay, self._cancel_flag.is_set)
    except ConnectionError as e:
        with self._done_lock:
            if self._fatal_msg is None:
                self._fatal_msg = str(e)
                self._fatal_kind = "connection"
            self._done_count += 1
        break
    # ... TimeoutError / RuntimeError / Exception 同型
```
`self.after()`/`self.text` に一切依存しないため、この部分は `ocr_pipeline.py` の関数（例: `consume_one(provider, item, prompt, state, cancel_check) -> None`）へそのまま移設できる。`self.provider.ocr_image_ex` 呼び出しと `self._record_page_success`/`_record_retryable_failure` をコールバック引数に置換する形。

**非ブロッキング producer / sentinel 送出パターン（producer 側は dialog に残すが、キュー操作ヘルパーは `ocr_pipeline.py` へ）**（`ocr_dialog.py` lines 1397-1406, 1352-1365）:
```python
# 非ブロッキング enqueue（producer 側・成功/失敗を bool で返すヘルパーへ抽出）
try:
    self._render_queue.put_nowait((page_idx, b64))
except queue.Full:
    g = gen
    self.after(100, lambda _g=g: self._render_next_page(_g))
    return

# sentinel 非ブロッキング送出・部分送信の再試行（不変条件を ocr_pipeline.py の docstring に明文化・L-6h）
sent = 0
for _ in range(self.concurrency):
    try:
        self._render_queue.put_nowait(None)
        sent += 1
    except queue.Full:
        break
if sent < self.concurrency:
    g = gen
    self.after(100, lambda _g=g: self._render_next_page(_g))
```

**置き換え対象（アンチパターンとして残さない）**（`pagefolio/ocr.py` lines 358-386, `run_with_bounded_buffer._producer`）:
```python
def _producer():
    try:
        for page_idx in page_indices:
            ...
            while True:
                if _is_cancelled():
                    return
                try:
                    buf.put((page_idx, b64), timeout=0.1)
                    break
                except queue.Full:
                    continue
    finally:
        for _ in range(workers):
            buf.put(None)  # L-6h: 無条件 blocking put
```
→ 専用スレッド + blocking put 構造は**採用しない**（D-01・Pitfall 1）。`ocr_pipeline.py` の producer 関連 API は「レンダリング方法」を規定しない薄いユーティリティに限定する。

---

### `tests/test_ocr_pipeline.py`（新設・test）

**Analog:** `tests/test_pagination.py`（純ロジック層のテスト構成）・移設元 `tests/test_ocr.py:1230-1327`（bounded buffer テスト）

`run_with_bounded_buffer` 由来のテスト（`test_ocr.py:1262,1282,1316` 呼び出し箇所）をそのまま移設し、新 API（`PipelineState`/`consume_one`/enqueue ヘルパー）に合わせて書き換える。`test_pagination.py` の「Tk/fitz 非依存関数を直接呼んで assert する」スタイルに倣う。

---

### `pagefolio/ocr.py`（修正・utility）

**変更内容:** `run_with_bounded_buffer`（lines 306-498）を削除し `ocr_pipeline.py` の新実装へ委譲/置換。`run_parallel`・プロンプト解決系（`resolve_ocr_prompt`等）・`build_provider` は変更なし。

**削除前に確認すべき外部参照チェック**（RESEARCH.md Open Question 1）:
```bash
grep -rn "run_with_bounded_buffer" README.md 開発履歴.md plugins/
```

---

### `pagefolio/ocr_dialog.py`（修正・component）

**Analog:** 自身（`_render_next_page` lines 1323-1414 / `_worker` lines 1430-1586）— 一本化後はこれらのメソッドを `ocr_pipeline.*` を呼ぶ薄いラッパーへ縮小する。

**L-6a 修正対象**（レンダー失敗時にプログレスバー未更新）— `_render_next_page` の except ブロック（lines 1407-1409）:
```python
except Exception as e:
    logger.exception("ページ処理失敗 (p.%d): %s", page_idx, e)
    self.errors[page_idx] = f"image conversion error: {e}"
    # ← ここに progress_var/progress_bar 更新の after 呼び出しが欠落（要追加）
```
修正時は成功パスの `self.after(0, lambda d=done_disp: self._on_progress_bar(d))` と同型の呼び出しをこの except 節にも追加し、当該ページを「処理済み」として計上する。

**L-6j 修正対象**（"off" 切替時に `_update_ocr_buttons_state()` 未呼出）— `_apply_llm_settings`（lines 842-957 付近、正常系末尾および例外分岐 lines 952-955 双方）:
```python
except Exception as e:
    ...
    # 例外分岐でも _update_ocr_buttons_state() が呼ばれるよう、
    # 呼び出しを try/except の外側（関数末尾）へ移動する（Pitfall 6）
```

---

### `pagefolio/ocr_providers.py`（修正・service）

**Analog:** 自身（`_raise_mapped_http_error` / `_detect_tesseract` / `TesseractProvider` / `LMStudioProvider._post_chat`）

**エラー body 切り詰め（L-6d）** — `_raise_mapped_http_error`（lines 193-215）:
```python
try:
    err_body = e.read().decode("utf-8", errors="replace")
except Exception:
    err_body = ""
message = f"HTTP {e.code}: {err_body or e.reason}"
```
→ `err_body` を `[:500]` 等で切り詰める（全プロバイダ共有関数のため 5 プロバイダ全てのエラーメッセージテストへ波及することに注意・Pitfall 4）。

**Tesseract 言語再検出・段階的縮退（L-4・D-05/D-06）** — `_detect_tesseract`（lines 960-990）は都度呼び出し可能な形のまま `build_provider` から都度呼ぶよう変更。`ocr_image`（lines 1024-1057）の固定ロジック（line 1039）:
```python
# 現状: self.lang を完全無視
lang = "jpn+eng" if "jpn" in _TESSERACT_LANGS else "eng"
```
→ D-06 の段階的縮退（`self.lang` の部分集合優先 → 全滅なら自動決定）へ書き換え。`_TESSERACT_AVAILABLE, _TESSERACT_LANGS = _detect_tesseract()`（line 994・import 時固定）はプロバイダ生成時再評価に変更し、`dialogs/llm_config.py` 側の同名定数参照（Pitfall 2）も同じ関数経由に統一する。

**URL スキーム検証共通ヘルパー（L-6e・D-13）** — 追加対象は `LMStudioProvider._post_chat`（line 296 `endpoint` 生成直後）・`list_models`・`OllamaProvider`/`RunPodProvider` の同型箇所:
```python
def _post_chat(self, payload):
    endpoint = self.url.rstrip("/") + "/v1/chat/completions"
    # ← ここで _require_http_scheme(self.url) 相当の検証を追加
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(...)
```
RESEARCH.md Pattern 4 の `_require_http_scheme(url)`（`urlsplit(url).scheme` 判定・`RuntimeError` 送出）をそのまま実装する。

**Gemini モデル名 URL エスケープ（L-6f）** — `GENERATE_CONTENT_ENDPOINT.format(model=self.model)`（lines 706-708, 811）に `urllib.parse.quote(self.model, safe="")` を適用。

---

### `pagefolio/plugins.py`（修正・service）

**Analog:** 自身（`register_ocr_provider` lines 200-219 / `unload_plugin` lines 152-161）

**重複名検証追加（L-2・D-08）** — `register_ocr_provider`:
```python
def register_ocr_provider(self, name: str, cls) -> None:
    from pagefolio.ocr_providers import OCRProvider
    if not (isinstance(cls, type) and issubclass(cls, OCRProvider)):
        raise TypeError(f"{cls} は OCRProvider のサブクラスでなければなりません")
    self._provider_registry[name] = cls  # ← ここに組み込み名衝突チェック（拒否+warning）
                                          #    プラグイン間重複（後勝ち+warning）を追加
    logger.debug("OCR プロバイダ登録: %s -> %s", name, cls.__name__)
```
組み込み名リスト: `claude / gemini / lmstudio / tesseract / ollama / runpod / off`（既存コードのどこかに定数化されていなければ本改修で定数化）。name→plugin_id の対応を registry 側で追跡する構造（D-09 の unload 解除に必要）を追加。

**unload 時の registry 解除追加（L-2・D-09）** — `unload_plugin`:
```python
def unload_plugin(self, plugin_id, app=None):
    if plugin_id in self._plugins:
        if app:
            try:
                self._plugins[plugin_id].on_unload(app)
            except Exception as e:
                logger.exception("プラグインアンロード失敗 (%s): %s", plugin_id, e)
        del self._plugins[plugin_id]
        self._plugin_modules.pop(plugin_id, None)
        # ← ここに self._provider_registry から plugin_id 由来エントリを解除する処理を追加
```

**公開アクセサ追加（L-3・D-10）** — `get_disabled_ids`（lines 221-223）と同じ「読み取り専用の薄いラッパー」パターンで新設:
```python
def get_disabled_ids(self):
    """無効化されたプラグインIDリストを返す"""
    return list(self._disabled)

# 同型で追加:
# def get_ocr_provider(self, name): return self._provider_registry.get(name)
# def list_ocr_providers(self): return list(self._provider_registry.keys())
```

---

### `pagefolio/dialogs/llm_config.py`（修正・component）

**Analog:** 自身の `_fetch_models`/`_test_connection`（LM Studio 用・lines 1120-1161）と `_fetch_ollama_models`（lines 1164 以降）

**私有アクセス置換（L-3・D-10）:**
```python
# 現状（置換対象）
if plugin_manager is not None and name in plugin_manager._provider_registry:
    ...
self._plugin_manager._provider_registry.keys()
```
→ `plugin_manager.get_ocr_provider(name)` / `self._plugin_manager.list_ocr_providers()` に置換（`ocr.py:720` も同様）。

**重複解消対象（L-6i）** — `_fetch_models`（1120-1141）と `_test_connection`（1142-1161）はロジックがほぼ同一:
```python
def _fetch_models(self):
    url = self.lm_url_var.get().strip()
    if not url:
        self._set_lm_status(self._L["settings_lm_test_fail"].format(error="URL is empty"), kind="fail")
        return
    self._set_lm_status(self._L["settings_lm_testing"].format(url=url), kind="info")
    try:
        models = LMStudioProvider(url=url, model="").list_models()
    except (ConnectionError, TimeoutError, RuntimeError) as e:
        self._set_lm_status(self._L["settings_lm_test_fail"].format(error=str(e)), kind="fail")
        return
    self.lm_model_combo["values"] = models
    self._set_lm_status(self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok")

def _test_connection(self):
    # ↑と全く同じフロー。差分は self.lm_model_combo["values"] = models の代入有無のみ
```
共通ヘルパー抽出（例: `_probe_provider(url_var, provider_factory, update_combo: bool)`）でパラメータ化する（Claude's Discretion）。Pitfall 5 に注意: Ollama ペア（`_fetch_ollama_models`/`_test_ollama_connection`）は L-6 原文に明記がないため、共通ヘルパー化がここまで自然に波及する場合は PLAN.md に明示的にスコープ拡張として記載すること（D-11 は暗黙拡張のみ禁止）。

---

### `pagefolio/lang.py`（修正・config）

**Analog:** 既存 `tesseract_lang_fallback` キー（ja: line 449 / en: line 1025 付近、D-07 で言及）

ja/en 両辞書へ同一キーで追加する既存ルールに従う。新規キー（例: フォールバック発生時の1回限り注記文言）は `test_lang_parity.py` のキー数一致監視対象になるため、追加時は必ずペアで追加すること。

---

### `CLAUDE.md`（修正・config）

**Analog:** 既存モジュール構成表の1行フォーマット（`themes.py` / `undo_store.py` などの記述パターン）。`ocr_pipeline.py` を「Tk/fitz 非依存の producer-consumer 純ロジック層（D-02）」として1行追記する。

---

## Shared Patterns

### Tk/fitz 非依存の純ロジック層分離
**Source:** `pagefolio/pagination.py`, `pagefolio/md_render.py`, `pagefolio/undo_store.py`
**Apply to:** `pagefolio/ocr_pipeline.py`（新設）
モジュール冒頭に「ここには fitz/tkinter を一切 import しない」旨を明記し、pytest から直接呼べる純関数/軽量クラス構成にする。

### 裸の except 禁止・logger 経由記録
**Source:** CLAUDE.md 規約・`ocr_providers.py` 全体、`plugins.py` の `except Exception as e: logger.exception(...)` パターン
**Apply to:** 全修正ファイル（`ocr_pipeline.py`/`ocr_providers.py`/`plugins.py`/`ocr_dialog.py`）

### 公開アクセサ経由の私有属性隔離
**Source:** `pagefolio/plugins.py:221-223 get_disabled_ids`（既存の薄いラッパーパターン）
**Apply to:** `get_ocr_provider`/`list_ocr_providers` 新設（`_provider_registry` は非公開のまま）

### LANG キーの ja/en 同時追加
**Source:** `pagefolio/lang.py`（既存キー全般）・`tests/test_lang_parity.py`
**Apply to:** L-4 フォールバック注記の新規/拡張キー

### 世代ガード・非ブロッキング put の踏襲
**Source:** `pagefolio/ocr_dialog.py:1330-1332`（gen 不一致 early return）・:1397-1406（put_nowait + after 再試行）
**Apply to:** `ocr_pipeline.py` 抽出後も dialog 側にこの制御構造を残す（D-01 の核心）

## No Analog Found

なし。全対象ファイルが既存コードベース内に直接の自身analog（修正対象そのもの）または近縁の確立パターン（`pagination.py`/`md_render.py`/`undo_store.py`）を持つ。

## Metadata

**Analog search scope:** `pagefolio/` 全体（`ocr.py`, `ocr_dialog.py`, `ocr_providers.py`, `plugins.py`, `dialogs/llm_config.py`, `pagination.py`, `lang.py`）, `tests/`（`test_ocr.py`, `test_pagination.py`）
**Files scanned:** 9（対象ファイル本体 + `pagination.py` 参照analog）
**Pattern extraction date:** 2026-07-05
