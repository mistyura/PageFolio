# Architecture Patterns — OCR Provider Abstraction

**Domain:** Python/Tkinter デスクトップアプリ (PageFolio) への OCR プロバイダ抽象化統合
**Researched:** 2026-06-06
**Overall confidence:** HIGH（既存コードの実読 + 仕様書 `docs/OCRプロバイダ化_見積もり仕様.md` に基づく）

---

## 推奨アーキテクチャ概要

```text
                 ┌──────────────────────────────────────────────────────┐
                 │                PDFEditorApp                          │
                 │  (OCRMixin が self.settings["ocr_provider"] を参照)  │
                 └──────────────────┬───────────────────────────────────┘
                                    │ _start_ocr() で provider を解決
                                    ▼
                 ┌──────────────────────────────────────────────────────┐
                 │            pagefolio/ocr_providers.py                │
                 │                                                      │
                 │  OCRProvider (abstract base)                         │
                 │   ├─ ocr_image(b64_png, prompt, **kwargs) -> str     │
                 │   ├─ list_models() -> list[str]                      │
                 │   └─ 例外規約: ConnectionError / TimeoutError /      │
                 │                RuntimeError / OCRAPIKeyError (新設)  │
                 │                                                      │
                 │  LMStudioProvider(OCRProvider)   ← ocr.py から移動  │
                 │  ClaudeProvider(OCRProvider)     ← フェーズ2 新設   │
                 │  GeminiProvider(OCRProvider)     ← フェーズ3 新設   │
                 │  TesseractProvider(OCRProvider)  ← フェーズ4 任意   │
                 └──────────────────────────────────────────────────────┘
                                    ▲
                 ┌──────────────────┴───────────────────────────────────┐
                 │            pagefolio/ocr.py（改修後）                │
                 │                                                      │
                 │  page_to_png_b64()          ← そのまま残す           │
                 │  has_embedded_text()        ← 新設（テキスト判定）   │
                 │  run_parallel(provider, images_b64, ...)             │
                 │    ← call_lm_studio_parallel を provider 非依存化    │
                 │  build_provider(settings) -> OCRProvider             │
                 │    ← settings["ocr_provider"] からファクトリ生成     │
                 │  OCRMixin                   ← _start_ocr のみ改修   │
                 └──────────────────────────────────────────────────────┘
                                    │ provider + doc を渡す
                                    ▼
                 ┌──────────────────────────────────────────────────────┐
                 │           pagefolio/ocr_dialog.py（改修後）          │
                 │                                                      │
                 │  provider 選択UI（Radiobutton / SettingsDialog 側）  │
                 │  APIキー未設定エラー表示（OCRAPIKeyError をキャッチ） │
                 │  LM Studio 固有 UI（url_var / model_var）を          │
                 │    provider == "lmstudio" 時のみ表示                 │
                 │  _worker: フェーズ1逐次レンダ→並列送信 を維持        │
                 │           フェーズ3でレンダ→即送信→破棄に変更        │
                 └──────────────────────────────────────────────────────┘

（フェーズ4 任意）
                 ┌──────────────────────────────────────────────────────┐
                 │      PluginManager + PDFEditorPlugin（拡張）         │
                 │                                                      │
                 │  PluginManager._provider_registry: dict[str, type]  │
                 │  PluginManager.register_provider(name, cls)         │
                 │  app.register_ocr_provider(name, cls) ヘルパー       │
                 │                                                      │
                 │  plugins/my_ocr.py が on_load() 内で                │
                 │    app.register_ocr_provider("myocr", MyProvider)   │
                 │  を呼ぶだけで OCRDialog のプロバイダ選択に反映される │
                 └──────────────────────────────────────────────────────┘
```

---

## コンポーネント境界

