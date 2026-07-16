# Phase 1: 基盤分割（肥大モジュールリファクタリング） - Research

**Researched:** 2026-07-13
**Domain:** 既存 Python/Tkinter デスクトップアプリの肥大モジュール分割（パッケージ化リファクタリング）+ 機密キー管理の中央レジストリ化
**Confidence:** HIGH（対象コード全文・既存テスト・既存前例パターンをすべて直接読了した curated 調査。外部ライブラリ調査は不要— 本フェーズは新規依存を一切追加しない純粋リファクタリング）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ocr_providers パッケージの分割単位**
- **D-01:** 分割粒度は**1プロバイダ=1ファイル**。`pagefolio/ocr_providers/` パッケージに `base.py`（`OCRProvider` ABC + 共有ヘルパー）・`errors.py`（`OCRAPIKeyError`/`OCRRetryableError`/`OCRContextLengthError` 等）・`lmstudio.py`・`claude.py`・`gemini.py`・`tesseract.py`（`_detect_tesseract` 含む）・`ollama.py`・`runpod.py` を配置。各ファイル約150〜330行。dialogs/ 分割の「1クラス=1ファイル」前例と一貫。
- **D-02:** OpenAI互換チャット系3プロバイダ（LMStudio/Ollama/RunPod）の重複コード（`_build_payload`/`_post_chat` 等）は**機械的移動に徹し共通化しない**。3者の payload には微妙な差分（RunPod Serverless 形式・Ollama `/api/chat` 等）があり、安易な共通化は回帰リスク。中間基底クラス（OpenAICompatProvider 等）の導入は将来の別タスク。
- **D-03:** `tests/test_ocr_providers.py` は**分割せず現状維持**。既存テストが旧 import パス経由でグリーンのまま通ること自体が後方互換の検証になる。Phase 1 の差分はソース側に限定する。

**llm_config の分割戦略**
- **D-04:** 単一クラス `LLMConfigDialog`（約1550行・`_build` だけで約920行）は **Mixin 分割**で再構成する。`pagefolio/dialogs/llm_config/` パッケージ化し、self 参照メソッドをそのまま移す機械的移動に近い形にする（PDFEditorApp の 8 Mixin 構成の確立パターンと一貫）。
- **D-05:** Mixin の分割軸は**責務別3層**: `dialog.py`（本体 `__init__`/`_apply`/`_on_provider_change` 等の共通部・約400行）・`sections.py`（`_build` の UI セクション構築・約700行）・`model_fetch.py`（`_fetch_models_async` + プロバイダ別 probe/refresh 群・約400行）。プロバイダ別分割は不採用（共通セクションとの絡みで切り出し線が複雑になるため）。
- **D-06:** Phase 2（テンプレート/フォールバック UI 追加）向けの**投機的な仕込みはしない**（純粋分割のみ・YAGNI）。セクション登録機構や空セクションは作らない。責務別 Mixin 構造自体が拡張ポイントとして十分。

**_SENSITIVE_KEYS 中央レジストリ**
- **D-07:** レジストリは**新 ocr_providers パッケージ内**に `ocr_providers/registry.py` として新設。プロバイダ定義と同居させ「新プロバイダ追加時に触る場所が1箇所」を実現。stdlib のみ依存（Tk/fitz 非依存）に保ち、`settings.py` から import しても循環しない設計とする。
- **D-08:** 宣言方式は**宣言的 dict 一本**（例: `PROVIDER_ENV_KEYS = {"claude": ("ANTHROPIC_API_KEY",), "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "runpod": ("RUNPOD_API_KEY",)}`・タプル順序が解決優先順）。セッションキー名（`claude_api_key` 等の小文字バリアント）もレジストリから導出する。Provider クラス属性からの収集は不採用（settings のガードが全 Provider import に依存し、プラグイン動的登録との整合問題を抱え込むため）。
- **D-09:** 統合範囲は**全参照面**: (1) `settings._SENSITIVE_KEYS` をレジストリから生成、(2) `ocr.py` `build_provider` のキー解決、(3) `ocr_dialog.py` の送信先確認 dict（provider→env var）、(4) `llm_config.py` の環境変数チェック — 4箇所すべてをレジストリ参照へ置換し重複マッピングを排除。Gemini の dual env var 優先順（GEMINI_API_KEY 優先→GOOGLE_API_KEY・D-06/WR-03 由来）は不変で保持。既存の keyguard 回帰テスト（`test_settings_keyguard.py`・3経路テスト）が安全網。生成後の `_SENSITIVE_KEYS` は現行10エントリと同等以上（大小文字バリアント含む）であること。

**内部 import の移行方針**
- **D-10:** 内部コード（`ocr.py`・`ocr_dialog.py`・`app.py` 等の分割対象外ファイル）の import は**旧パスのまま維持**（`from pagefolio.ocr_providers import ClaudeProvider` 等）。パッケージ直下 import を今後も正規の公開面として扱う。分割対象外ファイルに差分を出さず、re-export 面が本番コードで常時検証される。
- **D-11:** `__init__.py` は**完全再エクスポート**: private ヘルパー（`_raise_mapped_http_error`・`_detect_tesseract`・`_require_http_scheme` 等）含む旧モジュールレベル名をすべて公開し、import 表面の完全互換を保証。constants.py 分割前例の `# noqa: F401` パターンを踏襲。`pagefolio.dialogs.llm_config` も同様（`from pagefolio.dialogs import LLMConfigDialog` / `from pagefolio.dialogs.llm_config import LLMConfigDialog` の両方が動作すること）。

### Claude's Discretion
- base.py と errors.py の間のシンボル配置の細目（リトライヘルパー `parse_retry_after`/`looks_like_context_error` をどちらに置くか等）
- registry.py の関数 API 設計（`sensitive_keys()`/`env_vars_for(provider)` 等の名前・シグネチャ）
- `test_imports.py` へ追加する後方互換テストの具体的なケース構成（分割前に先行追加すること自体は必達）
- CLAUDE.md のファイル構成表の更新内容

