---
phase: 01-foundation-split
plan: 02
subsystem: ocr
tags: [refactor, packaging, ocr-providers, registry, sensitive-keys]

# Dependency graph
requires:
  - phase: 01-foundation-split (Plan 01)
    provides: "後方互換 import 安全網（TestOcrProvidersImports・TestPackageSurface 負ガード）"
provides:
  - "pagefolio/ocr_providers/ パッケージ（base.py/errors.py/registry.py/lmstudio.py/claude.py/gemini.py/tesseract.py/ollama.py/runpod.py の10ファイル）"
  - "旧 pagefolio/ocr_providers.py モジュールの削除（パッケージへ完全移行）"
  - "registry.py の PROVIDER_ENV_KEYS 宣言的 dict + env_vars_for/primary_env_var/resolve_env_key/sensitive_keys（V180-ROBUST-02 の基盤）"
  - "tests/test_settings_keyguard.py の sensitive_keys() 網羅性テスト（TestRegistrySensitiveKeysCoverage）"
  - "CLAUDE.md への registry.py 独立性制約の明文化（REVIEWS.md Antigravity LOW #2 反映）"
affects: [01-foundation-split Plan 03 (settings.py/ocr.py/ocr_dialog.py の registry 参照統合), 01-foundation-split Plan 04 (llm_config Mixin 分割・model_fetch.py の env var 統合)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "1プロバイダ=1ファイルの機械的分割（dialogs/ パッケージ化の前例踏襲・D-01）"
    - "純ロジック層レジストリ（registry.py・stdlib のみ依存・pagefolio 内部モジュール非依存の独立性制約を docstring 明文化）"

key-files:
  created:
    - pagefolio/ocr_providers/__init__.py
    - pagefolio/ocr_providers/base.py
    - pagefolio/ocr_providers/errors.py
    - pagefolio/ocr_providers/registry.py
    - pagefolio/ocr_providers/lmstudio.py
    - pagefolio/ocr_providers/claude.py
    - pagefolio/ocr_providers/gemini.py
    - pagefolio/ocr_providers/tesseract.py
    - pagefolio/ocr_providers/ollama.py
    - pagefolio/ocr_providers/runpod.py
  modified:
    - tests/test_settings_keyguard.py
    - CLAUDE.md
  deleted:
    - pagefolio/ocr_providers.py

key-decisions:
  - "TesseractProvider.__init__ の _detect_tesseract() 呼び出しを、tesseract.py 内モジュールローカル名の直接呼び出しから pagefolio.ocr_providers パッケージ再エクスポート経由の遅延 import へ変更（分割前は同一モジュール内の名前空間で monkeypatch が効いていたが、分割後は tesseract.py 単独では既存テストの monkeypatch(ocr_providers, '_detect_tesseract') を拾えないため）"
  - "__init__.py に urllib.request / subprocess を re-export（D-03: test_ocr_providers.py が ocr_providers.urllib.request / ocr_providers.subprocess の属性チェーンで monkeypatch するため、パッケージ側にこれら stdlib モジュールの属性が必要）"
  - "registry.py は sensitive_keys() で (1) セッションキー形式 (2) 環境変数名+小文字バリアント (3) 汎用 api_key の3系統を導出し、現行 _SENSITIVE_KEYS の10エントリと完全一致する集合を生成"

patterns-established:
  - "純ロジック層レジストリの独立性制約をモジュール docstring + CLAUDE.md の両方に明文化し、将来の循環 import を予防する（REVIEWS.md 反映パターン）"

requirements-completed: [V180-REFAC-01, V180-ROBUST-02]

coverage:
  - id: D1
    description: "ocr_providers.py（1537行）を base/errors/registry+6プロバイダの10ファイルパッケージへ機械的分割し、__init__.py で全17シンボル+urllib.request/subprocessを完全re-export"
    requirement: "V180-REFAC-01"
    verification:
      - kind: unit
        ref: "tests/test_imports.py::TestOcrProvidersImports (pytest tests/test_imports.py -k OcrProviders -q)"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py (pytest tests/test_ocr_providers.py -q・D-03凍結・無修正で185件全通過)"
        status: pass
    human_judgment: false
  - id: D2
    description: "registry.py を新設し PROVIDER_ENV_KEYS 宣言的dict + env_vars_for/primary_env_var/resolve_env_key/sensitive_keys を実装。stdlib(os)のみ依存・pagefolio内部モジュール非依存の独立性制約をdocstringに明文化し、AST検証で機械的に保証"
    requirement: "V180-ROBUST-02"
    verification:
      - kind: unit
        ref: "python -c \"import pagefolio.ocr_providers.registry as r; assert callable(r.env_vars_for) and callable(r.primary_env_var) and callable(r.sensitive_keys)\""
        status: pass
      - kind: unit
        ref: "AST検証: registry.py が pagefolio配下のimportを一切持たない"
        status: pass
      - kind: unit
        ref: "tests/test_settings_keyguard.py::TestRegistrySensitiveKeysCoverage (pytest tests/test_settings_keyguard.py -q)"
        status: pass
    human_judgment: false
  - id: D3
    description: "registry.py の独立性制約をCLAUDE.md「既知の制限・注意事項」へ1項目追記（REVIEWS.md Antigravity LOW #2反映・スコープ限定）"
    requirement: "V180-ROBUST-02"
    verification:
      - kind: manual_procedural
        ref: "git diff CLAUDE.md で独立性制約1行追記のみであることを目視確認"
        status: pass
    human_judgment: false

duration: 約19分
completed: 2026-07-13
status: complete
---

# Phase 01 Plan 02: ocr_providers 分割 + registry.py 新設 Summary

**pagefolio/ocr_providers.py（1537行・6プロバイダ）を base/errors/registry+6プロバイダの10ファイルパッケージへ機械的分割し、プロバイダ→環境変数の中央レジストリ registry.py（V180-ROBUST-02）を新設した**

## Performance

- **Duration:** 約19分
- **Started:** 2026-07-13T20:40:44Z（前セッションから継続）
- **Completed:** 2026-07-13T20:59:39Z
- **Tasks:** 2
- **Files modified:** 13（新規10 + 変更2 + 削除1）

## Accomplishments
- `pagefolio/ocr_providers.py`（1537行モノリス）を `base.py`（OCRProvider ABC + `_require_http_scheme`）・`errors.py`（3例外クラス + リトライ/コンテキスト長判定ヘルパー）・`registry.py`（新設）・`lmstudio.py`/`claude.py`/`gemini.py`/`tesseract.py`/`ollama.py`/`runpod.py`（各プロバイダ）の10ファイルへ機械的分割（D-01/D-02: 行の移動のみ、共通化・リネーム・最適化なし）
- `registry.py` を新設し `PROVIDER_ENV_KEYS` 宣言的 dict（claude/gemini/runpod → 環境変数タプル）+ `env_vars_for`/`primary_env_var`/`resolve_env_key`/`sensitive_keys` を実装。stdlib（`os`）のみ依存・pagefolio 内部モジュール非依存の独立性制約をモジュール docstring に明文化し、AST 検証（pagefolio 配下 import 不在）で機械的に保証
- `pagefolio/ocr_providers/__init__.py` で全17シンボル（プロバイダ6クラス・例外3クラス・private ヘルパー8個）を完全 re-export。加えて D-03 互換のため `urllib.request`/`subprocess` も re-export（既存テストの属性チェーン monkeypatch 対応）
- `tests/test_settings_keyguard.py` に `TestRegistrySensitiveKeysCoverage` を追加し、`sensitive_keys()` が現行 `_SENSITIVE_KEYS` の10エントリを部分集合として含むことを機械検証（Pitfall 5）
- `CLAUDE.md`「既知の制限・注意事項」へ registry.py の独立性制約を1項目追記（REVIEWS.md Antigravity LOW #2 反映・スコープ限定）
- `pytest tests/test_imports.py -k "OcrProviders or LlmConfig or PackageSurface"`・`pytest tests/test_ocr_providers.py`（185件・D-03凍結）・`pytest -q`（全903件）・`ruff check . && ruff format --check .` 全緑を確認

## Task Commits

Each task was committed atomically:

1. **Task 1: ocr_providers.py を base/errors/6プロバイダへ機械的分割し、registry.py を新設、__init__.py で完全 re-export** - `723f0c8` (refactor)
2. **Task 2: registry.sensitive_keys() 網羅性テストを追加し、registry.py 独立性制約を CLAUDE.md へ明文化、全体回帰を確認** - `9bfc010` (test)

**Plan metadata:** (このコミット・docs: complete plan)

## Files Created/Modified
- `pagefolio/ocr_providers/__init__.py` - 全17シンボル + urllib.request/subprocess の完全 re-export
- `pagefolio/ocr_providers/base.py` - `OCRProvider` ABC + `_require_http_scheme` + `_ALLOWED_URL_SCHEMES`
- `pagefolio/ocr_providers/errors.py` - `OCRAPIKeyError`/`OCRRetryableError`/`OCRContextLengthError` + リトライ/コンテキスト判定ヘルパー
- `pagefolio/ocr_providers/registry.py` - **新設**。`PROVIDER_ENV_KEYS` + `env_vars_for`/`primary_env_var`/`resolve_env_key`/`sensitive_keys`
- `pagefolio/ocr_providers/lmstudio.py` / `claude.py` / `gemini.py` / `tesseract.py` / `ollama.py` / `runpod.py` - 各プロバイダの機械的移動
- `pagefolio/ocr_providers.py` - **削除**（パッケージへ移行）
- `tests/test_settings_keyguard.py` - `TestRegistrySensitiveKeysCoverage` 追加
- `CLAUDE.md` - registry.py 独立性制約を1項目追記

## Decisions Made
- `TesseractProvider.__init__` の `_detect_tesseract()` 呼び出しを、tesseract.py 内モジュールローカル名の直接呼び出しから `pagefolio.ocr_providers` パッケージ再エクスポート経由の遅延 import（関数内 `from pagefolio.ocr_providers import _detect_tesseract as _redetect`）へ変更。分割前は `TesseractProvider` と `_detect_tesseract` が同一モジュール内にあり `monkeypatch.setattr(ocr_providers, "_detect_tesseract", fake_detect)` が単一名前空間で効いていたが、分割後は tesseract.py 単体の module-global 参照では `ocr_providers`（`__init__.py`）側の属性差し替えを拾えなくなるため、既存テスト（`test_tesseract_redetect_reflects_new_langpacks`）の互換のために必要な措置
- `__init__.py` に `urllib.request`/`subprocess` を re-export。D-03（`test_ocr_providers.py` 無修正で全通過）のため、既存テストが `ocr_providers.urllib.request`/`ocr_providers.subprocess` の属性チェーンで `urlopen`/`run` を monkeypatch している箇所に対応（実体は各プロバイダファイルが import する共有 stdlib モジュールオブジェクトと同一であり、monkeypatch はグローバルに反映される）
- `registry.py` の `sensitive_keys()` は (1) セッションキー形式 `{provider}_api_key` (2) 環境変数名そのもの+小文字バリアント (3) 汎用 `api_key` の3系統を導出。生成結果は現行 `_SENSITIVE_KEYS`（10エントリ）と完全一致（多くも少なくもない）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] TesseractProvider の `_detect_tesseract` monkeypatch 互換性喪失を修正**
- **Found during:** Task 1（分割直後の `pytest tests/test_ocr_providers.py -q` 実行）
- **Issue:** 分割により `TesseractProvider.__init__` 内の `_detect_tesseract()` 呼び出しが tesseract.py 自身のモジュール名前空間で解決されるようになり、既存テスト `test_tesseract_redetect_reflects_new_langpacks` が `monkeypatch.setattr(ocr_providers, "_detect_tesseract", fake_detect)`（`pagefolio.ocr_providers` パッケージの属性を差し替え）で行う再検出モックが効かなくなった
- **Fix:** `TesseractProvider.__init__` 内で `_detect_tesseract` を呼ぶ箇所を、関数内遅延 import `from pagefolio.ocr_providers import _detect_tesseract as _redetect` 経由に変更し、パッケージ側の（monkeypatch 後の）最新の属性値を毎回参照するようにした
- **Files modified:** `pagefolio/ocr_providers/tesseract.py`
- **Verification:** `pytest tests/test_ocr_providers.py -q` で185件全通過（修正前は該当1件が失敗）
- **Committed in:** `723f0c8`（Task 1 コミットに含む）

