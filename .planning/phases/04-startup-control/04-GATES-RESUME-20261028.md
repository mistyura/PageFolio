# Phase 04 検証ゲート再開の追補証拠（2026-10-28）

## 対象と入力同一性

- 対象: v1.10.0 マイルストーン最初のPhase 04、6 PLAN / 6 SUMMARY、13タスク、5要件。製品コード・試験・過去の失敗原本は今回変更しない。
- 成功済み単一native全件: `.planning/debug/startup-wake-foreground-evidence/full-native-after-state/run.json`（SHA256 `d8ed68275d9d6e259c5b38ee0f3df6110c9c36f34960e10588f1c6c20024370b`）、`pytest.txt`（SHA256 `b66139731b42ca2ce2a47432ece06a1170c6bde80b8018bf661b68da7acada55`）。`run.json` は exit 0 / timeout false / inputs_unchanged true。`pytest.txt` は **2047 passed / 1 warning / 427.01秒**。警告はPyMuPDFの既存 `ByteString` 廃止予告。
- `inputs-before.json` と `inputs-after.json` はどちらもSHA256 `2b6844acd19961efb6e052b2318b2406b248c84d4389945fa595cd38f83e22bb`、118ファイルのhash mapが一致。ゲート報告を編集する前に各118ファイルの現行SHA256を再計算し、**118/118一致、変更0、欠落0**。その後、今回のNyquist判定に伴って `04-VALIDATION.md` を更新したため、更新後は117/118一致で差分は同報告1ファイルのみ。製品・試験・設定のbytesは変えていない。
- 本監査中に全件試験とwake対象試験は再実行していない。報告更新後はDoDがVALIDATION状態を読むため `tests/test_gsd_dod.py` のみ専用basetempで実行し、**19 passed / 2 warnings / 0.42秒、exit 0**。生ログは `04-gate-dod-20261028.txt`（SHA256 `6e6bf66ebb7bce1212d02cd9b4afb33ebacf333e498ee953d3879a418ea20cea`）。警告は既存PyMuPDFと、並行作業中にpytest共有cacheへ書けなかった通知。必須試験は成功し再走していない。一時basetempは本試験で作成した専用領域だけを削除した。
- 原本の失敗は `04-reverify-20261028/native/{run.json,pytest-full.txt,inputs-before.json,inputs-after.json}` に保持。初回 `foreground_unchanged=False` の発生原因は採取不足で未確定。試験判定の偽陽性は `.planning/debug/resolved/startup-wake-foreground.md` の正負対照で確認済み。

## ゲート結果

| 順番 | ゲート | 判定 | 現行根拠と未実施部分 |
|---|---|---|---|
| 1 | Nyquist（`verify:post`、失敗時halt） | pass | `04-VALIDATION.md` を `status: validated` / `nyquist_compliant: true` に更新。6 PLAN/6 SUMMARYの13タスクと5要件を既存試験へ照合、自動ギャップ0。新wakeの正負対照・実Tcl3条件は同入力全件に含まれる。人手W・実EXEは除外。 |
| 2 | Security（`verify:post`、失敗時halt） | pass | `04-SECURITY.md` の計画時22脅威はclosed 22/open 0、ASVS L1/block_on high。追加のWin32スレッドメッセージ境界を実装と負対照で監査。実OS入力・別権限/session受入はPhase06へ移管済み。 |
| 3 | UI（`verify:post`、失敗時skip） | partial | `04-UI-REVIEW.md` の抽象6柱を現行コードで再監査。wakeはUI描画を変えない。実表示・DPI・クリックのvisual captureはnot-run、scoreは付与しない。承認済み `06-UAT-CARRYOVER.md` へ維持。 |
| 4 | Code Review（`execute:post`、advisory） | issues_found | `04-REVIEW.md` を既存14ファイル＋新wake3ファイルの17ファイルへ拡張し、現行Critical 0/Warning 1。追加のCritical/Warningは検出せず。 |
| 5 | Disposition（advisory） | open 0/total 2 | `04-REVIEW-DISPOSITION.md`: 既存CR-01は04-06修正のためfixed、現行レビューには含めない。WR-01はdeferredを維持し、W07bの15609msと単独15140msをPhase06で再評価する。 |
| 6 | Regression | 対象なし | 現行マイルストーンはROADMAPの「v1.10.0 多重起動防止・起動操作の改善」Phases 4–6。Phase04が最初でprior phaseのVERIFICATIONは存在しない。既存05-VERIFICATIONは後続Phase05であり、priorとして実行しない。 |

`loop render-hooks verify:post` は Nyquist→Security→UI の順でactive（onError halt/halt/skip）、`execute:post` はCode Review active（onError skip）と確認した。TDDフックは該当なし。gap-closure manifest対象外、Regression manifestは有効だが最初のphaseのため対象なし。

## 監査範囲と残る制約

現行ソースの `pagefolio/__main__.py` はTk初期化後に `UiThreadWake` を開始し、root破棄前にcloseする。`pagefolio/startup_win32.py` は `PostThreadMessageW` をbindし、`pagefolio/startup_wake.py` は生成元threadへの `WM_NULL` だけを120ms周期で投稿する。`tests/test_startup_wake.py` / `tests/startup_wake_child.py` は禁止前景API・ctypes迂回・別宛先・別種別・owner呼出を拒否する正負対照と、Tcl待機の回復・終了を確認する。今回の読解・`git diff --check`・禁止パターン検索で新たな欠陥は検出していない。

DEP-05、owner_missing、WR-01、未分類edge、禁止事項の未確認、Phase06のW人手受入・実EXEは解除しない。UIは部分判定のままで、Phase04の最終 `04-VERIFICATION.md`、STATE、ROADMAP、requirements、`phase.complete` は親担当の独立検証後に判断する。今回の変更は上記5つのゲート報告と本追補だけで、コミットは行わない。
