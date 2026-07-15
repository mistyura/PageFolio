---
phase: 04-ocr
plan: 03
subsystem: ocr
tags: [batch-ocr, tkinter-menu, ttk-treeview, cross-file-summary, tdd]

# Dependency graph
requires:
  - phase: 04-ocr (04-01)
    provides: "BatchFileEntry/BatchState/STATUS_* 定数（Tk/fitz非依存の純ロジック層）"
  - phase: 04-ocr (04-02)
    provides: "BatchOCRDialog コア（D&D+ファイル選択投入・3列Treeview二段進捗・per-file OCRRunEngine ループ・2階層キャンセル）"
provides:
  - "BatchOCRDialog のファイル横断統合サマリ（_format_batch_summary_input/_on_batch_summary/_batch_summary_worker）"
  - "BatchOCRDialog のファイル別結果閲覧（_on_select_file/_render 相当/_on_export_file）"
  - "OCRDialog からコピペ移植した _insert_markdown/_confirm_summary_cost/_format_pages_text"
  - "本プロジェクト初の tk.Menu メニューバー（app.py:_build_menubar・_open_batch_ocr）"
  - "ui_builder._build_styles の Treeview 用 ttk.Style（テーマ追随）"
  - "pagefolio/dialogs/__init__.py の BatchOCRDialog 後方互換 re-export"
affects: [04-VALIDATION, 04-UAT]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OCRDialog インスタンスメソッドを継承・cross-import せず同一シグネチャ・同一挙動でコピペ移植する独立ダイアログパターン（04-02から継続）"
    - "ttk.Style ブロックを _build_styles 内へ追記することで、既存の _rebuild_ui→_build_styles() 再呼び出し経路にテーマ追随を自動的に乗せる"
    - "本プロジェクト初の tk.Menu を app.py の __init__/_rebuild_ui 双方から _build_menubar() で呼び、root.winfo_children() 破棄後も再構築されるようにする"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/batch_ocr.py
    - pagefolio/lang.py
    - pagefolio/ui_builder.py
    - pagefolio/app.py
    - pagefolio/dialogs/__init__.py
    - tests/test_batch_ocr_dialog.py

key-decisions:
  - "_format_pages_text は entry（BatchFileEntry）を明示引数に取る形で実装した。OCRDialog の同名メソッドは self.page_indices/results を暗黙参照するが、BatchOCRDialog は複数ファイルを扱うため単一の等価属性がなく、entry 引数化が必然的差分（挙動＝セパレータ付きページ本文連結は同一）"
  - "_insert_markdown は self.text を暗黙参照する形（OCRDialogと完全に同一シグネチャ）で実装し、結果閲覧・サマリ表示の両方が同一 Text ウィジェットへ描画される設計とした（OCRDialogの単一結果ビュー踏襲）"
  - "provider.supports_text_prompt が False のときのエラーメッセージは self.app.settings のプロバイダキーをそのまま使い、OCRDialog の _provider_display_name のような人間可読名マッピングは複製しなかった（スコープ最小化・エラーゲート構造自体は同一）"
  - "ui_builder.py の Treeview 用 style.configure/style.map は # fmt: off/on + noqa E501 で単一物理行に保つ（plan acceptance の literal grep パターン一致を優先）"
  - "menubar は app.py の __init__ と _rebuild_ui 双方で _build_menubar() を呼ぶ設計とした。プラン本文は __init__ 相当としか明記していないが、_rebuild_ui は root.winfo_children() を全破棄するためテーマ切替時にメニューバーが消失する Rule 2（欠落した重要機能）に該当し自動追加した"

patterns-established:
  - "SUMMARY_TOO_LONG_CHARS はモジュール定数 import（from pagefolio.ocr_dialog import SUMMARY_TOO_LONG_CHARS）のみで再利用し、新規ハード閾値は追加しない（D-14）"

requirements-completed: [V180-BATCH-05]

