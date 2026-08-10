# Architecture Research — v1.9.0（安全性・整合性の是正 + OpenAI プロバイダ追加）

**Domain:** 既存 Python/Tkinter デスクトップアプリ（PageFolio）への機能追加・リファクタリング
**Researched:** 2026-08-10
**Confidence:** HIGH（すべて実コード読解に基づく。外部ドキュメントへの依存なし）

> 本ファイルは v1.8.0 期（2026-07-13）の旧 ARCHITECTURE.md（バッチOCR/プロバイダフォールバック/サムネイル仮想化/肥大モジュール分割の統合設計）を置き換える。旧内容は `.planning/milestones/v1.8.0-*` にて実装済み・アーカイブ済みのため、v1.9.0 マイルストーンの設計に更新した。

本ドキュメントは新規スタック選定のための調査ではなく、**既存コードベースの実構造を読解した上での改修設計**である。対象は `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md` が指摘した V190-REV-01〜08 のうち、特にアーキテクチャ判断を要する「プロバイダメタデータ一元化（REV-08）」「OpenAI プロバイダ追加」「ロールバック機構（REV-01/03/04/07）」を扱う。

---

## 1. 現状把握：プロバイダメタデータの重複マップ

実ファイルを読解し、同一情報（プロバイダ名の集合・表示名・クラウド判定・既定モデル・送信先ホスト・フォールバック候補）がどこに何回登場するかを列挙する。

### 1.1 「クラウド判定」の重複（`{"claude", "gemini", "runpod"}` 相当の集合が5箇所）

| ファイル:行 | 形態 | 内容 |
|---|---|---|
| `pagefolio/ocr.py:566-570` | `_cloud_providers = {"claude", "gemini", "runpod"}` | `_start_ocr` 内でセッション API キー事前解決の要否判定 |
| `pagefolio/ocr_dialog.py:602-603` | `_cloud_providers = {"claude", "gemini", "runpod"}` | `_check_cloud_api_key` 相当の箇所でAPIキー確認の要否判定 |
| `pagefolio/ocr_dialog.py:905-926`（`_is_cloud_provider`） | `if name in ("claude", "gemini", "runpod")` + `isinstance(..., (ClaudeProvider, GeminiProvider, RunPodProvider))` の二重判定 | コスト確認・API キー確認の要否判定 |
| `pagefolio/dialogs/batch_ocr.py:496`（`_is_cloud_provider`） | `if name in ("claude", "gemini", "runpod")` | `ocr_dialog.py` と同名だが独立実装（後述 1.7 節） |
| `pagefolio/dialogs/batch_ocr.py:63` | `{"claude", "gemini", "runpod", "lmstudio", "ollama"}` | 別の集合（ネットワーク送信ありの全プロバイダ、非クラウド含む） |

**同一集合が最低 5 箇所に手書きされている。**

### 1.2 「表示名（プロバイダ名→LANG キー名）」の重複（2箇所・実装方式も異なる）

| ファイル:行 | 内容 |
|---|---|
| `pagefolio/ocr_dialog.py:829-838`（`_provider_display_name`） | `name == "claude"` → `self._L["ocr_provider_name_claude"]` … の if 連鎖 |
| `pagefolio/ocr_dialog.py:2320-2325`（`_provider_key_to_display_name` 内 `_key_map` dict） | `{"claude": "ocr_provider_name_claude", "gemini": ..., "tesseract": ..., "runpod": ..., "lmstudio": ..., "": ...}` — **同一ファイル内で同じ対応関係を dict として再定義** |

`pagefolio/dialogs/batch_ocr.py` にもコスト確認メッセージ等で同型の分岐が散在するが、これは 1.7 節で述べる意図的なコピペ移植であり別カウントとする。

### 1.3 「既定モデル」の重複（ハードコード文字列が最低 5 箇所ずつ）

`"claude-sonnet-4-6"` という既定値文字列: `pagefolio/ocr.py:452`、`pagefolio/dialogs/llm_config/sections.py:429`、`pagefolio/dialogs/llm_config/dialog.py:409`、`pagefolio/ocr_dialog.py:1231`、`pagefolio/dialogs/batch_ocr.py:522` の**5箇所**に個別のフォールバック値としてベタ書き。
`"gemini-2.5-flash"` も同様に `ocr.py:469`、`sections.py:530`、`dialog.py:417`、`ocr_dialog.py:1224`、`batch_ocr.py:516` の**5箇所**。

これらは `ClaudeProvider.RECOMMENDED_MODELS[1]`（`pagefolio/ocr_providers/claude.py:32`）・`GeminiProvider.RECOMMENDED_MODELS[3]`（`pagefolio/ocr_providers/gemini.py:36-42`）と**一致を人力で保っている**だけであり、モデルの世代交代（v1.8.1 の gemini-3 系対応のように）が起きるたびに 5 箇所を揃えて直す必要がある。

### 1.4 「送信先ホスト」の重複（4箇所）

| ファイル:行 | 内容 |
|---|---|
| `pagefolio/ocr_dialog.py:1223-1232`（`_confirm_cost`） | `gemini→"generativelanguage.googleapis.com"` / `runpod→settings["runpod_url"]` / `else(claude)→"api.anthropic.com"` |
| `pagefolio/ocr_dialog.py:1258-1266`（`_confirm_summary_cost`） | 同一分岐をほぼそのままコピー |
| `pagefolio/ocr_dialog.py:2330-2350`（フォールバック確認ダイアログ用） | 同一分岐の3個目のコピー（+ tesseract 分岐が追加） |
| `pagefolio/dialogs/batch_ocr.py:515-522` / `963-969` | `ocr_dialog.py` と**意図的にコピペ移植**（1.7 節参照） |

