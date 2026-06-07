# Phase 6: Gemini Provider + 逐次レンダリング最適化 — Research

**Researched:** 2026-06-07
**Domain:** Gemini API 統合・producer-consumer メモリ最適化・OCR モックテスト（Python/Tkinter）
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 逐次レンダリング方式（OCR-PERF-02・成功基準2）
- **D-01:** メモリ上限の保証方式は **上限付きバッファ（producer-consumer）**。メインスレッドが先読みレンダリングして上限 N 枚の境界付きキューに積み、ワーカーが消費したら破棄する。完全逐次（render1→send1）や「クラウドのみ逐次・ローカル現状維持」は不採用。
- **D-02:** バッファ上限は **並列度連動**（例: `concurrency + 余裕分`）。具体的な余裕分の係数は Claude 裁量。
- **D-03:** 進捗 UI は **統合プログレス**（「処理済み X/総数」の単一バー）。OCR 完了ページ数を主軸にし、スキップページも処理済みに含める。
- **D-04:** Phase 4 D-03 の「ワーカー内 fitz アクセスゼロ」は **必達**。

#### Gemini Provider（OCR-API-02 / OCR-API-03）
- **D-05:** `GeminiProvider` は `ClaudeProvider` と同じテンプレートで実装。エンドポイント `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`、認証は `x-goog-api-key` ヘッダー方式、画像は `inline_data: {mime_type, data}`、レスポンスは `candidates[].content.parts[].text` を走査して結合。
- **D-06:** 環境変数解決は **`GEMINI_API_KEY` 優先 → 未設定なら `GOOGLE_API_KEY` フォールバック**。
- **D-07:** 並列度は **Gemini=1**（`default_concurrency=1`/`max_concurrency=1`）。429/5xx は既存 `OCRRetryableError` 層を再利用。
- **D-08:** 推奨デフォルトモデルは **`gemini-2.5-flash` 主推奨**、`gemini-2.5-pro` を選択肢。旧 preview ID は使わない。

#### Gemini パラメータ UI（OCR-API-02 + OCR-UI 連携）
- **D-09:** Gemini は **temperature 欄のみ表示**し、`thinkingBudget=0` を送って thinking を明示無効化する。`thinkingConfig` の正確なフィールド配置は Claude 裁量（リサーチで確認）。
- **D-10:** Gemini 用の payload 構築責任は **Provider 内に集約**。

#### ocr_scale 既定見直し（OCR-PERF-05）
- **D-11:** `DEFAULT_SETTINGS["ocr_scale"]` を **2.0 → 1.5** に変更。既存ユーザーの保存値は **据え置き**。
- **D-12:** トレードオフヒントは **設定欄（`llm_config.py` の `ocr_scale` スライダー近傍）に常設の短い説明**を置く。文言は `lang.py` に日英で追加。

#### OCR モックテスト（OCR-QA-01）
- **D-13:** **逐次レンダリングのメモリ非蓄積リグレッションテストを入れる**。`FakeProvider` の `ocr_image` 呼び出し時点で同時保持される画像数が上限を超えないことを機械的に検証する。producer-consumer ロジックは Tk/スレッド非依存に切り出せる形で実装し、テスト可能性を確保する。
- **D-14:** Gemini モックテストは **4 点**: ① payload 構築（`inline_data`・`x-goog-api-key` ヘッダー・`thinkingBudget=0`）② レスポンス解析（`candidates[].content.parts[].text` 結合）③ `list_models`（`supportedGenerationMethods` フィルタ）④ dual env var 解決（`GEMINI_API_KEY`→`GOOGLE_API_KEY`）。

### Claude's Discretion
- producer-consumer のバッファ上限の余裕係数（D-02）・キュー/Queue 実装の具体形・キャンセル時の in-flight ページ処理（D-01/D-04）
- `OCRAPIKeyError` のフォールバック env 名併記の有無（D-06）
- Gemini `thinkingConfig.thinkingBudget` の正確なフィールド配置・generationConfig 構造（D-09）
- バッファ上限テストの切り出し方（producer-consumer を Tk 非依存ヘルパー化するか）（D-13）
- `ocr_scale` ヒント文言の正確な表現（D-12）

### Deferred Ideas (OUT OF SCOPE)
- TesseractProvider・PluginManager 登録フック（`register_ocr_provider`）・本格的な多言語文言整備・README/開発履歴更新 → Phase 7（OCR-EXT-01/02・OCR-QA-02）
- OS キーストア連携（Windows Credential Manager）によるキー永続化 → 次マイルストーン（Out of Scope）
- `ocr_scale` の既存ユーザーへのワンタイム移行 → 今回は不採用

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | 説明 | リサーチ支援 |
|----|------|------------|
| OCR-API-02 | ユーザーは Gemini（generateContent・inline_data・モデル一覧・`GEMINI_API_KEY`/`GOOGLE_API_KEY`）でページを OCR できる | §Standard Stack / §Gemini API 仕様 / §Code Examples |
| OCR-PERF-02 | ページ単位の逐次レンダリング → 送信 → 破棄でメモリ使用量を抑える（全ページ画像の一括保持を廃止） | §Producer-Consumer パターン / §Architecture Patterns |
| OCR-PERF-05 | `ocr_scale` のデフォルトを 1.5 に見直し、速度/コスト ↔ 精度のトレードオフヒントを UI に表示する | §Don't Hand-Roll（ヒント文言） / §Code Examples |
| OCR-QA-01 | 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテストする（`tests/test_ocr.py`） | §Validation Architecture / §Common Pitfalls |

</phase_requirements>

---

## Summary

Phase 6 はすでに Phase 4/5 で整備された `OCRProvider` 抽象・`run_parallel`・`OCRRetryableError` バックオフ共通層を土台として、3 つの主要な実装領域を持つ。

**第一領域: GeminiProvider 追加**。`ClaudeProvider` と同一テンプレートで `ocr_providers.py` に実装する。エンドポイント・認証（`x-goog-api-key` ヘッダー）・payload 構造（`inline_data`・`generationConfig.thinkingConfig`）・レスポンス解析（`candidates[]`）はすべて公式ドキュメントで検証済み（HIGH 信頼度）。`thinkingConfig.thinkingBudget=0` は `generationConfig` の直下に置く（公式ドキュメント確認済み）。

