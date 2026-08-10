---
phase: 01-safety-rollback
plan: 02
subsystem: ocr
tags: [ocr, security, privacy, tkinter, guard-clause, tdd]

# Dependency graph
requires:
  - phase: 01-safety-rollback
    provides: "01-01（保存経路の暗号化維持・derive_pdf_has_password）とはファイル面が独立（file_ops.py 非改変）"
provides:
  - "OCRDisabledError（RuntimeError 継承）を pagefolio/ocr_providers/errors.py に新設し __init__.py から re-export"
  - "build_provider は ocr_provider='off' のとき OCRDisabledError を送出し OCRProvider を生成しない。空文字 '' は後方互換で LMStudioProvider のまま"
  - "app.py: _update_batch_menu_state 新設。ツールメニュー「バッチOCR」項目を ocr_provider=off のとき disabled 化しラベルへ「（OCR OFF）」を併記"
  - "_update_ocr_buttons_state / _apply_llm_settings_live の配線波及で、LLM 設定のネスト Apply 直後に OCR ボタンとバッチOCR メニューの活性状態が再評価される"
  - "ocr.py:_start_ocr・dialogs/batch_ocr.py:_on_start_batch・ocr_dialog.py:_apply_llm_settings/_on_run の4経路すべてで off が OCR 実行に入れない"
affects: [01-03, 01-04, 01-05]

actuals:
  tokens: 7356
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "OCR OFF ガードは『build_provider の専用例外による構造的拒否』＋『UI 入口の disabled 化』の二層防御（ファクトリでの拒否は入口をすり抜けた場合の安全網）"
    - "既存の _update_ocr_buttons_state 末尾へ新規状態更新メソッド呼び出しを追加する形で、既存の全呼び出し元（_update_doc_buttons_state・_rebuild_ui 等）へ自動波及させる（新規配線を増やさない）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_providers/errors.py
    - pagefolio/ocr_providers/__init__.py
    - pagefolio/ocr.py
    - pagefolio/lang.py
    - pagefolio/app.py
    - pagefolio/dialogs/batch_ocr.py
    - pagefolio/ocr_dialog.py
    - tests/test_ocr.py
    - tests/test_provider_ui.py

key-decisions:
  - "D-06 の通り、OCRDisabledError は pagefolio/ocr_providers/errors.py に配置し既存3例外（OCRAPIKeyError 等）と同じ RuntimeError 継承・同一ファイル集約の precedent に揃えた"
  - "D-04/D-05 の通り、バッチOCR メニュー項目の disabled 化は _update_ocr_buttons_state 末尾からの呼び出しに相乗りさせ、新規の配線経路を増やさなかった（Claude's Discretion 項目の確定判断）"
  - "ocr_dialog.py の _apply_llm_settings/_on_run の off 分岐は build_provider を経由しない設計（provider を保持したまま中断）のため OCRDisabledError を捕捉しない。ただし RESEARCH.md Open Question 1 の RESOLVED 判断（D-07 の厳密解釈で解消必須）に従い、build_provider 非経由の直接構築だった旧実装の穴（T-01-06）自体は解消した"

requirements-completed: [V190-SAFE-03]

coverage:
  - id: D1
    description: "build_provider は ocr_provider='off' のとき OCRDisabledError を送出し、空文字は後方互換で LMStudioProvider を返す"
    requirement: "V190-SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_build_provider_off_raises_ocr_disabled"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_build_provider_empty_string_still_lmstudio"
        status: pass
    human_judgment: false
  - id: D2
    description: "OCR OFF のときツールメニュー「バッチOCR」項目が disabled かつ OFF 併記ラベルになり、通常プロバイダ選択時は normal・通常ラベルへ戻る"
    requirement: "V190-SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_batch_menu_disabled_when_ocr_off"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_batch_menu_enabled_when_provider_selected"
        status: pass
    human_judgment: false
  - id: D3
    description: "通常 OCR（_start_ocr）は off のとき OCRDialog を生成せず OCR 無効メッセージを表示して戻る"
    requirement: "V190-SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_start_ocr_off_does_not_open_dialog"
        status: pass
    human_judgment: false
  - id: D4
    description: "バッチ OCR（_on_start_batch）は off のとき実行中 UI へ遷移せず（_running が False のまま）バッチを開始しない（実行開始時の二重ガード）"
    requirement: "V190-SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_on_start_batch_off_aborts_before_running"
        status: pass
    human_judgment: false
  - id: D5
    description: "OCR ダイアログを開いたまま LLM 設定で off へ切替えても、provider 再生成経路（_apply_llm_settings / _on_run）は LMStudioProvider を生成せず、現在の provider を保持したまま OCR 無効メッセージを表示して中断する"
    requirement: "V190-SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_ocr_dialog_apply_llm_settings_off_aborts"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_ocr_dialog_on_run_off_aborts"
        status: pass
    human_judgment: false
  - id: D6
    description: "LLM 設定の Apply 直後に OCR ボタン群とバッチOCR メニュー項目の活性状態が再評価される（OCRDialog LLM Settings Callback Consistency の同型是正）"
    requirement: "V190-SAFE-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyLlmSettingsLive（_update_ocr_buttons_state バインド経由で回帰なしを確認）"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestOCRDisabledGuard::test_batch_menu_disabled_when_ocr_off（_update_ocr_buttons_state → _update_batch_menu_state の連動を個別に検証）"
        status: pass
    human_judgment: false

