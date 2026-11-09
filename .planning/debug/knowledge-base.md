# GSD Debug Knowledge Base

解決済みデバッグの知見。類似症状の調査で仮説と再発防止策を参照する。

---

## w02-preview-peer-expired — Tclのイベント待機停止で二次起動が期限切れになる

- **Date:** 2026-10-28
- **Error patterns:** W02/preview@module, os_error=233, connection_failed, expired, accepted後に5秒期限切れ, Alt+Tab, after停止, NtUserGetMessage, CPU/ctx増分0
- **Root cause(s):** Tk/Tclの通知器がタイムアウトのないGetMessageで待ち続け、afterによる起動要求処理が停止する機構を観測・人工再現。TclNotifier窓のない状態ではWM_TIMERによる回復も働かない。Alt+Tab直後に自然発生するきっかけは未特定であり、IME等が原因と確定したわけではない。
- **Fix:** 一次プロセスのTk初期化後にUiThreadWakeを開始し、生成元UIスレッドへ120ms周期でWM_NULLを投稿する。root破棄前に停止・回収し、補助スレッドはTk APIや入力/前面化APIを使わない。5秒期限は維持。ソース版v1.10.1で利用者確認済み。
- **Files changed:** pagefolio/startup_wake.py, pagefolio/__main__.py, pagefolio/startup_win32.py, tests/test_startup_wake.py, tests/startup_wake_child.py（ほか版同期・文書。詳細はresolved/w02-preview-peer-expired.md）
- **Why not caught:** 仮想時計の期限処理テストは停止後の期限切れを検証するが、Windows通知器のメッセージ消失からの回復を検証するゲートがなかった。
- **Recurrence guard:** tests/test_startup_wake.py:test_native_tcl_getmessage_stall_recovers_with_product_wakeで人工停止の対照群と製品見張りの回復を比較。test_entry_stops_wake_before_root_destructionで正常/異常終了の回収順を検証。投稿1か所を無効化した隔離コピーでは800.86ms停止し、実製品では122.73msで回復。全件2036件成功・通常操作の利用者確認済み。
- **Scope:** 本デバッグの解決確認。Phase 06正式受入・元のW02失敗証拠の変更・EXE再生成・出荷承認は別。追加の30回再走は要求しない。

---