**第二領域: producer-consumer 逐次レンダリング（OCR-PERF-02）**。`OCRDialog._render_next_page`（メインスレッド生産者）と `_worker`/`run_parallel`（消費者）の間に `queue.Queue(maxsize=N)` を挿入する方式が最適。現行の「全ページ先にレンダリング → まとめて API 送信」を「N 枚先読みバッファで pipeline 化」に変える。フェーズ境界（fitz=メインスレッド・API=ワーカー）は既存設計から変えない。バッファ上限 `N = concurrency + 1`（余裕係数 1）がワーカー飢えを抑えつつメモリを制限する最適点と判断する（後述）。

**第三領域: テスト・UI 調整**。`GeminiProvider` のモックテスト 4 点・逐次レンダリングのメモリ非蓄積リグレッション・`ocr_scale` 既定 1.5 化・設定欄ヒント文言追加。既存 `test_ocr.py`/`test_ocr_providers.py` の `ClaudeProvider` テストパターンをほぼそのまま踏襲できる。

**Primary recommendation:** GeminiProvider は ClaudeProvider コードをテンプレートに `thinkingConfig`・`inline_data`・candidates 解析・dual env var 解決を差し替えるだけで実装可能。producer-consumer は `queue.Queue(maxsize=concurrency+1)` を `ocr_dialog.py` に追加し、メインスレッドの `_render_next_page` が `put_nowait` またはブロッキング `put`、ワーカースレッドが `get` する構成とする。

---

## Architectural Responsibility Map

| 機能 | 主担当層 | 副担当層 | 根拠 |
|------|---------|---------|------|
| Gemini API 呼び出し（payload 構築・HTTP・レスポンス解析） | `GeminiProvider`（`ocr_providers.py`） | — | Provider 集約原則（D-05/D-10）|
| `GEMINI_API_KEY`/`GOOGLE_API_KEY` 解決 | `_resolve_api_key`（`ocr.py`）| `OCRMixin._start_ocr` | 既存 claude 解決パターンに gemini 分岐を追加 |
| producer-consumer バッファ管理（生産者） | `OCRDialog._render_next_page`（メインスレッド） | — | fitz はメインスレッド専属（Phase 4 D-03） |
| producer-consumer バッファ管理（消費者） | `OCRDialog._worker`（バックグラウンドスレッド） | `run_parallel` | API 呼び出しはワーカーで並列実行 |
| 進捗 UI 更新 | `OCRDialog`（`self.after(0, ...)`） | — | Tkinter スレッド安全ルール（Pitfall 3） |
| `ocr_scale` 既定値 | `DEFAULT_SETTINGS`（`settings.py`） | `llm_config.py`（UI 表示） | 設定ファイルの単一情報源 |
| `ocr_scale` ヒント文言 | `lang.py` | `llm_config.py`（ウィジェット） | Phase 5 D-12 踏襲 |
| GeminiProvider のモックテスト | `tests/test_ocr_providers.py` | `tests/test_ocr.py` | 既存 Claude テストと同一ファイル構成 |
| 逐次レンダリングのメモリ非蓄積テスト | `tests/test_ocr.py` | — | producer-consumer ヘルパーを Tk 非依存で切り出し |

---

## Standard Stack

### Core（新規 pip 依存なし）

| ライブラリ | バージョン | 用途 | 既存/追加 |
|-----------|-----------|------|----------|
| `urllib.request` | 標準ライブラリ | Gemini API HTTP POST/GET | 既存 |
| `queue.Queue` | 標準ライブラリ | producer-consumer バッファ | 追加（標準ライブラリ） |
| `threading.Event` | 標準ライブラリ | キャンセルフラグ（既存）| 既存 |
| `json` | 標準ライブラリ | payload シリアライズ | 既存 |
| `os` | 標準ライブラリ | 環境変数読み取り | 既存 |

**新規外部 pip パッケージ: ゼロ**。`queue` は Python 標準ライブラリのため pip 依存は一切増えない（STACK.md 確認済み・OUT OF SCOPE：公式 SDK 採用）。

### Phase 6 で変更するファイル一覧

| ファイル | 変更種別 | 主な変更内容 |
|---------|---------|------------|
| `pagefolio/ocr_providers.py` | 追加 | `GeminiProvider` クラス追加 |
| `pagefolio/ocr.py` | 改修 | `build_provider` に `gemini` 分岐追加・`_resolve_api_key` に gemini 対応追加 |
| `pagefolio/ocr_dialog.py` | 改修 | producer-consumer 化（`_render_next_page`・`_worker`）・統合プログレス |
| `pagefolio/settings.py` | 改修 | `DEFAULT_SETTINGS["ocr_scale"]` 2.0 → 1.5・`gemini_model` デフォルト追加 |
| `pagefolio/dialogs/llm_config.py` | 改修 | gemini 分岐追加・`ocr_scale` ヒント常設 |
| `pagefolio/lang.py` | 改修 | Gemini 名・dual env var エラー・`ocr_scale` ヒント文言追加 |
| `tests/test_ocr_providers.py` | 追加 | `GeminiProvider` 4 点モックテスト |
| `tests/test_ocr.py` | 追加 | 逐次レンダリングのメモリ非蓄積テスト |

---

## Package Legitimacy Audit

> Phase 6 は外部 pip パッケージを一切追加しない（標準ライブラリ `queue` のみ追加使用）。

**本セクション: 該当なし** — 新規パッケージ追加ゼロ。slopcheck 実行不要。

---

## Architecture Patterns

### System Architecture Diagram

