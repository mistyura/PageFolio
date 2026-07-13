# Phase 1: 基盤分割（肥大モジュールリファクタリング） - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

`ocr_providers.py`（1537行）と `dialogs/llm_config.py`（1659行）を責務別パッケージへ分割し（後方互換 import 維持・`test_imports.py` 先行拡張）、`_SENSITIVE_KEYS` をプロバイダ→環境変数マッピングから生成される中央レジストリへ再編する。挙動変更・新機能追加は一切行わない**純粋リファクタリングフェーズ**。以降のフェーズ（Phase 2 のテンプレート/フォールバック UI・Phase 3 の OCRRunEngine 抽出）の土台となる。

対象要件: V180-REFAC-01（ocr_providers 分割）・V180-REFAC-02（llm_config 分割）・V180-ROBUST-02（_SENSITIVE_KEYS 中央レジストリ化）。

**スコープ外:** `ocr_dialog.py` の分割（Phase 3 の OCRRunEngine 抽出で扱う）・テンプレート/フォールバック機能（Phase 2）・挙動やUIの変更全般。

</domain>

<decisions>
## Implementation Decisions

### ocr_providers パッケージの分割単位
- **D-01:** 分割粒度は**1プロバイダ=1ファイル**。`pagefolio/ocr_providers/` パッケージに `base.py`（`OCRProvider` ABC + 共有ヘルパー）・`errors.py`（`OCRAPIKeyError`/`OCRRetryableError`/`OCRContextLengthError` 等）・`lmstudio.py`・`claude.py`・`gemini.py`・`tesseract.py`（`_detect_tesseract` 含む）・`ollama.py`・`runpod.py` を配置。各ファイル約150〜330行。dialogs/ 分割の「1クラス=1ファイル」前例と一貫。
- **D-02:** OpenAI互換チャット系3プロバイダ（LMStudio/Ollama/RunPod）の重複コード（`_build_payload`/`_post_chat` 等）は**機械的移動に徹し共通化しない**。3者の payload には微妙な差分（RunPod Serverless 形式・Ollama `/api/chat` 等）があり、安易な共通化は回帰リスク。中間基底クラス（OpenAICompatProvider 等）の導入は将来の別タスク。
- **D-03:** `tests/test_ocr_providers.py` は**分割せず現状維持**。既存テストが旧 import パス経由でグリーンのまま通ること自体が後方互換の検証になる。Phase 1 の差分はソース側に限定する。

### llm_config の分割戦略
- **D-04:** 単一クラス `LLMConfigDialog`（約1550行・`_build` だけで約920行）は **Mixin 分割**で再構成する。`pagefolio/dialogs/llm_config/` パッケージ化し、self 参照メソッドをそのまま移す機械的移動に近い形にする（PDFEditorApp の 8 Mixin 構成の確立パターンと一貫）。
- **D-05:** Mixin の分割軸は**責務別3層**: `dialog.py`（本体 `__init__`/`_apply`/`_on_provider_change` 等の共通部・約400行）・`sections.py`（`_build` の UI セクション構築・約700行）・`model_fetch.py`（`_fetch_models_async` + プロバイダ別 probe/refresh 群・約400行）。プロバイダ別分割は不採用（共通セクションとの絡みで切り出し線が複雑になるため）。
- **D-06:** Phase 2（テンプレート/フォールバック UI 追加）向けの**投機的な仕込みはしない**（純粋分割のみ・YAGNI）。セクション登録機構や空セクションは作らない。責務別 Mixin 構造自体が拡張ポイントとして十分。

### _SENSITIVE_KEYS 中央レジストリ
- **D-07:** レジストリは**新 ocr_providers パッケージ内**に `ocr_providers/registry.py` として新設。プロバイダ定義と同居させ「新プロバイダ追加時に触る場所が1箇所」を実現。stdlib のみ依存（Tk/fitz 非依存）に保ち、`settings.py` から import しても循環しない設計とする。
- **D-08:** 宣言方式は**宣言的 dict 一本**（例: `PROVIDER_ENV_KEYS = {"claude": ("ANTHROPIC_API_KEY",), "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "runpod": ("RUNPOD_API_KEY",)}`・タプル順序が解決優先順）。セッションキー名（`claude_api_key` 等の小文字バリアント）もレジストリから導出する。Provider クラス属性からの収集は不採用（settings のガードが全 Provider import に依存し、プラグイン動的登録との整合問題を抱え込むため）。
- **D-09:** 統合範囲は**全参照面**: (1) `settings._SENSITIVE_KEYS` をレジストリから生成、(2) `ocr.py` `build_provider` のキー解決、(3) `ocr_dialog.py` の送信先確認 dict（provider→env var）、(4) `llm_config.py` の環境変数チェック — 4箇所すべてをレジストリ参照へ置換し重複マッピングを排除。Gemini の dual env var 優先順（GEMINI_API_KEY 優先→GOOGLE_API_KEY・D-06/WR-03 由来）は不変で保持。既存の keyguard 回帰テスト（`test_settings_keyguard.py`・3経路テスト）が安全網。生成後の `_SENSITIVE_KEYS` は現行10エントリと同等以上（大小文字バリアント含む）であること。