| コンポーネント | 責務 | ファイル | 新設 / 改修 |
|---------------|------|---------|-------------|
| `OCRProvider` | プロバイダ抽象基底: `ocr_image()` / `list_models()` / 例外規約 | `pagefolio/ocr_providers.py` | **新設** |
| `LMStudioProvider` | OpenAI 互換 Vision API 実装（`build_chat_payload` + `call_lm_studio` を内包） | `pagefolio/ocr_providers.py` | **新設**（`ocr.py` から移動） |
| `ClaudeProvider` | Anthropic messages API 実装（urllib 直叩き） | `pagefolio/ocr_providers.py` | **新設**（フェーズ2） |
| `GeminiProvider` | Google AI Studio generateContent 実装（urllib 直叩き） | `pagefolio/ocr_providers.py` | **新設**（フェーズ3） |
| `TesseractProvider` | tesseract-ocr ローカル実行ラッパー | `pagefolio/ocr_providers.py` | **新設**（フェーズ4・任意） |
| `OCRAPIKeyError` | APIキー未設定を示す専用例外（`RuntimeError` の子クラス） | `pagefolio/ocr_providers.py` | **新設** |
| `run_parallel()` | provider 非依存の並列 OCR ループ（旧 `call_lm_studio_parallel`） | `pagefolio/ocr.py` | **改修**（シグネチャ変更） |
| `build_provider()` | `settings["ocr_provider"]` からプロバイダインスタンスを生成するファクトリ | `pagefolio/ocr.py` | **新設** |
| `has_embedded_text()` | `fitz.Page.get_text()` でテキスト埋め込み判定 | `pagefolio/ocr.py` | **新設** |
| `OCRMixin._start_ocr()` | `build_provider()` を呼び、`OCRDialog` に渡す（provider 中立化） | `pagefolio/ocr.py` | **改修** |
| `OCRDialog` | プロバイダ選択UI・APIキー未設定エラー・LM Studio 条件表示 | `pagefolio/ocr_dialog.py` | **改修** |
| `SettingsDialog` | `ocr_provider` 選択ドロップダウン（または Radiobutton）追加 | `pagefolio/dialogs/settings.py` | **改修** |
| `settings._load_settings()` | `ocr_provider: "off"` デフォルト追加（APIキーは保存しない） | `pagefolio/settings.py` | **改修** |
| `lang.py` | プロバイダ名・APIキー未設定・コスト警告・Tesseract 精度注記の多言語文言追加 | `pagefolio/lang.py` | **改修** |
| `ui_builder.py` | OCR ボタン表示制御（`ocr_provider == "off"` 時は disabled / 非表示） | `pagefolio/ui_builder.py` | **改修** |
| `PluginManager` | `_provider_registry` + `register_provider()` メソッド追加 | `pagefolio/plugins.py` | **改修**（フェーズ4） |
| `PDFEditorApp` | `register_ocr_provider()` ヘルパー追加 | `pagefolio/app.py` | **改修**（フェーズ4） |

---

## データフロー（改修後）

### OCR 実行フロー（プロバイダ中立）

```
ユーザー「読み取り実行」ボタン
│
▼
OCRMixin._start_ocr(page_indices)
  └─ provider = build_provider(self.settings)
       └─ settings["ocr_provider"] が "off" → エラーメッセージ表示して終了
          "lmstudio" → LMStudioProvider(url, model, timeout, max_tokens, temperature)
          "claude"   → ClaudeProvider(api_key=os.environ["ANTHROPIC_API_KEY"], model, timeout)
          "gemini"   → GeminiProvider(api_key=os.environ["GEMINI_API_KEY" or "GOOGLE_API_KEY"], model, timeout)
  └─ OCRDialog(parent, app, doc, page_indices, provider=provider, ...)

OCRDialog._worker(prompt)
│
├─ フェーズ1（逐次レンダリング）: fitz の同一 Document 並行アクセスを避ける
│    for page_idx in page_indices:
│      b64 = page_to_png_b64(doc[page_idx], scale)   ← メインスレッド用 doc を使用
│      images[page_idx] = b64                          ← メモリに一時保持
│
│    ※ フェーズ3（逐次レンダ→即送信→破棄）では:
│    for page_idx in page_indices:
│      b64 = page_to_png_b64(doc[page_idx], scale)
│      text = provider.ocr_image(b64, prompt)          ← 送信直後に b64 破棄
│      results[page_idx] = text
│
├─ フェーズ2（並列 API 送信）:
│    results, errors, fatal_msg, fatal_kind = run_parallel(
│        provider,     ← OCRProvider インスタンスを渡す
│        images,
│        page_indices,
│        concurrency=concurrency,
│        on_progress=...,
│        is_cancelled=...
│    )
│
└─ UI 更新 (self.after(0, ...)) → _render_results_ordered()
```