`api.anthropic.com` / `generativelanguage.googleapis.com` という定数文字列は `ClaudeProvider.MESSAGES_ENDPOINT`(`claude.py:30`) / `GeminiProvider.GENERATE_CONTENT_ENDPOINT`(`gemini.py:30-33`) から導出できる値だが、現状は UI 側で手書きの別文字列として保持されている。

### 1.5 「プロバイダ一覧（combobox 用リスト）」の重複（2箇所・ほぼ同一）

`pagefolio/dialogs/llm_config/sections.py:87-95`（`_base_providers`）:
```
["off", "lmstudio", "ollama", "runpod", "claude", "gemini", "tesseract"]
```
`pagefolio/dialogs/llm_config/sections.py:1024-1031`（`_base_fallback_providers`）:
```
["lmstudio", "ollama", "runpod", "claude", "gemini", "tesseract"]
```
差分は先頭の `"off"` の有無のみ。**同一ファイル内 900 行離れた場所に、ほぼ同じ 6〜7 要素のリストが2回**書かれている。

### 1.6 「API キー未設定エラーの文言キー」の重複（2箇所）

`pagefolio/ocr_dialog.py:1298-1301` と `pagefolio/dialogs/batch_ocr.py:548-551` が全く同じ dict:
```python
{"claude": "ocr_api_key_missing", "gemini": "ocr_api_key_missing_gemini", "runpod": "ocr_api_key_missing_runpod"}
```

### 1.7 意図的な重複（変更しない方がよいもの）

`pagefolio/dialogs/batch_ocr.py` の冒頭コメント（4-16行目）は明示的に「`OCRDialog` のコスト確認系メソッド（`_confirm_cost`/`_estimate_cost`/`_is_cloud_provider`/`_check_cloud_api_key`）は**同一シグネチャ・同一挙動の独立実装（コピペ移植）**であり、`OCRDialog` を継承せず・そのインスタンスメソッドを import して流用しない」と宣言している（04-02-PLAN.md Review Incorporation 懸念5 を根拠に）。これは **Tkinter ウィジェット依存のロジック**を共有すると `OCRDialog` と `BatchOCRDialog` が結合してしまう懸念への対策であり、正当な設計判断である。

→ ここが Q1 の核心の示唆になる: **「ロジックの重複」は意図的に許容されている一方、「データ（プロバイダ名・表示名キー・既定モデル・ホスト）の重複」は誰も意図していない副作用**。一元化すべきは後者のみであり、`OCRDialog`/`BatchOCRDialog` の独立性という既存の設計判断を壊してはならない。

---

## 2. 設計：プロバイダメタデータ一元化（V190-REV-08 への回答）

### 2.1 新設モジュール `pagefolio/ocr_providers/catalog.py`

`registry.py` と同じパッケージ内に併設する（`registry.py` が既に「独立性制約付きの隣接モジュール」という前例を作っているため、認知コストが最小）。

**独立性制約（V180-D-01）との関係**: `registry.py` 自体は一切変更しない。`catalog.py` は `registry.py` を import する（`registry.py`→`catalog.py` の逆方向 import は発生しないため循環しない）。`catalog.py` は「非機密メタデータ」のみを扱い、機密（APIキー・環境変数値）は一切保持しない——環境変数**名**の解決は `registry.env_vars_for()` にそのまま委譲し、`catalog.py` では再定義しない。

```python
# pagefolio/ocr_providers/catalog.py（設計イメージ）
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderMeta:
    name: str                     # settings["ocr_provider"] の値と一致（例: "claude"）
    display_name_key: str         # LANG のキー名（例: "ocr_provider_name_claude"）
    is_cloud: bool                # 外部送信あり = コスト確認/送信先確認/APIキー欄が必要
    model_setting_key: str | None # settings 内のモデルキー（例: "claude_model"）。無ければ None
    default_model: str | None     # モデル未設定時の既定値（Provider の RECOMMENDED_MODELS[0] 等と同期）
    host: str | None              # 固定送信先ホスト（claude/gemini/openai）。ユーザー設定URL依存なら None
    fallback_eligible: bool       # フォールバック候補一覧に出すか（off は False）


PROVIDERS: "dict[str, ProviderMeta]" = {
    "off":       ProviderMeta("off", "ocr_provider_name_off", False, None, None, None, False),
    "lmstudio":  ProviderMeta("lmstudio", "ocr_provider_name_lmstudio", False, "lm_studio_model", "", None, True),
    "ollama":    ProviderMeta("ollama", "ocr_provider_name_ollama", False, "ollama_model", "", None, True),
    "runpod":    ProviderMeta("runpod", "ocr_provider_name_runpod", True, "runpod_model", "", None, True),  # host は runpod_url 依存
    "claude":    ProviderMeta("claude", "ocr_provider_name_claude", True, "claude_model", "claude-sonnet-4-6", "api.anthropic.com", True),
    "gemini":    ProviderMeta("gemini", "ocr_provider_name_gemini", True, "gemini_model", "gemini-2.5-flash", "generativelanguage.googleapis.com", True),
    "tesseract": ProviderMeta("tesseract", "ocr_provider_name_tesseract", False, None, None, None, True),
}


def provider_names(include_off: bool = True) -> list:
    """combobox 用の全プロバイダ名（プラグイン分は呼び出し側で追加）。"""
    return [n for n in PROVIDERS if include_off or n != "off"]


def fallback_candidate_names() -> list:
    return [n for n, m in PROVIDERS.items() if m.fallback_eligible]


def is_cloud_provider(name: str) -> bool:
    m = PROVIDERS.get(name)
    return bool(m and m.is_cloud)


def host_for(name: str, settings: dict) -> str:
    """送信先ホストを解決する。URL依存プロバイダ（runpod）は settings から
    読む。固定ホスト（claude/gemini/openai）は catalog の値をそのまま返す。"""
    m = PROVIDERS.get(name)
    if m is None:
        return ""
    if m.host:
        return m.host
    if name == "runpod":
        return settings.get("runpod_url", "")
    return ""


def default_model_for(name: str) -> str:
    m = PROVIDERS.get(name)
    return (m.default_model or "") if m else ""
```

