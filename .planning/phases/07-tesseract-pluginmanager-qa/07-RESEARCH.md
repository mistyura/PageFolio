# Phase 7: Tesseract + PluginManager 拡張 + QA - Research

**Researched:** 2026-06-09
**Domain:** Python subprocess / Tesseract OCR / Tkinter Combobox / Plugin architecture
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**OCR-EXT-01: TesseractProvider**
- D-01: 起動時に `subprocess.run(["tesseract", "--version"], ...)` で存在チェック。結果をモジュールレベルフラグ `_TESSERACT_AVAILABLE` に保持。
- D-02: 未インストール時は Combobox で `"tesseract"` エントリを `state="disabled"` でグレーアウト。
- D-03: 精度劣後注記は `tesseract` 選択時の展開欄内に常設ラベルとして表示。
- D-04: OCR 言語オプションは `jpn+eng` 固定。`jpn` 未インストール時は `eng` のみにフォールバック（`tesseract --list-langs` で検出）。

**OCR-EXT-02: PluginManager 登録フック**
- D-05: `PluginManager` に `register_ocr_provider(name: str, cls: type[OCRProvider])` を追加。登録データは `_provider_registry: dict[str, type[OCRProvider]]` で保持。
- D-06: プラグインは `on_load(app)` 内で `app.plugin_manager.register_ocr_provider(...)` を呼ぶ。
- D-07: `build_provider` は既存 `if name in (...)` 分岐の後に `PluginManager._provider_registry` を参照するフォールバックを追加。参照渡し方法は Claude 裁量。
- D-08: LLMConfigDialog の Combobox values はダイアログ展開時に `["off", "lmstudio", "claude", "gemini", "tesseract"] + list(plugin_manager._provider_registry.keys())` を取得して設定。

**OCR-QA-02: ドキュメント整備**
- D-09: `lang.py` に Tesseract 専用文言を追加し、`ocr_progress_skip` 等の未使用エントリを削除または整理。
- D-10: README.md の OCR セクションを v1.4.0 版に更新（プロバイダ一覧・環境変数・Tesseract インストール案内）。
- D-11: 開発履歴.md に v1.4.0 エントリを追記（Phase 4〜7 サマリー）。

### Claude's Discretion
- `_TESSERACT_AVAILABLE` フラグの保持場所（`ocr_providers.py` モジュールレベル推奨）
- Tesseract 未インストール時の Combobox disabled 実装の具体（ttk Combobox は個別エントリ disabled 不可のため代替手段）
- `PluginManager` への `build_provider` の参照渡し方法
- `ocr_progress_skip` 等の整理方針の詳細（削除 or コメントアウト or 維持）

### Deferred Ideas (OUT OF SCOPE)
- Tesseract の言語パック選択 UI（`-l` オプションカスタマイズ）
- TesseractProvider の精度向上設定（`--psm`・`--oem` 等）
- OS キーストア連携（Windows Credential Manager）
- OCR 結果のページ埋め込み（検索可能 PDF 化）
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OCR-EXT-01 | TesseractProvider（subprocess 直呼び・`jpn+eng` 固定 / `jpn` 未インストール時は `eng` フォールバック・精度劣後注記常設） | subprocess stdin/stdout パターン確認済み・--list-langs 出力解析パターン確認済み |
| OCR-EXT-02 | `PluginManager.register_ocr_provider(name, cls)` フック。`build_provider` が登録リストを参照し、LLMConfigDialog 展開時に Combobox へ自動追加 | PluginManager 現行構造・build_provider 挿入箇所・Combobox 動的更新パターン確認済み |
| OCR-QA-02 | 全プロバイダの未整備文言整理を `lang.py` で日英対応。README の OCR セクション更新・開発履歴 v1.4.0 追記 | lang.py の未使用エントリ・sec_ocr 等の固有参照確認済み |
</phase_requirements>

---

## Summary

このフェーズは既存の OCR プロバイダアーキテクチャ（Phase 4〜6 で確立）に対して、3 つの独立した拡張を加える。

**第一の拡張（OCR-EXT-01）** は `TesseractProvider` の追加。既存の LMStudioProvider / ClaudeProvider / GeminiProvider と同一インターフェースを持つが、ネットワーク通信なしに `subprocess.run(["tesseract", ...])` で動作する。`b64_png` を受け取り一時ファイルを経由するか stdin に流し込み、stdout から OCR テキストを取得する。**stdin パイプ方式** (`tesseract stdin stdout`) が Windows 環境で動作確認済みで一時ファイル管理が不要なため推奨する。

