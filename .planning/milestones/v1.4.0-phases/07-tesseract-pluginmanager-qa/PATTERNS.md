# Phase 7: Tesseract + PluginManager 拡張 + QA — Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 8
**Analogs found:** 8 / 8

---

## File Classification

| 新規/変更ファイル | Role | Data Flow | 最近似アナログ | 一致品質 |
|-----------------|------|-----------|--------------|---------|
| `pagefolio/ocr_providers.py` (TesseractProvider 追加) | service | transform (subprocess → text) | `GeminiProvider` (同ファイル) | exact-role, diff-data-flow |
| `pagefolio/ocr.py` (build_provider 分岐追加) | service | request-response | `build_provider` の gemini 分岐 (l.494–505) | exact |
| `pagefolio/plugins.py` (_provider_registry + register_ocr_provider 追加) | service | event-driven | `PluginManager.fire_event` (l.186–196) | role-match |
| `pagefolio/dialogs/llm_config.py` (Combobox 動的化・tesseract フレーム追加) | component | request-response | `_on_provider_change` + `gemini_section_frame` ブロック (l.485–512) | exact |
| `pagefolio/lang.py` (文言追加・整理) | config | — | `lang.py` 既存エントリ (l.1–60 以降) | exact |
| `README.md` (OCR セクション更新) | config | — | なし（文書のみ） | no-analog |
| `開発履歴.md` (v1.4.0 エントリ) | config | — | なし（文書のみ） | no-analog |
| `tests/test_ocr_providers.py` (TestTesseractProvider 追加) | test | transform | `TestGeminiProviderBasic` / `TestGeminiProviderOcrImage` クラス (l.719–1011) | exact |

---

## Pattern Assignments

### `pagefolio/ocr_providers.py` — TesseractProvider (service, transform)

**アナログ:** `GeminiProvider` (同ファイル `pagefolio/ocr_providers.py`)

**選定理由:** Tesseract は API 呼び出しを持たず、代わりに `subprocess` でローカル実行する。
GeminiProvider は API キー必須・ネットワーク依存だが、クラス構造（クラス属性 `default_concurrency`、`__init__` での設定格納、`ocr_image`/`list_models` の 2 抽象メソッド実装）が最も近い。
ClaudeProvider は effort/temperature の切り替えロジックが複雑すぎるため非推奨。

**インポートパターン** (`pagefolio/ocr_providers.py` l.1–12):
```python
import abc
import json
import logging
import socket
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
```

TesseractProvider は urllib 不要。代わりに以下を追加する:
```python
import shutil
import subprocess
```

**クラス属性パターン** (`GeminiProvider` l.435–443):
```python
class GeminiProvider(OCRProvider):
    default_concurrency = 1   # Free Tier の RPM 上限対応
    max_concurrency = 1

    RECOMMENDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]
```

TesseractProvider では `default_concurrency = 1` / `max_concurrency = 2`（CPU バウンド）、
`RECOMMENDED_LANGS = ["jpn", "eng", "jpn+eng"]` をクラス属性として定義する。

**`__init__` パターン** (`GeminiProvider.__init__` l.445–459):
```python
def __init__(self, api_key, model, timeout=120, max_tokens=4096, temperature=0.1):
    self.api_key = api_key
    self.model = model
    self.timeout = timeout
    self.max_tokens = max_tokens
    self.temperature = temperature
```

TesseractProvider では API キー・モデル・temperature は不要。代わりに:
```python
def __init__(self, lang="jpn+eng", psm=3, timeout=60):
    self.lang = lang
    self.psm = psm
    self.timeout = timeout
```

**`ocr_image` — subprocess 呼び出しコアパターン:**
LMStudioProvider の `ocr_image` (l.123–168) の try/except 構造を参考に、
urllib 例外を subprocess 例外へ置き換える:
```python
def ocr_image(self, b64_png, prompt, **kwargs):
    import base64, tempfile, os
    # base64 → PNG 一時ファイル → tesseract stdout → テキスト返却
    png_bytes = base64.b64decode(b64_png)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png_bytes)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "-l", self.lang, "--psm", str(self.psm)],
            capture_output=True, text=True, timeout=self.timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"tesseract 失敗: {result.stderr.strip()}")
        return result.stdout
    except FileNotFoundError as e:
        raise RuntimeError("tesseract が見つかりません。インストールと PATH 設定を確認してください") from e
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"timed out after {self.timeout}s") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
```