### プロバイダ選択フロー

```
SettingsDialog でユーザーが ocr_provider を選択
  └─ settings["ocr_provider"] に保存（"off" | "lmstudio" | "claude" | "gemini" | "tesseract"）
  └─ APIキーは settings に**書かない**（os.environ から実行時のみ参照）
  └─ _save_settings(settings)

OCRDialog 初期化時:
  └─ provider が ClaudeProvider / GeminiProvider の場合:
       os.environ.get("ANTHROPIC_API_KEY") が None
         → OCRAPIKeyError を raise
         → _finish_error() で「環境変数 ANTHROPIC_API_KEY が未設定です」を表示
         → 実行ボタンを disabled のまま
```

---

## 設計パターン

### パターン 1: Strategy パターン（プロバイダ差し替え）

**概要:** `OCRProvider` を Strategy インターフェースとし、`run_parallel()` は Strategy を受け取る。

```python
# pagefolio/ocr_providers.py
import abc

class OCRProvider(abc.ABC):
    """OCR プロバイダ抽象基底クラス。
    
    例外規約:
      ocr_image(), list_models() は以下のいずれかを raise する:
        ConnectionError  - 接続失敗（ネットワーク到達不能、サーバ未起動）
        TimeoutError     - タイムアウト
        OCRAPIKeyError   - APIキー未設定（クラウドプロバイダのみ）
        RuntimeError     - APIエラー（4xx/5xx、Vision非対応モデル等）
    """

    @abc.abstractmethod
    def ocr_image(self, b64_png: str, prompt: str, **kwargs) -> str:
        """PNG の base64 文字列を送信し、OCR テキストを返す。"""

    @abc.abstractmethod
    def list_models(self) -> list:
        """利用可能なモデル ID のリストを返す。取得不能時は空リストを返す。"""


class OCRAPIKeyError(RuntimeError):
    """APIキー未設定を示す専用例外。環境変数名を保持する。"""
    def __init__(self, env_var: str):
        self.env_var = env_var
        super().__init__(f"環境変数 {env_var} が設定されていません")


class LMStudioProvider(OCRProvider):
    """LM Studio OpenAI 互換 Vision API（urllib 直叩き）"""
    def __init__(self, url, model, timeout=120, max_tokens=-1, temperature=0.1):
        self.url = url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def ocr_image(self, b64_png, prompt, **kwargs):
        # 旧 call_lm_studio() の実装をここに移動
        ...

    def list_models(self):
        # 旧 fetch_lm_studio_models() の実装をここに移動
        ...
```

### パターン 2: Factory パターン（プロバイダ生成）

**概要:** `build_provider(settings)` が設定値からプロバイダを生成。OCRMixin は具体クラスを知らない。