```
メインスレッド                    バックグラウンドスレッド
────────────────────              ────────────────────────────────
OCRDialog._on_run()
  │
  ├─ build_provider("gemini") → GeminiProvider(api_key, model)
  │
  ├─ queue = Queue(maxsize=concurrency+1)
  │
  └─ _render_next_page() ──────────────────────────────────────────┐
       (after(0) 小分け連鎖)                                        │
       for page in page_indices:                                    │
         b64 = page_to_png_b64(doc[page])  ← fitz アクセスここだけ │
         queue.put((page, b64))  ─────────→ [バッファ queue]       │
                                                      │            │
                                              _worker()            │
                                              ┌──────────────────┐ │
                                              │ while True:      │ │
                                              │  item=queue.get()│ │
                                              │  if item is None:│ │
                                              │    break(完了)   │ │
                                              │  page_idx, b64   │ │
                                              │  = item          │ │
                                              │  provider.ocr_   │ │
                                              │  image(b64, ...)  │ │
                                              │  del b64 ←破棄  │ │
                                              │  after(0, update)│ │
                                              └──────────────────┘ │
       queue.put(None) ─────────────────────────────────────────────┘
       (全ページ完了シグナル)

GeminiProvider.ocr_image():
  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
  Header: x-goog-api-key: {api_key}
  Body: {
    "contents": [{"parts": [{"inline_data": {...}}, {"text": prompt}]}],
    "generationConfig": {
      "temperature": 0.1,
      "maxOutputTokens": 4096,
      "thinkingConfig": {"thinkingBudget": 0}
    }
  }
  → Response: candidates[0].content.parts[].text を結合
```

### Recommended Project Structure（変更対象ファイルのみ）

```
pagefolio/
├── ocr_providers.py   # GeminiProvider を ClaudeProvider の後に追加
├── ocr.py             # build_provider: gemini 分岐追加・_resolve_api_key: gemini 対応
├── ocr_dialog.py      # producer-consumer 化（Queue 導入）
├── settings.py        # DEFAULT_SETTINGS["ocr_scale"] = 1.5、gemini_model 追加
├── lang.py            # Gemini 文言・ocr_scale ヒント追加
└── dialogs/
    └── llm_config.py  # gemini provider 欄追加・ocr_scale ヒント常設
tests/
├── test_ocr_providers.py  # TestGeminiProvider* 追加
└── test_ocr.py            # TestProducerConsumerMemory 追加
```

---

## Pattern 1: GeminiProvider の payload 構造と thinkingConfig

**What:** Gemini `generateContent` の正確なリクエストボディ構造

**検証根拠:** 公式ドキュメント `ai.google.dev/api/generate-content`・`ai.google.dev/gemini-api/docs/thinking` から直接確認済み（HIGH 信頼度）。

**重要事項（D-09 の裁量決定）:**
`thinkingConfig` は `generationConfig` の **直下** に置く（トップレベルではない）。公式ドキュメントの REST 例で確認済み：

```python
# Source: ai.google.dev/gemini-api/docs/thinking (2026-06-07 確認)
def _build_payload(self, b64_png, prompt):
    """GeminiProvider の generateContent ペイロード構築（内部メソッド）"""
    return {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": b64_png,
                        }
                    },
                    {"text": prompt},  # 画像の後にテキスト（公式推奨順序）
                ]
            }
        ],
        "generationConfig": {
            "temperature": self.temperature,
            "maxOutputTokens": self.max_tokens,
            # thinkingConfig は generationConfig の直下（トップレベルではない）
            "thinkingConfig": {
                "thinkingBudget": 0  # 0 = thinking 明示無効化（D-09）
            },
        },
    }
```

**認証ヘッダー（D-05）:**
```python
# Source: ai.google.dev/api/generate-content (2026-06-07 確認) + STACK.md
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": self.api_key,  # URL クエリ ?key= は使わない（ログ漏洩回避）
}
```

**エンドポイント構築:**
```python
# Source: STACK.md §Gemini API（2026-06-06 確認）
GENERATE_CONTENT_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
endpoint = self.GENERATE_CONTENT_ENDPOINT.format(model=self.model)
```

---

## Pattern 2: GeminiProvider のレスポンス解析（防衛的実装）

**What:** `candidates` が空（安全フィルタ・SAFETY ブロック）の場合への対処が必要

**検証根拠:** PITFALLS.md §Pitfall 6（Gemini candidates 空ケース）・公式ドキュメント

```python
# Source: PITFALLS.md §Pitfall 6（防衛的レスポンス解析パターン）
def _parse_response(self, body):
    """レスポンス解析（防衛的実装）。candidates 空チェック必須（Pitfall 6）"""
    candidates = body.get("candidates", [])
    if not candidates:
        # finishReason が SAFETY / RECITATION の場合は candidates が空
        reason = body.get("promptFeedback", {}).get("blockReason", "unknown")
        raise RuntimeError(f"Gemini blocked: {reason}")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [p["text"] for p in parts if "text" in p]
    if not texts:
        raise RuntimeError(f"Gemini: no text in response parts: {body}")
    return "\n".join(texts)
```

---

## Pattern 3: dual env var 解決（D-06）

**What:** `GEMINI_API_KEY` 優先・未設定なら `GOOGLE_API_KEY` フォールバック

```python
# Source: CONTEXT.md D-06 / docs/OCRプロバイダ化_見積もり仕様.md §2.3（2026-06-07 確認）
# ocr.py の _resolve_api_key に gemini 分岐を追加する
if provider_name == "gemini":
    env_var_primary = "GEMINI_API_KEY"
    env_var_fallback = "GOOGLE_API_KEY"
    key = os.environ.get(env_var_primary) or os.environ.get(env_var_fallback)
    if key:
        return key
    key = session_keys.get("gemini", "")
    if key:
        return key
    raise OCRAPIKeyError(env_var_primary)  # 主環境変数名でエラー表示
```

---

## Pattern 4: producer-consumer バッファ（D-01/D-02 の具体実装）

**What:** `queue.Queue(maxsize=N)` を使った bounded buffer パターン

**バッファ上限の余裕係数決定（D-02 裁量）:**

| 設定 | LM Studio（並列8） | Gemini（並列1） | Claude（並列2） | 評価 |
|------|------------------|----------------|----------------|------|
| `maxsize=concurrency` | 8枚 | 1枚 | 2枚 | ワーカーが飢えやすい |
| `maxsize=concurrency+1` | 9枚 | 2枚 | 3枚 | ★推奨: 飢え防止+最小バッファ |
| `maxsize=concurrency*2` | 16枚 | 2枚 | 4枚 | 必要以上にメモリ消費 |

**推奨:** `maxsize = concurrency + 1`。ワーカーが 1 スロット消費中に次の 1 枚を先読みできる最小マージンを確保しつつ、メモリ上限を `concurrency+1` 枚に保証する。