**第二の拡張（OCR-EXT-02）** は `PluginManager` への `_provider_registry` 辞書と `register_ocr_provider` メソッドの追加。`build_provider` に登録リスト参照フォールバックを追加し、`LLMConfigDialog.__init__` で Combobox values を動的に構築する。

**第三の拡張（OCR-QA-02）** は `lang.py` の文言整備と README・開発履歴の更新。`ocr_progress_skip` は `ocr_dialog.py` 内で実際には参照されていないことをコード検索で確認済み（未使用エントリ）。

**Primary recommendation:** TesseractProvider は `stdin` パイプ方式で実装し、Tesseract 存在チェックと言語チェックを `ocr_providers.py` モジュールレベルで起動時に一度だけ実行する。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tesseract OCR 実行 | `ocr_providers.py` (TesseractProvider) | `ocr.py` (build_provider) | 既存プロバイダパターンに合わせて OCRProvider 抽象基底を継承 |
| Tesseract 存在検出 | `ocr_providers.py` モジュールレベル | — | 起動時に一度だけ実行し、結果をモジュールフラグとして保持 |
| プロバイダ登録フック | `plugins.py` (PluginManager) | `ocr.py` (build_provider) | PluginManager が registry を保持し、build_provider がフォールバック参照 |
| Combobox 動的更新 | `dialogs/llm_config.py` | — | ダイアログ展開時に plugin_manager._provider_registry から values を構築 |
| 文言管理 | `pagefolio/lang.py` | — | 既存パターン踏襲（Phase 5/6 と同じ ja/en 両辞書に同一キーで追加） |

---

## Standard Stack

### Core（追加依存なし）
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess (stdlib) | Python 3.8+ | tesseract 直呼び | pip 依存ゼロ要件（V14-D-01 踏襲） |
| base64 (stdlib) | Python 3.8+ | b64_png → PNG バイト変換 | 既存パターン（`page_to_png_b64` と逆方向） |
| tempfile (stdlib) | Python 3.8+ | stdin 方式の fallback 用 | 標準ライブラリのみ |

**Installation:**
```
# 追加インストールなし（stdlib のみ使用）
```

---

## Package Legitimacy Audit

> このフェーズは外部パッケージをインストールしない（stdlib のみ）。

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| （なし） | — | — | — |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** none

---

## Architecture Patterns

### System Architecture Diagram

```
[PDF ページ]
    │ page_to_png_b64() (ocr.py / メインスレッド)
    ▼
[base64 PNG 文字列]
    │ ワーカースレッドに渡す
    ▼
[TesseractProvider.ocr_image()]
    │ base64 → PNG バイト列に decode
    │ subprocess.run(["tesseract", "stdin", "stdout", "-l", lang, "--psm", "6"])
    │   stdin=png_bytes
    ▼
[stdout テキスト] ─── RuntimeError (tessract 実行失敗)
    │
    ▼
[OCR 結果文字列]
```

```
[アプリ起動時]
    │ subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
    │ → _TESSERACT_AVAILABLE = True/False
    │ subprocess.run(["tesseract", "--list-langs"], ...)
    │ → _TESSERACT_LANGS = {"eng", "jpn", ...}  (frozenset)
    ▼
[LLMConfigDialog 展開時]
    │ values = BASE_PROVIDERS + list(plugin_manager._provider_registry.keys())
    │ if not _TESSERACT_AVAILABLE: combo.set("tesseract エントリを末尾に追加、行を disabled 扱い")
    ▼
[プロバイダ選択 → _on_provider_change()]
    │ tesseract 展開フレームの pack/pack_forget 切替
    │ 精度劣後注記ラベルの常設表示
```

### Recommended Project Structure
```
pagefolio/
├── ocr_providers.py          # TesseractProvider 追加・モジュールレベルフラグ追加
├── ocr.py                    # build_provider に "tesseract" 分岐 + plugin_manager フォールバック
├── plugins.py                # _provider_registry + register_ocr_provider 追加
├── lang.py                   # Tesseract 専用文言追加・未使用エントリ整理
└── dialogs/
    └── llm_config.py         # Combobox 動的構築・tesseract 展開フレーム追加

tests/
└── test_ocr_providers.py     # TestTesseractProvider クラス追加
```

---

## 調査結果詳細

### 1. ocr_providers.py — 既存プロバイダ構造 [VERIFIED: コードベース直接確認]

**OCRProvider 抽象基底クラス（L16〜55）:**
- `ocr_image(self, b64_png, prompt, **kwargs) -> str` — 抽象メソッド
- `list_models(self) -> list[str]` — 抽象メソッド
- `default_concurrency: int = 2`、`max_concurrency: int = 8` — クラス属性