```python
# pagefolio/ocr.py
import os
from pagefolio.ocr_providers import (
    LMStudioProvider, ClaudeProvider, GeminiProvider, OCRAPIKeyError
)

def build_provider(settings: dict, extra_registry: dict = None) -> "OCRProvider":
    """settings["ocr_provider"] から OCRProvider インスタンスを生成する。
    
    extra_registry: PluginManager._provider_registry から渡されるプラグイン提供プロバイダ。
    """
    name = settings.get("ocr_provider", "off")

    # プラグイン登録プロバイダ（フェーズ4）を先に確認
    if extra_registry and name in extra_registry:
        return extra_registry[name](settings)

    if name == "lmstudio":
        return LMStudioProvider(
            url=settings.get("lm_studio_url", "http://localhost:1234"),
            model=settings.get("lm_studio_model", ""),
            timeout=int(settings.get("ocr_timeout", 120)),
            max_tokens=int(settings.get("ocr_max_tokens", -1)),
            temperature=float(settings.get("ocr_temperature", 0.1)),
        )
    if name == "claude":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise OCRAPIKeyError("ANTHROPIC_API_KEY")
        return ClaudeProvider(api_key=key, ...)
    if name == "gemini":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise OCRAPIKeyError("GEMINI_API_KEY")
        return GeminiProvider(api_key=key, ...)
    raise ValueError(f"不明なプロバイダ: {name}")
```

### パターン 3: fitz スレッドセーフティ制約への対処

**制約:** `fitz.Document` を `ThreadPoolExecutor` のワーカースレッドに渡してはならない。同一 Document への並行アクセスはメモリ破壊・クラッシュを引き起こす可能性がある。

**現行の正しい対処（`OCRDialog._worker`）:**
- フェーズ1（ループ）: `doc[page_idx]` へのアクセスを**直列**で行い base64 変換して `images` dict に保持。
- フェーズ2: `images` dict（文字列のみ）を `run_parallel()` に渡す。ここで初めてスレッドが動く。

**フェーズ3 逐次レンダリング化（メモリ最適化）:**
```python
# _worker 内（逐次レンダ→即送信→破棄）
for i, page_idx in enumerate(self.page_indices):
    if cancelled: break
    # ① メインスレッドのみが doc を触る（この関数は daemon thread だが doc への
    #    アクセスはシリアルであるため安全）
    b64 = page_to_png_b64(doc[page_idx], scale=scale)
    # ② 送信はプロバイダが行う（HTTP IO のみ、fitz 不使用）
    try:
        text = provider.ocr_image(b64, prompt)
        results[page_idx] = text
    except Exception as e:
        errors[page_idx] = str(e)
    finally:
        del b64  # メモリ解放
```

> 注意: 逐次レンダリング化後は `run_parallel()` を使わず直列ループになる。
> 並列度設定は「クラウド送信の同時接続数」としてのみ有効なため、
> フェーズ3 以降では逐次レンダリング専用パスと並列送信パスを分離するか、
> セマフォ制御で並列度を制限するアーキテクチャを検討する。

---

## アンチパターン（回避すべき設計）

### アンチパターン 1: `doc` をスレッドに渡す

**何が起きるか:** `ThreadPoolExecutor` のワーカーが `fitz.Document` を並列アクセスすると、PyMuPDF 内部のメモリ管理が競合しクラッシュ・データ破損が起きる。
**代わりに:** `page_to_png_b64()` での変換（メインスレッド or シリアル）を完了させてから `run_parallel()` に文字列だけ渡す。

### アンチパターン 2: `ocr_dialog.py` が `LMStudioProvider` を直接 import する

**何が起きるか:** ダイアログがプロバイダ実装に密結合し、プロバイダ追加のたびにダイアログを書き換える必要が生じる。
**代わりに:** `OCRDialog` は `OCRProvider` インスタンスを受け取るだけ。具体クラスは `OCRMixin._start_ocr()` で解決する。

### アンチパターン 3: APIキーを `settings.json` に書く

**何が起きるか:** APIキーが平文でディスクに保存される。PyInstaller exe 配布時のセキュリティリスク。
**代わりに:** `os.environ.get("ANTHROPIC_API_KEY")` を実行時にのみ参照。`settings.json` には `ocr_provider` 名のみ保存する。

### アンチパターン 4: `PluginManager.fire_event()` でプロバイダを登録させる