```python
# Source: 設計判断（D-02 裁量・ARCHITECTURE.md §パターン3 の逐次レンダリング化を拡張）

# ── ocr_dialog.py の改修イメージ ──

import queue  # 標準ライブラリ

def _on_run(self):
    ...
    # バッファ: maxsize = 並列度 + 1（余裕係数 1 で飢えを防止・D-02）
    self._render_queue = queue.Queue(maxsize=self.concurrency + 1)
    self._render_idx = 0
    self._render_next_page()  # メインスレッドで逐次生産開始

def _render_next_page(self):
    """メインスレッド（生産者）: 1ページ render → キューに積む（after(0) 連鎖）"""
    if self._cancel_flag.is_set():
        # キャンセル: 完了シグナルを送ってワーカーを終わらせる
        self._render_queue.put(None)
        self._finish_cancelled()
        return

    total = len(self.page_indices)
    idx = self._render_idx

    if idx >= total:
        # 全ページ完了: ワーカーに終了シグナルを送る
        self._render_queue.put(None)
        return  # _finish_complete は _worker が呼ぶ

    page_idx = self.page_indices[idx]
    try:
        page = self.doc[page_idx]
        if has_embedded_text(page):
            self.results[page_idx] = page.get_text()
            self._skipped_pages.add(page_idx)
            # スキップ: キューに積まず次ページへ
        else:
            b64 = page_to_png_b64(page, scale=self._ocr_scale)
            # ブロッキング put（キューが満杯なら待つ）
            # ただしキャンセル検出のため短いタイムアウトでループする
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
    self.after(0, self._render_next_page)  # 次ページを連鎖

def _start_worker_thread(self):
    # _render_next_page が起動直後にワーカーを開始する（重なり実行）
    self._worker_thread = threading.Thread(target=self._worker, daemon=True)
    self._worker_thread.start()

def _worker(self):
    """バックグラウンドスレッド（消費者）: キューから取り出して API 送信"""
    done = 0
    skipped_count = len(self._skipped_pages)
    total = len(self.page_indices)

    while True:
        try:
            item = self._render_queue.get(timeout=1.0)
        except queue.Empty:
            # タイムアウト: キャンセル or メインスレッド待ち
            if self._cancel_flag.is_set():
                break
            continue

        if item is None:
            break  # 完了シグナル

        page_idx, b64 = item
        try:
            text = self.provider.ocr_image(b64, self._ocr_prompt)
            self.results[page_idx] = text
            done += 1
        except Exception as e:
            self.errors[page_idx] = str(e)
            done += 1
        finally:
            del b64  # 送信直後に破棄（D-01 メモリ保証）
            self._render_queue.task_done()

        # 進捗通知（after(0) 経由でメインスレッドへ・Pitfall 3）
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

**注意:** 上記は `run_parallel` を直接使わずワーカー内で直列ループする構成。GeminiProvider の `max_concurrency=1` に最適化されているが、LM Studio（並列 8）では並列度を活かせない。並列度を維持しつつ producer-consumer を実現する場合は以下の考慮が必要（後述 §Common Pitfalls §Pitfall-A）。

---

## Pattern 5: 並列度を維持した producer-consumer（LM Studio 兼用）

**What:** `run_parallel` を維持しつつ画像を先行バッファ制御する設計

クラウドプロバイダ（Gemini=1・Claude=2）は上記 Pattern 4 で十分だが、LM Studio（並列 8）は `ThreadPoolExecutor` の並列実行が必要。両者を統合する方法：

```python
# 方法A: run_parallel に images_b64 を段階的に渡す（シンプル）
# _worker 内で queue から取り出しながら run_parallel を呼ぶのは複雑なため、
# 実用的には「メインスレッドで全ページを queue に積む → _worker が queue を消費しながら
# provider.ocr_image を直接呼ぶ（LM Studio でも並列度 1 相当）」か、
#
# 方法B: _worker 内で ThreadPoolExecutor を直接管理する（複雑だが並列度を維持できる）
#
# 推奨判断: Phase 6 の主目的は「クラウドプロバイダでメモリを節約」であり、
# LM Studio の並列 8 はメモリ問題が元から小さい。
# よって Phase 6 では方法A（直列消費）を採用し、LM Studio も concurrency=1 相当で動作させる。
# これは後方互換で「全体として遅くなる」が、「全ページ base64 がメモリに乗らない」
# という成功基準 2 を確実に達成できる。
# Phase 7 以降で LM Studio 高並列パスを別実装に分岐させることができる。
```

---

## Pattern 6: Tk 非依存 producer-consumer ヘルパー（テスト可能化・D-13）

**What:** キュー管理とバッファ上限検証をテスト可能な純粋関数として切り出す

```python
# pagefolio/ocr_dialog.py 内またはヘルパー関数として（D-13 裁量）
def _run_with_bounded_buffer(
    render_fn,      # page_idx -> b64_png str（メインスレッドで呼ぶ前提・テストでは直接呼ぶ）
    ocr_fn,         # b64_png -> str（API 呼び出し・テストでは FakeProvider を渡す）
    page_indices,   # list[int]
    maxsize,        # バッファ上限
    is_cancelled,   # () -> bool
    on_done,        # (page_idx, text_or_error) -> None
):
    """Tk 非依存の producer-consumer ループ（テストで直接呼び出せる）"""
    buf = queue.Queue(maxsize=maxsize)

    def producer():
        for page_idx in page_indices:
            if is_cancelled():
                break
            b64 = render_fn(page_idx)
            while not is_cancelled():
                try:
                    buf.put((page_idx, b64), timeout=0.1)
                    break
                except queue.Full:
                    pass
        buf.put(None)

    def consumer():
        while True:
            item = buf.get(timeout=1.0)
            if item is None:
                break
            page_idx, b64 = item
            try:
                text = ocr_fn(b64)
                on_done(page_idx, text)
            finally:
                del b64
                buf.task_done()

    # メインスレッドで producer を実行し、consumer を別スレッドで起動
    # （テストでは直接 producer() + consumer() を同期的に呼ぶか、
    #   threading.Thread で起動してテストする）
    ...