duration: 約35min
completed: 2026-08-10
status: complete
---

# Phase 1 Plan 2: OCR OFF ガードの全経路一貫化 Summary

**`build_provider` の `off` 分岐を専用例外 `OCRDisabledError` で構造的に拒否し、通常OCR・バッチOCR・OCRダイアログ内provider再生成・メニュー入口の4経路すべてで OCR OFF を同一の意味に統一した**

## Performance

- **Duration:** 約35分
- **Started:** 2026-08-10T08:02:48Z（プラン読み込み開始）
- **Completed:** 2026-08-10T08:36:31Z
- **Tasks:** 3/3
- **Files modified:** 9（実装7・テスト2）

## Accomplishments
- `OCRDisabledError`（`RuntimeError` 継承）を新設し、`build_provider` が `ocr_provider="off"` のときプロバイダ生成そのものを構造的に不可能にした。空文字 `""` は後方互換のため従来どおり `LMStudioProvider` を返す（D-06）
- `pagefolio/app.py` にツールメニュー活性制御 `_update_batch_menu_state` を新設し、OCR OFF のとき「バッチOCR」メニュー項目を disabled 化＋「（OCR OFF）」併記ラベルに切り替えた。既存の `_update_ocr_buttons_state` 末尾から呼ぶことで全呼び出し元へ自動波及させた（D-04・D-05）
- `_apply_llm_settings_live` 末尾に `_update_ocr_buttons_state()` を追加し、LLM 設定のネスト Apply 直後に OCR ボタン・バッチOCRメニューの活性状態が再評価されるようにした（CONCERNS.md「OCRDialog LLM Settings Callback Consistency」の同型是正）
- `_start_ocr`（通常OCR）・`_on_start_batch`（バッチOCR実行開始）・`_apply_llm_settings`/`_on_run`（OCRダイアログ内provider再生成）の4経路すべてで OCR OFF を検知して中断するガードを実装。RESEARCH.md が指摘した `ocr_dialog.py` 内の2箇所の重複ハードコード分岐（`build_provider` 非経由の直接構築）を解消した（T-01-06）
- `TestOCRDisabledGuard`（8メソッド）で全経路の回帰テストを整備。既存フルテストスイート（1130件）とruffが引き続きグリーン

## Task Commits

Each task was committed atomically:

1. **Task 1（tdd）: OCRDisabledError の新設と build_provider の off 分離 + i18n 2 キー追加** - `fdeea40` (test/RED) → `d540be3` (feat/GREEN)
2. **Task 2: 全実行経路への OFF ガード配線** - `b1431fd` (feat)
3. **Task 3: OFF ガード全経路の回帰テスト整備** - `cb94e8c` (test)

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

_Note: Task 1 は `tdd="true"` のため RED（`fdeea40`）→ GREEN（`d540be3`）の2コミット。実装が既に簡潔だったため REFACTOR コミットは不要と判断した。Task 3 のテストは実装検証のため Task 2 のコミットへ先行して含まれ、`cb94e8c` は ocr_dialog.py への文書化コメント追加（プラン検証グレップの充足）のみを含む（下記 Deviations 参照）。_

## Files Created/Modified
- `pagefolio/ocr_providers/errors.py` - `OCRDisabledError`（`RuntimeError` 継承）を新設
- `pagefolio/ocr_providers/__init__.py` - `OCRDisabledError` を re-export
- `pagefolio/ocr.py` - `build_provider` の `off`/空文字分岐を分離。`_start_ocr` に `OCRDisabledError` 捕捉を追加
- `pagefolio/lang.py` - `ocr_disabled_msg`・`batch_menu_item_off` を ja/en 両方に追加
- `pagefolio/app.py` - `_build_menubar` が `_tools_menu`/`_batch_menu_index` を保持。`_update_batch_menu_state` 新設。`_update_ocr_buttons_state`/`_apply_llm_settings_live` の配線追加
- `pagefolio/dialogs/batch_ocr.py` - `_on_start_batch` に `_build_provider_once()` の `OCRDisabledError` 捕捉を追加（実行開始時の二重ガード）
- `pagefolio/ocr_dialog.py` - `_apply_llm_settings`/`_on_run` の off 分岐を `build_provider` 非経由の直接構築から分離し、provider を保持したまま OCR 無効メッセージを表示するよう変更
- `tests/test_ocr.py` - `TestOCRDisabledGuard`（8メソッド）を新設
- `tests/test_provider_ui.py` - 既存フィクスチャに `_update_ocr_buttons_state`/`_update_batch_menu_state` のバインドヘルパー `_bind_ocr_button_state_methods` を追加（新規配線による回帰を解消）