### Deferred Ideas (OUT OF SCOPE)
- **OpenAI互換プロバイダの中間基底クラス（OpenAICompatProvider）導入** — LMStudio/Ollama/RunPod の重複吸収。将来の別タスク（D-02 で明示的に不採用としたリファクタ拡張）
- **tests/test_ocr_providers.py のプロバイダ別分割** — 将来テストが肥大化した際に検討（D-03 で今回は不採用）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V180-REFAC-01 | `ocr_providers.py`（1537行・実測）がパッケージ分割される（後方互換 import 維持・`test_imports.py` 先行拡張） | 「Architecture Patterns」の完全シンボル一覧・パッケージ構造・「Common Pitfalls」#1/#2/#4 |
| V180-REFAC-02 | `dialogs/llm_config.py`（1660行・実測）がパッケージ分割される（後方互換 import 維持・`test_imports.py` 先行拡張） | 「Architecture Patterns」Mixin 分割設計・「Common Pitfalls」#3/#5 |
| V180-ROBUST-02 | `_SENSITIVE_KEYS` がプロバイダ→環境変数マッピングから生成される中央レジストリへ再編される | 「Don't Hand-Roll」・「Code Examples」registry.py 設計・「Common Pitfalls」#6 |
</phase_requirements>

## Summary

本フェーズは新規機能を一切追加しない**純粋な構造リファクタリング**であり、対象は3点: (1) `pagefolio/ocr_providers.py`（実測1537行、6プロバイダ+共有基盤）のパッケージ分割、(2) `pagefolio/dialogs/llm_config.py`（実測1660行、単一クラス）の Mixin パッケージ分割、(3) API キー機密判定の `_SENSITIVE_KEYS` を4箇所の重複マッピングから中央レジストリへ集約。プロジェクトには既に2つの完成した前例（DEBT-01: `pagefolio/dialogs/` パッケージ化・DEBT-02: `constants.py`→`themes.py`/`lang.py` 分割）があり、いずれも「サブパッケージ化 + `__init__.py` での完全 re-export（`# noqa: F401`）」という同一パターンを使っている。本フェーズはこのパターンをそのまま2つの新対象に適用するだけであり、新規の設計判断はほぼ不要。

最大のリスクは「re-export の抜け漏れ」による後方互換破壊である。`ocr_providers.py` は private ヘルパー（`_require_http_scheme`・`parse_retry_after`・`looks_like_context_error`・`_raise_mapped_http_error` 等）まで含めて `tests/test_ocr_providers.py` から直接 import されており、`__init__.py` の re-export リストから1つでも漏れると即座にテストが赤くなる。本 RESEARCH では実コードを全文精査し、re-export が必要な**全17シンボル**を「Architecture Patterns」に列挙した。もう一つのリスクは `_SENSITIVE_KEYS` レジストリ化で、現行の10エントリには「プロバイダ短縮名+`_api_key`」（セッションキー形式）と「環境変数名の小文字化」という**2つの異なる命名規則が混在**しており（例: claude は `claude_api_key`≠`anthropic_api_key` だが runpod は両方とも `runpod_api_key` に一致）、単純な機械的生成では抜けが生じる。これは「Common Pitfalls」#6 に詳述する。

**Primary recommendation:** DEBT-01/DEBT-02 の re-export パターンをそのまま適用し、分割前に `test_imports.py` へ本 RESEARCH 列挙済みの全シンボルに対する明示 import テストを追加してから分割を開始する。`_SENSITIVE_KEYS` は「セッションキー形式」と「環境変数名（大小文字）」の両方を派生させる関数を registry.py に実装し、既存10エントリ全てを生成結果でカバーできることを `test_settings_keyguard.py` で確認する。

## Architectural Responsibility Map

本プロジェクトは単一プロセスの Tkinter デスクトップアプリであり、Web アプリの Browser/Server/DB 階層は存在しない。代わりに「UI 非依存の純ロジック層」と「Tkinter/fitz 依存の UI 層」という自プロジェクト固有の階層分けが確立している（`pagination.py`・`ocr_pipeline.py`・`undo_store.py` が純ロジック層の前例）。本フェーズの分割対象をこの階層で分類する。

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OCR プロバイダ実装（HTTP/subprocess 通信） | 純ロジック層（Tk/fitz 非依存） | — | `ocr_providers.py` は `urllib`/`subprocess`/`abc` のみに依存し Tk/fitz を一切 import しない。既存 `pagination.py`/`ocr_pipeline.py` と同じ層に属する |
| `_SENSITIVE_KEYS` レジストリ | 純ロジック層（Tk/fitz 非依存） | 設定永続化層（`settings.py`） | dict 定義と関数のみで stdlib 完結。`settings.py`（永続化）・`ocr.py`（キー解決）双方から参照される横断的関心事 |
| LLMConfigDialog UI 構築 | Tkinter UI 層 | 純ロジック層（`_apply` のクランプ計算部分） | `tk.Toplevel` サブクラスであり Tkinter に強く依存。ただし値のクランプ・バリデーションロジックは分離可能 |
| モデル一覧取得（`_fetch_models_async`） | Tkinter UI 層（`threading`+`after()` ブリッジ） | 純ロジック層（`Provider.list_models()` 自体） | スレッド↔メインスレッドの橋渡しは Tkinter 依存だが、実際の HTTP 呼び出しは Provider 側（純ロジック層）に委譲済み |
| 設定ファイル永続化（`_save_settings`） | 設定永続化層（`settings.py`） | — | JSON I/O のみ。Tk 非依存 |

## Standard Stack

本フェーズは**新規パッケージ依存を一切追加しない**。既存 stdlib のみで完結する。

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `abc` | stdlib | `OCRProvider` 抽象基底クラス | 既存コードが使用中、変更なし |
| `urllib.request`/`urllib.error` | stdlib | 各プロバイダの HTTP 通信 | 既存コードが使用中、変更なし（V14-D-01「新規 pip 依存ゼロ方針」継続） |
| `subprocess` | stdlib | Tesseract 呼び出し | 既存コードが使用中、変更なし |
| `tkinter`/`tkinter.ttk` | stdlib | LLMConfigDialog UI | 既存コードが使用中、変更なし |
| `threading` | stdlib | `_fetch_models_async` バックグラウンド実行 | 既存コードが使用中、変更なし |

