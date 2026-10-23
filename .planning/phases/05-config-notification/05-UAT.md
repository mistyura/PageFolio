---
phase: 05-config-notification
status: complete
source: 05-04-PLAN.md
---

# Phase 5 設定通知の人手受入

自動試験と利用者の目視は別の証拠とする。実施者・時刻・根拠が未記録の行はpendingのままで、今回の自動focus assertをpassへ転用しない。実EXEの最終受入はPhase 6。DEP-05/owner_missing/通知前景不一致の原因は未解決で出荷不可。

## エージェントによる準備・起動

- 開発入口: `05-NOTICE-HARNESS.py read-corrupt|read-unreadable|save-write|save-replace`。エージェントが`.venv/Scripts/pythonw.exe`で起動し、利用者は画面だけを操作する。
- `tests/config_notice_support.py`が実App import/初期化前に設定・2種の外部プロンプト・pluginsの解決先を私有TemporaryDirectoryへ差し替える。実ACL変更なし。実PDFを開かず、メモリ内の1ページPDFを作る。
- 画面は通常のPageFolioと「PageFolio 隔離受入: scenario」の操作パネル。パネルを閉じると隠れる。終了はパネルの「製品の終了操作」を使う。
- 保存/印刷競合の操作パネルボタンは既存ToastManagerへの開発用注入であり、OS印刷や実PDF保存を行わない。既存retry/bound_docの製品経路は自動回帰試験で別途確認する。
- 各終了後、callback/Toast停止→Undo解放→Document close→root destroy→一時領域解放→利用者原本存在/相対パス/SHA256照合を行う。初期化例外時も同じ解放を行う。
- 初回起動の履歴: read-corrupt（2026-10-24 01:00 JST、launcher PID33244 / 実Python PID32632）。通常権限のGet-ProcessでMainWindowTitle=PageFolio、MainWindowHandle=16845424、Responding=True、stderr空を確認。現在の生存状態を示すものではない。これは画面生成の自動確認であり、人手合格ではない。sandboxのGet-Processはhandle=0を返したため、通常権限で照合した。
- 初回Toastの10秒が経過した場合はエージェントがこの隔離harnessを終了・再起動する。利用者にCLIや実利用設定の操作を求めない。H01〜H03の起動直後確認は再起動後の実表示で行う。

## 操作と期待結果

| ID | scenario / 操作 | 目視する期待結果 | 判定 | 実施者・時刻・根拠 |
|---|---|---|---|---|
| H01 | read-corrupt / 起動画面と入力欄 | 破損の文言、既定値での起動案内。入力先を奪わずPDF回転・Undo・Redoを継続できる | pass | 利用者・2026-10-24 JST。チャット回答「約10秒で消え、①〜③も確認済み」。案内文・入力先不変・回転/Undo/Redoを明示確認 |
| H02 | read-unreadable / 起動画面と同値Apply | H01と別の読取不能文言。未保存通知が出て偽の保存成功表示がない | pass | 利用者・2026-10-24 JST。起動PID31392。読取不能の別文言・同値Applyの未保存通知・保存成功表示なしを「4項目とも確認できた」で明示確認 |
| H03 | read-corrupt / 通知を10秒待つ、再起動して✕ | 10秒の可視時間で消去、または✕で一度だけ消化。入力先が変わらない | pass | 利用者・2026-10-24 JST。再確認用起動PID21536、回答「約10秒で消え、①〜③も確認済み」。約10秒消去の経路を確認。✕の別経路は未実施 |
| H04 | save-write / 同値Applyを2回→言語切替 | 各失敗が一つずつ順送り。同時表示は1つ、再構築後は現在言語で残時間分表示 | pass | 利用者・2026-10-24 JST。起動PID31200。2回Apply→言語切替→現在言語の通知を✕で順送りする操作を「3項目とも確認できた」で明示確認 |
| H05 | save-replace / 同値Apply→I/O障害解除→同値Apply | replace失敗を通知。成功操作の偽表示なし。解除後の保存は成功し、未消化の過去失敗は消されない | pass | 利用者・2026-10-24 JST。起動PID9288。「2項目とも確認できた」で失敗通知→障害解除→保存成功・未消化通知保持を明示確認 |
| H06 | save-write / Apply直後に実Settingsを10秒以上開く | モーダル中は通知が隠れ消化されず、閉じると未消化イベントが残時間分見える | pass | 利用者・2026-10-24 JST。Apply直後→実Settingsを10秒以上保持→閉鎖後の通知保持を「3項目とも確認できた」で明示確認。通知開始前の厳密な境界は自動試験の証拠を参照 |
| H07 | save-write / 実Settings→内側LLMを開閉→外側を10秒保持 | 内側を閉じても外側のモーダル保護が続き、外側を閉じるまで通知が消えない | pass | 利用者・2026-10-24 JST。「3項目とも確認できた」で内側LLM開閉→外側10秒保持→閉鎖後の通知保持を明示確認 |
| H08 | save-write / 既存PDF保存Toast注入→同値Apply→成功dismiss | 既存通知を閉じた後に設定失敗を確認できる。設定通知は一度ずつ表示 | pass | 利用者・2026-10-24 JST。「2項目とも確認できた」で既存Toast→Apply→成功dismiss後の設定失敗通知再開を明示確認 |
| H09 | save-replace / 製品終了No→Yes（初回失敗）→No→Yes | 最初のNoは保存しない。初回失敗で編集画面を維持。次のNoも維持。次回Yesは保存を省略して終了 | pass | 利用者・2026-10-24 JST。I/O障害再注入後のNo→Yes→No→Yesの各画面維持/終了を「4段階とも確認できた」で明示確認 |
| H10 | save-replace / 初回終了失敗→障害解除→明示Apply成功→障害再注入→終了Yes | 明示成功で失敗flagが解除され、次の終了失敗では再び画面を維持。続く独立終了Yesは保存省略 | pass | 利用者・2026-10-24 JST。新規起動PID23492。初回失敗→保存成功→再注入後の再失敗→次の独立終了を「4段階とも確認できた」で明示確認 |
| H11 | read-unreadable / I/O障害解除→同値Apply→終了Yes | 同じセッションでは引き続き未保存通知。終了時には追加の保存失敗通知を出さない | pass | 利用者・2026-10-24 JST。障害解除後の同値Apply抑止と終了Yesで追加通知なしを「4項目とも確認できた」で明示確認 |
| H12 | save-write / 実Pluginを変更せずclose/rescan | 無変更操作で保存失敗イベントを増やさない | pass | 利用者・2026-10-24 JST。「2項目とも確認できた」で無変更再検出・閉鎖による新規失敗通知なしを明示確認 |