**`list_models` — ローカルコマンドパターン:**
GeminiProvider の「キー未設定時は静的リストを返す」パターン (l.578–580) を参考に、
tesseract コマンド不在時は RECOMMENDED_LANGS を返す:
```python
def list_models(self):
    # tesseract --list-langs からインストール済み言語を返す
    if not shutil.which("tesseract"):
        return list(self.RECOMMENDED_LANGS)
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stderr.splitlines() or result.stdout.splitlines()
        return [l.strip() for l in lines if l.strip() and "List" not in l]
    except Exception:
        return list(self.RECOMMENDED_LANGS)
```

---

### `pagefolio/ocr.py` — `build_provider` 分岐追加 (service, request-response)

**アナログ:** `build_provider` の `elif name == "gemini":` 分岐 (l.494–505)

**コアパターン** (`pagefolio/ocr.py` l.494–507):
```python
elif name == "gemini":
    # api_key は settings から読まず引数のみ・settings へ書き込まない（D-01/D-05）
    from pagefolio.ocr_providers import GeminiProvider

    return GeminiProvider(
        api_key=api_key or "",
        model=settings.get("gemini_model", "gemini-2.5-flash"),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
        max_tokens=int(settings.get("ocr_max_tokens", 4096)),
        temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
    )
# Phase 7 で追加するプロバイダはここに分岐を追加する
raise ValueError(f"未対応のプロバイダ: {name}")
```

TesseractProvider 分岐は `elif name == "gemini":` ブロックの直後、`raise ValueError` の前に挿入:
```python
elif name == "tesseract":
    from pagefolio.ocr_providers import TesseractProvider

    return TesseractProvider(
        lang=settings.get("tesseract_lang", "jpn+eng"),
        psm=int(settings.get("tesseract_psm", 3)),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
    )
```

プラグインフォールバック分岐（`_provider_registry` を参照）は `raise ValueError` の直前:
```python
# プラグイン登録プロバイダへのフォールバック
# (PluginManager._provider_registry に登録されていれば使用)
# Phase 7 で実装
```

---

### `pagefolio/plugins.py` — `_provider_registry` + `register_ocr_provider` (service, event-driven)

**アナログ:** `PluginManager.fire_event` (l.186–196) および `_plugins` / `_disabled` の辞書管理パターン (l.83–87)

**既存辞書管理パターン** (`pagefolio/plugins.py` l.83–87):
```python
def __init__(self):
    self._plugins = {}       # {plugin_id: plugin_instance}
    self._plugin_modules = {}  # {plugin_id: module}
    self._disabled = set()   # 無効化されたプラグインIDのセット
```

`_provider_registry` は同じ辞書パターンを使い `__init__` に追加:
```python
self._provider_registry = {}  # {provider_name: OCRProvider サブクラス}
```

**`register_ocr_provider` メソッドパターン:**
`fire_event` (l.186–196) の `getattr` ガード構造を参考に、登録時バリデーションを入れる:
```python
def register_ocr_provider(self, name, provider_class):
    """プラグインが OCR プロバイダを登録する。

    引数:
      name:           プロバイダ識別名（例: "my_ocr"）
      provider_class: OCRProvider のサブクラス（インスタンスではなくクラス）

    例外: TypeError — provider_class が OCRProvider のサブクラスでない場合
    """
    from pagefolio.ocr_providers import OCRProvider

    if not (isinstance(provider_class, type) and issubclass(provider_class, OCRProvider)):
        raise TypeError(f"{provider_class} は OCRProvider のサブクラスでなければなりません")
    self._provider_registry[name] = provider_class
    logger.debug("OCR プロバイダ登録: %s -> %s", name, provider_class.__name__)
```

**`fire_event` のエラー隔離パターン** (`pagefolio/plugins.py` l.186–196):
```python
def fire_event(self, event_name, *args, **kwargs):
    """有効な全プラグインにイベントを通知する"""
    for _plugin_id, plugin in self.plugins.items():
        method = getattr(plugin, event_name, None)
        if method:
            try:
                method(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    "プラグインイベント %s 発火失敗: %s", event_name, e
                )
```

