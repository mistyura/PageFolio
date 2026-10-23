---
phase: 05-config-notification
plan: "02"
subsystem: configuration
tags: [settings, tkinter, toast, pytest]
requires:
  - phase: 05-01
    provides: 設定読込分類とApp所有の通知キュー
provides:
  - 原子的設定保存のbool契約と保存失敗時の原本・メモリ保護
  - 終了確認先行と初回保存失敗時の終了保留
  - FIFO通知の残時間・世代管理と再構築・モーダル・カテゴリ競合からの復帰
affects: [05-03, 05-04, 06-release-validation]
actuals:
  tokens: 9378
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [App所有FIFOと可視時間, 世代付きToast終了callback, 100ms grab監視]
key-files:
  created: []
  modified:
    - pagefolio/settings.py
    - pagefolio/app.py
    - pagefolio/toast.py
    - pagefolio/ui_builder.py
    - tests/test_config_notification.py
    - tests/test_settings_keyguard.py
    - tests/test_toast.py
key-decisions:
  - 承認済みTask 1の実装をSHA256照合して再利用し同一入力の全件を反復しない
  - 通知はuser/expiredだけ消化しreplaced/rebuild/modalでは残時間を保持する
  - 未解決の起動問題と手動UATは実装完了から分離し出荷停止を維持する
requirements-completed: []
requirements-addressed: [V110-CFG-02, V110-CFG-03, V110-CFG-04]
commits: 2
plan_head_before: be1eb1975ac59d7dfbe9620e5cd7e83a73f83f09
plan_head_after: 838c4b087770dbf687068a95cdd8275d4f25af45
duration: 27min
completed: 2026-10-23
status: complete
---

# Phase 05 Plan 02: 設定保存失敗と通知寿命の保護 Summary

設定保存失敗を原本・メモリ保持付きで通知し、未消化イベントを再構築・モーダル・PDF保存/印刷Toastの割込み後も残り時間で再開する。

## Accomplishments

- `_save_settings`は排他的tmp作成・close後replaceの成功だけTrue。失敗時は原本を維持して自身が作成したtmpだけ削除し、機密値を保存コピー・ログから除く。
- `_persist_settings`で一般設定Applyの結果を通知へ接続。unreadableはセッション中I/Oを抑止、corruptは明示成功だけ保護解除、保存失敗でもメモリ反映を保持する。
- 終了確認Noは保存しない。初回終了保存失敗は編集・Document・Undo・rootを維持し、次の独立終了は保存を省略する。
- 各失敗は別event_idのFIFOとなり、表示中の時間だけ10秒から差し引く。再構築時は現在言語へ更新し、ネストしたgrab中は表示・消化を停止する。
- Toastは旧frame/timer/on_closeを片付けてから終了通知し、idleで次を開始。古いtimer/callbackは世代で無効化する。既存retry更新・ボタン順序・PDF/印刷の成功dismissを維持する。

## Task Commits

1. **Task 1: 05-02-01 一般設定保存と終了保護** — `ef5124c834691cdfd6ab0bb46960a27bf768aa06`
2. **Task 2: 05-02-02 未消化通知と寿命の保護** — `838c4b087770dbf687068a95cdd8275d4f25af45`

実装7ファイル。台帳基点から実測2コミット。`evaluation-scope`は同番号の過去マイルストーンまで返すため、実測には保存済み台帳と上記HEAD境界を使用した。

## Verification