```

このヘルパーを切り出すことで、`FakeProvider` の `ocr_image` 呼び出し時点で同時保持される画像数が `maxsize` を超えないことをテストで機械的に確認できる。

---

## Don't Hand-Roll

| 問題 | 作ってはいけないもの | 使うべきもの | 理由 |
|------|---------------------|-------------|------|
| バウンドキュー | カスタム queue 実装 | `queue.Queue(maxsize=N)` | Python 標準・スレッドセーフ・ブロッキング put/get 付き |
| Gemini SDK 代替 | `urllib` 以外の HTTP クライアント | `urllib.request`（既存パターン踏襲） | PyInstaller .exe 肥大化防止（STACK.md §新規追加なし）|
| thinkingConfig の独自実装 | 独自の「思考抑制」ロジック | `generationConfig.thinkingConfig.thinkingBudget=0` | Gemini 公式 API の規約フィールド |
| 環境変数フォールバック | 独自のキーストアや config 解析 | `os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")` | Phase 5 の `_resolve_api_key` パターンを踏襲 |
| 防衛的 JSON 解析 | 決め打ちキーアクセス | candidates 空チェック + parts 走査 | Pitfall 6（安全フィルタによる空 candidates）|

---

## Runtime State Inventory

> Phase 6 はコード追加・既存ファイル改修のみ。外部サービス/DB の文字列置換は一切なし。

| カテゴリ | 確認結果 | 対応 |
|---------|---------|------|
| 保存データ | なし — Gemini API キーは `settings.json` に書かない（確認済み：D-06・`_SENSITIVE_KEYS` ガード） | 不要 |
| ライブサービス設定 | なし — n8n/CI/外部サービスの Phase 6 依存なし | 不要 |
| OS 登録状態 | なし | 不要 |
| シークレット/env | `GEMINI_API_KEY`・`GOOGLE_API_KEY` を実行時読み取りのみ（保存しない） | 実装ルール確認のみ |
| ビルド成果物 | `dist/PageFolio/pagefolio_settings.json` が存在（git 管理外）。`ocr_scale` が `2.0` で固定されている場合は新規ユーザーには 1.5 が適用されるが既存ファイルは据え置き（D-11 通り） | 既存ファイルは変更しない |

---

## Common Pitfalls

### Pitfall-A: 直列ループで LM Studio の並列度を失う

**What goes wrong:** Pattern 4 の `_worker` 直列ループを採用すると、LM Studio は `max_concurrency=8` だが実効並列度は 1 になる。Phase 5 以前と比べて LM Studio OCR が遅くなる可能性がある。

**Why it happens:** producer-consumer の消費者が 1 スレッドで直列ループするため。

**How to avoid:** Phase 6 の目的は「クラウドでのメモリ節約」であり、LM Studio の速度劣化は許容できる範囲と判断する（D-01 設計判断）。もし LM Studio 並列維持が必要なら、消費者スレッドを複数起動するか `run_parallel` に段階的に items を渡す設計に変更すること。リリースノートに「ローカル LM Studio での並列度が 1 相当になる変更」を明記する。

**Warning signs:** LM Studio OCR の処理時間がページ数に正比例して増え、従来の 1/8 程度の並列効果がなくなる。

### Pitfall-B: `put()` ブロック中にキャンセルが効かない

**What goes wrong:** `queue.Queue.put()` を timeout なしで呼ぶと、キューが満杯の際にメインスレッドがブロックし続ける。キャンセルボタンを押しても応答しない。

**Why it happens:** メインスレッドでのブロッキング put はキャンセルイベントを確認できない。

**How to avoid:** `put(item, timeout=0.1)` をループで呼び、`queue.Full` 例外を受け取ったら `_cancel_flag.is_set()` を確認する（Pattern 4 のコード参照）。

### Pitfall-C: `thinkingConfig` をトップレベルに置く誤り

**What goes wrong:** `thinkingConfig` をリクエストボディのトップレベルに置くと API が無視するか 400 エラーになる。

**Why it happens:** 公式ドキュメントの読み間違い。`generationConfig` の直下に置く必要がある。

**How to avoid:** RESEARCH.md Pattern 1 のコードサンプルをそのまま使う。`generationConfig: { thinkingConfig: { thinkingBudget: 0 } }` の構造を確認する（公式ドキュメント `ai.google.dev/gemini-api/docs/thinking` 確認済み）。

**Warning signs:** API から 400 Bad Request が返される・thinkingBudget が無視されてコスト/レイテンシが予想より高い。

### Pitfall-D: `candidates` 空時の IndexError

**What goes wrong:** `candidates[0]` に直接アクセスすると、安全フィルタ・RECITATION などで candidates が空の場合に IndexError が発生する。

**Why it happens:** LMStudio の `choices[0]` 決め打ちパターンを Gemini にそのまま適用しようとするため。

**How to avoid:** Pattern 2 の防衛的解析を必ず使う。`candidates = body.get("candidates", []); if not candidates: raise RuntimeError(...)` を最初に確認する（Pitfall 6・PITFALLS.md 参照）。

### Pitfall-E: `_cancel_flag` が producer-consumer で正しく伝搬しない

**What goes wrong:** キャンセル時にメインスレッドは `_render_next_page` を止めても、ワーカースレッドは残った items を消費し続ける。または完了シグナル `None` を送らないためワーカーが `get()` でブロックし続ける。

**Why it happens:** キャンセル時のフロー設計漏れ。

**How to avoid:** キャンセル検出時は必ず `self._render_queue.put(None)` を呼んでワーカーを終了させる。ワーカー側も `queue.Empty` タイムアウト時に `_cancel_flag` を確認する（Pattern 4 参照）。

### Pitfall-F: `_is_cloud_provider()` / `_needs_session_key()` の gemini 分岐欠落

**What goes wrong:** `ocr_dialog.py` の `_is_cloud_provider()` に `gemini` 分岐が追加されないと、Gemini でもセッションキー欄・コスト確認ダイアログが表示されない。

**Why it happens:** Phase 5 は Claude 専用で実装されており、`if name == "claude"` の条件分岐になっている。

**How to avoid:** `_is_cloud_provider()`・`_needs_session_key()`・`_provider_display_name()`・`_on_run()` の provider 分岐に `"gemini"` を追加する。コスト確認ダイアログのメッセージも `api.anthropic.com` ではなく実際のホスト名を使う。

### Pitfall-G: `_apply_llm_settings` の gemini 分岐欠落