coverage:
  - id: D1
    description: "_format_batch_summary_input が完了済み（STATUS_DONE）ファイルのみを対象に、ファイル名見出し（=== name ===）を挿入して連結する（D-15）"
    requirement: V180-BATCH-05
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchSummary::test_batch_summary_concat"
        status: pass
    human_judgment: false
  - id: D2
    description: "_on_batch_summary は完了ファイル0件で complete_text_ex を呼ばず no-op（D-13・自動生成しない）"
    requirement: V180-BATCH-05
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchSummary::test_batch_summary_zero_completed_noop"
        status: pass
    human_judgment: false
  - id: D3
    description: "連結後の合計文字数が SUMMARY_TOO_LONG_CHARS を超える場合 askyesno 過大警告を経由し、拒否時は complete_text_ex が呼ばれない（D-14）"
    requirement: V180-BATCH-05
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchSummary::test_batch_summary_oversized_warns"
        status: pass
    human_judgment: false
  - id: D4
    description: "from pagefolio.dialogs import BatchOCRDialog が成功する（後方互換 re-export・到達性）"
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchSummary::test_batch_dialog_reexport"
        status: pass
    human_judgment: false
  - id: D5
    description: "ファイル別結果閲覧が _insert_markdown（OCRDialogコピペ移植）を用いて描画し、エクスポートがファイル単位である（D-16）"
    verification:
      - kind: unit
        ref: "tests/test_lang_parity.py::test_no_unused_lang_keys（batch_export_btn/batch_file_select_label参照経由の到達性）"
        status: pass
    human_judgment: true
    rationale: "ファイル選択 Combobox → _on_select_file → _insert_markdown 描画の実ウィンドウでの見た目・スクロール挙動は目視確認が必要（04-VALIDATION.md Manual-Only Verifications）。ロジック自体（_format_pages_text の内容抽出）は test_batch_summary_concat が間接検証済み"
  - id: D6
    description: "新規メニュー項目「バッチOCR」（アクセラレータなし・クリック起動）から BatchOCRDialog を独立起動できる（D-01・D-04）"
    verification:
      - kind: unit
        ref: "手動スモークテスト（TkinterDnD.Tk() 上での _build_menubar/_open_batch_ocr 実行確認・実施記録は本SUMMARYのAccomplishments参照）"
        status: pass
    human_judgment: true
    rationale: "メニュークリックでのダイアログ起動という実UI操作は自動テスト対象外（tkinterdnd2 GUI操作は既存方針でも手動検証扱い）。プログラムからの _open_batch_ocr() 呼び出し自体は正常終了することを確認済みだが、実際のメニュークリック操作とTreeview/メニューのテーマ配色は04-VALIDATION.mdの手動検証に委ねる"
  - id: D7
    description: "Treeview/メニューのテーマ配色（dark/light）が C 辞書に整合し、_rebuild_ui→_build_styles() 再呼び出しでテーマ追随する（Pitfall 4）"
    verification:
      - kind: unit
        ref: "手動スモークテスト（_toggle_lang() 経由の _rebuild_ui 呼び出しでメニューバー再構築を確認）"
        status: pass
    human_judgment: true
    rationale: "実配色（dark/light 双方）の目視確認は04-VALIDATION.md Manual-Only Verificationsに委ねる。Style定義がC辞書のみ参照しハードコードhexがないことはコードレビューで確認済み"

duration: 15min
completed: 2026-07-15
status: complete
---

# Phase 4 Plan 3: バッチOCR統合サマリ・結果閲覧・メニュー起動導線 Summary

**BatchOCRDialog にファイル横断統合サマリ（見出し連結・過大警告・手動トリガー）とファイル別結果閲覧を追加し、本プロジェクト初の tk.Menu メニューバーからの起動導線・Treeview用ttk.Style・後方互換re-exportを配線してバッチOCR機能（V180-BATCH-01〜05）を完成させた**

## Performance

- **Duration:** 約15分
- **Started:** 2026-07-15T13:00:00Z
- **Completed:** 2026-07-15T13:08:24Z
- **Tasks:** 3
- **Files modified:** 6（新規0・変更6）