### Supporting
本フェーズで新規追加するものはコード分割の器（新規モジュールファイル）のみであり、外部ライブラリの追加はない。

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 宣言的 dict レジストリ（D-08） | Provider クラス属性からの動的収集（例: `Provider.env_vars` クラス変数） | CONTEXT.md で不採用理由が明示済み: 全 Provider の import に settings ガードが依存することになり、プラグイン動的登録プロバイダとの整合が複雑化する |
| Mixin 分割（D-04） | 単純な関数分割（クラスを保ったままファイルだけ分ける） | Mixin の方が PDFEditorApp の確立パターンと一貫し、`self` 参照コードの機械的移動がしやすい |

**Installation:** 不要（新規パッケージ追加なし）。

**Version verification:** 該当なし。既存 `requirements.txt` の固定バージョン（pymupdf 1.27.2.2 / Pillow 12.2.0 / tkinterdnd2 0.4.3）は本フェーズで変更しない。

## Package Legitimacy Audit

**該当なし。** 本フェーズは外部パッケージを一切導入しない純粋な内部リファクタリングである（新規 `import` 対象はすべてプロジェクト内 stdlib 依存モジュール）。Package Legitimacy Gate はスキップする。

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ UI 層（Tkinter）                                                  │
│                                                                   │
│  llm_config/ (新パッケージ・Mixin 3層)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐        │
│  │ dialog.py    │  │ sections.py  │  │ model_fetch.py    │        │
│  │ (共通部・     │  │ (_build UI   │  │ (_fetch_models_   │        │
│  │  __init__/   │←→│  セクション   │←→│  async + probe/   │        │
│  │  _apply/     │  │  構築)       │  │  refresh 群)       │        │
│  │  _on_*)      │  │              │  │                    │        │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘        │
│         └──────────class LLMConfigDialog(DialogMixin,──┘            │
│                            SectionsMixin, ModelFetchMixin)          │
│         __init__.py が re-export → 既存 import パス完全互換          │
└───────────────────────────┬───────────────────────────────────────┘
                            │ from pagefolio.ocr_providers import
                            │   ClaudeProvider, GeminiProvider,
                            │   LMStudioProvider, _detect_tesseract
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 純ロジック層（Tk/fitz 非依存）                                       │
│                                                                   │
│  ocr_providers/ (新パッケージ・1プロバイダ=1ファイル)                 │
│  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐       │
│  │base.py │ │errors.py│ │registry.py│ │lmstudio│ │claude  │ ...   │
│  │OCRProv-│ │OCRAPIKey│ │PROVIDER_  │ │.py     │ │.py     │       │
│  │ider ABC│ │Error等  │ │ENV_KEYS   │ │        │ │        │       │
│  └────┬───┘ └────┬────┘ └─────┬─────┘ └───┬────┘ └───┬────┘       │
│       └──────────┴─────────────┴───────────┴──────────┘           │
│                    __init__.py が全シンボル re-export               │
│                    （既存 import パス `pagefolio.ocr_providers`     │
│                     完全互換・private ヘルパー含む）                 │
└───────────┬─────────────────────────────────────────┬─────────────┘
            │                                         │
            ▼                                         ▼
┌───────────────────────────┐          ┌──────────────────────────────┐
│ settings.py                │          │ ocr.py / ocr_dialog.py        │
│ _SENSITIVE_KEYS =           │          │ build_provider() /            │
│   registry.sensitive_keys() │          │ _resolve_api_key() が         │
│ （4箇所の重複マッピングを     │          │ registry.env_vars_for() を    │
│   registry 参照へ統合）      │          │ 参照（D-09 全参照面統合）      │
└───────────────────────────┘          └──────────────────────────────┘
```

### Recommended Project Structure
```
pagefolio/
├── ocr_providers/                  # REFAC-01: パッケージ化（旧 ocr_providers.py を置換）
│   ├── __init__.py                 # 完全 re-export（全17シンボル・# noqa: F401）
│   ├── base.py                     # OCRProvider ABC + _require_http_scheme + _ALLOWED_URL_SCHEMES
│   ├── errors.py                   # OCRAPIKeyError/OCRRetryableError/OCRContextLengthError
│   │                                # + parse_retry_after/looks_like_context_error/
│   │                                #   _raise_mapped_http_error/_retryable_http_message/
│   │                                #   _CONTEXT_ERROR_MARKERS（Claude's Discretion:
│   │                                #   base.py と errors.py どちらに置くか）
│   ├── registry.py                  # 新設: PROVIDER_ENV_KEYS 宣言的 dict + 導出関数群（ROBUST-02）
│   ├── lmstudio.py                  # LMStudioProvider
│   ├── claude.py                    # ClaudeProvider
│   ├── gemini.py                    # GeminiProvider
│   ├── tesseract.py                 # TesseractProvider + _detect_tesseract
│   ├── ollama.py                    # OllamaProvider
│   └── runpod.py                    # RunPodProvider
├── dialogs/
│   ├── llm_config/                  # REFAC-02: パッケージ化（旧 llm_config.py を置換）
│   │   ├── __init__.py              # LLMConfigDialog を re-export
│   │   ├── dialog.py                 # DialogMixin: __init__/_apply/_on_provider_change/
│   │   │                             #   _on_model_change/_resize_to_fit/_set_lm_status 等
│   │   ├── sections.py               # SectionsMixin: _build + 各プロバイダ UI セクション構築
│   │   └── model_fetch.py            # ModelFetchMixin: _fetch_models_async +
│   │                                  #   _probe_*/_refresh_*/_fetch_* 群
│   ├── __init__.py                   # 既存（DEBT-01 前例・変更なし）
│   └── settings.py                   # 既存（llm_config import 元・変更なし）
├── settings.py                       # _SENSITIVE_KEYS を registry 生成へ置換（ROBUST-02）
├── ocr.py                            # build_provider/_resolve_api_key が registry 参照へ（D-09）
└── ocr_dialog.py                     # _check_cloud_api_key の env_var dict が registry 参照へ（D-09）
```

### Pattern 1: `__init__.py` 完全再エクスポート（DEBT-01/DEBT-02 前例の踏襲）

**What:** サブパッケージ化後の `__init__.py` で旧モジュールの全公開シンボル（private ヘルパー含む）を re-export する。

**When to use:** 単一モジュールをパッケージへ分割する際、既存の import パス（`from pagefolio.xxx import Yyy`）を一切変更させたくない場合に必須。

**Example（既存 `pagefolio/dialogs/__init__.py` の実物パターン）:**
```python
# Source: pagefolio/dialogs/__init__.py（本プロジェクトの確立済み前例・DEBT-01）
"""pagefolio.dialogs — 後方互換の再エクスポート集約"""

