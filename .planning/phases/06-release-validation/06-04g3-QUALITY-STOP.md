# 世代3・品質ゲート停止（2026-10-28）

## 現行判定

**2026-10-28追記: 現行入力の品質停止を解除。** 利用者の停止条件解消指示後、診断原本を保存してAST不変の整形を行い、全体Ruff137件、保留中の実OS監査接続/9プロセス各1回、単一全件2071 passed/2 warnings/480.86秒/exit0を確認した。全件は失敗0・ERROR0・skip0、実行前後の入力不変。証拠は `.planning/debug/quality-gate-unblock-20261028/`、判断と残件は `.planning/debug/quality-gate-unblock.md`。下記の初回失敗と47診断原本は保持する。次は06-03のresume_contractに従う現行入力・依存鮮度・台帳の照合。Phase 06の自動完了、未実施人手受入、出荷承認を意味しない。

## 初回停止時の判定（過去の記録）

**Phase 06・OCR接続の人手確認・後続実行・commit・出荷を停止する。**
06-04のexecution_rulesにある「通知前景不一致」の同種再発に該当する。再実行、期限変更、skip、製品修正は行っていない。次は `$gsd-debug continue simultaneous-owner-missing` で保存済み証拠から再開する。元のowner_missing/DEP-05と同じ原因とは断定しない。

## 最新native単一全件

- **1846 passed / 1 failed / 1 warning / 180.20秒 / exit 1**。最初の失敗で停止。
- 失敗: `tests/test_startup_windows.py:784`、`test_notice_dedup_eight_processes_keep_original_deadline`。
- assert: `final["foreground_before"] == final["foreground_after"]`、実測 `396656 != 789312`。
- `06-04g3-quality-fixed/run.json` と `pytest-full.txt` が正本。ログSHA256 `015e8e3a9dc25ea1db7d4668c1ed41e3cdb08d5884e6511c0ec17ef239aa7777`。
- 127入力の前後hashは一致、変更0。manifest SHA256 `635096fee8272cadf1090443a2b76f1483c8dde23b1d6465dce974d2f46287ea`。環境SHA256は先行2047件成功時と同じ `574d41cd3f6e3c4d440e790319db9db2d8a6dd2531ffccd4cea63be8b97a6bcf`。
- 警告は既存PyMuPDF ByteString廃止予告1件。今回の失敗はTcl警告ではない。

## 初回失敗原本の保全

専用basetemp `C:/Users/shdwf/AppData/Local/Temp/pf06-g3-quality-5c082ebe-9c38-467e-b140-e9d6198f2137` を削除・再利用しない。失敗ケースだけを `06-04g3-quality-fixed/failure-notice/` へコピーし、47ファイル・5905 bytesの全SHA256一致を確認した。`failure-notice-manifest.json` に原本path/hashを保持。9 processのresult.json/traceback.log、ready、ownerのforeground-audit.jsonlを含む。今回のcollectorはpoll/reader診断を新規実装しておらず、採取されていない終了経路を後から補完しない。

## 保存された前景観測（因果の確定ではない）

- owner PID16616、通知HWND3738882、表示期限差1800ms、elapsed1859ms。
- 表示前/直後はともにHWND396656、破棄前/直後はともにHWND789312。
- observer開始/表示呼出時: PID18044、`CASCADIA_HOSTING_WINDOW_CLASS`、tick9957250。
- 通知公開: tick9957265。
- 待機中のWinEvent: tick9957843、HWND789312、PID4080、`Chrome_WidgetWin_1`。
- 通知終了/observer解除: tick9959093、解除成功・observer errorなし。

変化は保存された表示直後〜破棄前の間に観測され、前景先は通知窓とは異なる。ただし変更を起こした操作・送信元・製品関与はこの記録だけで断定しない。先行する読込拒否試行への「手動で閉じた／終了した」という回答を、この別時刻の全件失敗の説明へ転用しない。

## 先行成果と残件

- v1.10.1世代3の実初回/再build、build-only監査、自動保護/起動/更新/外部障害成立は個別の生証拠として保持する。品質合格・出荷承認とは別。
- 初回全件のW12b同版copy宣言の更新漏れは修正済み。初回1495 passed/1 failedの原本と、修正後局所10 passedを `06-RESUME-20261028.md` に記録。最新失敗は別症状であり、反復で隠さない。
- preparation-only監査は未合格。接続2条件（ocr-single/w05b-modal）未実施と、旧世代の16 run参照不足を `06-04g3-preparation-pending.json` に保存。参照不足は品質停止後に修正していない。
- 全110受入subrowはnot-run。Phase4の既存passed報告は今回書き換えないが、最新native失敗を無視してリリース依存を合格扱いしない。Phase5の既存完了、未解除DEP-05/owner_missing/WR-01等も保持する。
- 製品・試験・版番号の追加変更とcommitはなし。既存dirty/indexを保持。
