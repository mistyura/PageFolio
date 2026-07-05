---
phase: 02-ocr
plan: 01
subsystem: plugins
tags: [plugin-system, ocr-registry, encapsulation]

requires: []
provides:
  - "PluginManager.register_ocr_provider の重複名ポリシー（組み込み名衝突拒否・プラグイン間後勝ち上書き、警告付き）"
  - "unload_plugin 時の OCR プロバイダ registry 解除（owner ベース）"
  - "PluginManager.get_ocr_provider(name) / list_ocr_providers() 公開アクセサ"
affects: [02-02, 02-03, 02-04]

tech-stack:
  added: []
  patterns:
    - "get_disabled_ids と同型の薄い公開アクセサラッパー（get_ocr_provider/list_ocr_providers）"
    - "on_load 前後で _loading_plugin_id を設定/クリアし、register_ocr_provider がその値を owner 追跡に使う一時コンテキスト方式"

key-files:
  created: []
  modified:
    - pagefolio/plugins.py
    - pagefolio/ocr.py
    - pagefolio/dialogs/llm_config.py
    - tests/test_plugins.py
    - tests/test_ocr_providers.py
    - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md

key-decisions:
  - "register_ocr_provider の公開シグネチャは変更せず、ロード中プラグインIDを内部コンテキスト属性(_loading_plugin_id)経由で owner 追跡する方式を採用（D-08/D-09）"
  - "_provider_registry は私有属性のまま維持し、リネーム公開はしない（get_ocr_provider/list_ocr_providers の薄いアクセサ経由のみ公開）"

patterns-established:
  - "OCR provider registry へのアクセスは常に公開アクセサ(get_ocr_provider/list_ocr_providers)経由。ocr.py/llm_config.py からの _provider_registry 直接参照は禁止"

requirements-completed: [V171-OCR-03]

coverage:
  - id: D1
    description: "register_ocr_provider が組み込み名衝突を logger.warning のうえ拒否し、プラグイン間の重複名は後勝ち上書き（警告付き）"
    requirement: "V171-OCR-03"
    verification:
      - kind: unit
        ref: "tests/test_plugins.py -k duplicate_builtin or unload_deregisters or public_accessor"
        status: pass
    human_judgment: false
  - id: D2
    description: "unload_plugin でそのプラグインが登録した OCR プロバイダが registry から解除される"
    requirement: "V171-OCR-03"
    verification:
      - kind: unit
        ref: "tests/test_plugins.py -k unload_deregisters"
        status: pass
    human_judgment: false
  - id: D3
    description: "get_ocr_provider(name)/list_ocr_providers() 公開アクセサ追加、ocr.py:720-721・llm_config.py:127 の私有アクセスを置換"
    requirement: "V171-OCR-03"
    verification:
      - kind: unit
        ref: "tests/test_plugins.py, tests/test_ocr.py, tests/test_provider_ui.py -q"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-05
status: complete
---

# Phase 02 Plan 01: プラグイン OCR provider registry 堅牢化 Summary

**register_ocr_provider に重複名ポリシー(組み込み名衝突拒否・プラグイン間後勝ち上書き)と unload 時の owner ベース解除を追加し、get_ocr_provider/list_ocr_providers 公開アクセサ経由へ ocr.py/llm_config.py の私有アクセスを置換**

## Performance

- **Duration:** 約20分（実装・テスト作業）
- **Started:** 2026-07-05T07:03:00+09:00
- **Completed:** 2026-07-05T07:23:45+09:00
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments
- `register_ocr_provider` が組み込み名（claude/gemini/lmstudio/tesseract/ollama/runpod/off）との衝突を `logger.warning` のうえ拒否し、プラグイン同士の重複名は後勝ち上書き（警告付き）
- `unload_plugin` で、そのプラグインが登録した OCR プロバイダ登録を owner 追跡に基づき registry から解除
- `PluginManager.get_ocr_provider(name)` / `list_ocr_providers()` 公開アクセサを新設し、`ocr.py:720-721` と `dialogs/llm_config.py:127` の `_provider_registry` 私有アクセスを置換
- REVIEW.md（260610-aaa-v140-review-fixplan）の L-2/L-3 に解消済みマークとコミットハッシュを追記