from pagefolio.dialogs.about import AboutDialog  # noqa: F401
from pagefolio.dialogs.llm_config import LLMConfigDialog  # noqa: F401
from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog  # noqa: F401
# ... 以下同様に全ダイアログクラスを re-export
```

同じ形で `pagefolio/constants.py`（DEBT-02）も分割後 re-export している:
```python
# Source: pagefolio/constants.py（本プロジェクトの確立済み前例・DEBT-02）
from pagefolio.lang import LANG  # noqa: F401
from pagefolio.themes import THEMES, C  # noqa: F401
```

**本フェーズでの適用（`pagefolio/ocr_providers/__init__.py` に必要な完全シンボルリスト・実コード精査で確認済み）:**
```python
# 想定コード例（Claude's Discretion 範囲: base/errors 間の配置以外は固定）
from pagefolio.ocr_providers.base import (  # noqa: F401
    OCRProvider,
    _ALLOWED_URL_SCHEMES,
    _require_http_scheme,
)
from pagefolio.ocr_providers.errors import (  # noqa: F401
    OCRAPIKeyError,
    OCRRetryableError,
    OCRContextLengthError,
    _CONTEXT_ERROR_MARKERS,
    _retryable_http_message,
    parse_retry_after,
    looks_like_context_error,
    _raise_mapped_http_error,
)
from pagefolio.ocr_providers.lmstudio import LMStudioProvider  # noqa: F401
from pagefolio.ocr_providers.claude import ClaudeProvider  # noqa: F401
from pagefolio.ocr_providers.gemini import GeminiProvider  # noqa: F401
from pagefolio.ocr_providers.tesseract import (  # noqa: F401
    TesseractProvider,
    _detect_tesseract,
)
from pagefolio.ocr_providers.ollama import OllamaProvider  # noqa: F401
from pagefolio.ocr_providers.runpod import RunPodProvider  # noqa: F401
```
**根拠:** `tests/test_ocr_providers.py` を全文 grep した結果、`_require_http_scheme`・`parse_retry_after`・`looks_like_context_error` は private 名のままパッケージ直下から直接 import されている（例: `from pagefolio.ocr_providers import parse_retry_after`）。1つでも re-export から漏れると `test_ocr_providers.py`（D-03 により変更禁止）が即座に失敗する。

### Pattern 2: Mixin 分割（PDFEditorApp 8 Mixin 構成の踏襲）

**What:** 単一の巨大クラスを、`self` 状態を共有する複数の Mixin クラスへ責務別に分割し、最終的に多重継承で1クラスへ再構成する。

**When to use:** クラスが複数の明確な責務（構築/構成 vs UI 組み立て vs 非同期処理）を持ち、かつメソッド間で `self.xxx` 属性を密に共有している場合。

**Example（既存 `pagefolio/app.py` の実物パターン）:**
```python
# Source: pagefolio/app.py:107-117（本プロジェクトの確立済み前例）
class PDFEditorApp(
    UIBuilderMixin,
    FileOpsMixin,
    PageOpsMixin,
    RedactOpsMixin,
    ViewerMixin,
    DnDMixin,
    OCRMixin,
    PrintOpsMixin,
):
    MAX_UNDO = 20

    def __init__(self, root):
        ...
```

**本フェーズでの適用（`pagefolio/dialogs/llm_config/__init__.py` 想定）:**
```python
# 想定コード例（D-04/D-05 に基づく設計）
import tkinter as tk

from pagefolio.dialogs.llm_config.dialog import DialogMixin
from pagefolio.dialogs.llm_config.model_fetch import ModelFetchMixin
from pagefolio.dialogs.llm_config.sections import SectionsMixin


class LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel):
    """LLM 設定ダイアログ（OCR と設定で共有）— Mixin 分割後の統合クラス"""

    def __init__(self, parent, current_settings, on_apply, ...):
        # 旧 __init__ の内容をそのまま移動（DialogMixin 側に実体を持たせるか
        # ここに残すかは Claude's Discretion。tk.Toplevel.__init__ 呼び出し順に注意）
        ...
```
**注意:** `tk.Toplevel` を継承する既存クラスなので、多重継承の MRO（`super().__init__(parent)` の解決順）を壊さないよう `tk.Toplevel` を継承リストの末尾に置く（既存コードは `class LLMConfigDialog(tk.Toplevel):` で `super().__init__(parent)` を呼んでいるため、Mixin を先に、`tk.Toplevel` を最後に配置するのが安全）。

### Pattern 3: 宣言的レジストリからの複数命名規則導出（registry.py 新設パターン）

**What:** プロバイダ→環境変数の1つの宣言的マッピングから、複数の異なる命名規則（env var 名そのもの・env var 名の小文字化・セッションキー形式）を導出する関数群。

**When to use:** 同じ「プロバイダの機密キー」という概念が、コードベース内の複数箇所で異なる文字列表現（`ANTHROPIC_API_KEY` 環境変数名 / `claude_api_key` セッションキー名 / `anthropic_api_key` 小文字化）で参照されている場合。

**Example（想定設計・Claude's Discretion の関数 API 部分）:**
```python
# pagefolio/ocr_providers/registry.py（新設・想定コード例）
"""プロバイダ→環境変数の中央レジストリ（ROBUST-02）。

新しい OCR プロバイダを追加する際、機密キー関連の変更箇所を
この1ファイルに閉じ込めるための唯一の情報源（Single Source of Truth）。
stdlib のみ依存（Tk/fitz 非依存）。
"""

# プロバイダ短縮名 → 環境変数名タプル（優先順）。
# gemini の GEMINI_API_KEY 優先 → GOOGLE_API_KEY フォールバックは
# WR-03/D-06 で確定済みの挙動であり、タプル順序がそのまま優先順を表す。
PROVIDER_ENV_KEYS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "runpod": ("RUNPOD_API_KEY",),
}