**各プロバイダの共通パターン:**
- `__init__` で settings 由来のパラメータを受け取る（api_key / url / model / timeout など）
- `_build_payload()` で API リクエストボディを構築（内部メソッド）
- `ocr_image()` で API を呼び出してテキストを返す
- `list_models()` でモデル一覧を返す（オフライン時は静的リストを返す設計）

**TesseractProvider の設計方針（既存パターンに合わせる）:**
```python
class TesseractProvider(OCRProvider):
    default_concurrency = 1   # シングルスレッド前提（CONTEXT D-05）
    max_concurrency = 1       # GeminiProvider と同じ理由で上限 1

    def __init__(self):
        pass  # 設定なし（API キー・URL 不要）

    def ocr_image(self, b64_png, prompt, **kwargs) -> str:
        # base64 → PNG バイト → stdin パイプ → stdout テキスト

    def list_models(self) -> list[str]:
        return ["tesseract"]  # 固定の単一エントリ
```

**モジュールレベルフラグの実装パターン（CONTEXT D-01）:**
```python
import subprocess

def _detect_tesseract():
    """起動時に一度だけ呼ばれる検出関数"""
    try:
        r = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True, timeout=5
        )
        if r.returncode != 0:
            return False, frozenset()
        # --list-langs でインストール済み言語を取得
        r2 = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True, timeout=5
        )
        lines = r2.stdout.decode(errors="replace").splitlines()
        langs = frozenset(
            line.strip() for line in lines
            if line.strip() and not line.startswith("List of")
        )
        return True, langs
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False, frozenset()

_TESSERACT_AVAILABLE, _TESSERACT_LANGS = _detect_tesseract()
```

**実機確認結果（本 dev 環境）:**
- `tesseract v5.5.0.20241111` がインストール済み [VERIFIED: subprocess 直接実行]
- `--list-langs` の出力は **stdout** に出る（Windows 版。stderr に出る環境もあるため両方確認が必要）[VERIFIED: 実機確認]
- `tesseract stdin stdout` による stdin パイプ方式が Windows で動作確認済み [VERIFIED: 実機確認]
- `jpn`・`jpn_vert`・`eng`・`osd` がインストール済み [VERIFIED: 実機確認]

---

### 2. ocr.py — build_provider 関数（L456〜507） [VERIFIED: コードベース直接確認]

現行の `build_provider` は以下の分岐構造：
```python
def build_provider(settings, api_key=None):
    name = settings.get("ocr_provider", "lmstudio")
    if name in ("lmstudio", "", "off"):
        return LMStudioProvider(...)
    elif name == "claude":
        return ClaudeProvider(...)
    elif name == "gemini":
        return GeminiProvider(...)
    # Phase 7 で追加するプロバイダはここに分岐を追加する
    raise ValueError(f"未対応のプロバイダ: {name}")  # L507
```

**Phase 7 での変更点:**
1. `elif name == "tesseract":` 分岐を追加（L507 の前）
2. `raise ValueError` の前に `plugin_manager._provider_registry` を参照するフォールバックを追加

**plugin_manager の参照渡し方法（CONTEXT D-07 — Claude 裁量）:**

3 つの選択肢を調査した：

| 方法 | メリット | デメリット |
|------|---------|-----------|
| シングルトン参照（モジュール変数） | 引数変更不要 | グローバル状態、テストしにくい |
| 引数追加 `build_provider(settings, api_key=None, plugin_manager=None)` | 明示的・テスト容易 | 呼び出し箇所の変更が必要 |
| `app` 経由（ocr_dialog 等で `self.app.plugin_manager` を渡す） | 既存コードとの一貫性 | 関数シグネチャが変わる |

**推奨: `plugin_manager=None` 引数追加方式**。`build_provider` の呼び出し箇所（`ocr_dialog.py` や `OCRMixin._start_ocr`）は既に `app` への参照を持っているため、`app.plugin_manager` を渡すのが最も明示的で後方互換性も保てる。デフォルト `None` にすることで既存テストを壊さない。

---

### 3. plugins.py — PluginManager クラス（L80〜） [VERIFIED: コードベース直接確認]

現行の `PluginManager.__init__`:
```python
def __init__(self):
    self._plugins = {}
    self._plugin_modules = {}
    self._disabled = set()
```

**Phase 7 での追加（CONTEXT D-05）:**
```python
def __init__(self):
    self._plugins = {}
    self._plugin_modules = {}
    self._disabled = set()
    self._provider_registry: dict[str, type] = {}  # OCR プロバイダ登録辞書

def register_ocr_provider(self, name: str, cls) -> None:
    """サードパーティ OCR プロバイダを登録する。
    プラグインの on_load(app) 内で呼び出すことを想定。
    """
    self._provider_registry[name] = cls
    logger.info("OCR プロバイダを登録しました: %s -> %s", name, cls.__name__)
```