## Accomplishments
- `pagefolio/dialogs/batch_ocr.py` に `_insert_markdown`/`_confirm_summary_cost`/`_format_pages_text` を `OCRDialog`（`ocr_dialog.py`）からコピペ移植（継承・cross-import せず、`ocr_dialog.py` は本フェーズで無変更・`git diff --name-only` で確認済み）
- `_format_batch_summary_input` を新設し、STATUS_DONE ファイルのみを対象に `batch_summary_file_header`（`=== name ===`）見出しを挿入して連結する D-15 を実装
- `_on_batch_summary`（「📊 サマリ作成」手動トリガー）を実装。完了0件は no-op（D-13）、非対応プロバイダはエラー表示、クラウド時は `_check_cloud_api_key`→`_confirm_summary_cost` の順でコスト確認（D-14）、`SUMMARY_TOO_LONG_CHARS` 超過時は追加 askyesno 警告を経由し、承認後にワーカースレッド1本+世代ガード+`_summary_cancel_flag` で `_batch_summary_worker` を実行
- ファイル別結果閲覧（D-16）: ファイル選択 `ttk.Combobox` + 移植済み `_insert_markdown` による整形描画 + `_on_export_file` によるファイル単位エクスポート（raw テキスト維持）を実装
- `_on_close`（04-02実装）を拡張し、バッチ実行中またはサマリ生成中に `_batch_cancel_flag`/`_file_cancel_flag`/`_summary_cancel_flag` の3フラグを同時 set するようにした
- 本プロジェクト初の `tk.Menu` メニューバーを `app.py:_build_menubar` として新設。「ツール」→「バッチOCR」（アクセラレータなし・クリック起動のみ・Pitfall 5回避）から `_open_batch_ocr` で `BatchOCRDialog` を独立起動（`self.doc`/`self.filepath` 非参照・D-04）。`__init__`/`_rebuild_ui` 双方から呼ぶことでテーマ切替後もメニューバーが残る
- `ui_builder._build_styles` に Treeview 用 `ttk.Style`（`style.configure("Treeview"...)`/`style.map("Treeview"...)`）を C 辞書参照のみで追記し、既存の `_rebuild_ui→_build_styles()` 再呼び出し経路でテーマ追随することを確認（Pitfall 4）
- `pagefolio/dialogs/__init__.py` に `from pagefolio.dialogs.batch_ocr import BatchOCRDialog` の後方互換 re-export を追加
- `pagefolio/lang.py` に `batch_file_select_label`/`batch_export_btn`/`batch_summary_btn`/`batch_summary_file_header`/`batch_menu_tools`/`batch_menu_item` を ja/en 同時追加（既存 `ocr_summary_*`/`ocr_page_separator`/`ocr_cost_confirm_title` 等の汎用キーは再利用し重複追加しなかった）
- `tests/test_batch_ocr_dialog.py` に `TestBatchSummary`（見出し連結・zero-completed no-op・過大警告拒否・後方互換 re-export）4テストを新設し全件 green を確認
- 手動スモークテスト（`TkinterDnD.Tk()` 上で `PDFEditorApp` を実インスタンス化）で、メニューバー構築・`_toggle_lang()` 経由の `_rebuild_ui` 後もメニューバーが再構築されること・`_open_batch_ocr()` が例外なくダイアログを起動することを確認

## Task Commits

Each task was committed atomically:

1. **Task 1: ファイル横断統合サマリ + ファイル別結果閲覧** - `ba8b234` (feat)
2. **Task 2: メニューバー起動導線 + Treeview/メニュー Style + 後方互換 re-export** - `b66e5ca` (feat)
3. **Task 3: test_batch_ocr_dialog.py — サマリ連結・過大警告・到達性テスト追加** - `f2a8719` (test)

_Note: プラン frontmatter は tdd="true" だが、04-02 と同様に本プラン独自の実装先行構造（テストファイル自体は Task 3 が新規テストを追加）のため plan の action/verify 記載どおり Task 1/2 は feat コミットとした。Task 3 で新規テスト4件を追加し全件 green を確認している。_

## Files Created/Modified
- `pagefolio/dialogs/batch_ocr.py` - ファイル横断統合サマリ（見出し連結・過大警告・手動トリガー）・ファイル別結果閲覧（Combobox+_insert_markdown+ファイル単位エクスポート）・`_on_close` の summary flag 拡張
- `pagefolio/lang.py` - `batch_file_select_label`/`batch_export_btn`/`batch_summary_btn`/`batch_summary_file_header`/`batch_menu_tools`/`batch_menu_item` を ja/en 同時追加
- `pagefolio/ui_builder.py` - `_build_styles` に Treeview 用 ttk.Style（C辞書参照・テーマ追随）を追記
- `pagefolio/app.py` - `_build_menubar`（tk.Menu新設）・`_open_batch_ocr`（BatchOCRDialog独立起動）を追加し `__init__`/`_rebuild_ui` 双方から呼ぶ
- `pagefolio/dialogs/__init__.py` - `BatchOCRDialog` の後方互換 re-export 行を追加
- `tests/test_batch_ocr_dialog.py` - `TestBatchSummary` クラス（4テスト: 見出し連結・zero-completed・過大警告・re-export到達性）を新設