### 内部 import の移行方針
- **D-10:** 内部コード（`ocr.py`・`ocr_dialog.py`・`app.py` 等の分割対象外ファイル）の import は**旧パスのまま維持**（`from pagefolio.ocr_providers import ClaudeProvider` 等）。パッケージ直下 import を今後も正規の公開面として扱う。分割対象外ファイルに差分を出さず、re-export 面が本番コードで常時検証される。
- **D-11:** `__init__.py` は**完全再エクスポート**: private ヘルパー（`_raise_mapped_http_error`・`_detect_tesseract`・`_require_http_scheme` 等）含む旧モジュールレベル名をすべて公開し、import 表面の完全互換を保証。constants.py 分割前例の `# noqa: F401` パターンを踏襲。`pagefolio.dialogs.llm_config` も同様（`from pagefolio.dialogs import LLMConfigDialog` / `from pagefolio.dialogs.llm_config import LLMConfigDialog` の両方が動作すること）。

### Claude's Discretion
- base.py と errors.py の間のシンボル配置の細目（リトライヘルパー `parse_retry_after`/`looks_like_context_error` をどちらに置くか等）
- registry.py の関数 API 設計（`sensitive_keys()`/`env_vars_for(provider)` 等の名前・シグネチャ）
- `test_imports.py` へ追加する後方互換テストの具体的なケース構成（分割前に先行追加すること自体は必達）
- CLAUDE.md のファイル構成表の更新内容

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・フェーズ定義
- `.planning/REQUIREMENTS.md` — V180-REFAC-01/02・V180-ROBUST-02 の要件文言（本フェーズの対象3要件）
- `.planning/ROADMAP.md` — Phase 1 の Goal・Success Criteria（成功基準4項目）・依存関係

### リサーチ成果物
- `.planning/research/PITFALLS.md` — 落とし穴9「肥大モジュール分割で後方互換 import が壊れる」（test_imports.py 先行拡張の必達手順）・落とし穴10「スレッド調整コード分離時のロック不整合」（本フェーズでは model_fetch.py の非同期取得層に留意）
- `.planning/research/SUMMARY.md` — v1.8.0 全体の推奨アプローチ（分割順序: ocr_providers → llm_config →（Phase 3で）ocr_dialog）

### 前例パターン（コード内）
- `pagefolio/dialogs/__init__.py` — DEBT-01 前例: サブパッケージ化 + `__init__.py` 再エクスポートの実装形
- `pagefolio/constants.py` — DEBT-02 前例: 分割後の再エクスポート（`# noqa: F401`）パターン
- `tests/test_imports.py` — TEST-03 前例: 明示 import + assert の後方互換テスト集約形式（本フェーズで先行拡張する対象）
- `tests/test_settings_keyguard.py` — _SENSITIVE_KEYS の既存回帰テスト（レジストリ生成後もグリーン維持が必達）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pagefolio/dialogs/` パッケージ構造: サブパッケージ + `__init__.py` re-export の完成形。ocr_providers/ と llm_config/ のパッケージ化はこの形をそのまま踏襲できる
- `tests/test_imports.py`: 後方互換 import テストの受け皿が既にある（4クラス34テスト・追加は既存形式に合わせるだけ）
- PDFEditorApp の 8 Mixin 構成: LLMConfigDialog の Mixin 分割の参照実装

### Established Patterns
- 後方互換 re-export（DEBT-01/02 前例）: 旧シンボルを `__init__.py`/旧モジュールで `# noqa: F401` 再エクスポート
- 純ロジック層の分離（pagination.py/ocr_pipeline.py 等）: registry.py も同様に Tk/fitz 非依存で作る
- ruff ルール S/B 有効・裸 except 禁止・`# type: ignore` 禁止

### Integration Points
- `ocr_providers.py` の現構造: 共有基盤（1〜248行: `_require_http_scheme`・エラー3種・`parse_retry_after`・`looks_like_context_error`・`_raise_mapped_http_error`・`OCRProvider` ABC）+ 6プロバイダ（LMStudio 249〜/Claude 425〜/Gemini 753〜/Tesseract 1023〜/Ollama 1169〜/RunPod 1346〜）
- `llm_config.py` の現構造: `_build`（177〜1096行）が全プロバイダセクション構築、`_fetch_models_async` + `_probe_*`/`_refresh_*` 群（1301〜1553行）が非同期モデル取得、`_apply`（1554行〜）が適用
- プロバイダ→環境変数マッピングの現重複箇所（D-09 の統合対象）: `settings.py:23`（_SENSITIVE_KEYS）・`ocr.py:230-257`（build_provider キー解決）・`ocr_dialog.py:1268-1270`（送信先確認 dict）・`llm_config.py:512,612` 等（環境変数チェック）
- 呼び出し側（import 元）: `ocr.py`・`ocr_dialog.py`・`app.py`・`plugins.py`（register_ocr_provider）・テスト群 — D-10 によりこれらは無変更

</code_context>

<specifics>
## Specific Ideas

- 分割は「機械的移動」を徹底し、行の移動以外のコード変更（リネーム・共通化・最適化）を混ぜない。挙動同一性の検証可能性を最優先する
- 作業順序はリサーチ推奨どおり ocr_providers → llm_config の順（`test_imports.py` 先行拡張 → 分割 → 全テストグリーン確認のサイクルを各分割で回す）
- 分割後の各ファイルが ruff（line-length 88・I ルール）を素通りすること

</specifics>

<deferred>
## Deferred Ideas

- **OpenAI互換プロバイダの中間基底クラス（OpenAICompatProvider）導入** — LMStudio/Ollama/RunPod の重複吸収。将来の別タスク（D-02 で明示的に不採用としたリファクタ拡張）
- **tests/test_ocr_providers.py のプロバイダ別分割** — 将来テストが肥大化した際に検討（D-03 で今回は不採用）

</deferred>

---

*Phase: 1-基盤分割（肥大モジュールリファクタリング）*
*Context gathered: 2026-07-13*