**2. [Rule 3 - Blocking] `__init__.py` への `urllib.request`/`subprocess` re-export 追加**
- **Found during:** Task 1（分割直後のフルテスト実行）
- **Issue:** 分割によりモノリスの module-level `import urllib.request`/`import subprocess` が `pagefolio.ocr_providers`（`__init__.py`）から消え、既存テストの `ocr_providers.urllib.request`/`ocr_providers.subprocess` 属性チェーンによる monkeypatch が `AttributeError` を起こした（86件失敗）
- **Fix:** `__init__.py` に `import subprocess` / `import urllib.request` を追加し、パッケージが従来どおりこれらの stdlib モジュールを属性として保持するようにした
- **Files modified:** `pagefolio/ocr_providers/__init__.py`
- **Verification:** `pytest tests/test_ocr_providers.py -q` で185件全通過（修正前は該当86件が失敗）
- **Committed in:** `723f0c8`（Task 1 コミットに含む）

---

**Total deviations:** 2 auto-fixed（いずれも Rule 3 - blocking issue: 機械的分割によって既存の凍結テスト（D-03）が壊れた箇所を修正）
**Impact on plan:** 両修正とも D-03（`test_ocr_providers.py` 無修正で全通過）の必達要件を満たすために不可欠。プロバイダの実挙動（HTTP リクエスト内容・エラー変換規約）は一切変更していない。スコープ拡大なし。