## Decisions Made
- `_format_pages_text` は `entry`（`BatchFileEntry`）を明示引数に取る形で実装した。`OCRDialog` の同名メソッドは `self.page_indices`/`results` を暗黙参照するが、`BatchOCRDialog` は複数ファイルを扱うため単一の等価属性が存在せず、`entry` 引数化が必然的差分（挙動＝「セパレータ付きページ本文連結」は同一）
- `_insert_markdown` は `OCRDialog` と完全に同一シグネチャ（`self.text` を暗黙参照）で実装し、結果閲覧・サマリ表示の両方が同一 `Text` ウィジェットへ描画される設計とした（`OCRDialog` の単一結果ビュー踏襲・実装コスト最小化）
- `provider.supports_text_prompt` が `False` のときのエラーメッセージは `self.app.settings` のプロバイダキーをそのまま使い、`OCRDialog._provider_display_name` のような人間可読名マッピングは複製しなかった（スコープ最小化。エラーゲート構造自体は同一）
- `ui_builder.py` の Treeview 用 `style.configure`/`style.map` は `# fmt: off`/`# fmt: on` + `noqa: E501` で単一物理行に保った。プラン acceptance の literal grep パターン（`style.configure("Treeview"` 等）に一致させるための対応
- メニューバーは `app.py` の `__init__` と `_rebuild_ui` 双方で `_build_menubar()` を呼ぶ設計とした。プラン本文は「`__init__` 相当」としか明記していないが、`_rebuild_ui` は `root.winfo_children()` を全破棄するためテーマ切替時にメニューバーが消失する。これは Rule 2（欠落した重要機能）に該当するため自動的に追加した（手動スモークテストで `_toggle_lang()` 後もメニューバーが再構築されることを確認済み）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `_rebuild_ui` 経路でもメニューバーが再構築されるよう `_build_menubar()` 呼び出しを追加**
- **Found during:** Task 2（メニューバー実装時）
- **Issue:** プラン本文は「`app.py` の `__init__` 相当で」メニューバーを配線すると記載しており、`_rebuild_ui`（テーマ/言語切替時に `root.winfo_children()` を全破棄して `_build_ui()` を再実行する既存経路）での再構築には触れていなかった。`__init__` のみに配線すると、テーマ切替や言語切替のたびにメニューバー自体が消失する
- **Fix:** `_build_menubar()` を `__init__` と `_rebuild_ui` の両方から呼ぶよう実装
- **Files modified:** pagefolio/app.py
- **Verification:** 手動スモークテスト（`TkinterDnD.Tk()` 上で `PDFEditorApp` を生成し `_toggle_lang()` を呼び出し、`_rebuild_ui` 後も `self._menubar` が再生成され `_open_batch_ocr()` が正常動作することを確認）
- **Committed in:** b66e5ca（Task 2 commit）

---

**Total deviations:** 1 auto-fixed（Rule 2・欠落した重要機能の追加）
**Impact on plan:** メニューバーの永続性を担保する必須の追加であり、プランの意図（D-01「独立ダイアログを起動できる」を常時可能にする）を損なわない。No scope creep。

## Issues Encountered
None - ruff/pytest フルスイートとも一発で green（`ruff check .`/`ruff format --check .` 双方クリーン、`pytest` 1014件全通過）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- バッチOCR機能（V180-BATCH-01〜05）がユーザーから到達可能な状態で完成した（Phase 4 全3プラン完了）
- 04-VALIDATION.md の Manual-Only Verifications（メニュー「バッチOCR」の実クリック起動・Treeview/メニューの実配色 dark/light 両テーマ確認・実サマリ出力品質）は `/gsd-verify-work` 実行時の人手確認事項として残存（コード上のブロッカーではない。本SUMMARYの coverage D5〜D7 に human_judgment: true として明記済み）
- ブロッカーなし。フルスイート1014件green・ruffクリーンで Phase 4 検証（`/gsd-verify-work`）へ進行可能

---
*Phase: 04-ocr*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/batch_ocr.py
- FOUND: pagefolio/lang.py
- FOUND: pagefolio/ui_builder.py
- FOUND: pagefolio/app.py
- FOUND: pagefolio/dialogs/__init__.py
- FOUND: tests/test_batch_ocr_dialog.py
- FOUND commit: ba8b234
- FOUND commit: b66e5ca
- FOUND commit: f2a8719