`env_vars_for` はそのまま `registry.py` から re-export せず、呼び出し側が必要なら `from pagefolio.ocr_providers.registry import env_vars_for` を直接使う（既存の `sections.py:14` の慣習を踏襲）。`catalog.py` は「表示・分類」の責務のみを持ち、「機密キー解決」の責務は `registry.py` に残す——**責務分離を1モジュール内で混在させない**のが独立性制約を将来にわたり守るコツ。

### 2.2 データ構造の選定理由（dataclass vs plain dict vs frozen 定数）

| 案 | 評価 |
|---|---|
| **`@dataclass(frozen=True)` + `dict[str, ProviderMeta]`（採用）** | 属性アクセス（`meta.host`）で誤字が `AttributeError` として早期検出される。`frozen=True` で実行時の書き換え事故を防ぐ（既存コードベースは `frozen=True` を多用していないが、`registry.py` の「読み取り専用の中央データ」という性格に最も合致）。Python 3.8+ 対応（本プロジェクトの最低要件）は `dataclasses` 標準ライブラリで満たせる。 |
| plain dict の入れ子（`PROVIDERS["claude"]["host"]`） | 既存コードの主流スタイル（`settings` 辞書等）に近く親しみやすいが、キー名の typo が実行時まで検出されない。プロバイダ数が 7〜8 と少数であり dataclass の恩恵の方が大きいと判断。 |
| モジュールレベルの複数 dict（`DISPLAY_NAMES = {...}`, `HOSTS = {...}`, `CLOUD_PROVIDERS = {...}` と分割） | 現状の重複パターン（1.1〜1.6節）をそのまま「グローバル定数化」しただけで、プロバイダ追加時に複数の dict へ同期して追記する必要が残り、一元化の効果が薄い。**不採用**。 |

### 2.3 既存 7 参照面への段階的移行（後方互換を保った移行手順）

移行は「`catalog.py` を追加するだけの回（動作変化なし・純粋追加）」→「1ファイルずつ参照元を catalog 経由へ置き換える回（各回で既存テストが動作無変更を保証）」の順で行う。**一括置換はしない**（同時に7ファイルを触ると、どこかで表示順や既定値が1つでもズレたときの原因切り分けが困難になるため）。

| 順序 | 対象ファイル | 変更内容 | リスク |
|---|---|---|---|
| 0 | `pagefolio/ocr_providers/catalog.py`（新規） | `catalog.py` 単体を追加し、`tests/test_ocr_provider_catalog.py`（新規）で `PROVIDERS` の内容そのものを固定内容としてアサート | ゼロ（既存コードから未参照） |
| 1 | `pagefolio/dialogs/llm_config/sections.py` | `_base_providers`(87-95) と `_base_fallback_providers`(1024-1031) を `catalog.provider_names()` / `catalog.fallback_candidate_names()` に置換 | 低（combobox の values 一致を既存 UI テストで検証可能） |
| 2 | `pagefolio/ocr_dialog.py` | `_provider_display_name`(812-838)・`_provider_key_to_display_name`(2303-2325) を `catalog.PROVIDERS[name].display_name_key` 参照に統一。`_is_cloud_provider`(905-926) を `catalog.is_cloud_provider(name)` に置換（isinstance フォールバック分岐は当面残す＝プラグインプロバイダ対応のため） | 中（表示名の LANG キー解決経路が変わるため `tests/test_provider_ui.py` の該当ケースを重点確認） |
| 3 | `pagefolio/ocr_dialog.py`（コスト確認） | `_confirm_cost`/`_confirm_summary_cost`/フォールバック確認ダイアログの host 分岐を `catalog.host_for(name, settings)` に置換 | 低〜中（runpod の URL 依存分岐だけ catalog 側で settings 参照が必要、2.1 のとおり実装済み） |
| 4 | `pagefolio/dialogs/batch_ocr.py` | 2/3 と同型の置換。**ただし `OCRDialog` からの import・継承は行わず**、catalog という「データ」だけを共有する（1.7 節どおりロジックの独立性は維持） | 低（データ源泉の変更のみ、独自実装の構造は不変） |
| 5 | `pagefolio/ocr.py` | `_cloud_providers` 変数(566-570) を `catalog.is_cloud_provider` へ | 低 |
| 6 | `pagefolio/dialogs/llm_config/dialog.py` | セッション API キー同期ループ(520-524)のタプルは個別ウィジェット変数（`self.claude_api_key_var` 等）に紐づくため完全な動的化はスコープ外（v1.9.0 では見送り、コメントで理由を明記）。OpenAI 追加時に1行追記のみで対応 | 低（据え置き判断） |
| 7 | `pagefolio/lang.py` | 変更なし（キー**名**の対応は catalog 側が持つが、キーの**値**＝翻訳文言は引き続き lang.py が真実源） | ゼロ |

各ステップは独立した GSD プランとして計画・検証可能な粒度であり、途中で打ち切っても（例: ステップ3までで止めても）システムは常に動作する状態を保つ。

---

## 3. OpenAI プロバイダの統合ポイント（Q2 への回答）

### 3.1 実装の土台：LM Studio Provider がほぼそのまま流用できる

