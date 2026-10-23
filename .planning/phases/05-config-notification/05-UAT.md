---
phase: 05-config-notification
status: pending
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
- 起動状態: **未起動**。最終ゲート成功後にエージェントが起動する。ここは起動実測後だけ更新する。

## 操作と期待結果

| ID | scenario / 操作 | 目視する期待結果 | 判定 | 実施者・時刻・根拠 |
|---|---|---|---|---|
| H01 | read-corrupt / 起動画面と入力欄 | 破損の文言、既定値での起動案内。入力先を奪わずPDF回転・Undo・Redoを継続できる | pending | 未実施 |
| H02 | read-unreadable / 起動画面と同値Apply | H01と別の読取不能文言。未保存通知が出て偽の保存成功表示がない | pending | 未実施 |
| H03 | read-corrupt / 通知を10秒待つ、再起動して✕ | 10秒の可視時間で消去、または✕で一度だけ消化。入力先が変わらない | pending | 未実施 |
| H04 | save-write / 同値Applyを2回→言語切替 | 各失敗が一つずつ順送り。同時表示は1つ、再構築後は現在言語で残時間分表示 | pending | 未実施 |
| H05 | save-replace / 同値Apply→I/O障害解除→同値Apply | replace失敗を通知。成功操作の偽表示なし。解除後の保存は成功し、未消化の過去失敗は消されない | pending | 未実施 |
| H06 | save-writeまたはsave-replace / 通知前と表示途中に実Settingsを10秒以上開く | モーダル中は通知が隠れ消化されず、閉じると未消化イベントが残時間分見える | pending | 未実施 |
| H07 | save-write / 実Settings→内側LLMを開閉→外側を10秒保持 | 内側を閉じても外側のモーダル保護が続き、外側を閉じるまで通知が消えない | pending | 未実施 |
| H08 | save-write / 既存PDF保存Toast注入→同値Apply→成功dismiss | 既存通知を閉じた後に設定失敗を確認できる。設定通知は一度ずつ表示 | pending | 未実施 |
| H09 | save-replace / 製品終了No→Yes（初回失敗）→No→Yes | 最初のNoは保存しない。初回失敗で編集画面を維持。次のNoも維持。次回Yesは保存を省略して終了 | pending | 未実施 |
| H10 | save-replace / 初回終了失敗→障害解除→明示Apply成功→障害再注入→終了Yes | 明示成功で失敗flagが解除され、次の終了失敗では再び画面を維持。続く独立終了Yesは保存省略 | pending | 未実施 |
| H11 | read-unreadable / I/O障害解除→同値Apply→終了Yes | 同じセッションでは引き続き未保存通知。終了時には追加の保存失敗通知を出さない | pending | 未実施 |
| H12 | 任意scenario / 実Pluginを変更せずclose/rescan | 無変更操作で保存失敗イベントを増やさない | pending | 未実施 |

H09/H10は保存失敗による終了保留を認識できるか、H01/H02/H06は文言と編集継続の人間の認識を判定する。結果は `pass` / `fail` と観測内容で返す。画像だけで入力先や編集継続を推測しない。

## 未確定項目

- descriptor-less prohibition 2件は **flagged-unverified**。利用者が文言と編集継続を目視するまで解除しない。
- edge-probe 4件（CFG-01〜04）は **unclassified/unresolved**、verification/resolution=null。自動境界試験による読み替えなし。
- Nyquist実走、独立code/secure/goal-backward確認、Phase 6 EXE受入は未実施。

## 自動証拠の参照

`05-EVIDENCE.json`と各PLANのSUMMARYに実command/exit/件数/hashを記録する。自動試験は手動欄を更新しない。目視未実施のため、本書の存在だけでPhase 5の正式完了としない。