**What goes wrong:** `_apply_llm_settings` でプロバイダが `gemini` に変更された際、`provider` インスタンスが再生成されない（claude/lmstudio の分岐のみ）。

**Why it happens:** Phase 5 実装は claude/lmstudio の 2 分岐のみ（既存コード確認済み）。

**How to avoid:** `_apply_llm_settings` の `elif name == "gemini":` 分岐を追加し、`build_provider` 経由で `GeminiProvider` を生成する。

---

## Code Examples

### GeminiProvider の `ocr_image` 骨格

```python
# Source: STACK.md §Gemini API (2026-06-06) + ai.google.dev/gemini-api/docs/thinking (2026-06-07)
class GeminiProvider(OCRProvider):
    """Google AI Studio Gemini API プロバイダ（urllib 直叩き）。"""

    default_concurrency = 1
    max_concurrency = 1

    GENERATE_CONTENT_ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent"
    )
    MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
    RECOMMENDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]

    def __init__(self, api_key, model, timeout=120, max_tokens=4096, temperature=0.1):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _build_payload(self, b64_png, prompt):
        return {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": b64_png}},
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "thinkingConfig": {"thinkingBudget": 0},  # thinking 明示無効化
            },
        }

    def ocr_image(self, b64_png, prompt, **kwargs):
        endpoint = self.GENERATE_CONTENT_ENDPOINT.format(model=self.model)
        payload = self._build_payload(b64_png, prompt)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
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

        try:
            result = json.loads(body)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Unexpected response: {body[:500]}") from e
        return self._parse_response(result)

    def _parse_response(self, body):
        candidates = body.get("candidates", [])
        if not candidates:
            reason = body.get("promptFeedback", {}).get("blockReason", "unknown")
            raise RuntimeError(f"Gemini blocked: {reason}")
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p["text"] for p in parts if "text" in p]
        if not texts:
            raise RuntimeError(f"Gemini: no text in response: {body}")
        return "\n".join(texts)

    def list_models(self):
        if not self.api_key:
            return list(self.RECOMMENDED_MODELS)
        timeout = 10
        req = urllib.request.Request(  # noqa: S310
            self.MODELS_ENDPOINT,
            headers={"x-goog-api-key": self.api_key},
            method="GET",
        )
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
        return [
            m.get("name", "").replace("models/", "")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
            and m.get("name", "")
        ]
```

### `build_provider` の gemini 分岐

```python
# Source: ocr.py の既存 claude 分岐パターンを踏襲（2026-06-07 確認）
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

### `_resolve_api_key` の gemini 分岐

```python
# Source: ocr.py の既存 claude 分岐パターンを踏襲（CONTEXT.md D-06）
if provider_name == "gemini":
    env_var_primary = "GEMINI_API_KEY"
    key = os.environ.get(env_var_primary) or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    key = session_keys.get("gemini", "")
    if key:
        return key
    raise OCRAPIKeyError(env_var_primary)