`fire_event` パターンとの一貫性：プラグインが `on_load(app)` の中で `app.plugin_manager.register_ocr_provider("myprovider", MyProvider)` を呼ぶ形。これは既存の `fire_event` のコールバック構造と対称的。

---

### 4. dialogs/llm_config.py — Combobox と _on_provider_change パターン [VERIFIED: コードベース直接確認]

**現行の Combobox 初期化（L97〜108）:**
```python
self.provider_combo = ttk.Combobox(
    provider_row,
    textvariable=self.provider_var,
    values=["off", "lmstudio", "claude", "gemini"],  # ← Phase 7 で動的生成に変更
    state="readonly",
    ...
)
```

**Phase 7 での変更（CONTEXT D-08）:**
`_build()` で Combobox を構築する時点では `plugin_manager` への参照が必要。
`LLMConfigDialog.__init__` に `plugin_manager=None` 引数を追加し、`_build()` で以下のように構築する：

```python
base_providers = ["off", "lmstudio", "claude", "gemini", "tesseract"]
plugin_providers = list(self._plugin_manager._provider_registry.keys()) \
    if self._plugin_manager else []
self.provider_combo["values"] = base_providers + plugin_providers
```

**ttk.Combobox の個別エントリ disabled 問題（CONTEXT D-02 — Claude 裁量）:**

ttk.Combobox は `state="readonly"` または `state="disabled"` で**全体**を制御するしかなく、個別エントリを disabled にする標準 API は存在しない [VERIFIED: Tkinter ドキュメント・コードベース確認] [ASSUMED: 代替手段の完全なリスト]。

実用的な代替手段：

| 手段 | 実装難度 | UX |
|------|---------|-----|
| **エントリを追加しない**（Tesseract 未インストール時は values から除外）+ ツールチップ的な説明ラベルを別途表示 | 低 | シンプル・明確 |
| `"tesseract (未インストール)"` のような文字列でエントリを表示し、選択時に `provider_var` を前の値にリセット + 警告ラベル表示 | 中 | 視覚的に存在を示せる |
| `postcommand` で `state="disabled"` に切り替えて選択を阻止 | 中 | 不確実・UX 悪い |

**推奨: 「エントリを追加しない + 説明ラベル」方式**。
Tesseract 未インストール時は `values` から `"tesseract"` を除き、代わりに Combobox の下に小さなラベルで `"Tesseract: 未インストール（tesseract.exe が見つかりません）"` を表示する。これが最もシンプルで後方互換性も高い。

ただし、CONTEXT D-02 は `state="disabled"` でグレーアウトする方向性を示しているため、**「値として追加するが選択時に前の値に戻す」** 方式も許容される。その場合の実装：
```python
# Combobox の <<ComboboxSelected>> ハンドラ内で
if self.provider_var.get() == "tesseract" and not _TESSERACT_AVAILABLE:
    self.provider_var.set(self._prev_provider)
    self._set_lm_status(self._L["tesseract_not_installed_hint"], kind="fail")
```

---

### 5. lang.py — 既存 OCR 文言・未使用エントリ [VERIFIED: コードベース直接確認]

**`ocr_progress_skip` の使用状況:**
- `lang.py` の ja（L267）と en（L622）に定義済み
- `ocr_dialog.py` でも `ocr.py` でも参照されていない（grep で確認済み）[VERIFIED: コードベース直接確認]
- Phase 4 の VERIFICATION.md にも「INFO: デッドな辞書エントリ」として記録済み

**整理方針（Claude 裁量）の推奨:** 削除。コメントアウトよりも明確で、ruff チェックの煩雑さも生じない。CONTEXT D-09 でも「削除または整理」とある。

**`sec_ocr` と `ocr_dialog_title` の現状:**
- `sec_ocr`: `"🔍 OCR（LM Studio）"` — ui_builder.py で参照。プロバイダ非依存の名称に変更推奨（例: `"🔍 OCR"`）
- `ocr_dialog_title`: `"OCR — LM Studio"` — ocr_dialog.py で参照。同様に変更推奨

**追加が必要な Tesseract 専用文言キー:**

