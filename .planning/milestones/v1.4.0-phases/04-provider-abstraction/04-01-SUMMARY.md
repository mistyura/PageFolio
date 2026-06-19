---
phase: 04-provider-abstraction
plan: 01
subsystem: ocr
tags: [ocr, provider, abc, urllib, lmstudio, strategy-pattern]

# Dependency graph
requires: []
provides:
  - "OCRProvider 抽象基底クラス（abc.ABC・ocr_image/list_models 抽象メソッド・default_concurrency/max_concurrency クラス属性・例外規約 docstring）"
  - "OCRAPIKeyError（RuntimeError サブクラス・env_var 属性）"
  - "LMStudioProvider（OCRProvider 実装・ocr_image + list_models・現行と同一の例外マッピング）"
  - "pagefolio/ocr_providers.py（新規モジュール・fitz/Tkinter 非依存）"
affects:
  - "04-02-PLAN.md（run_parallel 一般化・build_provider ファクトリで LMStudioProvider を使用）"
  - "04-03-PLAN.md（settings.py・lang.py 更新で OCRAPIKeyError を使用）"
  - "Phase 05 以降（ClaudeProvider / GeminiProvider の追加先）"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Strategy パターン: OCRProvider を抽象基底とし後続プランが run_parallel の引数として受け取る"
    - "例外規約の基底昇格: ConnectionError / TimeoutError / OCRAPIKeyError / RuntimeError を docstring に明記"
    - "urllib 直叩き + # noqa: S310: 新規 pip 依存ゼロ方針（V14-D-01）を Provider 内にも踏襲"
    - "fitz/Tkinter 完全分離: ocr_providers.py は import fitz / tkinter を一切持たない"

key-files:
  created:
    - "pagefolio/ocr_providers.py — OCRProvider / OCRAPIKeyError / LMStudioProvider を提供する新規モジュール"
    - "tests/test_ocr_providers.py — 23 テストケース（Task 1〜2 の RED/GREEN サイクル）"
  modified: []

key-decisions:
  - "TDD サイクル: RED（失敗テスト先行コミット）→ GREEN（実装コミット）の 2 コミット構成"
  - "list_models() のタイムアウトは 10 秒固定（現行 fetch_lm_studio_models と同一）— self.timeout を使わず内部既定"
  - "docstring の例外規約はクラスレベルと各メソッドレベルの両方に記載（Claude's Discretion 適用）"

patterns-established:
  - "Provider クラスは fitz / tkinter / StringVar / .after() を一切参照しない（スレッド境界明確化の前提）"
  - "クラス属性 default_concurrency / max_concurrency で並列度ポリシーをプロバイダが宣言（D-10）"

requirements-completed:
  - OCR-PROV-01
  - OCR-PROV-02

# Metrics
duration: 3min
completed: 2026-06-06
---

# Phase 4 Plan 01: OCRProvider 抽象基底 + LMStudioProvider Summary

**`abc.ABC` 抽象基底 `OCRProvider` と例外専用クラス `OCRAPIKeyError`、LM Studio urllib 直叩き実装 `LMStudioProvider` を `pagefolio/ocr_providers.py` として新設し、後続プランの Provider インターフェース契約を確定した**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-06T06:10:20Z
- **Completed:** 2026-06-06T06:13:30Z
- **Tasks:** 2 (Task 1: OCRProvider + OCRAPIKeyError、Task 2: LMStudioProvider)
- **Files modified:** 2

## Accomplishments

- `pagefolio/ocr_providers.py` を新設。`OCRProvider`（abc.ABC）・`OCRAPIKeyError`（RuntimeError 子）・`LMStudioProvider` を提供
- `LMStudioProvider.ocr_image` に `call_lm_studio` ロジックを、`list_models` に `fetch_lm_studio_models` ロジックを移設。例外マッピングは現行と完全一致
- `ocr_providers.py` が fitz / Tkinter を一切参照しない（後続フェーズのスレッド境界明確化の前提条件を達成）
- 23 テストケースが全 PASS（222/222 全体テストも緑）

## Task Commits

TDD サイクルに従い 2 コミット構成:

1. **RED — 失敗テスト追加** - `e2b2ecb` (test)
2. **GREEN — ocr_providers.py 実装 + ruff 修正** - `90b2a29` (feat)

## Files Created/Modified

- `C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_providers.py` — OCRProvider / OCRAPIKeyError / LMStudioProvider を提供する新規モジュール（172 行）
- `C:/Users/shdwf/work/project/PageFolio/tests/test_ocr_providers.py` — 23 テストケース（Task 1 基底クラス 9件・Task 2 Provider 14件）

## Decisions Made

- `list_models()` のタイムアウトは `self.timeout` ではなく 10 秒固定とした（現行 `fetch_lm_studio_models` の既定と一致。kwargs で上書き可能な設計は入れず、モデル一覧取得の意図に合わせてシンプルに保つ）
- TDD RED/GREEN の 2 コミット構成を採用した（plan の tdd="true" 指定に従う）
- ruff I001（import 未ソート）をテストファイルに検出し、`ruff --fix` で自動修正した（逸脱: Rule 1 — Auto-fix）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff I001 import ブロック未ソートを修正**
- **Found during:** GREEN フェーズのリント確認
- **Issue:** `tests/test_ocr_providers.py` で `import pytest` の後に `# noqa: F401` コメントを付けたため import グループが乱れ、ruff I001 エラーが発生
- **Fix:** `ruff check --fix` を実行してソート順を自動修正
- **Files modified:** `tests/test_ocr_providers.py`
- **Verification:** `ruff check . && ruff format --check .` が exit 0 で通過
- **Committed in:** `90b2a29`（feat コミットに同梱）

---

**Total deviations:** 1 auto-fixed（Rule 1 — Bug）
**Impact on plan:** リントのみの修正。機能・インターフェースへの影響なし。

## Issues Encountered

なし。

## User Setup Required

なし — 外部サービス設定不要。

## Next Phase Readiness

- `OCRProvider` / `OCRAPIKeyError` / `LMStudioProvider` の契約が確定し、Plan 02（`run_parallel` 一般化・`build_provider` ファクトリ）が依存できる状態になった
- `ocr.py` の既存関数（`build_chat_payload` / `call_lm_studio` / `fetch_lm_studio_models`）は本プランでは温存済み。Plan 02 でのリファクタ時に削除または deprecated 化する

---
## Self-Check: PASSED

- `pagefolio/ocr_providers.py` — FOUND
- `tests/test_ocr_providers.py` — FOUND
- `.planning/phases/04-provider-abstraction/04-01-SUMMARY.md` — FOUND
- commit `e2b2ecb` — FOUND
- commit `90b2a29` — FOUND

---
*Phase: 04-provider-abstraction*
*Completed: 2026-06-06*