```

### `settings.py` の gemini 設定追加と ocr_scale 変更

```python
# Source: settings.py DEFAULT_SETTINGS（現在の ocr_scale=2.0 を 1.5 に変更・D-11）
defaults = {
    ...
    "ocr_scale": 1.5,          # D-11: 1.5 に変更（新規ユーザー向け）
    ...
    "gemini_model": "gemini-2.5-flash",   # Phase 6: Gemini 推奨モデル（D-08）
}
```

### `lang.py` の追加文言キー

```python
# Source: ARCHITECTURE.md §lang.py（既存キー一覧）・CONTEXT.md D-12（文言要件）
# 以下を lang.py の日英辞書に追加する
"ocr_provider_name_gemini": {"ja": "Gemini (Google AI)", "en": "Gemini (Google AI)"},
"ocr_api_key_missing_gemini": {
    "ja": "環境変数 GEMINI_API_KEY が未設定です（フォールバック: GOOGLE_API_KEY）。設定してからアプリを再起動してください。",
    "en": "Environment variable GEMINI_API_KEY is not set (fallback: GOOGLE_API_KEY). Please set it and restart the app.",
},
"ocr_scale_tradeoff_hint": {
    "ja": "低=速い/安い・高=精度、低スペックは 1.5 推奨",
    "en": "Low=fast/cheap, High=accuracy. 1.5 recommended for low-spec PCs.",
},
```

---

## State of the Art

| 旧アプローチ | 現行アプローチ | 変更時期 | 影響 |
|------------|--------------|--------|------|
| 全ページ base64 一括保持 | producer-consumer bounded buffer | Phase 6 | 低 RAM PC でのメモリ節約 |
| LMStudio 専用実装 | OCRProvider 抽象 + 複数実装 | Phase 4〜6 | プロバイダ差し替え可能 |
| `ocr_scale=2.0` 既定 | `ocr_scale=1.5` 既定 | Phase 6 | 新規ユーザーの転送コスト削減 |
| thinking=ON (Gemini 2.5-flash 既定) | `thinkingBudget=0` で明示 OFF | Phase 6 | OCR 不要な思考コスト回避 |
| `claude` のみのクラウドゲート | `claude`/`gemini` 両対応のクラウドゲート | Phase 6 | Gemini でもコスト確認・セッションキー欄が機能 |

**廃止・非推奨:**
- `gemini-2.5-flash-preview-09-2025`: 2026-07-09 廃止予定。`gemini-2.5-flash`（stable GA）を使用すること（STACK.md §廃止）。

---

## Assumptions Log

| # | 主張 | セクション | 外れた場合のリスク |
|---|------|-----------|-----------------|
| A1 | `thinkingConfig.thinkingBudget=0` が `generationConfig` の直下に置くことで思考を無効化できる | §Pattern 1 / §Code Examples | Gemini API が 400 エラーを返す・コスト超過 |
| A2 | `list_models` レスポンスの `name` フィールドは `"models/gemini-2.5-flash"` 形式で、`models/` プレフィックスを除去すればモデル ID になる | §Code Examples（list_models） | モデル ID の形式が変わりコンボボックスに変な値が表示される |
| A3 | バッファ上限 `concurrency + 1` がワーカー飢えを防ぐ最小マージンとして十分 | §Pattern 4 | LM Studio で並列度が落ちる（許容済み）|
| A4 | `queue.Queue.get(timeout=1.0)` ループがキャンセル検出に十分なレスポンス速度を持つ | §Pattern 4 | キャンセル後 1 秒程度の遅延が生じる（UX 上は許容範囲） |

**空の場合:** A1〜A4 の 4 件は訓練知識ベースで確認済みまたは公式ドキュメント確認済み。A1 のみ「公式ドキュメントで確認済み」（ai.google.dev/gemini-api/docs/thinking）。他は ASSUMED。

---

## Open Questions

1. **GeminiProvider.list_models の `name` フィールド形式**
   - 分かっていること: STACK.md に `models[].name`（例: `"models/gemini-2.5-flash"`）と記載あり
   - 不明な点: `"models/"` プレフィックスが常に付くか、または ID 形式が変わる可能性
   - 推奨: `m.get("name", "").replace("models/", "")` で安全に処理する実装を採用

2. **`thinkingBudget=0` が Gemini 2.5 Flash で確実に thinking をオフにするか**
   - 分かっていること: 公式ドキュメントで `thinkingBudget=0` = thinking 無効化と確認済み
   - 不明な点: Flash のマイナーバージョン更新で挙動が変わるリスク
   - 推奨: Phase 6 ではこのまま採用し、コスト超過が報告されたら次フェーズで見直す

3. **`_run_with_bounded_buffer` ヘルパーを別モジュールに切り出すか**
   - 分かっていること: D-13 で「Tk 非依存に切り出せる形で」という指定あり
   - 不明な点: `ocr_dialog.py` 内のネストした関数で十分かどうか
   - 推奨: テスト可能性を最優先にするなら `ocr.py` 内のモジュール関数として切り出す。`ocr_dialog.py` 内でのネストは Tkinter 依存が入り込むリスクがある

---

## Environment Availability

| 依存 | 必要とする機能 | 利用可能 | バージョン | フォールバック |
|-----|--------------|---------|----------|-------------|
| Python `queue` | producer-consumer バッファ | ✓ | 標準ライブラリ（Python 3.8+） | — |
| Python `threading` | ワーカースレッド | ✓ | 標準ライブラリ | — |
| `urllib.request` | Gemini API HTTP | ✓ | 標準ライブラリ | — |
| Gemini API (外部) | OCR-API-02 実機テスト | 不明（環境変数依存） | — | モックテストで代替 |
| pytest | OCR-QA-01 テスト | ✓ | 9.0.2（`pyproject.toml` 確認済み） | — |

**ネットワーク不要な欠落依存なし** — pytest モックテストは Gemini API 実接続なしで動作する。実機テスト（成功基準1 の確認）は `GEMINI_API_KEY` 環境変数が設定された環境が必要。

---

## Validation Architecture

> `workflow.nyquist_validation = true`（`config.json` 確認済み）のため本セクションを含める。

### Test Framework

| プロパティ | 値 |
|---------|---|
| フレームワーク | pytest 9.0.2 |
| 設定ファイル | `pyproject.toml`（`[tool.pytest.ini_options]`） |
| クイック実行 | `pytest tests/test_ocr_providers.py tests/test_ocr.py -x` |
| フルスイート | `pytest` |

### Phase Requirements → Test Map

| Req ID | 振る舞い | テスト種別 | 自動化コマンド | ファイル存在 |
|--------|---------|-----------|--------------|------------|
| OCR-API-02 | GeminiProvider.ocr_image が payload を正しく構築する（inline_data・x-goog-api-key・thinkingBudget=0） | unit（モック） | `pytest tests/test_ocr_providers.py::TestGeminiProviderBuildPayload -x` | ❌ Wave 0 |
| OCR-API-02 | GeminiProvider.ocr_image が candidates[].content.parts[].text を結合して返す | unit（モック） | `pytest tests/test_ocr_providers.py::TestGeminiProviderOcrImage::test_success_returns_text -x` | ❌ Wave 0 |
| OCR-API-02 | GeminiProvider.list_models が supportedGenerationMethods でフィルタする | unit（モック） | `pytest tests/test_ocr_providers.py::TestGeminiProviderListModels -x` | ❌ Wave 0 |
| OCR-API-02 | `GEMINI_API_KEY` 優先・`GOOGLE_API_KEY` フォールバック解決 | unit | `pytest tests/test_ocr.py::TestResolveApiKeyGemini -x` | ❌ Wave 0 |
| OCR-API-02 | build_provider("gemini") が GeminiProvider を返す | unit | `pytest tests/test_ocr.py::TestBuildProviderGemini -x` | ❌ Wave 0 |
| OCR-PERF-02 | FakeProvider の ocr_image 呼び出し時点で同時保持画像数がバッファ上限以内 | unit（Tk 非依存） | `pytest tests/test_ocr.py::TestProducerConsumerMemory -x` | ❌ Wave 0 |
| OCR-PERF-05 | DEFAULT_SETTINGS["ocr_scale"] == 1.5 | unit | `pytest tests/test_ocr.py::TestDefaultSettings::test_ocr_scale_default_is_1_5 -x` | ❌ Wave 0 |
| OCR-QA-01 | 既存 TestClaudeProvider* / TestLMStudioProvider* 引き続き通過 | unit（回帰） | `pytest tests/test_ocr_providers.py -x` | ✅ |
| OCR-QA-01 | 既存 TestRunParallel* / TestRunParallelBackoff* 引き続き通過 | unit（回帰） | `pytest tests/test_ocr.py -x` | ✅ |

### Sampling Rate

- **タスクコミット毎:** `pytest tests/test_ocr_providers.py tests/test_ocr.py -x`
- **Wave マージ毎:** `pytest`（フルスイート）
- **フェーズゲート:** フルスイートグリーン確認後 `/gsd-verify-work`

### Wave 0 のギャップ（実装前に作成が必要なテスト）

- [ ] `tests/test_ocr_providers.py` に `TestGeminiProviderBasic`・`TestGeminiProviderBuildPayload`・`TestGeminiProviderOcrImage`・`TestGeminiProviderListModels` を追加
- [ ] `tests/test_ocr.py` に `TestResolveApiKeyGemini`・`TestBuildProviderGemini`・`TestProducerConsumerMemory`・`TestDefaultSettings::test_ocr_scale_default_is_1_5` を追加
- [ ] `TestProducerConsumerMemory` の実装: `_run_with_bounded_buffer`（またはその同等物）を Tk 非依存で呼び出し、`FakeProvider.ocr_image` 呼び出し時点での `in_flight` 数が `maxsize` を超えないことを `threading.Lock` で計測するテスト

---

## Project Constraints (from CLAUDE.md)

CLAUDE.md から抽出した実行可能な指示の一覧。プランナーはこれらとの矛盾がないことを確認すること。

| 指示 | Phase 6 への影響 |
|-----|---------------|
| `ruff check . && ruff format .` を全 py 編集後に実行 | 各タスクのサブステップに Ruff チェックを含める |
| 裸の `except:` 禁止（必ず `except Exception as e:`） | `GeminiProvider` 全例外ハンドラで準拠 |
| `# type: ignore` の無断使用禁止 | 型アノテーション不要（Python 3.8 互換の範囲） |
| テーマ色は `C["KEY"]` 辞書経由（ハードコード禁止） | `llm_config.py` の gemini 欄追加でも `C` を使う |
| APIキーを `settings.json` に書かない（最優先） | `_SENSITIVE_KEYS` に `"gemini_api_key"` を追加済みか確認 |
| `pytest` コミット前に通過必須 | Wave 0 のテスト追加が前提 |
| コミットメッセージは日本語 | プランナーがコミットメッセージ例を日本語で示す |
| バージョン番号更新（`constants.py`・README・開発履歴） | Phase 6 完了時に v1.4.0 または中間バージョンへ更新 |