| キー | 日本語 | 英語 |
|------|--------|-------|
| `ocr_provider_name_tesseract` | `"Tesseract (ローカル)"` | `"Tesseract (Local)"` |
| `tesseract_accuracy_warning` | `"※ Tesseract の精度は LLM ベースのプロバイダより劣ります"` | `"Note: Tesseract accuracy is lower than LLM-based providers."` |
| `tesseract_not_installed` | `"Tesseract がインストールされていません（tesseract コマンドが見つかりません）"` | `"Tesseract is not installed (command not found)."` |
| `tesseract_lang_fallback` | `"jpn 言語パックが見つかりません。eng のみで実行します"` | `"jpn language pack not found. Running with eng only."` |
| `tesseract_not_installed_hint` | `"Tesseract がインストールされていません。他のプロバイダを使用してください"` | `"Tesseract is not installed. Please use another provider."` |

---

### 6. subprocess.run での画像 OCR — stdin/stdout パターン [VERIFIED: 実機確認]

**確認済みパターン（Windows 環境・tesseract v5.5.0）:**

```python
import subprocess, base64

def _run_tesseract(b64_png: str, lang: str = "jpn+eng") -> str:
    """base64 PNG を stdin 経由で tesseract に送り stdout テキストを返す。

    stdin パイプ方式: tesseract stdin stdout -l <lang> --psm 6
    Windows 環境での動作確認済み。
    """
    png_bytes = base64.b64decode(b64_png)
    try:
        result = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", lang, "--psm", "6"],
            input=png_bytes,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError as e:
        raise RuntimeError("tesseract コマンドが見つかりません") from e
    except subprocess.TimeoutExpired as e:
        raise TimeoutError("Tesseract がタイムアウトしました") from e

    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")
        raise RuntimeError(f"Tesseract エラー (rc={result.returncode}): {err}")
    return result.stdout.decode("utf-8", errors="replace").strip()
```

**--list-langs の出力先（プラットフォーム差異注意）:**
- Windows（確認済み）: **stdout** に出力
- Linux 系（一般的な報告）: stderr に出力する場合がある [ASSUMED]
- 両方を確認するフォールバック実装を推奨：

```python
r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, timeout=5)
raw = (r.stdout or r.stderr).decode(errors="replace")  # Windows は stdout、Linux は stderr
langs = frozenset(
    line.strip() for line in raw.splitlines()
    if line.strip() and not line.lower().startswith("list of")
)
```

**注意点（pitfall）:**
- `capture_output=True` は Python 3.7+ 以降のみ。Python 3.8+ が要件なので問題なし。
- `psm 6`: "Assume a single uniform block of text." — PDF ページ OCR に適切。
- stdin パイプ方式は PNG バイトを直接渡せるため一時ファイル管理不要。ただし tesseract のバージョンや OS によって `stdin` を受け付けない場合は一時ファイル方式にフォールバックすること。

---

### 7. ttk.Combobox の個別エントリ disabled — 制約と代替手段 [VERIFIED: コードベース確認]

ttk.Combobox の標準 API:
- `state="readonly"`: ドロップダウン選択のみ可（テキスト入力不可）
- `state="disabled"`: Combobox 全体を無効化（クリックもドロップダウンも不可）
- `state="normal"`: 自由入力可

**個別エントリ disabled の標準方法は存在しない** [ASSUMED: Tkinter の設計上の制約]。

代替手段の比較（本フェーズで推奨する方法：**選択後リセット + ステータスラベル**）:

```python
def _on_provider_change(self, _event=None):
    provider = self.provider_var.get()

    # Tesseract が未インストールで選択された場合はリセット
    if provider == "tesseract" and not _TESSERACT_AVAILABLE:
        # 直前の有効なプロバイダに戻す
        self.provider_var.set(self._last_valid_provider)
        self._set_lm_status(self._L["tesseract_not_installed_hint"], kind="fail")
        return

    self._last_valid_provider = provider  # 有効な選択を記録
    # ... 以降の pack/pack_forget 処理
```