def primary_env_var(provider_name):
    """プロバイダの主要（最優先）環境変数名を返す。"""
    return PROVIDER_ENV_KEYS[provider_name][0]


def env_vars_for(provider_name):
    """プロバイダの環境変数名タプル（優先順）を返す。"""
    return PROVIDER_ENV_KEYS[provider_name]


def resolve_env_key(provider_name):
    """os.environ から最初に見つかった値を優先順で解決する（読み取り専用）。"""
    import os

    for var in PROVIDER_ENV_KEYS.get(provider_name, ()):
        val = os.environ.get(var)
        if val:
            return val
    return None


def sensitive_keys():
    """_SENSITIVE_KEYS 集合を生成する（現行10エントリと同等以上を保証）。

    現行 _SENSITIVE_KEYS には2つの異なる命名規則が混在しているため、
    両方を派生させて漏れをなくす（Common Pitfalls #6 参照）:
      1. セッションキー形式:  "{provider_name}_api_key" （例: claude_api_key）
      2. 環境変数の大文字/小文字バリアント: 各 PROVIDER_ENV_KEYS の値そのもの
         と、その小文字化（例: ANTHROPIC_API_KEY / anthropic_api_key）
    加えて、プロバイダに紐付かない汎用キー "api_key" は
    レジストリから導出不可能なため明示的に残す（将来のプラグインプロバイダ用）。
    """
    keys = {"api_key"}  # 汎用キー（プロバイダ非依存・手動維持）
    for provider_name, env_vars in PROVIDER_ENV_KEYS.items():
        keys.add(f"{provider_name}_api_key")  # セッションキー形式
        for var in env_vars:
            keys.add(var)  # 大文字（環境変数名そのもの）
            keys.add(var.lower())  # 小文字バリアント
    return keys
```

**検証（現行10エントリとの照合・Claude's Discretion 実装後に必ず確認すること）:**
`sensitive_keys()` の出力は最低でも次の10個を含む必要がある: `claude_api_key, gemini_api_key, google_api_key, anthropic_api_key, api_key, GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, runpod_api_key, RUNPOD_API_KEY`。上記の想定実装で生成される集合は `{api_key, claude_api_key, ANTHROPIC_API_KEY, anthropic_api_key, gemini_api_key, GEMINI_API_KEY, gemini_api_key(重複), GOOGLE_API_KEY, google_api_key, runpod_api_key, RUNPOD_API_KEY, runpod_api_key(重複)}` となり、現行10エントリを完全に包含する（`gemini_api_key` と `runpod_api_key` はセッションキー形式と env var 小文字化が偶然一致するため重複するが `set` により1エントリに収束する）。

### Anti-Patterns to Avoid
- **`__init__.py` での部分的 re-export:** 「主要クラスだけ re-export すればいい」という判断は禁物。`test_ocr_providers.py` は private ヘルパー関数も直接 import しているため、全シンボルの列挙が必須（Pattern 1 参照）。
- **機械的移動中の「ついでのリファクタ」:** D-02/D-06 で明示的に禁止されている。OpenAI 互換3プロバイダの重複統合・投機的な拡張ポイント追加は本フェーズのスコープ外。1PR=1関心事を徹底する。
- **`_SENSITIVE_KEYS` をレジストリの単純な `.values()` フラット化のみで生成:** Common Pitfalls #6 の通り、環境変数名だけでは現行10エントリを再現できない（セッションキー形式の `claude_api_key` 等が漏れる）。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| モジュール分割時の後方互換 import 維持 | 独自の import フック・`__getattr__` による動的 re-export | `__init__.py` での明示 `from ... import ...  # noqa: F401` | 既存 DEBT-01/DEBT-02 前例と一貫。動的 import フックは IDE 補完・静的解析（ruff の F401 検出等）を壊す |
| プロバイダ→環境変数の対応表 | YAML/JSON 設定ファイルからの動的ロード | Python dict リテラル（`PROVIDER_ENV_KEYS`） | プロバイダ数が7程度で今後も急増しない。設定ファイル化はオーバーエンジニアリング（YAGNI・D-06 と同じ精神） |
| Mixin 間の状態共有 | 依存性注入コンテナ・サービスロケータ | 素の `self.xxx` 属性共有（既存 8 Mixin パターンと同型） | プロジェクト全体で確立済みのパターンからの逸脱は保守性を下げる |

**Key insight:** 本フェーズは「新しい仕組みを作る」フェーズではなく「既存の確立済みパターンを機械的に複製する」フェーズである。DEBT-01/DEBT-02 という2つの完成済み前例が存在する以上、独自解を検討する余地はほぼない。

## Common Pitfalls

### Pitfall 1: `__init__.py` の re-export リストから private ヘルパーが漏れる

**What goes wrong:** `OCRProvider`・`ClaudeProvider` などの主要クラスだけ re-export し、`_require_http_scheme`・`parse_retry_after`・`looks_like_context_error`・`_raise_mapped_http_error` のような private 関数を「内部実装だから」と re-export リストから外してしまう。

**Why it happens:** アンダースコアプレフィックスは「非公開」を連想させるため、re-export の対象外だと誤解しやすい。

**How to avoid:** 分割前に旧 `ocr_providers.py` の全モジュールレベル定義（`class`/`def`/大文字定数）を機械的に列挙し（本 RESEARCH の Pattern 1 に完全リストあり・全17シンボル）、そのすべてを `__init__.py` に反映する。加えて `tests/test_ocr_providers.py` を grep して実際に import されている private シンボルと突き合わせる。

**Warning signs:** `test_ocr_providers.py` の特定テストクラスのみ `ImportError` で失敗する。

### Pitfall 2: `tesseract.py` の `_detect_tesseract` が `llm_config.py` から見えなくなる

**What goes wrong:** `_detect_tesseract` を `tesseract.py`（TesseractProvider と同居）に配置した後、`__init__.py` での re-export を忘れると、`llm_config.py`（分割対象外・D-10 により import 文は変更しない）の `from pagefolio.ocr_providers import (..., _detect_tesseract)` が壊れ、LLMConfigDialog のコンストラクタが `ImportError` で即死する。

**Why it happens:** `_detect_tesseract` は `TesseractProvider` と同じファイルに移動されるため「一緒に見えるはず」という思い込みが生じやすいが、re-export は明示的に書かなければ機能しない。