**何が起きるか:** イベント通知機構（観察者パターン）をサービス登録に流用すると、登録順・副作用・非同期性が複雑になる。
**代わりに:** `PluginManager.register_provider(name, cls)` という専用メソッドを追加する（解釈B）。

---

## 統合ポイント詳細

### `settings.py` の変更

```python
# _load_settings() の defaults に追加
"ocr_provider": "off",          # "off" | "lmstudio" | "claude" | "gemini" | "tesseract"
"ocr_claude_model": "claude-haiku-4-5",
"ocr_gemini_model": "gemini-2.5-flash",
# lm_studio_url / lm_studio_model は既存のまま維持
# ※ ANTHROPIC_API_KEY / GEMINI_API_KEY は環境変数のみ・ここに書かない
```

### `lang.py` に追加すべき文言キー

| キー | 日本語 | 英語 |
|------|--------|------|
| `ocr_provider_label` | プロバイダ: | Provider: |
| `ocr_provider_off` | OCR無効 (off) | OCR disabled (off) |
| `ocr_provider_lmstudio` | LM Studio (ローカル) | LM Studio (local) |
| `ocr_provider_claude` | Claude (Anthropic) | Claude (Anthropic) |
| `ocr_provider_gemini` | Gemini (Google AI) | Gemini (Google AI) |
| `ocr_provider_tesseract` | Tesseract (ローカル・精度限定) | Tesseract (local, limited) |
| `ocr_apikey_missing` | 環境変数 {env_var} が未設定です。設定してからアプリを再起動してください。 | Environment variable {env_var} is not set. Please set it and restart the app. |
| `ocr_cost_warning` | クラウドプロバイダ: {count} ページを外部APIへ送信します（従量課金・プライバシー注意）。続けますか？ | Cloud provider: {count} page(s) will be sent to an external API (pay-per-use, privacy notice). Continue? |
| `ocr_provider_off_btn_hint` | OCR が無効です。設定からプロバイダを選択してください。 | OCR is disabled. Select a provider in Settings. |
| `ocr_text_skip_notice` | p.{page}: テキスト埋め込み済みのためスキップしました | p.{page}: Skipped (embedded text detected) |

### `ui_builder.py` の変更

```python
# _build_tools_scrollable() 内の OCR ボタン部分
# ocr_provider == "off" の場合は両ボタンを disabled として生成する
# （後からプロバイダ設定変更時に enabled/disabled を切り替えるため
#   _doc_buttons リストとは別の _ocr_buttons リストで管理することを推奨）
is_ocr_on = self.settings.get("ocr_provider", "off") != "off"
state = "normal" if is_ocr_on else "disabled"
```

### `OCRDialog` の変更ポイント

1. `__init__` に `provider: OCRProvider` 引数を追加（`url`, `model` は lmstudio 専用に縮退）
2. `_fetch_models()` を `provider.list_models()` 経由に変更
3. `_build()` で LM Studio 固有行（サーバURL / モデルコンボ）を `isinstance(provider, LMStudioProvider)` で条件表示
4. `_worker()` の API 呼び出し部分を `run_parallel(provider, ...)` に置き換え
5. `_finish_error()` で `OCRAPIKeyError` を受け取り専用メッセージ表示

---

## プラグイン登録フック（フェーズ4・解釈B）

### 新設する拡張ポイント

```python
# pagefolio/plugins.py に追加
class PluginManager:
    def __init__(self):
        ...
        self._provider_registry: dict = {}  # {name: OCRProvider subclass}

    def register_provider(self, name: str, provider_cls: type) -> None:
        """OCR プロバイダクラスを名前で登録する。
        
        プラグインは on_load(app) 内で app.register_ocr_provider() を通じて呼ぶ。
        """
        self._provider_registry[name] = provider_cls

    def get_provider_registry(self) -> dict:
        """登録済みプロバイダクラス辞書のコピーを返す。"""
        return dict(self._provider_registry)
```