- **Task 1:** 先行4ファイルと`tests/test_startup_windows.py`のSHA256が条件付き再開承認時と一致。`debug/simultaneous-owner-missing-evidence/resume-check-20261023.md`および`resume-final-20261023/status.json`の対象9件×3回・全件1680 passed / 1 warning / 254.81秒 / exit 0を再利用した。診断tracerの未コミット変更は今回の製品コミットに含めていない。
- **Task 2 局所:** `pytest tests/test_config_notification.py tests/test_toast.py tests/test_settings_keyguard.py -x -q --tb=short --basetemp=...pf_0502_task2_targeted_confirmed`は **104 passed / 1 warning / 4.29秒 / exit 0**。
- **Task 2 全件:** `pytest -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_0502_task2_full`は **1694 passed / 1 warning / 264.76秒 / exit 0**。除外・skip・期限延長なし。`-x`は最初の失敗で停止するためで、今回は全件実行した。警告は既存のPyMuPDF ByteString非推奨。
- 純状態試験はfake clock/afterで9999/10000ms、4秒後割込み/再構築、残り6秒、連続失敗、期限とgrab同時、ネストgrab、旧callback、閉鎖時取消を検証した。
- 実Tk試験はretry有無・順序、frame/timer破棄順、非同期idle、期限、実Appの再構築と言語更新、入力先不変、既存保存/印刷retryを検証した。手動の視覚UATとは区別する。
- 全体`ruff check .`→Python対象`ruff format . --config "include = ['*.py', '*.pyi', '*.ipynb']"`（103 unchanged）→check→AST→`git diff --check`は親が通常環境でexit 0を確認。同一コードのため再利用した。
- 非表示`pythonw`と`Start-Process -WindowStyle Hidden`で既存runnerの前景安定確認・CREATE_NO_WINDOW・証拠保存を再利用。`05-02-task2-full/status.json`に実行コマンドとexit 0。診断423ファイルはコピー時と完了後に原本・コピー・manifestのSHA256一致を確認した。

## TDD Notes

- Task 1の先行RED/GREENはCHECKPOINTの証拠を引き継ぎ、再実装しなかった。
- Task 2の`test_interruption_preserves_remaining_time[save_file]`は予定どおり`10000 == 6000`で失敗。`05-02-task2-red.xml`と`05-02-task2-red.json`に実出力を保持し、`check tdd-red-evidence`で`RED_EVIDENCE_OK`を確認してから製品実装した。fixture/collection障害ではない。
- 初回のRED記録はPowerShellのBOM/拡張string metadataで判定器が拒否した。元JUnitを改変せずUTF-8文字列として記録し直して判定を通した。RED単独コミットはAGENTS.mdのコミット前pytest成功条件に従い作成していない。
- 実装後の局所試験で、終了処理のfake rootにafter_cancelが不足していたためfixtureを補完した。追加の実再構築試験は普通のtk.Tkにtkdnd commandがないため1 failed/8 passedとなり、製品と同じTkinterDnD.Tkへ変更して104 passedを確認した。失敗ログを保持している。

## Deviations from Plan

- **[Rule 3 - Blocking] 検証環境:** sandboxの前景はHWND=nullで開始前停止。通常環境でもTerminal前景が続いたケースは30秒で開始前停止し、反復せず利用者の切替を待った。非console前景を確認後だけ試験を開始した。各preflight/statusを保持する。
- **[Rule 3 - Blocking] 既存証拠の走査権限:** `pf_owner_missing_entry_audit_20261023`のアクセス拒否で全体formatがexit 2。親が旧ACLを`05-02-evidence-acl-before.json`へ保存し、読取/走査権限だけ補った。内容18ファイルのSHA256不変を確認して静的検証成功。証拠削除・pyproject編集・除外による回避はしていない。
- 版番号・README・開発履歴の同期は承認済みPROJECT/CONTEXTどおりPhase 6担当。既存の開発履歴/requirements/debug差分は変更していない。

## Remaining Work

- owner_missing・通知前景不一致・DEP-05は未解決。今回成功は原因修復ではなく、再発時は実装・後続実行・commitを停止し初回証拠を保持する。
- 05-03の全保存元統合と05-04の複合受入は未着手。`requirements.ready-ids`はV110-CFG-02/03/04を全てblockedと返したため、要件完了を先取りしない。
- Phase 6へ移管したWindows EXE/手動UATはnot-runのまま。出荷不可を維持する。
- 製品スタブ・新しい未対処の信頼境界は検出しなかった。

## Self-Check: PASSED

変更7ファイル、検証ログ、RED証拠、診断manifestの存在を確認。両実装commitはHEAD祖先で、台帳からの実測2コミットと一致。全件成功後のソース変更なし。