## Issues Encountered
None（上記2件は Deviations セクションで対応済み）

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `pagefolio/ocr_providers/` パッケージが確立され、Plan 03（settings.py/ocr.py/ocr_dialog.py の registry 参照統合）・Plan 04（llm_config Mixin 分割）が `registry.env_vars_for`/`primary_env_var`/`sensitive_keys` を参照できる状態になった
- `_SENSITIVE_KEYS` の実配線置換（`settings.py` を `sensitive_keys()` へ差し替え）は Plan 03 の担当として未着手のまま残っている（本プランでは registry.py の新設・網羅性検証のみ）
- ブロッカーなし

---
*Phase: 01-foundation-split*
*Completed: 2026-07-13*

## Self-Check: PASSED

- FOUND: pagefolio/ocr_providers/__init__.py
- FOUND: pagefolio/ocr_providers/base.py
- FOUND: pagefolio/ocr_providers/errors.py
- FOUND: pagefolio/ocr_providers/registry.py
- FOUND: pagefolio/ocr_providers/lmstudio.py
- FOUND: pagefolio/ocr_providers/claude.py
- FOUND: pagefolio/ocr_providers/gemini.py
- FOUND: pagefolio/ocr_providers/tesseract.py
- FOUND: pagefolio/ocr_providers/ollama.py
- FOUND: pagefolio/ocr_providers/runpod.py
- CONFIRMED DELETED: pagefolio/ocr_providers.py
- FOUND commit: 723f0c8
- FOUND commit: 9bfc010