```python
# pagefolio/app.py に追加
class PDFEditorApp(...):
    def register_ocr_provider(self, name: str, provider_cls: type) -> None:
        """プラグインから OCR プロバイダを登録するヘルパー。"""
        self.plugin_manager.register_provider(name, provider_cls)
```

```python
# プラグイン側（plugins/my_azure_ocr.py）の使用例
from pagefolio.plugins import PDFEditorPlugin
from pagefolio.ocr_providers import OCRProvider

class AzureOCRProvider(OCRProvider):
    def ocr_image(self, b64_png, prompt, **kwargs): ...
    def list_models(self): return ["azure-vision-v4"]

class AzureOCRPlugin(PDFEditorPlugin):
    name = "Azure OCR"
    def on_load(self, app):
        app.register_ocr_provider("azure", AzureOCRProvider)
```

`build_provider()` は `extra_registry=self.plugin_manager.get_provider_registry()` を受け取り、
組み込みプロバイダより前にプラグイン登録プロバイダを確認する。これにより組み込みプロバイダの上書きも可能になる（意図的に「lmstudio」を別実装で置き換えるプラグインも書ける）。

---

## ビルド順（依存関係を考慮した推奨実装順）

### フェーズ1 — プロバイダ抽象化（他フェーズの土台）

```
Step 1-1:  pagefolio/ocr_providers.py 新設
           - OCRProvider 抽象基底クラス
           - OCRAPIKeyError 例外クラス
           - LMStudioProvider（ocr.py の call_lm_studio + fetch_lm_studio_models を移動）

Step 1-2:  pagefolio/ocr.py 改修
           - call_lm_studio / build_chat_payload / fetch_lm_studio_models を ocr_providers.py に委譲
           - call_lm_studio_parallel → run_parallel(provider, images_b64, ...) にリネーム+シグネチャ変更
           - build_provider(settings) ファクトリ追加（lmstudio のみ対応の時点では十分）
           - has_embedded_text(page) 追加（fitz.Page.get_text() ベース）
           - OCRMixin._start_ocr() で build_provider() を呼ぶよう改修

Step 1-3:  pagefolio/ocr_dialog.py 改修
           - __init__ に provider 引数追加
           - _fetch_models() → provider.list_models() に変更
           - _worker() → run_parallel(provider, ...) に変更
           - テキスト埋め込み判定（has_embedded_text）をレンダリングループ前に追加

Step 1-4:  tests/test_ocr_providers.py 新設
           - LMStudioProvider.ocr_image() のペイロード構築をモックでテスト
           - run_parallel() の正常/キャンセル/致命的エラーのテスト
           - has_embedded_text() のテスト
```

> フェーズ1 完了時点では既存の LM Studio 挙動が完全に維持される。

### フェーズ2 — Claude プロバイダ追加

```
Step 2-1:  pagefolio/ocr_providers.py に ClaudeProvider 追加
           - messages API ペイロード構築
           - レスポンス解析（content[0].text を type=="text" で走査）
           - モデル一覧（/v1/models）
           - OCRAPIKeyError を os.environ 未設定時に raise

Step 2-2:  pagefolio/ocr.py の build_provider() に "claude" ケース追加

Step 2-3:  pagefolio/settings.py に ocr_provider / ocr_claude_model を追加

Step 2-4:  pagefolio/lang.py に Claude 向け文言キーを追加

Step 2-5:  pagefolio/ocr_dialog.py を改修
           - OCRAPIKeyError を _finish_error() でハンドル
           - LM Studio 固有 UI を条件表示

Step 2-6:  pagefolio/dialogs/settings.py に ocr_provider 選択 UI 追加

Step 2-7:  pagefolio/ui_builder.py の OCR ボタン enable/disable 制御追加

Step 2-8:  tests/test_ocr_providers.py に ClaudeProvider テスト追加
```

### フェーズ3 — Gemini プロバイダ + 逐次レンダリング最適化