`register_ocr_provider` は `fire_event` の `try/except Exception as e` パターンを踏襲し、
プラグイン側の登録失敗がアプリ全体をクラッシュさせないようにする。

---

### `pagefolio/dialogs/llm_config.py` — Combobox 動的化 + tesseract フレーム (component, request-response)

**アナログ:** `_on_provider_change` (l.485–512) および `gemini_section_frame` 構築ブロック (l.219–251)

**Combobox values 設定箇所** (l.97–106):
```python
self.provider_combo = ttk.Combobox(
    provider_row,
    textvariable=self.provider_var,
    # Phase 7: tesseract を追加予定
    values=["off", "lmstudio", "claude", "gemini"],
    state="readonly",
    font=self._font(-1),
    width=14,
)
```

Phase 7 では `values=["off", "lmstudio", "claude", "gemini", "tesseract"]` に変更する。
プラグイン登録プロバイダは `PluginManager._provider_registry.keys()` から動的に取得して追記する:
```python
# PluginManager が利用可能な場合はプラグイン登録プロバイダも追加
extra = list(plugin_manager._provider_registry.keys()) if plugin_manager else []
values = ["off", "lmstudio", "claude", "gemini", "tesseract"] + extra
self.provider_combo["values"] = values
```

**`_on_provider_change` のフレーム pack/pack_forget パターン** (l.485–512):
```python
def _on_provider_change(self, _event=None):
    provider = self.provider_var.get()

    if provider == "lmstudio":
        self.url_section_frame.pack(fill="x", padx=24, pady=(4, 2))
    else:
        self.url_section_frame.pack_forget()

    if provider == "claude":
        self.claude_section_frame.pack(fill="x", padx=24, pady=(4, 2))
        self.gemini_section_frame.pack_forget()
        self._on_model_change()
    elif provider == "gemini":
        self.gemini_section_frame.pack(fill="x", padx=24, pady=(4, 2))
        self.claude_section_frame.pack_forget()
        self.effort_frame.pack_forget()
        self.temperature_frame.pack(fill="x", padx=24, pady=2)
    else:
        self.claude_section_frame.pack_forget()
        self.gemini_section_frame.pack_forget()
        self.effort_frame.pack_forget()
        self.temperature_frame.pack(fill="x", padx=24, pady=2)
```

tesseract フレームは `elif provider == "gemini":` の直後に追加する:
```python
elif provider == "tesseract":
    self.tesseract_section_frame.pack(fill="x", padx=24, pady=(4, 2))
    self.claude_section_frame.pack_forget()
    self.gemini_section_frame.pack_forget()
    self.effort_frame.pack_forget()
    self.temperature_frame.pack_forget()
```

**tesseract フレーム構築パターン — Gemini フレームを参照** (l.219–251):
```python
# ── Gemini 固有欄（gemini 選択時のみ表示）──
self.gemini_section_frame = tk.Frame(self, bg=C["BG_DARK"])

gemini_model_row = tk.Frame(self.gemini_section_frame, bg=C["BG_DARK"])
gemini_model_row.pack(fill="x", padx=0, pady=2)
tk.Label(
    gemini_model_row,
    text=self._L["settings_lm_model"],
    bg=C["BG_DARK"],
    fg=C["TEXT_MAIN"],
    font=self._font(-1),
    width=20,
    anchor="w",
).pack(side="left")
self.gemini_model_var = tk.StringVar(
    value=self.current_settings.get("gemini_model", "gemini-2.5-flash"),
)
self.gemini_model_combo = ttk.Combobox(
    gemini_model_row,
    textvariable=self.gemini_model_var,
    font=self._font(-1),
    values=GeminiProvider.RECOMMENDED_MODELS,
)
self.gemini_model_combo.pack(side="left", fill="x", expand=True, padx=4)
```

tesseract フレームでは `gemini_model_combo` の代わりに言語 Combobox と PSM Spinbox を用意する。
モデル更新ボタン (l.245–251) の代わりに「インストール済み言語の取得」ボタンを同パターンで作成する。