または、よりシンプルに「Tesseract 未インストール時は values から除外し、代わりに説明テキストを表示」する方式：
```python
# _build() 内
base = ["off", "lmstudio", "claude", "gemini"]
if _TESSERACT_AVAILABLE:
    base.append("tesseract")
plugin_extras = list(pm._provider_registry.keys()) if pm else []
self.provider_combo["values"] = base + plugin_extras

# values から除外した場合、別途説明ラベルを追加
if not _TESSERACT_AVAILABLE:
    tk.Label(provider_row, text=self._L["tesseract_not_installed"],
             fg=C["TEXT_SUB"], bg=C["BG_DARK"], font=self._font(-2)).pack(...)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tesseract 呼び出し | pytesseract ライブラリ | `subprocess.run(["tesseract", ...])` | pip 依存ゼロ要件（V14-D-01 踏襲） |
| --list-langs パース | 独自フォーマットパーサー | 単純な splitlines() + frozenset | 出力形式は行ごとに言語名のみのシンプル構造 |
| プロバイダ登録 | 独自イベントシステム | `PluginManager._provider_registry` dict + `on_load` ライフサイクル | 既存 fire_event パターンと一貫性を保つ |

---

## Common Pitfalls

### Pitfall 1: --list-langs の出力先が OS 依存
**What goes wrong:** Windows では stdout に出るが Linux では stderr に出る場合がある
**Why it happens:** tesseract の OS 別ビルド差異
**How to avoid:** `raw = (r.stdout or r.stderr).decode(...)` で両方を確認する
**Warning signs:** `_TESSERACT_LANGS` が空 frozenset になる

### Pitfall 2: stdin パイプ方式で PNG 以外を渡す
**What goes wrong:** tesseract stdin は PNG ヘッダーを期待する。b64 文字列をそのまま渡すと rc!=0
**Why it happens:** base64 decode を忘れる
**How to avoid:** `png_bytes = base64.b64decode(b64_png)` してから `input=png_bytes` に渡す
**Warning signs:** returncode=1 かつ "Error during processing." エラー

### Pitfall 3: Combobox values への参照渡しタイミング
**What goes wrong:** LLMConfigDialog が展開される前にプラグインが `register_ocr_provider` を呼んでいない場合、plugin 提供のプロバイダが Combobox に反映されない
**Why it happens:** プラグインは `on_load` で登録するが、アプリ起動時より後にプラグインを追加する場合
**How to avoid:** CONTEXT D-08 通り「ダイアログ展開時」に `_provider_registry.keys()` を参照する（起動時ではなくダイアログ `_build()` 時点で取得）
**Warning signs:** プラグイン登録後もダイアログに新プロバイダが表示されない

### Pitfall 4: build_provider のプラグイン参照で plugin_manager が None
**What goes wrong:** `plugin_manager=None` のとき `_provider_registry` アクセスで `AttributeError`
**Why it happens:** デフォルト引数を追加したが呼び出し箇所で渡し忘れ
**How to avoid:** `if plugin_manager is not None and name in plugin_manager._provider_registry:` でガード
**Warning signs:** テスト中に AttributeError が発生する

### Pitfall 5: sec_ocr / ocr_dialog_title の更新忘れ
**What goes wrong:** `sec_ocr` が `"OCR（LM Studio）"` のままだと Tesseract 追加後に UI が誤解を招く
**Why it happens:** lang.py の文言をプロバイダ非依存に更新しない
**How to avoid:** `sec_ocr` を `"🔍 OCR"` 等に変更し、`ocr_dialog_title` も同様に更新する

---

## Code Examples

### TesseractProvider の骨格
```python
# Source: 実機確認パターン（ocr_providers.py 既存構造を踏襲）
import subprocess
import base64

def _detect_tesseract():
    try:
        r = subprocess.run(
            ["tesseract", "--version"], capture_output=True, timeout=5
        )
        if r.returncode != 0:
            return False, frozenset()
        r2 = subprocess.run(
            ["tesseract", "--list-langs"], capture_output=True, timeout=5
        )
        raw = (r2.stdout or r2.stderr).decode(errors="replace")
        langs = frozenset(
            line.strip() for line in raw.splitlines()
            if line.strip() and not line.lower().startswith("list of")
        )
        return True, langs
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False, frozenset()

_TESSERACT_AVAILABLE, _TESSERACT_LANGS = _detect_tesseract()


class TesseractProvider(OCRProvider):
    default_concurrency = 1
    max_concurrency = 1

    def ocr_image(self, b64_png, prompt, **kwargs):
        # prompt は無視（Tesseract は固定動作）
        lang = "jpn+eng" if "jpn" in _TESSERACT_LANGS else "eng"
        png_bytes = base64.b64decode(b64_png)
        try:
            result = subprocess.run(
                ["tesseract", "stdin", "stdout", "-l", lang, "--psm", "6"],
                input=png_bytes,
                capture_output=True,
                timeout=60,
            )
        except FileNotFoundError as e:
            raise RuntimeError("tesseract コマンドが見つかりません") from e
        except subprocess.TimeoutExpired as e:
            raise TimeoutError("Tesseract がタイムアウトしました") from e
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            raise RuntimeError(f"Tesseract エラー (rc={result.returncode}): {err}")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def list_models(self):
        return ["tesseract"]
```

### PluginManager への _provider_registry 追加
```python
# Source: plugins.py 既存コードを踏襲
class PluginManager:
    def __init__(self):
        self._plugins = {}
        self._plugin_modules = {}
        self._disabled = set()
        self._provider_registry: dict = {}  # OCR プロバイダ登録辞書

    def register_ocr_provider(self, name: str, cls) -> None:
        """OCR プロバイダを登録する（プラグインの on_load から呼ぶ）"""
        self._provider_registry[name] = cls
        logger.info("OCR プロバイダを登録しました: %s -> %s", name, cls.__name__)
