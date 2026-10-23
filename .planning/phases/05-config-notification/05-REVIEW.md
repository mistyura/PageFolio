---
phase: 05-config-notification
reviewed: 2026-10-23T17:19:55Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - docs/CONFIGURATION.md
  - pagefolio/app.py
  - pagefolio/dialogs/plugin.py
  - pagefolio/dialogs/settings.py
  - pagefolio/dialogs/shortcuts.py
  - pagefolio/lang.py
  - pagefolio/ocr_dialog.py
  - pagefolio/redact_ops.py
  - pagefolio/settings.py
  - pagefolio/toast.py
  - pagefolio/ui_builder.py
  - pagefolio/viewer.py
  - tests/config_notice_support.py
  - tests/test_config_notification.py
  - tests/test_ocr.py
  - tests/test_pagination.py
  - tests/test_provider_ui.py
  - tests/test_settings_keyguard.py
  - tests/test_startup_windows.py
  - tests/test_toast.py
  - 開発履歴.md
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 5: コードレビュー報告

**レビュー日時:** 2026-10-23T17:19:55Z（2026-10-24 JST）
**深度:** standard
**対象ファイル:** 21
**状態:** clean

## Summary

前回のWR-01を修正コミット `2654882b7dc8abc3c8a78f802e27175845b7c8c8` の8行差分で再確認し、解消と判定した。CR-01/CR-02は前回確認した `7bbb06ce7f409b8ed090eb73d7a812ec9293926f` の製品修正を再利用し、修正後の利用者確認H13/H14も照合した。未解決のコード指摘はなく、BLOCKER・WARNING・INFOはいずれも0件、statusはclean。

指定21ファイルの既読レビュー結果を引き継ぎ、今回の追加確認は `tests/test_config_notification.py` の8行と `05-UAT.md` のH13/H14に限定した。全ソースの再調査や試験の再実行はしていない。構造プリパスと外部レビューレーンの指定はない。前回報告は `05-REVIEW.iter2.md` に保存され、更新前の本書とのSHA256一致を確認した。初回報告は `05-REVIEW.iter1.md` に残る。

## Narrative Findings (AI reviewer)

未解決の指摘なし。今回の修正差分から新しい具体的欠陥は検出しなかった。

## 前回指摘の解決判定

| 元ID | 判定 | 現行ソース・回帰の根拠 |
|---|---|---|
| CR-01（元BLOCKER） | 解消、利用者確認H13 pass | 修正 `7bbb06ce7f409b8ed090eb73d7a812ec9293926f`。`dialogs/settings.py:286-296` は内側Shortcuts自身のDestroyに限定し、生存する外側へgrabを復元する。実save/cancel/wm 3経路、子widget破棄、外側12秒保持、閉鎖後の通知開始は前回のコード・自動回帰確認を再利用した。H13は利用者が2026-10-24 JSTに修正7bbb06cで保存失敗→Settings→Shortcuts開閉→外側10秒以上保持後の通知保持を確認し、「2項目とも確認できた」と明示回答した。 |
| CR-02（元BLOCKER） | 解消、利用者確認H14 pass | 修正 `7bbb06ce7f409b8ed090eb73d7a812ec9293926f`。root Map/Unmap、表示開始・監視・期限時の可視性再検査、非消化中断、同event_idの残時間復帰、旧callback拒否とFIFOは前回のコード・自動回帰確認を再利用した。H14は利用者が2026-10-24 JSTに修正7bbb06cで約4秒表示→10秒以上最小化→復元後に残り約6秒を確認し、「2項目とも確認できた」と明示回答した。 |
| WR-01（元WARNING） | 解消 | 修正 `2654882b7dc8abc3c8a78f802e27175845b7c8c8`。`tests/test_config_notification.py:1514-1529` は通常の `entry.focus_set()` 後に観測し、非Noneの一般widget同一性を `widget_focus_check` へ別記する。`focus_check=verified` は `focused is entry` の場合だけとなり、Noneと非入力widgetはそれぞれ理由付きunverifiedへ分岐する。前景の強制取得は追加されていない。 |

H13/H14の人手根拠は `05-UAT.md` の追加受入表（起動PID18164）。前回報告時の `fixed: requires human verification` はこの利用者確認で充足した。今回の最終差分はテスト記録のみで、7bbb06cの製品実装を変更しない。H01〜H12の12 passは引き続き修正前の証拠として区別する。

## レビューの証拠と限界

- 製品修正時の局所288 passed / 1 warning / 15.35秒、全件1797 passed / 1 warning / 266.50秒、Ruff/format109/ASTと追加8回帰のコード照合は前回結果を再利用した。
- 最終テスト修正後は `05-focus-proof-final/status.json` のexit0と `pytest.txt` の1797 passed / 1 warning / 266.81秒を読み、現行差分に未コミット変更がないことを確認した。Ruff/format109/AST成功、`05-focus-proof-inputs.json` の入力103件と診断423件の現行hash一致は親の提出済み照合結果を参照する。レビュー中の新規試験・GUI実行はなく、これらを自分の再実行結果とは表記しない。
- 人手確認は利用者のH13/H14の観測と明示回答に基づく。レビュー担当自身による独立目視ではない。H01〜H12との実施時点を分け、自動試験から人手合格を推測していない。
- DEP-05/owner_missing/通知前景不一致/Tcl解放警告、descriptor不明の禁止2件、未分類edge4件は未解除。今回のコード判定は出荷承認・Phase正式完了ではなく、同種再発時停止を維持する。既報UI advisoryを新規指摘へ重複計上しない。
- 実装・テスト・共有文書は変更していない。出力は本レビューのみで、commitは行っていない。

---

_Reviewed: 2026-10-23T17:19:55Z_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
