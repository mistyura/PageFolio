---
phase: 01-safety-rollback
plan: 01
subsystem: file-ops
tags: [pymupdf, fitz, encryption, pdf-password, tdd]

# Dependency graph
requires: []
provides:
  - "_save_as は無条件で encryption=fitz.PDF_ENCRYPT_KEEP を付与し暗号化を維持する"
  - "_overwrite_current_file は encryption 未指定時に PDF_ENCRYPT_KEEP へ setdefault で既定化する（明示指定は上書きしない）"
  - "derive_pdf_has_password 純関数（pagefolio/file_ops.py モジュールレベル）で pdf_has_password を保存 kwargs から単一地点導出"
  - "_save_compressed は上書き分岐・別パス分岐の両方で暗号化を維持する"
  - "保存全経路（上書きインクリメンタル/フォールバック/名前を付けて保存/縮小保存2分岐）とパスワード付与/解除の回帰テスト（実ファイル needs_pass 計測）"
affects: [01-02, 01-03, 01-04, 01-05]

actuals:
  tokens: 3800
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "安全側デフォルトは setdefault で関数内に構造として埋め込む（呼び出し側の明示指定を破壊しない）"
    - "状態フラグ（pdf_has_password）は保存成功後にのみ、保存 kwargs から論理導出する単一関数へ集約し、実行時 I/O を発生させない"

key-files:
  created: []
  modified:
    - pagefolio/file_ops.py
    - tests/test_password.py

key-decisions:
  - "D-01/D-02/D-03 の通りに実装。_save_as は無確認で常に暗号化維持、_overwrite_current_file は setdefault 既定化、pdf_has_password は derive_pdf_has_password による論理導出に一本化した"
  - "_do_set_password / _remove_password の _is_current_file 分岐にあった pdf_has_password への直接代入を削除し、導出地点を _overwrite_current_file の1箇所へ閉じた（プラン Task 2 の指示どおり）"
  - "_save_compressed の save_kwargs に encryption=PDF_ENCRYPT_KEEP を追加し、上書き分岐だけでなく別パス保存分岐（doc.save 直接呼び出し）でも暗号化維持を担保した（V190-SAFE-01 の全経路化）"

patterns-established:
  - "保存 kwargs からの論理導出（derive_pdf_has_password）: NONE→False / AES_256→True / それ以外（KEEPを含む）→現在値維持、実行時に保存先を再オープンしない"

requirements-completed: [V190-SAFE-01, V190-SAFE-02]

coverage:
  - id: D1
    description: "「名前を付けて保存」が暗号化 PDF の暗号化を無条件で維持する"
    requirement: "V190-SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_save_as_keeps_encryption"
        status: pass
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_save_as_twice_keeps_encryption"
        status: pass
    human_judgment: false
  - id: D2
    description: "上書き保存（インクリメンタル失敗時のフォールバック）が暗号化を維持する"
    requirement: "V190-SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_overwrite_current_file_keeps_encryption"
        status: pass
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_save_file_fallback_keeps_encryption"
        status: pass
    human_judgment: false
  - id: D3
    description: "縮小最適化して保存が上書き・別パスの両分岐で暗号化を維持する"
    requirement: "V190-SAFE-01"
    verification:
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_save_compressed_overwrite_keeps_encryption"
        status: pass
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_save_compressed_new_path_keeps_encryption"
        status: pass
    human_judgment: false
  - id: D4
    description: "パスワード付与/解除の明示指定が既定化 setdefault に上書きされない"
    requirement: "V190-SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_set_password_kwargs_not_overridden"
        status: pass
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_remove_password_kwargs_not_overridden"
        status: pass
    human_judgment: false
  - id: D5
    description: "pdf_has_password が保存 kwargs から論理導出され、解除後の再暗号化・保存失敗時の状態不変を保証する"
    requirement: "V190-SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_password.py::TestDerivePdfHasPassword"
        status: pass
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_remove_then_save_file_stays_plain"
        status: pass
      - kind: unit
        ref: "tests/test_password.py::TestSavePathsKeepEncryption::test_overwrite_failure_keeps_password_state"
        status: pass
    human_judgment: false

duration: 約71min（うちチェックポイント承認待ちを除く実作業は約20min）
completed: 2026-08-10
status: complete
---

# Phase 1 Plan 1: 保存経路の暗号化維持 Summary

**PyMuPDF の保存3経路（名前を付けて保存・上書き/フォールバック・縮小保存の2分岐）に `encryption=PDF_ENCRYPT_KEEP` を構造的に既定化し、`derive_pdf_has_password` 純関数で `pdf_has_password` の導出地点を1箇所へ統一**

## Performance

- **Duration:** 約71分（Task 1 tracer コミットからチェックポイント承認・Task 2/3 完了まで。実作業のみは約20分）
- **Started:** 2026-08-10T15:47:09+09:00（Task 1 tracer コミット）
- **Completed:** 2026-08-10T16:58:49+09:00（Task 3 コミット）
- **Tasks:** 3/3
- **Files modified:** 2（`pagefolio/file_ops.py`, `tests/test_password.py`）