**`_apply` での設定収集パターン** (l.681–742) — `gemini_model` の取り出し方を踏襲:
```python
llm_settings["gemini_model"] = (
    self.gemini_model_var.get().strip() or "gemini-2.5-flash"
)
```

tesseract は:
```python
llm_settings["tesseract_lang"] = self.tesseract_lang_var.get().strip() or "jpn+eng"
llm_settings["tesseract_psm"] = max(0, min(13, int(self.tesseract_psm_var.get())))
```

---

### `pagefolio/lang.py` — tesseract 文言追加 (config)

**アナログ:** `pagefolio/lang.py` の既存エントリ構造 (l.1–60)

**エントリ追加パターン** — OCR 関連文言の命名規則を踏襲:
```python
# 既存 OCR 文言のキー命名例:
"ocr_provider_label":   "OCR プロバイダ:",
"ocr_effort_label":     "effort:",
"ocr_temperature_short": "温度:",
"ocr_model_refresh":    "モデル一覧を更新",
```

tesseract 専用キーは同じプレフィックス `ocr_` / `tesseract_` を使う:
```python
"tesseract_lang_label":      "言語:",
"tesseract_psm_label":       "PSM:",
"tesseract_fetch_langs":     "インストール済み言語を取得",
"tesseract_not_found":       "tesseract が見つかりません。インストールと PATH を確認してください",
"tesseract_precision_note":  "※ Tesseract は LLM より精度が低い場合があります",
"tesseract_psm_hint":        "3=全自動, 6=単一ブロック, 11=1行ずつ",
```

英語 (`"en"`) キーも同時に追加する（既存 `"en"` エントリを参照し同じキーを追記）。

---

### `tests/test_ocr_providers.py` — TestTesseractProvider (test, transform)

**アナログ:** `TestGeminiProviderBasic` (l.719–746) と `TestGeminiProviderOcrImage` (l.825–923)

**選定理由:** GeminiProvider は `list_models` で「キー未設定時に静的リスト返却」パターンを持ち、
TesseractProvider の「tesseract 未インストール時に RECOMMENDED_LANGS 返却」と構造が同一。
ClaudeProvider は effort/temperature 判定テストが多く複雑すぎる。

**テストクラス基本構造パターン** (l.719–746):
```python
class TestGeminiProviderBasic:
    """GeminiProvider の基本属性とインターフェース準拠を確認する"""

    def test_is_ocr_provider_subclass(self):
        from pagefolio.ocr_providers import GeminiProvider, OCRProvider
        assert issubclass(GeminiProvider, OCRProvider)

    def test_instantiation(self):
        from pagefolio.ocr_providers import GeminiProvider
        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        assert p is not None

    def test_default_concurrency(self):
        from pagefolio.ocr_providers import GeminiProvider
        assert GeminiProvider.default_concurrency == 1

    def test_max_concurrency(self):
        from pagefolio.ocr_providers import GeminiProvider
        assert GeminiProvider.max_concurrency == 1
```

TesseractProvider 向けに同じ構造で置き換える:
```python
class TestTesseractProviderBasic:
    def test_is_ocr_provider_subclass(self):
        from pagefolio.ocr_providers import OCRProvider, TesseractProvider
        assert issubclass(TesseractProvider, OCRProvider)

    def test_instantiation(self):
        from pagefolio.ocr_providers import TesseractProvider
        p = TesseractProvider()
        assert p is not None

    def test_default_concurrency(self):
        from pagefolio.ocr_providers import TesseractProvider
        assert TesseractProvider.default_concurrency == 1

    def test_recommended_langs_is_list(self):
        from pagefolio.ocr_providers import TesseractProvider
        assert isinstance(TesseractProvider.RECOMMENDED_LANGS, list)
```

**`monkeypatch` による subprocess モックパターン:**
GeminiProvider テストの `monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)` (l.798–803) に倣い、
subprocess.run をモックする:
```python
def test_ocr_image_success(self, monkeypatch):
    from pagefolio import ocr_providers
    import subprocess

    def fake_run(cmd, capture_output, text, timeout):
        class R:
            returncode = 0
            stdout = "OCR 結果\n"
            stderr = ""
        return R()

    monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
    # tempfile 書き込みが走るため tmp png 削除も monkeypatch 対象にする
    ...
```