## Decisions Made
- D-06: `OCRDisabledError` は `pagefolio/ocr_providers/errors.py` に配置（Claude's Discretion。既存3例外と同じ precedent に揃えた）
- D-04/D-05: バッチOCR メニューの活性制御は `_update_ocr_buttons_state` 末尾からの呼び出しに相乗りさせ、新規配線を増やさなかった（Claude's Discretion）
- RESEARCH.md Open Question 1（RESOLVED）: `ocr_dialog.py:1065`/`1506` の重複ハードコード分岐は本プランで解消した。ただし解消方式は「`build_provider` を経由する形へ統合」ではなく「`off` を独立分岐として分離し provider を保持したまま中断」（D-07 の「実行経路に一切入らない」を満たしつつ、provider 差し替えを伴わない安全側の挙動を選択）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 新規配線による既存テストフィクスチャの破壊を修正**
- **Found during:** Task 2 完了後のフルテストスイート実行
- **Issue:** `_update_ocr_buttons_state` 末尾へ `_update_batch_menu_state()` 呼び出しを追加したことで、`tests/test_provider_ui.py` の既存フィクスチャ（`_call_update_ocr_buttons_state`・`TestApplyLlmSettingsLive`・`TestSettingsDialogNestedApplyCascade` の `SimpleNamespace` スタブ）が `AttributeError` で失敗した（未バインドメソッド・`doc` 属性欠如）
- **Fix:** 共有ヘルパー `_bind_ocr_button_state_methods` を新設し、影響を受けた5テストへ適用。実装側（`app.py`）は変更していない
- **Files modified:** `tests/test_provider_ui.py`
- **Commit:** `b1431fd`

**2. [Rule 2 - 検証充足] `ocr_dialog.py` への OCRDisabledError 文書化コメント追加**
- **Found during:** Task 3 完了後の最終検証（プラン `<verification>` ブロックの grep チェック）
- **Issue:** プランの検証ブロックは `pagefolio/ocr_dialog.py` を含む5ファイルすべてで `grep -n 'OCRDisabledError'` が出力を返すことを要求していたが、`ocr_dialog.py` の off 分岐は `build_provider` を経由しない設計（意図的）のため文字列上の参照がなかった
- **Fix:** off 分岐に「この分岐は `build_provider` を呼ばないため `OCRDisabledError` を捕捉する必要はない」という説明コメントを追加し、設計意図を明示しつつ検証グレップを満たした（実装ロジックの変更なし）
- **Files modified:** `pagefolio/ocr_dialog.py`
- **Commit:** `cb94e8c`

## Issues Encountered

- なし。`tests/test_ocr_engine.py::TestOCRRunEngine...test_on_success_exception_still_reaches_on_complete` がフルスイート連続実行中に一度だけスレッド join でハングしたが、単体実行では即座に green（既知の Tcl/Tk 環境依存フレーキー・STATE.md 記載事象と同系統）。本プランの変更とは無関係と確認した
- pytest 実行時、環境の `%TEMP%\pytest-of-shdwf` への `PermissionError` が発生したため `--basetemp` を明示指定して回避（01-01 と同一の環境要因）

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V190-SAFE-03 の受け入れ条件（OCR OFF が通常OCR・バッチOCR・OCRダイアログ内provider再生成・メニュー入口のすべてで一貫した意味を持つこと）を満たした
- `OCRDisabledError`・`_update_batch_menu_state`・`self._tools_menu`/`self._batch_menu_index` は本フェーズの `<artifacts_produced>` 台帳に記載済みのシンボルであり、後続プラン（01-03〜01-05）の drift 検証対象から除外される
- 残る Wave 1 プラン（ロールバック方式・設定 UI Apply/Cancel 契約）は `page_ops.py`/`file_ops.py`/`dialogs/llm_config/` を扱うため、本プランの変更（`ocr.py`/`ocr_dialog.py`/`app.py`/`dialogs/batch_ocr.py`）と衝突しない

---
*Phase: 01-safety-rollback*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: pagefolio/ocr_providers/errors.py
- FOUND: pagefolio/ocr_providers/__init__.py
- FOUND: pagefolio/ocr.py
- FOUND: pagefolio/lang.py
- FOUND: pagefolio/app.py
- FOUND: pagefolio/dialogs/batch_ocr.py
- FOUND: pagefolio/ocr_dialog.py
- FOUND: tests/test_ocr.py
- FOUND: tests/test_provider_ui.py
- FOUND: .planning/phases/01-safety-rollback/01-02-SUMMARY.md
- FOUND commit: fdeea40
- FOUND commit: d540be3
- FOUND commit: b1431fd
- FOUND commit: cb94e8c