`pagefolio/ocr_providers/lmstudio.py` の docstring（4行目）が明記する通り、LM Studio は「OpenAI 互換 Vision API」（`/v1/chat/completions`、`image_url` + base64 data URI 形式のコンテンツブロック、`choices[0].message.content` レスポンス、`finish_reason == "length"` で切り詰め検出）を実装している。これは**そのまま OpenAI 本家のリクエスト/レスポンス契約と同一**である。

さらに `pagefolio/ocr_providers/errors.py:49` のコメント「OpenAI 互換: context_length_exceeded」および `_CONTEXT_ERROR_MARKERS`(51-60) は**既に OpenAI のエラーメッセージ形式を見込んで実装済み**であり、`_raise_mapped_http_error` はそのまま流用できる（変更不要）。

→ 結論: `OpenAIProvider` は `ClaudeProvider`/`GeminiProvider` よりも **`LMStudioProvider` の payload/response 処理をほぼコピーし、接続先・認証ヘッダー・モデル一覧取得だけを差し替える**のが最小実装コストになる。

### 3.2 新規ファイル

**`pagefolio/ocr_providers/openai_provider.py`**（`OpenAIProvider` クラス）

既存4ファイル（`claude.py`/`gemini.py`/`lmstudio.py`/`runpod.py`）と同型のパターンで実装する:

- `default_concurrency` / `max_concurrency`: Claude 相当（`2`/`2`）を初期値とし、実測で調整（OpenAI の rate limit は tier 依存のため保守的な既定が安全）
- `supports_text_prompt = True`
- `model_list_timeout = 30`（クラウド系共通）
- `CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"`
- `MODELS_ENDPOINT = "https://api.openai.com/v1/models"`
- `RECOMMENDED_MODELS`: 静的フォールバックリスト（API キー未設定時に返す。`ClaudeProvider.RECOMMENDED_MODELS` と同じ役割・`list_models()` 内で `if not self.api_key: return list(self.RECOMMENDED_MODELS)` パターンを踏襲）。**注意点（Pitfall）**: OpenAI の `/v1/models` レスポンスには Anthropic のような `capabilities.image_input.supported` フィールドが無いため、Claude 方式の「vision 対応モデルだけを自動フィルタ」は再現できない。生の一覧をそのまま返すか、モデル ID の命名規則によるヒューリスティックフィルタが必要——**フェーズ計画時に要判断事項として明記すること**。
- `_build_payload`/`_build_text_payload`: `LMStudioProvider` と同一構造（`image_url` に `data:image/png;base64,...`）
- `_post_chat`: `Authorization: Bearer {api_key}` ヘッダーを追加する以外は `LMStudioProvider._post_chat`/`ClaudeProvider._post_messages` と同型
- `ocr_image`/`ocr_image_ex`/`complete_text_ex`: `LMStudioProvider` と同一のレスポンスパース（`choices[0].message.content`、`finish_reason`）
- `list_models`: `ClaudeProvider.list_models` のページング構造よりも単純（OpenAI の `/v1/models` はページングなしの単純配列）

ファイル名は既存の「プロバイダ名そのまま.py」規則（`claude.py`/`gemini.py`）に合わせるなら `openai.py` が自然だが、**サブパッケージ内モジュールとして絶対 import される**ため実行時に PyPI の `openai` パッケージ（本プロジェクトは新規 pip 依存ゼロ方針のため未導入）と衝突する実害はない。ただし grep・エディタ検索時の紛らわしさを避けるため、本ドキュメントでは `openai_provider.py` を推奨名としつつ、チーム判断で `openai.py` に寄せても技術的問題はないと明記しておく。

### 3.3 修正ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `pagefolio/ocr_providers/registry.py` | `PROVIDER_ENV_KEYS` に `"openai": ("OPENAI_API_KEY",)` を1行追加（独立性制約は保たれる＝標準ライブラリのみ・内部 import なしのまま） |
| `pagefolio/ocr_providers/catalog.py`（2章で新設） | `PROVIDERS["openai"] = ProviderMeta("openai", "ocr_provider_name_openai", True, "openai_model", "<既定モデル>", "api.openai.com", True)` を1行追加 |
| `pagefolio/ocr_providers/__init__.py` | `from pagefolio.ocr_providers.openai_provider import OpenAIProvider  # noqa: F401` を re-export リストへ追加 |
| `pagefolio/ocr.py` | `build_provider()` に `elif name == "openai":` 分岐を追加（`claude`/`gemini` 分岐と同型・`mt <= 0` → 4096 クランプも同様に必要）。`_start_ocr` の `_cloud_providers` は catalog 経由に置換済みなら自動対応、未経由なら手動で `"openai"` を追加 |
| `pagefolio/dialogs/llm_config/sections.py` | `openai_section_frame`（Claude 節 413-513 相当をほぼ複製: モデル combobox・セッション API キー入力欄・トグル・モデル更新ボタン） |
| `pagefolio/dialogs/llm_config/dialog.py` | `_on_provider_change` に `elif provider == "openai":` 分岐（effort 相当の有無は要判断——OpenAI の推論系モデルは `reasoning_effort` パラメータを持つが、Anthropic の `effort` とは意味論が異なるため機械的流用は不可、ロードマップ/フェーズ計画で扱うオープン論点として明記）。`_apply()` の API キー同期ループへ `("openai", self.openai_api_key_var)` を追加 |
| `pagefolio/dialogs/llm_config/model_fetch.py` | `_refresh_openai_models`（`_refresh_claude_models`(206-243) と同型・`OpenAIProvider(api_key=..., model="")` を生成し `_fetch_models_async` へ委譲） |
| `pagefolio/ocr_dialog.py` | `OCR_PRICE_TABLE` に OpenAI モデル単価を追加。`_provider_display_name`/`_provider_key_to_display_name`/`_is_cloud_provider`/`_confirm_cost`/`_confirm_summary_cost`/フォールバック候補 host 表示/API キー欠落マップ（1298-1301）へ `"openai"` 分岐を追加（catalog 移行済みなら多くが自動対応） |
| `pagefolio/dialogs/batch_ocr.py` | 上と同型の追加（`OCR_PRICE_TABLE` コピー・`_cloud_providers` 集合・host 分岐・API キー欠落マップ）。**`OCRDialog` からの継承化はしない**（1.7 節の既存方針を維持） |
| `pagefolio/lang.py` | `ocr_provider_name_openai`・`ocr_api_key_missing_openai`・`settings_openai_model` 等の ja/en ペアを追加（キー数の左右一致ルールを厳守） |
| `tests/test_ocr_providers.py` ほか | `OpenAIProvider` の単体テスト（payload 構築・レスポンスパース・エラーマッピング・モデル一覧）を追加。既存プロバイダのテストパターンをそのまま転用可能 |
| `docs/OCR-PROVIDERS.md` / `docs/CONFIGURATION.md` | OpenAI セクションの追記（`OPENAI_API_KEY` の説明含む） |