```

### build_provider のフォールバック追加
```python
# Source: ocr.py L456〜507 の構造を踏襲
def build_provider(settings, api_key=None, plugin_manager=None):
    ...
    elif name == "tesseract":
        from pagefolio.ocr_providers import TesseractProvider
        return TesseractProvider()
    # プラグイン登録プロバイダへのフォールバック
    if plugin_manager is not None and name in plugin_manager._provider_registry:
        cls = plugin_manager._provider_registry[name]
        return cls()  # プラグインプロバイダは引数なしで初期化できることを前提
    raise ValueError(f"未対応のプロバイダ: {name}")
```

### LLMConfigDialog の Combobox 動的構築
```python
# Source: dialogs/llm_config.py L97〜108 の構造を踏襲
from pagefolio.ocr_providers import _TESSERACT_AVAILABLE

# _build() 内で呼ぶ
def _build_provider_values(self):
    base = ["off", "lmstudio", "claude", "gemini", "tesseract"]
    extras = (
        list(self._plugin_manager._provider_registry.keys())
        if self._plugin_manager else []
    )
    return base + extras

# Combobox 展開後にテスト入力で選択された "tesseract" を検出してリセット
def _on_provider_change(self, _event=None):
    provider = self.provider_var.get()
    if provider == "tesseract" and not _TESSERACT_AVAILABLE:
        self.provider_var.set(self._last_valid_provider)
        self._set_lm_status(self._L["tesseract_not_installed_hint"], kind="fail")
        return
    self._last_valid_provider = provider
    # ... 以降の pack/pack_forget
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LM Studio 単一プロバイダ | OCRProvider 抽象基底 + 複数プロバイダ | Phase 4 | プロバイダ差し替え可能 |
| pytesseract ライブラリ | subprocess 直呼び | Phase 7 (new) | pip 依存ゼロ維持 |
| 固定 Combobox values | 動的 values（plugin_manager 参照） | Phase 7 (new) | プラグイン拡張可能 |

**Deprecated/outdated:**
- `ocr_progress_skip` キー: lang.py に定義済みだが ocr_dialog.py で参照されていない → 削除対象

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Linux 環境では `tesseract --list-langs` が stderr に出力する | 調査結果 6 | Windows 専用実装になっているため低リスクだが、マルチ OS 対応時に問題 |
| A2 | ttk.Combobox の個別エントリ disabled は標準 API で不可 | 調査結果 7 | 将来の Tkinter 版で追加された場合はより良い実装に移行できる |
| A3 | プラグインプロバイダは引数なしで初期化できる | Code Examples / build_provider | プラグイン作者が引数必要な設計をした場合は呼び出し失敗する |

**リスク軽減策:** A3 については、プラグイン側が設定の受け取り方を任意にできるよう、将来的に `build_provider` が `settings` を渡せるインターフェース拡張を検討する（今フェーズはスコープ外）。

---

## Open Questions

1. **`sec_ocr` と `ocr_dialog_title` の更新スコープ**
   - What we know: 現在 "OCR（LM Studio）" と "OCR — LM Studio" と書かれている
   - What's unclear: Phase 7 で変更するか、次マイルストーンに先送りするか
   - Recommendation: OCR-QA-02 の「全プロバイダの未整備文言整備」スコープに含まれるため Phase 7 で更新する

2. **プラグインプロバイダへの settings 渡し方法**
   - What we know: 現行の `cls()` 引数なし初期化では設定（URL / API キー等）を渡せない
   - What's unclear: Phase 7 のスコープに含めるか
   - Recommendation: 今フェーズは `cls()` 引数なし（プラグイン作者が settings を別途取得することを前提）としてスコープを限定する

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Tesseract OCR | TesseractProvider | ✓ (dev env) | v5.5.0.20241111 | Combobox から除外 / 未インストール表示 |
| jpn 言語パック | TesseractProvider (jpn+eng) | ✓ (dev env) | — | eng のみで実行（D-04 フォールバック） |
| Python subprocess | TesseractProvider | ✓ | stdlib | — |