**How to avoid:** Pattern 1 の完全シンボルリストに `_detect_tesseract` が含まれていることを実装時に再確認する。`ocr.py` の `build_provider`（`elif name == "tesseract":` ブランチ）も同じ関数を import しているため、両方の呼び出し元で動作確認する。

**Warning signs:** アプリ起動時に「⚙ LLM 設定」ダイアログを開こうとするとクラッシュする（テストでは `test_provider_ui.py`/`test_imports.py` で検出可能）。

### Pitfall 3: `LLMConfigDialog` の Mixin 分割で `tk.Toplevel.__init__` の MRO が崩れる

**What goes wrong:** `DialogMixin`/`SectionsMixin`/`ModelFetchMixin` の継承順序や `tk.Toplevel` の継承位置を誤ると、`super().__init__(parent)` の解決順が変わり、`tk.Toplevel` の初期化が二重実行されたり全く実行されなかったりする。

**Why it happens:** Python の多重継承 MRO は直感に反しやすく、`tk.Toplevel` のような C 拡張バインディングのクラスは Mixin パターンとの相性を事前検証しないと壊れやすい。

**How to avoid:** `tk.Toplevel` を継承リストの最後に置く（`class LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel):`）。`__init__` の実装は既存コード同様どこか1箇所（推奨: `DialogMixin`）に集約し、他の Mixin は `__init__` を持たない設計にする。分割直後に手動でダイアログを一度開いて確認する（ヘッドレス CI では検出できない領域）。

**Warning signs:** ダイアログのタイトルバー・`grab_set()`・`resizable()` 等 `tk.Toplevel` 由来の属性が効かない。

### Pitfall 4: `pagefolio` トップレベルに `ocr_providers`/`LLMConfigDialog` を誤って新規公開してしまう

**What goes wrong:** 分割作業中に「ついでに使いやすくしよう」と `pagefolio/__init__.py` へ `ClaudeProvider` や `LLMConfigDialog` を追加 export してしまう。

**Why it happens:** `pagefolio/__init__.py` は他の多くのシンボル（`AboutDialog`・`SettingsDialog` 等）を re-export しているため、一貫性を求めて追加したくなる。

**How to avoid:** 現状の `pagefolio/__init__.py` は `ocr_providers.*` クラスも `LLMConfigDialog` も一切 export していない（既存 `tests/test_imports.py` のコメントに「LLMConfigDialog は pagefolio.dialogs 経由でアクセス可能だが、pagefolio トップレベルには非公開」と明記済み）。この現状を変更しないこと。D-10「内部 import は旧パスのまま維持」は「公開面を広げない」の裏返しでもある。

**Warning signs:** `test_imports.py` の `TestPackageSurface` クラスに新規アサーションを追加しようとして初めて気づく（追加してはいけない）。

### Pitfall 5: `_SENSITIVE_KEYS` レジストリ生成が既存10エントリの一部を欠落させる

**What goes wrong:** レジストリ実装時に「環境変数名とその小文字化」だけを機械的に生成し、「プロバイダ短縮名+`_api_key`」というセッションキー形式（`claude_api_key` は env var `ANTHROPIC_API_KEY` の小文字化とは**一致しない**）の生成を忘れる。

**Why it happens:** 現行 `_SENSITIVE_KEYS` は2つの異なる命名規則が偶然重なったり離れたりしている（`runpod_api_key` は両規則で一致するが `claude_api_key`≠`anthropic_api_key` は一致しない）ため、片方の規則だけ実装しても気づきにくい。

**How to avoid:** Pattern 3 の `sensitive_keys()` 実装例のように、(1) プロバイダ短縮名ベースのセッションキー形式、(2) 環境変数名の大文字/小文字両方、(3) プロバイダ非依存の汎用 `api_key`、の3系統をすべて生成する。実装後に `set(registry.sensitive_keys()) >= {既存10エントリ}` をテストで機械的に検証する（`test_settings_keyguard.py` の `TestSensitiveKeysConstant` に追加）。

**Warning signs:** `test_settings_keyguard.py` の既存テスト（`test_sensitive_keys_contains_claude` 等）が失敗する。

### Pitfall 6: レジストリ導入で `settings.py`↔`ocr_providers` 間に循環 import が生じる

**What goes wrong:** `registry.py` を `ocr_providers/` パッケージ内に置いた結果、`settings.py` が `from pagefolio.ocr_providers import registry` のような import を追加すると、`ocr_providers/__init__.py`（各プロバイダモジュールを import）→ プロバイダ側が将来 `settings.py` の関数を使うようになった場合に循環が生じるリスクがある。

**Why it happens:** `registry.py` はプロバイダ実装と同じパッケージに同居するため、settings.py からの参照が「パッケージ全体の import」を誘発しやすい。

**How to avoid:** D-07 の通り `registry.py` は stdlib のみ依存に保つ。`settings.py` からは `from pagefolio.ocr_providers.registry import sensitive_keys`（サブモジュール直接指定）でインポートし、`pagefolio.ocr_providers`（`__init__.py` 経由・全プロバイダを import する重い経路）を経由しないようにする。現状 `settings.py` は `ocr_providers` を一切 import していない（確認済み）ため、新規追加時にこの経路選択に注意する。

**Warning signs:** `import pagefolio.settings` が異常に遅くなる、または `ImportError: cannot import name ... (most likely due to a circular import)`。

## Code Examples

### `pagefolio/dialogs/__init__.py`（既存・DEBT-01 前例そのもの）
```python
# Source: pagefolio/dialogs/__init__.py（プロジェクト内実ファイル）
from pagefolio.dialogs.about import AboutDialog  # noqa: F401
from pagefolio.dialogs.export_images import ExportImagesDialog  # noqa: F401
from pagefolio.dialogs.llm_config import LLMConfigDialog  # noqa: F401
from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog  # noqa: F401
from pagefolio.dialogs.password import SetPasswordDialog  # noqa: F401
from pagefolio.dialogs.plugin import PluginDialog  # noqa: F401
from pagefolio.dialogs.settings import SettingsDialog  # noqa: F401
from pagefolio.dialogs.shortcuts import ShortcutsDialog  # noqa: F401
```
分割後もこのファイル自体は無変更（`from pagefolio.dialogs.llm_config import LLMConfigDialog` の行は、`llm_config.py` がパッケージ `llm_config/` に変わっても `llm_config/__init__.py` が `LLMConfigDialog` を re-export していれば無修正で動作する）。