### 3.4 一元化を先にやる場合 vs 後にやる場合の統合コスト比較

| | **catalog 先行**（本ドキュメント推奨） | **OpenAI 先行** |
|---|---|---|
| 3.3 表の「クラウド判定・表示名・host・既定モデル」系の変更 | catalog の `PROVIDERS` dict に **1エントリ追加するだけ**。3.3 表の該当セルは「catalog 移行済みなら自動対応」に縮退する | 1.1〜1.6 節で列挙した**5〜8箇所すべてに個別で "openai" 分岐を手で追記**する必要がある（Claude/Gemini/RunPod 追加時と同じ苦労を再現） |
| 後で catalog をやる場合の手戻り | 発生しない | catalog 導入時に、OpenAI 分も含めて 1.1〜1.6 節の**全箇所を再度触る**（1回で済むはずの改修を2回に分けて行うことになり、レビュー・テストの往復コストが倍増） |
| バグ混入リスク | 低（`PROVIDERS["openai"]` 1エントリの追加ミスは `test_ocr_provider_catalog.py` で機械的に検出可能） | 中〜高（8箇所の手書き分岐のうち1箇所でも書き漏らすと「OpenAI だけコスト確認が出ない」「フォールバック候補に出ない」等の潜在バグになりやすい——実際、V190-REV-08 の問題提起自体がこのパターンで発生したもの） |
| v1.9.0 全体の作業量 | catalog 移行（2.3 節・6ステップ）+ OpenAI 追加（3.2/3.3・新規1ファイル+催化された修正） | OpenAI 追加（3.3 の全箇所を素朴に手動追加）のみだが、将来 catalog をやる時に同等以上の作業が発生 |

**結論**: PROJECT.md の Key context にも「registry.py の独立性制約は維持し、非機密メタデータは別モジュールへ分離する」「P0/P1 は OpenAI 追加より前に完了させる」と明記されている通り、**catalog 先行が既定方針と整合し、かつ定量的にも統合コストが低い**。

---

## 4. ロールバック機構の配置（Q3 への回答）

### 4.1 現状の失敗パターンの分類

実コードを読解すると、v1.9.0 対象の 4 件（REV-01/03/04/07）は同じ「取り消し可能性」の問題に見えるが、**実際には性質が異なる 2 系統**に分かれる。

**系統A：Undo 記録タイミングの問題（REV-03/04）** — 操作の**実行前**に `_save_undo` を呼んでいるため、実行が失敗すると「起きていない操作」の Undo エントリだけが残る。

- `pagefolio/page_ops.py:182`（`_duplicate_page`）: `self._save_undo("duplicate", pno=pno)` を `try:` ブロックの**前**で呼んでいる。この "duplicate" op のデータ（`pno` 整数のみ）は挿入前の doc 状態を必要としない＝先に記録する必然性がない。
- `pagefolio/page_ops.py:758`（`_do_insert`）: 同様に `self._save_undo("insert", insert_at=insert_at)` をループの前で呼び、`data = [insert_at, 0]` というプレースホルダを後で `self._undo_stack[-1]["data"][1] = total`（768行目）で確定させる「二段階」パターンをすでに部分的に実装している。しかし例外時（783-790行目）は Undo エントリを pop するだけで、**`self.doc` に実際に挿入されてしまった一部ページを削除していない**うえ、`src`（`_open_path_as_pdf` で開いた挿入元 Document）を `finally` で閉じていない。

**系統B：復元（Undo/Redo 実行）自体の失敗（REV-07）** — `pagefolio/file_ops.py:179-186`（`_undo`）/`188-197`（`_redo`）は `state = self._undo_stack.pop()` の**直後**に `try/except` なしで `_restore_state(state)` を呼ぶ。`_restore_state` 内の多くの op（`delete`/`insert_undo`/`merge_undo` 等）はページ単位のループ処理であり、ループ途中で例外が起きると「一部ページだけ復元された状態」で例外が伝播し、かつ既に `pop()` 済みの `state` はどこにも残らない（履歴消失）。

この2系統を区別する理由: **系統Aは「記録するタイミングをずらす」だけで解決できるものが多く、系統Bは「消費（pop）と適用（restore）の間の原子性」の問題であり対処法が異なる**。

### 4.2 選択肢の比較