## Task Commits

Each task was committed atomically:

1. **Task 1: register_ocr_provider 堅牢化・unload 解除・公開アクセサ追加** - `c70ae29` (feat)
2. **Task 2: 私有アクセスの公開アクセサ置換 + REVIEW.md 完了追記** - `3e15369` (refactor), `873d391` (docs)

**Deviation fix:** `51c188b` (fix) — build_provider 変更に伴う既存 M-7 回帰テストの fake スタブ更新

_Note: STATE.md/ROADMAP.md の更新はこの SUMMARY 作成と合わせてオーケストレータが実行（executor エージェントの長時間停止によりオーケストレータが引き継ぎ完了）。_

## Files Created/Modified
- `pagefolio/plugins.py` - `_BUILTIN_PROVIDER_NAMES` 定数・`_provider_owners` 辞書・`_loading_plugin_id` コンテキスト属性・重複名ポリシー・unload 時解除・`get_ocr_provider`/`list_ocr_providers` 公開アクセサ
- `pagefolio/ocr.py` - `build_provider` が `_provider_registry` 直接アクセスから `get_ocr_provider()` 経由へ
- `pagefolio/dialogs/llm_config.py` - Combobox values 生成が `list_ocr_providers()` 経由へ
- `tests/test_plugins.py` - 重複組み込み名拒否・プラグイン間後勝ち上書き・unload 解除・公開アクセサ・build_provider 経由解決の新規テスト
- `tests/test_ocr_providers.py` - build_provider 変更に伴う fake PluginManager スタブ修正
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-2/L-3 に解消済みマーク追記

## Decisions Made
- register_ocr_provider の公開シグネチャ（プラグイン作者向けAPI）は変更せず、load_plugin/enable_plugin が on_load 呼び出し前後で `_loading_plugin_id` を設定/クリアする内部コンテキスト方式で owner 追跡を実現（RESEARCH.md Architecture Patterns 準拠）
- `_provider_registry` はリネーム公開せず私有属性のまま維持し、両アクセサ経由の読み取りのみ許可（RESEARCH.md Anti-Patterns 準拠）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - 本プラン起因の回帰] tests/test_ocr_providers.py の M-7 fake スタブ修正**
- **Found during:** Task 2（私有アクセスの公開アクセサ置換）後の全体テスト実行
- **Issue:** `build_provider` が `_provider_registry` 直接アクセスから `get_ocr_provider()` 呼び出しへ変わったため、`SimpleNamespace(_provider_registry=...)` で作られた既存の fake PluginManager スタブが `AttributeError` になった
- **Fix:** fake スタブを実際の `PluginManager` インスタンス（またはそれと同等の `get_ocr_provider` を持つ実装）を使う形に修正
- **Files modified:** tests/test_ocr_providers.py
- **Verification:** `pytest tests/test_plugins.py tests/test_ocr.py tests/test_provider_ui.py -q` および `pytest -q`（フルスイート）グリーン
- **Committed in:** 51c188b

---

**Total deviations:** 1 auto-fixed（本プラン変更起因の既存テストスタブ修正）
**Impact on plan:** スコープ外の変更なし。公開アクセサ導入という計画の意図から必然的に生じた既存テストの追従修正。

## Issues Encountered
executor エージェントが Task 完了・回帰修正コミット（51c188b）後、SUMMARY.md 作成前の段階で約45分間応答なしとなり停止（`running` ステータスのまま git 状態に変化なし）。ユーザーの判断によりエージェントを停止し、オーケストレータが検証（pytest 全体737件グリーン・ruff クリーン・acceptance_criteria 全項目確認）とこの SUMMARY.md 作成、STATE.md/ROADMAP.md 更新を引き継いで完了させた。実装・テスト内容そのものへの影響はなし。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `get_ocr_provider`/`list_ocr_providers` 公開アクセサが 02-02/02-03/02-04 の土台として利用可能
- `_provider_owners`/`_loading_plugin_id` 追跡機構は plugins.py 内部に閉じており、後続プランの OCR プロバイダ実装（TesseractProvider の tesseract_lang 対応等）に影響しない

---
*Phase: 02-ocr*
*Completed: 2026-07-05*