### `pagefolio/constants.py`（既存・DEBT-02 前例そのもの）
```python
# Source: pagefolio/constants.py（プロジェクト内実ファイル）
from pagefolio.lang import LANG  # noqa: F401
from pagefolio.themes import THEMES, C  # noqa: F401
```

### 既存 `_SENSITIVE_KEYS`（レジストリ化前・置換対象）
```python
# Source: pagefolio/settings.py:23-34（プロジェクト内実ファイル・現状）
_SENSITIVE_KEYS = {
    "claude_api_key",
    "gemini_api_key",
    "google_api_key",
    "anthropic_api_key",
    "api_key",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "runpod_api_key",
    "RUNPOD_API_KEY",
}
```

### レジストリ統合が必要な4箇所（D-09・実コード確認済み行番号）
```python
# (1) pagefolio/settings.py:23-34 — _SENSITIVE_KEYS 定義そのもの
#     → registry.sensitive_keys() から生成する形へ置換

# (2) pagefolio/ocr.py:208-267 — _resolve_api_key()
#     現状: if provider_name == "claude": env_var = "ANTHROPIC_API_KEY"; ... のハードコード分岐
#     → registry.env_vars_for(provider_name) を使った優先順ループへ置換
#     （Gemini の dual env var 処理・runpod の単一 env var 処理を統一的に扱えるようになる）

# (3) pagefolio/ocr_dialog.py:1267-1271 — _check_cloud_api_key() 内のエラーメッセージ用 dict
#     現状: env_var = {"claude": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY",
#            "runpod": "RUNPOD_API_KEY"}.get(name, "")
#     → registry.primary_env_var(name) へ置換

# (4) pagefolio/dialogs/llm_config.py:512, 612, 714 — 「既に環境変数が設定済み」注記の判定
#     現状: os.environ.get("RUNPOD_API_KEY") / os.environ.get("ANTHROPIC_API_KEY") /
#            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
#     → registry.env_vars_for(provider) をループして os.environ.get() する形へ統一
#     （Gemini の dual env var 表示ロジックも自然に一般化される）
```

## Runtime State Inventory

> 本フェーズは rename/refactor 分類に該当するため、以下を明示的に確認した。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | なし — 本フェーズはコード構造のみの変更であり、ユーザーデータ（`pagefolio_settings.json` の値そのもの）のスキーマは変更しない。`_SENSITIVE_KEYS` はガードの実装詳細であり保存データのキー名自体は変えない | なし |
| Live service config | なし — 外部サービス（LM Studio/Ollama/RunPod/Claude API/Gemini API）へのリクエスト形式・エンドポイントは一切変更しない（D-02 により機械的移動のみ） | なし |
| OS-registered state | なし — Windows Task Scheduler・pm2・systemd 等の登録は本プロジェクトに存在しない | なし |
| Secrets/env vars | 環境変数名（`ANTHROPIC_API_KEY`/`GEMINI_API_KEY`/`GOOGLE_API_KEY`/`RUNPOD_API_KEY`）自体は不変。レジストリ化は「参照方法の一元化」であり、ユーザーが設定済みの環境変数を読み替える必要はない | コード側の参照箇所変更のみ（利用者側アクション不要） |
| Build artifacts | `pagefolio.spec`（gitignore 対象・PyInstaller ビルド定義）は本フェーズの分割対象パッケージを個別列挙していないため影響なし（`hiddenimports` 等でモジュール個別指定していないことを実装時に一応確認） | 実装時に `pagefolio.spec`（存在すれば）を grep して `ocr_providers`/`llm_config` の個別参照がないか確認 |

**Nothing found in category:** Stored data / Live service config / OS-registered state — いずれも「なし」であることを実コード確認済み。

## Environment Availability