| 方式 | 概要 | 本プロジェクトへの適合性 |
|---|---|---|
| **A. 記録後置（record-after）** | `_save_undo` の呼び出しを「実処理が成功した後」に移す | 系統A（duplicate/insert）に最適。理由: これらの op の `state["data"]` は**事前の doc スナップショットを必要としない**（`duplicate` は整数 `pno` のみ、`insert` は `insert_at` と最終ページ数のみ）。事前キャプチャが不要なら、素直に「成功してから記録する」のが最小変更かつ最も分かりやすい。**推奨**。 |
| **B. try/except + 手動ロールバック（record-before + rollback-on-exception）** | 先に `_save_undo` するが、例外時に `pop()` して Blob を `_dispose_state` で解放し、かつ `self.doc` 側も部分適用分を巻き戻す | `crop`/`delete`/`page_edit` のように**事前スナップショットが必須**（`page.cropbox` や `_capture_page_blob` は「変更前」の値でなければ意味がない）な op に必要。現状これらは単一の同期呼び出し（例外を起こしにくい）なのでバグ化していないが、将来ページ範囲操作に拡張する場合の**予防設計**として、`file_ops.py` に汎用ヘルパー `_undo_guard(op, **kwargs)`（context manager）を用意しておくと良い。 |
| **C. 二段階コミット（プレースホルダ push → 確定 or 破棄）** | `_do_insert` が既に部分的に実装しているパターン。プレースホルダを push し、成功時に in-place で確定、失敗時に pop | 複数ファイルをまたぐループ処理（`_do_insert`）のように「事前に insert_at は分かるが総ページ数はループが終わるまで分からない」ケースに限り妥当。ただし **A（記録後置）で置き換え可能**なことに注意——`insert_at` はループ前から確定しているため、`_save_undo` 自体を丸ごとループ後（成功時）に1回呼べば済み、プレースホルダの二段階操作は不要になる。**現状の実装は複雑さの割に得るものが少ない過剰設計**であり、v1.9.0 でシンプルな A 方式へ置き換えることを推奨。 |
| **D. Document 全体の二相コミット（変更前に `doc.tobytes()` でスナップショットし、失敗時に丸ごと復元）** | 操作前に全体シリアライズし、失敗時にまるごと差し替える | **不採用**。これは BUG-02（Undo 実行時のフルシリアライズが大きな PDF で重い）として v1.3.0 で明示的に排除した設計そのものであり、Key Decision「`doc.tobytes()` 全体シリアライズを撤廃し、op ごとに逆操作を保持する」（PROJECT.md）に**正面から反する**。Core Value（「大きな PDF でも Undo/Redo が正しく・速く動作する」）を壊すため選択肢から除外する。 |

### 4.3 系統Aへの適用（REV-03/04）

**`_duplicate_page`（`page_ops.py:177-193`）の修正方針**: `_save_undo("duplicate", pno=pno)` を `try` ブロックの**中**・実処理成功後・`_refresh_all()` の前に移動する。`except` 節では Undo エントリを一切積まない（何も記録しない = 失敗前の状態のまま）。

**`_do_insert`（`page_ops.py:756-790`）の修正方針**:
1. `_save_undo` の呼び出しをループの**後**、`total` が確定してから1回だけ行う（プレースホルダ二段階を廃止）。
2. 各 `src`（`_open_path_as_pdf` の戻り値）を `try/finally` で確実に `close()` する。
3. 例外発生時、それまでに `self.doc` へ挿入済みのページ（`pos - insert_at` 件、`insert_at` を起点に昇順で存在）を、**`_restore_state` の `"insert"` op 分岐（`file_ops.py:391-394`）と全く同じロジック**（`for _ in range(挿入済み件数): self.doc.delete_page(insert_at)`）で取り除き、`self.doc` を操作前の状態へ戻す。この「失敗時ロールバック」と「Undo 実行」が同一の逆操作を再利用できる点は、対称デルタ設計（BUG-02 の Key Decision）の副産物として活用できる。

この2件は Blob ライフサイクル（`_capture_page_blob`/`_dispose_state`/`_push_evicting`）に一切触れない——なぜなら「記録前に失敗した」ケースでは Blob はそもそも作られていないため、解放すべき対象が存在しない。**A方式の最大の利点は Blob ライフサイクルとの相互作用を考えなくてよいこと**である。

### 4.4 系統Bへの適用（REV-07）

`_undo`/`_redo` を次のように変更する（`pop()` と `_restore_state()` の間に安全網を挟む）:

```python
def _undo(self):
    if not self._undo_stack:
        self._set_status(self._t("undo_empty"))
        return
    state = self._undo_stack.pop()
    try:
        inverse = self._restore_state(state)
    except Exception as e:
        # 復元失敗: 履歴を失わないよう state を undo スタックへ戻す。
        # self.doc は部分適用の可能性があるため、ユーザーへ明示的に警告する
        # （BUG-02 の Key Decision により全体スナップショット式のロールバックは
        # 採用しないため、doc 自体の完全な巻き戻しまでは保証しない）。
        self._undo_stack.append(state)
        logger.exception("Undo 復元に失敗しました: %s", e)
        messagebox.showerror(
            self._t("err_title"), self._t("err_undo_restore_failed").format(e=e)
        )
        return
    if inverse.get("data") is not state.get("data"):
        self._dispose_state(state)
    self._push_evicting(self._redo_stack, inverse)
    self._set_status(self._t("undo_done"))
```

`_redo` も対称に同じパターンを適用する。**スコープの明示的な限定**: この修正が保証するのは「復元処理が例外を投げても Undo/Redo 履歴のエントリ自体は消えない」ことであり、「`_restore_state` 内のループが3ページ処理した4ページ目で失敗した場合に doc を完全に元へ戻す」ことまでは保証しない（それを保証するには D 方式＝全体スナップショットが必要で、BUG-02 の設計判断と衝突する）。この限定はレビューノートの推奨対応「部分適用があり得る操作はロールバック可能な単位へ分割する」の**現実的な折衷案**であり、フェーズ計画時に受け入れ条件として明記すべき（「履歴は失われない」を保証、「doc の完全ロールバック」は将来課題として Deferred 扱いにする）。

