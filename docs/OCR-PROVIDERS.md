<!-- generated-by: gsd-doc-writer -->
# OCR プロバイダガイド

PageFolio の OCR 機能は、`pagefolio/ocr_providers.py` で定義された抽象基底クラス `OCRProvider` を中心に構成されています。
6 つの組み込みプロバイダと、プラグインによるカスタムプロバイダ追加の仕組みを提供します。

---

## 目次

1. [プロバイダ一覧](#プロバイダ一覧)
2. [OCRProvider 抽象基底クラス](#ocrprovider-抽象基底クラス)
3. [例外クラス](#例外クラス)
4. [組み込みプロバイダ詳細](#組み込みプロバイダ詳細)
   - [LMStudioProvider](#lmstudioprovider)
   - [ClaudeProvider](#claudeprovider)
   - [GeminiProvider](#geminiprovider)
   - [TesseractProvider](#tesseractprovider)
5. [build_provider ファクトリ](#build_provider-ファクトリ)
6. [並列実行](#並列実行)
7. [リトライ制御](#リトライ制御)
8. [カスタムプロバイダの追加（プラグイン）](#カスタムプロバイダの追加プラグイン)

---

## プロバイダ一覧

| プロバイダ名 | 設定値 | 認証 | ネットワーク | デフォルト並列度 |
|------------|--------|------|------------|---------------|
| LM Studio | `lmstudio` | 不要 | ローカル | 2 |
| Claude | `claude` | `ANTHROPIC_API_KEY` | クラウド（HTTPS） | 2 |
| Gemini | `gemini` | `GEMINI_API_KEY` | クラウド（HTTPS） | 1 |
| Ollama | `ollama` | 不要 | ローカル | 2 |
| RunPod | `runpod` | `RUNPOD_API_KEY` | クラウド（HTTPS） | 2 |
| Tesseract | `tesseract` | 不要 | ローカル（オフライン） | 1 |

---

## OCRProvider 抽象基底クラス

`pagefolio/ocr_providers.py` に定義。すべてのプロバイダはこのクラスを継承します。

```python
class OCRProvider(abc.ABC):
    default_concurrency: int = 2
    max_concurrency: int = 8

    @abc.abstractmethod
    def ocr_image(self, b64_png, prompt, **kwargs) -> str:
        ...

    @abc.abstractmethod
    def list_models(self) -> list:
        ...
```

### クラス属性

| 属性 | 説明 |
|------|------|
| `default_concurrency` | `run_parallel` / `run_with_bounded_buffer` がデフォルトで使用する並列度 |
| `max_concurrency` | 並列度の上限（設定値はこの値以下にクランプされる） |

### メソッド

#### `ocr_image(b64_png, prompt, **kwargs) -> str`

PNG 画像の base64 文字列を送信し、OCR テキストを返します。

| 引数 | 説明 |
|------|------|
| `b64_png` | PNG 画像の base64 文字列 |
| `prompt` | OCR 指示テキスト |
| `**kwargs` | プロバイダ固有の追加パラメータ |

**送出しうる例外:**

| 例外 | 条件 |
|------|------|
| `ConnectionError` | 接続失敗（サーバ未起動、ネットワーク到達不能） |
| `TimeoutError` | タイムアウト |
| `OCRAPIKeyError` | API キー未設定（クラウドプロバイダのみ） |
| `OCRRetryableError` | HTTP 429 または 5xx（リトライ可能） |
| `RuntimeError` | API エラー（4xx 等）またはレスポンス形式不正 |

#### `list_models() -> list[str]`

利用可能なモデル ID のリストを返します。取得不能時は空リストまたは静的リストを返します。

---

## 例外クラス

### `OCRAPIKeyError`

API キー未設定を示す専用例外。`env_var` 属性で対象の環境変数名を保持します。

```python
class OCRAPIKeyError(RuntimeError):
    def __init__(self, env_var):
        self.env_var = env_var
```

### `OCRRetryableError`

HTTP 429 / 5xx のリトライ可能エラー。`retry_after` 属性でサーバ指定の待機秒数を保持します（`None` の場合は指数バックオフを使用）。

```python
class OCRRetryableError(RuntimeError):
    def __init__(self, message, retry_after=None):
        self.retry_after = retry_after
```

---

## 組み込みプロバイダ詳細

### LMStudioProvider

LM Studio の OpenAI 互換 Vision API（`/v1/chat/completions`）を `urllib` で直接呼び出します。
API キー・インターネット接続は不要で、ローカル LAN 内で完結します。

**設定値:** `ocr_provider = "lmstudio"`

#### 必要な設定

| 設定キー | 既定値 | 説明 |
|---------|--------|------|
| `lm_studio_url` | `http://localhost:1234` | LM Studio サーバの URL |
| `lm_studio_model` | `""` | 使用するモデル名（空文字の場合は `"local-model"` を使用） |

LM Studio アプリを起動し、Vision 対応モデルをロードした状態でサーバを起動してください。

#### コンストラクタ

```python
LMStudioProvider(url, model, timeout=120, max_tokens=-1, temperature=0.1)
```

| 引数 | 説明 |
|------|------|
| `url` | LM Studio サーバの URL |
| `model` | 使用するモデル名 |
| `timeout` | HTTP タイムアウト秒数（既定: 120） |
| `max_tokens` | 最大トークン数（`-1` でモデル最大値に委ねる） |
| `temperature` | 温度パラメータ（OCR 用途は低温推奨・既定: 0.1） |

#### 並列度

| 属性 | 値 |
|------|-----|
| `default_concurrency` | 2 |
| `max_concurrency` | 8 |

---

### ClaudeProvider

Anthropic Claude の `/v1/messages` エンドポイントを `urllib` で直接呼び出します。
ページ画像を base64 で HTTPS 送信するため、インターネット接続が必要です。

**設定値:** `ocr_provider = "claude"`

#### 必要な設定

**環境変数（推奨）:**

```
ANTHROPIC_API_KEY=sk-ant-...
```

環境変数が未設定の場合、セッションメモリ（`app._session_api_keys["claude"]`）の値を使用します。
API キーは `pagefolio_settings.json` には保存されません。

**設定キー:**

| 設定キー | 既定値 | 説明 |
|---------|--------|------|
| `claude_model` | `claude-sonnet-4-6` | 使用するモデル ID |

#### 推奨モデル

| モデル ID | 特徴 |
|-----------|------|
| `claude-haiku-4-5` | 高速・低コスト |
| `claude-sonnet-4-6` | バランス型（effort パラメータ対応） |
| `claude-opus-4-8` | 高精度（effort パラメータ対応） |

#### コンストラクタ

```python
ClaudeProvider(api_key, model, timeout=120, max_tokens=4096, temperature=0.1, effort="low")
```

| 引数 | 説明 |
|------|------|
| `api_key` | Anthropic API キー（環境変数由来） |
| `model` | 使用するモデル ID |
| `timeout` | HTTP タイムアウト秒数（既定: 120） |
| `max_tokens` | 最大トークン数（既定: 4096。`-1` 指定時は 4096 に自動クランプ） |
| `temperature` | 温度パラメータ（haiku 系のみ使用・既定: 0.1） |
| `effort` | effort レベル（sonnet/opus 系で使用・既定: `"low"`） |

#### モデル別パラメータ制御

| モデル種別 | 適用パラメータ |
|-----------|--------------|
| `EFFORT_MODELS` に完全一致（sonnet/opus 系） | `output_config.effort` のみ送信 |
| haiku 系 | `temperature` のみ送信 |
| その他・未知モデル | 両方省略（前方互換） |

#### 並列度

| 属性 | 値 |
|------|-----|
| `default_concurrency` | 2 |
| `max_concurrency` | 2 |

---

### GeminiProvider

Google Gemini の `generateContent` API を `urllib` で直接呼び出します。
認証は `x-goog-api-key` ヘッダーを使用します（URL クエリパラメータ `?key=` は不使用）。
ページ画像を base64 で HTTPS 送信するため、インターネット接続が必要です。

**設定値:** `ocr_provider = "gemini"`

#### 必要な設定

**環境変数（優先順）:**

```
GEMINI_API_KEY=AIza...      # 優先
GOOGLE_API_KEY=AIza...      # フォールバック
```

環境変数が未設定の場合、セッションメモリ（`app._session_api_keys["gemini"]`）の値を使用します。
API キーは `pagefolio_settings.json` には保存されません。

**設定キー:**

| 設定キー | 既定値 | 説明 |
|---------|--------|------|
| `gemini_model` | `gemini-2.5-flash` | 使用するモデル ID |

#### 推奨モデル

| モデル ID | 特徴 |
|-----------|------|
| `gemini-2.5-flash` | 高速・低コスト（thinking 無効化対応） |
| `gemini-2.5-pro` | 高精度（thinkingConfig 省略） |

#### コンストラクタ

```python
GeminiProvider(api_key, model, timeout=120, max_tokens=4096, temperature=0.1)
```

| 引数 | 説明 |
|------|------|
| `api_key` | Google API キー（環境変数由来） |
| `model` | 使用するモデル ID |
| `timeout` | HTTP タイムアウト秒数（既定: 120） |
| `max_tokens` | 最大出力トークン数（既定: 4096。`-1` 指定時は 4096 に自動クランプ） |
| `temperature` | 温度パラメータ（既定: 0.1） |

#### モデル別パラメータ制御

| モデル種別 | `thinkingConfig` の扱い |
|-----------|----------------------|
| `flash` 等（non-pro） | `thinkingBudget: 0` を送信（thinking を無効化） |
| `pro` 系 | 省略（`pro` は thinking 無効化不可のため） |

#### 並列度

| 属性 | 値 | 備考 |
|------|-----|------|
| `default_concurrency` | 1 | Gemini Free Tier 10 RPM 対応 |
| `max_concurrency` | 1 | 並列度上限 |

---

### TesseractProvider

`tesseract` コマンドを stdin パイプ方式で呼び出します。
API キー・インターネット接続は不要で、完全なオフライン環境で動作します。

**設定値:** `ocr_provider = "tesseract"`

#### 必要な設定

Tesseract OCR をシステムにインストールし、`tesseract` コマンドが PATH 上にある必要があります。

**Windows へのインストール:**

[UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) のインストーラを使用してください。
日本語認識には `Japanese` 言語データ（`jpn`）を追加インストールしてください。

**インストール確認:**

```bash
tesseract --version
tesseract --list-langs
```

アプリ起動時に `_detect_tesseract()` が自動的に Tesseract の存在と利用可能言語を検出します。
`jpn` が利用可能な場合は `jpn+eng` で実行し、未インストールの場合は `eng` にフォールバックします。

#### コンストラクタ

```python
TesseractProvider(lang="jpn+eng", psm=3, timeout=60)
```

| 引数 | 説明 |
|------|------|
| `lang` | Tesseract に渡す言語コード（実行時は `_TESSERACT_LANGS` で自動解決） |
| `psm` | ページセグメンテーションモード（3=全自動、6=単一ブロック） |
| `timeout` | subprocess タイムアウト秒数（既定: 60） |

#### 注意事項

- LLM ベースのプロバイダより認識精度が劣る場合があります
- `prompt` 引数は Tesseract では無視されます（インターフェース互換のため受け取ります）

#### 並列度

| 属性 | 値 | 備考 |
|------|-----|------|
| `default_concurrency` | 1 | CPU バウンド・シングルスレッド前提 |
| `max_concurrency` | 2 | |

---

## build_provider ファクトリ

`pagefolio/ocr.py` に定義。設定辞書から適切な `OCRProvider` インスタンスを生成するファクトリ関数です。

```python
def build_provider(settings, api_key=None, plugin_manager=None) -> OCRProvider:
```

| 引数 | 説明 |
|------|------|
| `settings` | アプリ設定辞書（`ocr_provider` キーでプロバイダを選択） |
| `api_key` | クラウドプロバイダ用 API キー（`settings` には格納しない） |
| `plugin_manager` | `PluginManager` インスタンス（省略可）。プラグイン登録プロバイダへのフォールバックを有効化 |

`settings["ocr_provider"]` の値に応じて次のプロバイダを生成します:

| 値 | 生成されるプロバイダ |
|----|-------------------|
| `"lmstudio"` / `""` / `"off"` | `LMStudioProvider` |
| `"claude"` | `ClaudeProvider` |
| `"gemini"` | `GeminiProvider` |
| `"ollama"` | `OllamaProvider` |
| `"runpod"` | `RunPodProvider` |
| `"tesseract"` | `TesseractProvider` |
| 上記以外 | プラグインレジストリを検索 → 未登録なら `ValueError` |

**API キーの注入:**

```python
# build_provider は api_key を settings へ書き込まない
provider = build_provider(settings, api_key="sk-ant-...", plugin_manager=plugin_manager)
```

---

## 並列実行

`pagefolio/ocr.py` には 2 種類の並列実行関数があります。

### `run_parallel`

```python
def run_parallel(
    provider,
    images_b64,
    page_indices,
    concurrency=None,
    prompt="",
    timeout=None,
    on_progress=None,
    is_cancelled=None,
) -> tuple[dict, dict, str | None, str | None]:
```

事前に変換済みの `{page_idx: base64_png_str}` 辞書を受け取り、`ThreadPoolExecutor` で並列 OCR を実行します。

| 引数 | 説明 |
|------|------|
| `provider` | `OCRProvider` インスタンス |
| `images_b64` | `{page_idx: base64_png_str}` の辞書 |
| `page_indices` | 処理対象ページの順序付きリスト |
| `concurrency` | 並列度（`None` なら `provider.default_concurrency` を使用） |
| `prompt` | OCR 指示テキスト |
| `on_progress(done, page_idx, status)` | 完了通知コールバック |
| `is_cancelled() -> bool` | キャンセル判定関数 |

**戻り値:** `(results, errors, fatal_msg, fatal_kind)` のタプル

| 値 | 説明 |
|----|------|
| `results` | `{page_idx: text}` |
| `errors` | `{page_idx: message}` （ページ単位の失敗） |
| `fatal_msg` | 致命的エラーのメッセージ（`ConnectionError` / `TimeoutError`）。無ければ `None` |
| `fatal_kind` | `"connection"` / `"timeout"` / `None` |

### `run_with_bounded_buffer`

```python
def run_with_bounded_buffer(
    provider,
    render_fn,
    page_indices,
    concurrency=None,
    prompt="",
    on_done=None,
    is_cancelled=None,
) -> tuple[dict, dict, str | None, str | None]:
```

`render_fn`（`page_idx -> b64_png`）を producer スレッドが呼び出しながら、上限付きバッファ（`workers + 1`）を経由して consumer スレッドへ流すパイプライン実装です。全ページの base64 を同時にメモリに保持することなく OCR を実行できます。

| 引数 | 説明 |
|------|------|
| `render_fn` | `page_idx -> str | None`。`None` を返すとそのページをスキップ |
| その他 | `run_parallel` と同様 |

`on_done(page_idx, status, text_or_error)` コールバックの `status` 値:

| status | 意味 |
|--------|------|
| `"ok"` | OCR 成功 |
| `"err"` | ページ単位の失敗 |
| `"skip"` | スキップ |
| `"fatal_conn"` | 接続エラー（致命的） |
| `"fatal_timeout"` | タイムアウト（致命的） |

### OCR プロンプトプリセット

`pagefolio/ocr.py` には 3 つのプリセットが定義されています:

| キー | 用途 |
|------|------|
| `"text"` | テキスト全文抽出 |
| `"table"` | 表を Markdown テーブル形式で抽出 |
| `"markdown"` | 文書構造を保った Markdown 形式で抽出 |

プリセットは結果表示の整形（Markdown 描画）も兼ねます: `"markdown"` 選択時のみ
OCR 本文・サマリが整形表示されます（コピー / 保存は raw 維持）。

### プロンプト解決の優先順位

実際に送信されるプロンプトは `resolve_ocr_prompt` / `resolve_summary_prompt`
（`pagefolio/ocr.py`・純関数）が以下の優先順位で解決します:

| 種別 | 優先順位（上が最優先） |
|------|------------------------|
| OCR | ① カスタムプロンプト（外部 `ocr_custom_prompt.md` > 設定 `ocr_custom_prompt`）→ ② `PROVIDER_OCR_PROMPTS[provider][preset]`（claude / gemini のみ）→ ③ `OCR_PROMPTS[preset]`（既定 `text`） |
| サマリ | ① カスタムサマリプロンプト（外部 `ocr_summary_prompt.md` > 設定 `ocr_summary_prompt`）→ ② `PROVIDER_SUMMARY_PROMPTS[provider]`（claude / gemini のみ）→ ③ `DEFAULT_SUMMARY_PROMPT` |

カスタムプロンプト使用時はプリセットが実プロンプトへ反映されず「表示形式の選択」と
してのみ働きます。外部 md ファイル連動の詳細（配置場所・書き戻し・再読込タイミング）は
[CONFIGURATION.md](CONFIGURATION.md#カスタム--サマリプロンプトの仕様) を参照してください。

---

## リトライ制御

`OCRRetryableError`（HTTP 429 / 5xx）が発生した場合、`run_parallel` と `run_with_bounded_buffer` は自動的にリトライします。

### 定数

| 定数 | 値 | 説明 |
|------|-----|------|
| `MAX_RETRIES` | 3 | リトライ最大回数 |
| `RETRY_BASE_DELAY` | 1.0 秒 | 初回待機秒数（以降 `base * 2^(attempt-1)` の指数バックオフ） |
| `RETRY_AFTER_CAP` | 60.0 秒 | `Retry-After` ヘッダ値の上限クランプ |

### `clamp_retry_after`

```python
def clamp_retry_after(retry_after, cap=RETRY_AFTER_CAP) -> float:
```

サーバが返す `Retry-After` 値を `cap`（既定 60 秒）以下にクランプします。
過大な `Retry-After` 値による長時間ブロックを防ぎます。

### `interruptible_sleep`

```python
def interruptible_sleep(total, is_cancelled, step=0.5):
```

`total` 秒間を `step` 秒（既定 0.5 秒）刻みでスリープし、各ステップで `is_cancelled()` を確認します。
キャンセルが検出された時点でスリープを打ち切ります。

**リトライ待機の優先順位:**

1. `OCRRetryableError.retry_after` が設定されている場合 → その値を `clamp_retry_after` でクランプして使用
2. `retry_after = None` の場合 → `RETRY_BASE_DELAY * 2^(attempt-1)` の指数バックオフを使用

---

## カスタムプロバイダの追加（プラグイン）

プラグインの `on_load` フック内で `PluginManager.register_ocr_provider` を呼び出すことで、
カスタム OCR プロバイダを追加できます。

### 実装手順

**1. `OCRProvider` を継承したクラスを作成する**

```python
# plugins/my_ocr_plugin.py
from pagefolio.plugins import PDFEditorPlugin
from pagefolio.ocr_providers import OCRProvider


class MyOCRProvider(OCRProvider):
    default_concurrency = 1
    max_concurrency = 2

    def ocr_image(self, b64_png, prompt, **kwargs):
        # OCR 処理を実装する
        # 引数なしコンストラクタ契約（build_provider から cls() で呼ばれる）
        result_text = "..."
        return result_text

    def list_models(self):
        return ["my-ocr-model-v1"]


class MyOCRPlugin(PDFEditorPlugin):
    name = "My OCR Plugin"
    version = "1.0.0"

    def on_load(self, app):
        app.plugin_manager.register_ocr_provider("my_ocr", MyOCRProvider)

    def on_unload(self, app):
        pass
```

**2. プラグインファイルを `plugins/` ディレクトリに配置する**

```
PageFolio/
└── plugins/
    └── my_ocr_plugin.py
```

**3. アプリの設定で `ocr_provider` を登録名に設定する**

`pagefolio_settings.json` または LLM 設定ダイアログで `ocr_provider` を `"my_ocr"` に設定します。

### `register_ocr_provider` シグネチャ

```python
def register_ocr_provider(self, name: str, cls) -> None:
```

| 引数 | 説明 |
|------|------|
| `name` | プロバイダ識別名（例: `"my_ocr"`）。`build_provider` から参照される |
| `cls` | `OCRProvider` のサブクラス（インスタンスではなくクラスを渡す） |

`cls` が `OCRProvider` のサブクラスでない場合は `TypeError` を送出します。

### カスタムプロバイダのコンストラクタ規約

`build_provider` はプラグイン登録プロバイダを `cls()` で呼び出します（引数なし）。
初期化に必要な設定値はコンストラクタのデフォルト引数またはクラス変数で定義してください。

```python
class MyOCRProvider(OCRProvider):
    # コンストラクタは引数なしで呼び出せる必要がある
    def __init__(self, model="my-default-model"):
        self.model = model
```

---

## 参考情報

| 項目 | 参照先 |
|------|--------|
| 設定キー一覧 | `docs/CONFIGURATION.md` |
| プロバイダ設定 UI | `pagefolio/dialogs/llm_config.py` — `LLMConfigDialog` |
| OCR ダイアログ | `pagefolio/ocr_dialog.py` — `OCRDialog` |
| OCR 実行フロー | `pagefolio/ocr.py` — `OCRMixin._start_ocr` |