```
Step 3-1:  pagefolio/ocr_providers.py に GeminiProvider 追加
           - generateContent ペイロード構築（inline_data）
           - レスポンス解析（candidates[0].content.parts[0].text）
           - モデル一覧（/v1beta/models）
           - GEMINI_API_KEY / GOOGLE_API_KEY フォールバック

Step 3-2:  pagefolio/ocr.py の build_provider() に "gemini" ケース追加

Step 3-3:  pagefolio/ocr_dialog.py の _worker() を逐次レンダリング化
           - 全ページ一括変換 → 1ページずつ変換→送信→破棄
           - メモリ節約（低スペック PC 対策）
           ※ fitz スレッドセーフ制約: doc への全アクセスを _worker スレッド内で
             シリアル実行する既存構造を維持（並列化しない）

Step 3-4:  tests/test_ocr_providers.py に GeminiProvider テスト追加
```

### フェーズ4（任意） — Tesseract + プラグイン登録機構

```
Step 4-1:  pagefolio/ocr_providers.py に TesseractProvider 追加
           - pytesseract / subprocess 経由で tesseract 呼び出し
           - 依存なし時の ImportError を OCRAPIKeyError 相当の専用例外で処理

Step 4-2:  pagefolio/plugins.py に _provider_registry + register_provider() 追加

Step 4-3:  pagefolio/app.py に register_ocr_provider() ヘルパー追加

Step 4-4:  pagefolio/ocr.py の build_provider() に extra_registry 引数追加

Step 4-5:  ドキュメント・テスト更新
```

---

## スケーラビリティ考慮

| 考慮点 | 現時点 | プロバイダ追加後 | 注意事項 |
|--------|--------|-----------------|---------|
| 並列度上限 | MAX_OCR_CONCURRENCY=8 | クラウド: 2〜3 推奨（429対策） | プロバイダ別に定数を持つ |
| メモリ使用 | 全ページ base64 を一括保持 | フェーズ3 で逐次化（1ページ分のみ） | 低RAM PC での大PDF対策 |
| レート制限 | LM Studio はなし | Claude/Gemini は429が来うる | リトライ（指数バックオフ）検討 |
| タイムアウト | 120秒固定 | プロバイダ別のデフォルト推奨 | クラウドはネットワーク依存 |

---

## 信頼度評価

| 領域 | 信頼度 | 根拠 |
|------|--------|------|
| OCRProvider 抽象設計 | HIGH | 既存コード実読 + 仕様書の確定事項 |
| fitz スレッドセーフ制約の対処方法 | HIGH | 既存 _worker の正しい実装を確認済み |
| LMStudio → Provider 移動の具体手順 | HIGH | call_lm_studio / fetch_lm_studio_models の実装を実読済み |
| ClaudeProvider / GeminiProvider の API 形式 | HIGH | 仕様書 §3 の API 差分表 + 公知情報 |
| プラグイン登録機構の設計 | MEDIUM | 仕様書の「未決定」事項。フェーズ4 実装前に要確認 |
| Tesseract の精度・依存管理 | LOW | 仕様書に「現状あまり機能していない」とあり。実動作は未検証 |

---

## ソース

- `pagefolio/ocr.py` — 実コード実読（call_lm_studio, call_lm_studio_parallel, OCRMixin）
- `pagefolio/ocr_dialog.py` — 実コード実読（_worker の2フェーズ構造）
- `pagefolio/plugins.py` — 実コード実読（PluginManager の現状）
- `pagefolio/settings.py` — 実コード実読（デフォルト値一覧）
- `pagefolio/lang.py` — 実コード実読（OCR 文言キー一覧）
- `docs/OCRプロバイダ化_見積もり仕様.md` — 設計確定事項・ロードマップの一次情報源
- `.planning/codebase/ARCHITECTURE.md` — システム構成図・データフロー
- `.planning/PROJECT.md` — マイルストーン要件・Key Decisions