**Missing dependencies with no fallback:** なし（Tesseract 未インストール時は選択肢が disabled/除外になるだけで他プロバイダは正常動作）

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_ocr_providers.py -x -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OCR-EXT-01 | TesseractProvider.ocr_image が b64_png → str を返す | unit (monkeypatch subprocess) | `pytest tests/test_ocr_providers.py::TestTesseractProvider -x` | ❌ Wave 0 |
| OCR-EXT-01 | Tesseract 未インストール時に RuntimeError | unit (monkeypatch FileNotFoundError) | `pytest tests/test_ocr_providers.py::TestTesseractProvider::test_not_installed -x` | ❌ Wave 0 |
| OCR-EXT-01 | jpn 未インストール時に eng フォールバック | unit (monkeypatch _TESSERACT_LANGS) | `pytest tests/test_ocr_providers.py::TestTesseractProvider::test_lang_fallback -x` | ❌ Wave 0 |
| OCR-EXT-01 | list_models が ["tesseract"] を返す | unit | `pytest tests/test_ocr_providers.py::TestTesseractProvider::test_list_models -x` | ❌ Wave 0 |
| OCR-EXT-02 | PluginManager.register_ocr_provider が _provider_registry に登録する | unit | `pytest tests/test_plugins.py::TestPluginManagerProviderRegistry -x` | ❌ Wave 0 |
| OCR-EXT-02 | build_provider が plugin_manager._provider_registry を参照する | unit | `pytest tests/test_ocr.py::TestBuildProviderPlugin -x` | ❌ Wave 0 |
| OCR-QA-02 | lang.py に Tesseract 専用キーが存在する | unit (import check) | `pytest tests/test_lang.py::TestTesseractLangKeys -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_ocr_providers.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ocr_providers.py` に `TestTesseractProvider` クラス追加（OCR-EXT-01）
- [ ] `tests/test_plugins.py` に `TestPluginManagerProviderRegistry` クラス追加（OCR-EXT-02）
- [ ] `tests/test_ocr.py` に `TestBuildProviderPlugin` テスト追加（OCR-EXT-02）
- [ ] `tests/test_lang.py` があれば Tesseract 文言キーの存在チェックを追加（OCR-QA-02）

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | subprocess への入力は b64_png のみ（デコード後に tesseract stdin へ渡す）|
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| コマンドインジェクション（lang 引数） | Tampering | lang は `_TESSERACT_LANGS` に存在するもののみ使用。ユーザー入力を直接 `-l` に渡さない（D-04: `jpn+eng` 固定） |
| 大容量 PNG による DoS | DoS | タイムアウト 60s を設定（`subprocess.run timeout=60`） |
| 一時ファイル残留（tmpfile 方式使用時） | Tampering | stdin パイプ方式を優先して一時ファイルを不要にする |

**今フェーズのセキュリティ方針:** `lang` オプションは `_TESSERACT_LANGS` で検出済みのものか "eng" のフォールバックのみを使用し、ユーザー入力を直接 CLI 引数に渡さない。subprocess の引数はリスト形式（`["tesseract", ...]`）で渡し、shell=True を使用しない。

---

## Sources

### Primary (HIGH confidence)
- コードベース直接確認（grep・Read ツール）- ocr_providers.py / plugins.py / ocr.py / dialogs/llm_config.py / lang.py
- 実機での subprocess 実行確認（tesseract v5.5.0.20241111、Windows 11）

### Secondary (MEDIUM confidence)
- `.planning/phases/07-tesseract-pluginmanager-qa/07-CONTEXT.md` - フェーズ設計決定事項

### Tertiary (LOW confidence)
- Linux での `--list-langs` の stderr 出力についての一般的知識 [ASSUMED]
- ttk.Combobox の個別エントリ disabled 不可の制約 [ASSUMED: 訓練データ由来]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib のみ使用、追加依存なし
- Architecture: HIGH - 既存コードベースを直接確認、実機で動作検証済み
- Pitfalls: HIGH（tesseract stdin パターン）/ MEDIUM（OS 差異部分は ASSUMED あり）

**Research date:** 2026-06-09
**Valid until:** 2026-07-09（tesseract の仕様変更は稀なため 30 日）

---

## Project Constraints (from CLAUDE.md)

| Directive | Category |
|-----------|----------|
| 裸の `except:` 禁止（`except Exception as e:` 形式必須） | Coding convention |
| `# type: ignore` 無断使用禁止 | Coding convention |
| `ruff check . && ruff format .` を py ファイル編集後に実行 | Required tool |
| `pytest` をコミット前に実行 | Required tool |
| テーマ色は `C["KEY"]` 辞書で参照（ハードコード禁止） | Coding convention |
| フォントサイズは `self._font(delta)` で指定 | Coding convention |
| `pyproject.toml` / `ruff.toml` の編集禁止 | Forbidden pattern |
| `APP_VERSION` を更新する際は `constants.py`・`README.md`・`開発履歴.md` を同期 | Version management |
| すべての返答を日本語で行う | Language rule |