**`tesseract` 未インストール時のフォールバックテストパターン:**
GeminiProvider の「キー未設定時に RECOMMENDED_MODELS を返す」テスト (l.929–935) を参考:
```python
def test_list_models_tesseract_not_found_returns_recommended(self, monkeypatch):
    from pagefolio.ocr_providers import TesseractProvider
    monkeypatch.setattr("shutil.which", lambda _: None)
    p = TesseractProvider()
    result = p.list_models()
    assert result == list(TesseractProvider.RECOMMENDED_LANGS)
```

**エラーハンドリングテストパターン** — `TestGeminiProviderOcrImage` の例外系 (l.860–923):
```python
def test_timeout_raises_timeout_error(self, monkeypatch):
    import subprocess
    from pagefolio import ocr_providers

    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 60)

    monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
    p = ocr_providers.TesseractProvider(timeout=60)
    with pytest.raises(TimeoutError):
        p.ocr_image("Zg==", "describe")

def test_tesseract_not_found_raises_runtime_error(self, monkeypatch):
    from pagefolio import ocr_providers

    def fake_run(cmd, **kw):
        raise FileNotFoundError("tesseract")

    monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
    p = ocr_providers.TesseractProvider()
    with pytest.raises(RuntimeError, match="tesseract が見つかりません"):
        p.ocr_image("Zg==", "describe")
```

---

## Shared Patterns

### エラーハンドリング — RuntimeError/TimeoutError/ConnectionError の 3 層構造

**ソース:** `pagefolio/ocr_providers.py` (LMStudioProvider, l.147–168)

**適用先:** `TesseractProvider.ocr_image`

```python
try:
    # 処理本体
    ...
except urllib.error.HTTPError as e:
    raise RuntimeError(f"HTTP {e.code}: ...") from e
except socket.timeout as e:
    raise TimeoutError(f"timed out after {self.timeout}s") from e
except urllib.error.URLError as e:
    reason = getattr(e, "reason", e)
    if isinstance(reason, socket.timeout):
        raise TimeoutError(f"timed out after {self.timeout}s") from e
    raise ConnectionError(str(reason)) from e
```

TesseractProvider では urllib 例外を subprocess 例外に置き換える（上記 ocr_image パターン参照）。

### テーマ色参照 — `C["KEY"]` 経由

**ソース:** `pagefolio/dialogs/llm_config.py` l.49, l.80, l.85 等

**適用先:** tesseract フレームの全ウィジェット

```python
bg=C["BG_DARK"],
fg=C["TEXT_MAIN"],
fg=C["TEXT_SUB"],   # ヒントテキスト
fg=C["SUCCESS"],    # 成功ステータス
fg=C["ACCENT"],     # 失敗ステータス
fg=C["WARNING"],    # 処理中ステータス
```

### フォント参照 — `self._font(delta)` ヘルパー

**ソース:** `pagefolio/dialogs/llm_config.py` l.79, l.87, l.165 等

**適用先:** tesseract フレームの全 Label/Combobox/Entry

```python
font=self._font(-1),   # 通常フォント（-1 delta）
font=self._font(-2),   # ヒントテキスト（-2 delta）
font=self._font(2, "bold"),  # 見出し
```

### PluginManager での例外隔離パターン

**ソース:** `pagefolio/plugins.py` `fire_event` l.192–196

**適用先:** `register_ocr_provider` の呼び出し側（OCRMixin やプラグイン）

```python
try:
    method(*args, **kwargs)
except Exception as e:
    logger.exception("プラグインイベント %s 発火失敗: %s", event_name, e)
```

---

## No Analog Found

| ファイル | Role | Data Flow | 理由 |
|---------|------|-----------|------|
| `README.md` | config | — | Markdown ドキュメント。コードアナログなし |
| `開発履歴.md` | config | — | Markdown ドキュメント。コードアナログなし |

---

## Metadata

**アナログ検索スコープ:** `pagefolio/`, `tests/`
**スキャンファイル数:** 13
**Pattern extraction date:** 2026-06-09