## Accomplishments
- `_save_as` が無条件で `encryption=fitz.PDF_ENCRYPT_KEEP` を付与し、暗号化 PDF の「名前を付けて保存」が暗号化を維持することを実測回帰テストで固定（Task 1・tracer）
- `_overwrite_current_file` が `encryption` 未指定時に `save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)` で安全側既定化し、`_do_set_password`（AES-256）/ `_remove_password`（NONE）の明示指定は上書きしないことを担保（Task 2）
- モジュールレベル純関数 `derive_pdf_has_password(current, encryption)` を新設し、`pdf_has_password` の導出を `_overwrite_current_file` の保存成功直後の1箇所へ集約。実行時に保存先を再オープンする I/O は発生しない（Task 2）
- `_save_compressed` の `save_kwargs` へ `encryption=PDF_ENCRYPT_KEEP` を追加し、上書き分岐・別パス保存分岐の両方で暗号化維持を担保（Task 2・V190-SAFE-01 全経路化）
- 保存4経路 + パスワード付与/解除の明示経路すべてについて、保存先 PDF を実際に `fitz.open()` で開き直して `needs_pass` / `authenticate()` を計測する回帰テスト13件を追加。冪等性（Save As 連続実行・解除後上書き）と中断時保証（`os.replace` 失敗時の状態不変）のプローブ由来エッジも表現（Task 3）

## Task Commits

Each task was committed atomically:

1. **Task 1（tracer）: 「名前を付けて保存」の暗号化維持をエンドツーエンドで貫通させる** - `d3b4c7c` (feat)
2. **Task 2: 上書き保存フォールバックと縮小保存の暗号化既定化 + pdf_has_password 論理導出** - `6d2f45f` (test / RED) → `f0c8c3c` (feat / GREEN)
3. **Task 3: 保存全経路とプローブ由来エッジの回帰テスト整備** - `e84e337` (test)

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

_Note: Task 2 は `tdd="true"` のため RED（`6d2f45f`）→ GREEN（`f0c8c3c`）の2コミット。実装がすでに簡潔だったため REFACTOR コミットは不要と判断した。_

## Files Created/Modified
- `pagefolio/file_ops.py` - `derive_pdf_has_password` 純関数を新設。`_save_as`（無条件 KEEP 付与）・`_overwrite_current_file`（setdefault 既定化 + 導出呼び出し）・`_save_compressed`（save_kwargs へ KEEP 追加）・`_do_set_password`/`_remove_password`（直接代入を削除し導出地点へ委譲）を変更
- `tests/test_password.py` - `TestSavePathsKeepEncryption`（13メソッド）・`TestDerivePdfHasPassword`（3メソッド）を新設。実ファイル `needs_pass` 計測による回帰テスト

## Decisions Made
- D-01: `_save_as` は確認ダイアログを追加せず無条件で暗号化維持（解除は「🔒 パスワード → 解除」の明示操作のみで起こす契約を弱めないため）
- D-02: `_overwrite_current_file` の既定化は単純代入ではなく `setdefault` を使用（`_do_set_password`/`_remove_password` の明示指定を破壊しないため）
- D-03: `pdf_has_password` は保存 kwargs から論理導出する単一関数に閉じ、実行時に保存先を再オープンする I/O は行わない（Core Value の大 PDF 性能維持）。ただし回帰テスト側では実ファイルを開き直して `needs_pass` を検証し、導出ロジックの正しさを機械保証する
- `_save_compressed` の別パス保存分岐（`doc.save(path, **save_kwargs)`）も同型の平文化バグを持っていたため、RESEARCH.md の保存経路対応表には明示されていなかったが同時に是正した（要件文「いずれの経路で保存しても暗号化が維持される」を満たすため）

## Deviations from Plan

None - plan executed exactly as written（Task 2 の `tdd="true"` 指示どおり RED→GREEN の2コミット構成、REFACTOR は不要と判断したのみで、これは計画の許容範囲内）。

## Issues Encountered
- フルテストスイート（`pytest -q`）実行時、`tests/test_plugin_dialog_wheel.py` の2件が `_tkinter.TclError`（Tcl/Tk インタプリタ生成失敗）で ERROR になった。STATE.md に既知の Tcl/Tk フレーキー（v1.9.0 Phase 3 で切り分け・修復予定）として記録済みの事象であり、`tests/test_plugin_dialog_wheel.py` を単体実行すると2件とも green で通過することを確認した。本プランの変更（`pagefolio/file_ops.py` / `tests/test_password.py`）とは無関係
- pytest 実行時、環境の `%TEMP%\pytest-of-shdwf` ディレクトリへの `PermissionError`（Windows のアクセス拒否）が発生したため、`--basetemp` を明示指定して回避した。既存テストコードやプラン変更とは無関係な実行環境固有の事象

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V190-SAFE-01 / V190-SAFE-02 の受け入れ条件（保存経路からの意図しない平文化排除・`pdf_has_password` と実ファイルの一致）を Plan 01 の範囲で満たした
- `pagefolio/file_ops.py` の `derive_pdf_has_password` は本フェーズの `<artifacts_produced>` 台帳に記載済みのシンボルであり、後続プラン（01-02〜01-05）の drift 検証対象から除外される
- Wave 1 の残り Plan（OCR OFF 一貫化・ロールバック方式・設定 UI Apply/Cancel 契約）はいずれも `pagefolio/file_ops.py` 以外のファイル面（`ocr.py`/`app.py`/`page_ops.py`/`dialogs/llm_config/`）を扱うため、本プランの変更と衝突しない

---
*Phase: 01-safety-rollback*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: pagefolio/file_ops.py
- FOUND: tests/test_password.py
- FOUND: .planning/phases/01-safety-rollback/01-01-SUMMARY.md
- FOUND commit: d3b4c7c
- FOUND commit: 6d2f45f
- FOUND commit: f0c8c3c
- FOUND commit: e84e337