H09/H10は保存失敗による終了保留を認識できるか、H01/H02/H06は文言と編集継続の人間の認識を判定する。結果は `pass` / `fail` と観測内容で返す。画像だけで入力先や編集継続を推測しない。

## 未確定項目

## レビュー修正後の追加人手受入

| ID | 対象 | 判定 | 実施者・時刻・根拠 |
|---|---|---|---|
| H13 / CR-01 | 保存失敗通知を作りSettings→Shortcutsを開閉し、外側を10秒以上保持した後の通知保持 | pass | 利用者・2026-10-24 JST。修正7bbb06c、起動PID18164。「2項目とも確認できた」で明示確認 |
| H14 / CR-02 | 通知を約4秒表示→最小化10秒以上→復元後に残り約6秒表示 | pass | 利用者・2026-10-24 JST。修正7bbb06c、起動PID18164。「2項目とも確認できた」で明示確認 |

H01〜H12は修正前の結果として保持し、追加2境界だけを上記で補完した。

## 未確定項目の状態

- descriptor-less prohibition 2件は **flagged-unverified**。H01/H02/H06/H07で文言・入力先・編集継続・通知保持の利用者目視は得たが、禁止内容のdescriptorがなく各IDとの対応を確定できない。目視完了だけでresolvedへ変更しない。
- edge-probe 4件（CFG-01〜04）は **unclassified/unresolved**、verification/resolution=null。自動境界試験による読み替えなし。
- Nyquist実走、独立code/secure/goal-backward確認、Phase 6 EXE受入は未実施。

## 実施範囲と終了証拠

H01初回のlauncher PIDは31860。ほかの再起動PIDは上表のとおりで、各原文回答を根拠とする。H03は自然消去の経路を確認し、保存通知の✕はH04で確認した。H06の通知開始前の厳密な境界は自動証拠と区別する。人手用6起動のstdoutはfitz API非推奨の案内のみ、stderrは空で、終了時の原本hash照合結果は出力されていない。全harnessの終了・原本照合完了をこれらのログから推定しない。製品の終了操作を利用者へ案内済みで、残存processを強制終了しない。

## 自動証拠の参照

`05-EVIDENCE.json`と各PLANのSUMMARYに実command/exit/件数/hashを記録する。自動試験は手動欄を更新しない。2026-10-24 JSTの利用者の明示回答に基づきH01〜H12をpassとした。独立レビュー・Nyquist・Phase検証は別の完了ゲートであり、本書だけでPhase 5の正式完了としない。