### 4.5 系統C：保存の暗号化維持（REV-01）— 別レイヤの問題として切り分け

REV-01 は Undo/Blob ライフサイクルとは無関係の**保存パス**の問題であり、`_save_as`(688-709)・`_overwrite_current_file`(626-646)・`_save_compressed`(735-767) が個別に `encryption=` kwargs を組み立てている。`_overwrite_current_file` 自体は既に「メモリへシリアライズ→doc close→tmp書き込み→`os.replace`→再オープン、失敗時は元 bytes から doc を復元して例外再送出」という**アトミックな書き込みパターンを実装済み**（629-646行目のコメントに明記）。これを再利用し、`_save_as` も同一のアトミック書き込みヘルパーを通す形に統一するのが望ましい。

推奨: `_resolve_save_encryption_kwargs(self)` という小さいヘルパーを新設し、「`self.pdf_has_password` が True なら `encryption=fitz.PDF_ENCRYPT_KEEP`、False なら暗号化なし」を1箇所で決定し、`_save_file`/`_save_as`/`_overwrite_current_file`/`_save_compressed` の4呼び出し全てがこのヘルパー経由で kwargs を得るようにする。これも 2 章の catalog と同じ「散在した決定ロジックを1関数へ集約する」パターンであり、Undo のロールバック設計とは独立に進められる。

---

## 5. 推奨ビルド順序（Q4 への回答）

依存関係を軸に、v1.9.0 の 5 項目 + 既存レビュー8件を並べ替える。

```
Phase 1: 保存と編集の安全性（P0/P1・相互に独立、並行可）
  ├─ V190-REV-01: 暗号化維持ヘルパーの一本化（file_ops.py の保存系4メソッド）
  ├─ V190-REV-04: _duplicate_page の記録後置化（4.3節・系統A）
  ├─ V190-REV-03: _do_insert の記録後置化 + finally close + 部分ロールバック（4.3節）
  └─ V190-REV-07: _undo/_redo の復元失敗時スタック復帰（4.4節・系統B）
      ※ REV-04→REV-03→REV-07 の順が自然：
        単純な単一ページ op（duplicate）で「記録後置」パターンを確立してから、
        より複雑な複数ファイルループ（insert）に同じパターンを適用し、
        最後に「記録・適用」全体を包む安全網（undo/redo の例外保護）を被せる。
        REV-01 は保存パスで完全に独立しており、いつ着手してもよい。

Phase 2: 設定UIの整合性（P1・Phase 1と並行可、別ファイル群）
  ├─ V190-REV-05: 外部プロンプトファイル書き込みの Apply 一本化
  └─ V190-REV-06: テンプレート切替確認のファイル連動非依存化
      ※ dialogs/llm_config/{sections,dialog}.py のみに閉じており、
        file_ops.py/page_ops.py 側の変更と衝突しないため並行実施可能。

Phase 3: OCRプロバイダ基盤整理（P2・Phase 1/2 完了後）
  └─ V190-REV-08: catalog.py 新設 + 7参照面の段階的移行（2.3節の7ステップ）
      ※ なぜ Phase 1/2 の後か: PROJECT.md の Key context「P0/P1（V190-REV-01〜05）は
        OpenAI 追加より前に完了させる」という明示方針に加え、Phase 1 で
        file_ops.py/page_ops.py の分岐が変わる（記録後置化）ため、その変更が
        落ち着いてから ocr.py 側のメタデータ整理に着手する方が変更差分の
        レビューが容易（無関係な2種類の大改修が同時に同じPRへ混ざるのを避ける）。

Phase 4: OpenAI プロバイダのフル実装（catalog 完成後）
  └─ OpenAIProvider 新設 + catalog への1エントリ追加 + UI/バッチ/フォールバック統合
      ※ 3.4節の比較のとおり、catalog 完成後に着手することで統合コストが
        最小化される。Phase 3 に直接依存（catalog の PROVIDERS dict と
        provider_names()/fallback_candidate_names() が無いと、3.3表の
        UI/バッチ/フォールバック統合の大部分を再び手書きすることになる）。

Phase 5: 品質保証・持ち越し（Phase 1〜4と独立に並行可、リリースゲート）
  └─ Tkinter実行環境修復・GUI含む全テスト完走・IN-01・human-verify/UAT実機目視
      ※ どのPhaseの成果物にも依存しないインフラ的な作業だが、
        「全テスト完走」がリリースの最終ゲートである以上、最終確認は
        Phase 4 完了後に行うのが実務上自然（新規追加した OpenAI テストも
        含めて完走を確認する必要があるため）。
```

**依存関係の要点**:
- Phase 1 と Phase 2 は完全に独立（触るファイルが重ならない）ため、並行実施が可能。
- Phase 3（catalog）は Phase 1 の変更内容そのものには依存しないが、同一ファイル（`page_ops.py`/`ocr.py`）への変更が交錯しレビューが混乱するのを避けるため、順序として Phase 1 の後に置く（技術的な必須依存ではなく、変更管理上の推奨順序）。
- Phase 4（OpenAI）は Phase 3（catalog）に**技術的に依存**する（3.4節の理由により、catalog 未完成の状態で OpenAI を先に実装すると二度手間になる）。
- PROJECT.md の既存レビューノート（`.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md` §5「v1.9.0への推奨反映順」）が示す順序（1. 保存と編集の安全性 → 2. 設定UI → 3. Undo/Redo回帰強化 → 4. OCRプロバイダ基盤整理 → 5. ChatGPT追加 → 6. その他ブラッシュアップ）と本ドキュメントの Phase 1〜4 は整合している。本ドキュメントはこれに加えて「なぜその順序が依存関係として妥当か」（特に catalog→OpenAI の技術的依存）を実コード根拠付きで補強した。