**重要な追加確認:** `settings.py` の `_SENSITIVE_KEYS` 集合には `"gemini_api_key"` が既に含まれている（現在: `{"claude_api_key", "gemini_api_key", "anthropic_api_key", "api_key"}`）。Gemini キーの平文漏洩ガードは構造的にすでに存在する。

---

## Security Domain

> `security_enforcement: true`（config.json 確認済み）のため本セクションを含める。

### 適用される ASVS カテゴリ

| ASVS カテゴリ | 適用 | 標準コントロール |
|-------------|-----|---------------|
| V2 認証 | Yes（API キー） | 環境変数からのみ取得・`_SENSITIVE_KEYS` ガード |
| V3 セッション管理 | Yes（セッションメモリキー） | `_session_api_keys` 属性・プロセス終了で消滅 |
| V4 アクセス制御 | No | — |
| V5 入力検証 | Yes（API レスポンス） | `candidates` 空チェック・`json.JSONDecodeError` キャッチ |
| V6 暗号化 | No（urllib が HTTPS を使用） | `urllib.request.urlopen` は HTTPS で通信 |

### Phase 6 固有のセキュリティ脅威

| パターン | STRIDE | 標準対策 |
|---------|--------|---------|
| `GEMINI_API_KEY` の `settings.json` 漏洩 | 情報開示 | `_SENSITIVE_KEYS` ガード（`gemini_api_key` 追加確認）・`_save_settings` でフィルタ |
| `GEMINI_API_KEY` の URL クエリパラメータ露出 | 情報開示 | `x-goog-api-key` ヘッダー方式を採用（`?key=` 形式は使わない）|
| Gemini API レスポンスの RECITATION/SAFETY ブロック | 否認 | `candidates` 空ケースを RuntimeError にマップ・エラーメッセージに API キーを含めない |
| セッションキーのログ混入 | 情報開示 | `logger.exception()` で `b64_png`・`api_key` を含む変数をログしない |
| `GEMINI_API_KEY` の env var 誤設定（typo）による意図しない課金 | なりすまし | `OCRAPIKeyError` で明示エラー・コスト確認ダイアログ |

---

## Sources

### Primary（HIGH 信頼度）
- `ai.google.dev/api/generate-content` — Gemini generateContent エンドポイント・認証・inline_data・generationConfig 構造（2026-06-07 確認）
- `ai.google.dev/gemini-api/docs/thinking` — thinkingConfig.thinkingBudget の正確なフィールド配置（generationConfig 直下）・thinkingBudget=0 の意味（2026-06-07 確認）
- `.planning/research/STACK.md` — Gemini API 仕様（エンドポイント・認証・inline_data・レスポンス・list_models・推奨モデル）（2026-06-06 確認済み・HIGH）
- `pagefolio/ocr_providers.py` — ClaudeProvider 実装テンプレート（実コード実読）
- `pagefolio/ocr_dialog.py` — `_render_next_page`/`_worker` の現状構造（実コード実読）
- `pagefolio/ocr.py` — `run_parallel`/`build_provider`/`_resolve_api_key` の現状実装（実コード実読）
- `pagefolio/settings.py` — `DEFAULT_SETTINGS`・`_SENSITIVE_KEYS`（実コード実読）
- `tests/test_ocr_providers.py` — TestClaudeProvider* テストパターン（実コード実読）

### Secondary（MEDIUM 信頼度）
- `.planning/research/ARCHITECTURE.md` — OCRMixin/ocr_providers.py 統合設計・逐次レンダリング化の設計方針
- `.planning/research/PITFALLS.md` — Gemini candidates 空チェック・クラウド並列度・メモリ逼迫

### Tertiary（LOW 信頼度・ASSUMED タグ）
- `queue.Queue(maxsize=concurrency+1)` の余裕係数判断: 訓練知識ベース（公式に根拠文書なし）→ `[ASSUMED]`
- `list_models` の name フィールド形式 `"models/gemini-2.5-flash"` の replace 処理: STACK.md の例示から推測 → `[ASSUMED]`

---

## Metadata

**信頼度内訳:**
- Standard Stack（新規 pip ゼロ）: HIGH — 標準ライブラリのみ・STACK.md 確認済み
- GeminiProvider 仕様: HIGH — 公式ドキュメント直接確認済み（thinkingConfig 含む）
- producer-consumer 設計: HIGH（パターン自体）/ ASSUMED（余裕係数 +1）
- テストパターン: HIGH — 既存 ClaudeProvider テストを踏襲
- `ocr_scale` 既定変更: HIGH — D-11 確定事項

**Research date:** 2026-06-07
**Valid until:** 2026-07-07（Gemini モデル変更・thinkingConfig API 変更があれば再確認）