> 本フェーズはコード構造変更のみで外部サービス・新規ツールへの依存を追加しない。ビルド・テスト実行に必要な既存ツール（Python 3.8+/pytest/ruff/PyInstaller）はプロジェクトに既に導入済みであり、新規追加はない。このセクションは省略する（既存依存の可用性は本フェーズの対象外）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（`pyproject.toml` の `[tool.pytest.ini_options]`） |
| Config file | `pyproject.toml`（`testpaths = ["tests"]`） |
| Quick run command | `pytest tests/test_imports.py tests/test_settings_keyguard.py -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V180-REFAC-01 | `pagefolio.ocr_providers` の全シンボル（クラス+private ヘルパー）が分割後も import 可能 | unit（import 回帰） | `pytest tests/test_imports.py -k OcrProviders -x` | ❌ Wave 0（`TestOcrProvidersImports` 相当のクラスを `test_imports.py` へ先行追加する必要あり — D-11 必達要件） |
| V180-REFAC-01 | 既存 `test_ocr_providers.py`（1500+行）が分割後も無修正で全通過 | unit（既存回帰） | `pytest tests/test_ocr_providers.py -q` | ✅（既存ファイル・D-03 により無修正） |
| V180-REFAC-02 | `pagefolio.dialogs.llm_config.LLMConfigDialog` が両経路（`pagefolio.dialogs` 経由/`pagefolio.dialogs.llm_config` 直接）で import 可能 | unit（import 回帰） | `pytest tests/test_imports.py -k LlmConfig -x` | ✅ 部分的に既存（`test_individual_module_llm_config`/`test_llm_config_via_dialogs_subpackage` は既に存在。分割後も無修正で通ることを確認する） |
| V180-REFAC-02 | 既存 `test_provider_ui.py`（LLMConfigDialog 連携テスト）が分割後も無修正で全通過 | unit（既存回帰） | `pytest tests/test_provider_ui.py -q` | ✅（既存ファイル） |
| V180-ROBUST-02 | `sensitive_keys()` 生成結果が現行10エントリを完全カバー | unit | `pytest tests/test_settings_keyguard.py -k SensitiveKeysConstant -x` | ❌ Wave 0（レジストリ生成の網羅性テストを `test_settings_keyguard.py` に先行追加する必要あり） |
| V180-ROBUST-02 | 既存 keyguard 3経路テスト（claude/anthropic/gemini/api_key の非保存）が分割後も全通過 | unit（既存回帰） | `pytest tests/test_settings_keyguard.py -q` | ✅（既存ファイル） |
| 全要件 | pytest 全件・ruff 全件がグリーン（成功基準4） | full suite | `pytest -q && ruff check . && ruff format --check .` | ✅ |

### Sampling Rate
- **Per task commit:** `pytest tests/test_imports.py tests/test_ocr_providers.py tests/test_settings_keyguard.py -q`（分割直後の速い確認）
- **Per wave merge:** `pytest -q`（全879+件規模の既存スイート全体）
- **Phase gate:** `pytest` 全件グリーン + `ruff check . && ruff format .` クリーンが `/gsd-verify-work` 前提条件

### Wave 0 Gaps
- [ ] `tests/test_imports.py` へ `ocr_providers` パッケージ向けの後方互換 import テストクラスを追加（全17シンボル・分割**前**に追加し赤 → 分割後に緑にする、という TDD 的手順を推奨。CONTEXT.md D-09/D-11 で必達と明記済み）
- [ ] `tests/test_settings_keyguard.py` へ `sensitive_keys()` 生成結果が現行10エントリを部分集合として含むことを検証するテストを追加
- [ ] Framework install: 不要（pytest は既に導入済み）

## Security Domain

> `security_enforcement` の明示的な無効化設定は `.planning/config.json` に見当たらないため、有効（既定）として扱う。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | デスクトップアプリ単体・ユーザー認証機構なし |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし |
| V5 Input Validation | no（本フェーズは既存バリデーションロジックの移動のみ・新規入力経路を追加しない） | 既存の `_apply()` 内クランプ処理を機械的移動するのみ |
| V6 Cryptography | no | 本フェーズは暗号化処理を扱わない（AES-256 パスワード機能は対象外モジュール） |
| V14 Configuration（機密情報管理・本フェーズの実質対象） | yes | `_SENSITIVE_KEYS` ガード機構自体の**保護対象は不変**、実装をレジストリベースへ変更するのみ。既存 `test_settings_keyguard.py` の3経路テスト（JSON 非出力・ログ非出力・入力 dict 非破壊）が回帰検知の主体 |

### Known Threat Patterns for {既存デスクトップアプリの機密情報管理}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| リファクタリングによる `_SENSITIVE_KEYS` 網羅性の劣化（キー漏れで API キーが平文で `pagefolio_settings.json` へ書き込まれる） | Information Disclosure | Pitfall 5 の通り、`sensitive_keys()` の出力が現行10エントリを完全に包含することをテストで機械的に保証する。既存 `test_settings_keyguard.py::test_api_key_value_not_logged` も維持（キー値のログ非出力） |
| モジュール分割の re-export 漏れによる意図しないシンボル露出（private ヘルパーが誤って `pagefolio` トップレベルへ export される） | Information Disclosure（軽微・設計原則違反） | Pitfall 4 の通り `pagefolio/__init__.py` の公開面を本フェーズで拡張しない。既存 `TestPackageSurface` テストの現状維持を確認する |

## Sources

### Primary (HIGH confidence)
- `pagefolio/ocr_providers.py`（プロジェクト内実ファイル・全1537行を精査） — 分割対象の全シンボル一覧の一次情報源
- `pagefolio/dialogs/llm_config.py`（プロジェクト内実ファイル・全1660行を精査） — Mixin 分割対象の責務境界確認
- `pagefolio/settings.py`（プロジェクト内実ファイル） — `_SENSITIVE_KEYS`/`_save_settings` の現行実装
- `pagefolio/ocr.py`（プロジェクト内実ファイル） — `build_provider`/`_resolve_api_key` の env var 解決ロジック（D-09 統合対象2）
- `pagefolio/ocr_dialog.py`（プロジェクト内実ファイル） — `_check_cloud_api_key`/`_confirm_cost` の env var 参照箇所（D-09 統合対象3）
- `pagefolio/dialogs/__init__.py`・`pagefolio/constants.py`（プロジェクト内実ファイル） — DEBT-01/DEBT-02 の完成済み re-export パターン
- `pagefolio/app.py`（プロジェクト内実ファイル） — PDFEditorApp 8 Mixin 構成の実物パターン
- `pagefolio/plugins.py`（プロジェクト内実ファイル） — `register_ocr_provider`/`list_ocr_providers`（プラグイン動的登録との整合確認・D-08 不採用理由の裏付け）
- `tests/test_imports.py`・`tests/test_settings_keyguard.py`・`tests/test_ocr_providers.py`（プロジェクト内実ファイル） — 後方互換テスト網羅性・現行 `_SENSITIVE_KEYS` の10エントリ・private シンボル import 箇所の一次情報源
- `.planning/research/PITFALLS.md`（本プロジェクト curated・落とし穴9/10） — 肥大モジュール分割の re-export 破壊・スレッド調整コード分離時のロック不整合
- `.planning/research/SUMMARY.md`（本プロジェクト curated） — Phase 1 の位置付け・分割順序（ocr_providers→llm_config）の根拠
- `.planning/phases/01-foundation-split/01-CONTEXT.md`（ユーザー決定事項・D-01〜D-11）

### Secondary (MEDIUM confidence)
該当なし（本フェーズは外部ライブラリ調査を要しない内部リファクタリングのため）

### Tertiary (LOW confidence)
該当なし

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 新規依存なし、既存 stdlib 使用の継続を確認済み
- Architecture: HIGH — 分割対象2ファイルを全文精査し、re-export 対象シンボルを完全列挙済み。DEBT-01/DEBT-02 という自プロジェクト内の完成済み前例に基づく
- Pitfalls: HIGH — 実コード grep により re-export 漏れリスク箇所・`_SENSITIVE_KEYS` の命名規則不一致・循環 import リスクを具体的コード行で特定済み

**Research date:** 2026-07-13
**Valid until:** 60日（本フェーズは外部エコシステム変化の影響を受けない内部リファクタリングのため、通常の30日ルールより長め。ただし分割着手が大幅に遅れ対象ファイルに新規機能が追加された場合は再調査が必要）