---

## 6. 内部境界のまとめ（Integration Points）

| 境界 | 通信/依存の形 | 留意点 |
|---|---|---|
| `registry.py` ↔ `catalog.py` | 一方向 import（catalog → registry） | registry.py は catalog.py の存在を知らない。独立性制約（V180-D-01）はこの一方向性で守られる |
| `catalog.py` ↔ `settings.py`/UI モジュール群 | catalog.py は他モジュールから import される専用（catalog.py 自身は registry.py 以外を import しない） | catalog.py を「新しい独立モジュール」として registry.py と同格に扱う（settings.py からの循環 import を再発させないため） |
| `ocr_dialog.py` ↔ `dialogs/batch_ocr.py` | データ（catalog 経由の定数）のみ共有、コード（メソッド）は共有しない | 1.7/3.3節で確認した既存の意図的設計（コピペ移植方針）を尊重する |
| `file_ops.py`（Undo機構） ↔ `page_ops.py`/`redact_ops.py`（各操作） | `_save_undo`/`_capture_page_blob`/`_dispose_state` を各 Mixin から呼ぶ一方向依存 | 4.3節の「記録後置」原則を新規追加される操作（将来の op）にも適用できるよう、`pagefolio/CLAUDE.md` へ設計原則として明文化することを推奨（本 Phase 完了後のドキュメント更新タスク） |
| `ocr.py`（`build_provider`） ↔ `ocr_providers/*.py`（各 Provider 実装） | ファクトリパターン（関数内 import で循環回避、既存踏襲） | OpenAI 追加時も既存の関数内 import パターンを踏襲する（`from pagefolio.ocr_providers import OpenAIProvider` を `build_provider` 内で呼ぶ） |

---

## 7. アンチパターン（避けるべきこと）

### アンチパターン1: Document 全体のスナップショット式ロールバック

**何をやりがちか:** 失敗時に丸ごと `doc.tobytes()` で退避し、失敗時に丸ごと差し替える設計。
**なぜ問題か:** v1.3.0 で明示的に排除した BUG-02 の設計（フルシリアライズ）を再導入することになり、「大きな PDF でも Undo/Redo が正しく・速く動作する」という Core Value に反する。
**代わりにすること:** 4.2節の A/B 方式（記録タイミングの調整・try/except による部分ロールバック）で、op 単位の対称デルタ設計を維持する。

### アンチパターン2: `BatchOCRDialog` から `OCRDialog` のメソッドを import/継承してコード重複を解消しようとする

**何をやりがちか:** 1.6/3.3節で見た通り、コスト確認・API キー確認のロジックが両ファイルにコピペされている。これを「DRY にしよう」と安易に継承・共有関数化すると、両ダイアログの Tkinter ウィジェット依存関係が結合してしまう。
**なぜ問題か:** `batch_ocr.py` の冒頭コメントで明示的に否定されている設計（04-02-PLAN.md Review Incorporation 懸念5）であり、意図を無視した「改善」は past decision を覆すリファクタリング債務を生む。
**代わりにすること:** catalog.py が持つ**データ**（表示名・host・既定モデル・クラウド判定）だけを両者が個別に参照する。**ロジック**（メッセージ組み立て・ダイアログ表示）は引き続き別実装のまま。

### アンチパターン3: `registry.py` へ非機密メタデータを混在させる

**何をやりがちか:** 「どうせ同じパッケージだから」と `registry.py` に `DISPLAY_NAMES` や `RECOMMENDED_MODELS` を追記する。
**なぜ問題か:** V180-D-01 の独立性制約（標準ライブラリのみ・内部モジュール非 import）を将来にわたって守れなくなる（表示名は LANG 辞書と紐付ける必要があり、いずれ `lang.py` への依存を誘発しかねない）。
**代わりにすること:** 本ドキュメント通り `catalog.py` を新設し、`registry.py` は「機密キー名の解決」という単一責務のまま凍結する。

---

## 8. Sources

すべて実コード読解（外部ドキュメント参照なし）。主要根拠ファイル:line は本文中に都度明記した。特に参照が集中したファイル:

- `pagefolio/ocr.py`（`build_provider`・`_start_ocr`・`_cloud_providers`）
- `pagefolio/ocr_providers/registry.py`（`PROVIDER_ENV_KEYS`・独立性制約コメント）
- `pagefolio/ocr_providers/{claude,gemini,lmstudio,__init__}.py`（既存プロバイダ実装パターン）
- `pagefolio/ocr_providers/errors.py`（`_raise_mapped_http_error`・OpenAI 互換マーカー）
- `pagefolio/dialogs/llm_config/{sections,dialog,model_fetch}.py`（プロバイダ一覧・表示・APIキー同期・モデル取得の重複箇所）
- `pagefolio/ocr_dialog.py`（コスト確認・送信先確認・表示名解決の重複箇所）
- `pagefolio/dialogs/batch_ocr.py`（意図的コピペ移植の設計方針コメント）
- `pagefolio/file_ops.py`（`_save_undo`/`_undo`/`_redo`/`_restore_state`/`_apply_inverse`/Blob ライフサイクル・保存系メソッド）
- `pagefolio/page_ops.py`（`_duplicate_page`/`_do_insert`）
- `.planning/PROJECT.md`（Key Decisions・v1.9.0 スコープ）
- `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md`（V190-REV-01〜08 原文）
- `pagefolio/CLAUDE.md`（モジュール構成・OCR/LLM 注意事項）

---
*Architecture research for: PageFolio v1.9.0*
*Researched: 2026-08-10*
