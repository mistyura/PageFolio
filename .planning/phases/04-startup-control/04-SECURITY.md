---
phase: 04-startup-control
status: verified
threats_open: 0
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-10-22
---

# Phase 4 セキュリティ監査

全6 PLANの脅威を現コードで確認した。ASVS L1、high以上の未解決脅威0。SUMMARYの記述だけを閉鎖根拠にしない。再委任せずインラインで監査し、コード変更・コミットは行っていない。04-06後の再監査は既存T-04-01〜17とSCの構造的回帰を確認し、新規T-04-18〜21の実装と名前付き試験を照合した。

## Trust Boundaries

| 境界 | データと制御 |
|---|---|
| 別プロセス→所有者 | PID/生成時刻/session/logon SID、世代、期限付きactivate要求 |
| native worker→Tk | 最大32件queue、メインスレッドだけがUIを操作 |
| OS→native通知 | HWND、WndProc、timer、通知所有権snapshot |
| 試験→利用者環境 | 子ごとの一時設定/plugins/プロンプト、所有PID限定回収 |

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|---|---|---|---|---|---|---|
| T-04-01 | Spoofing | peer | high | mitigate | startup_win32.py:469 PID生成時刻/SID/session、生存handle。:773 client PID、:860 server PID照合 | closed |
| T-04-02 | Tampering | ACL | high | mitigate | :201 logon SID/SYSTEM限定DACL＋medium label、:225既存ACL検証、:735 remote拒否。A4両順4資源実測 | closed |
| T-04-03 | Denial of Service | pipe/固定名 | high | mitigate | :398 frame最大1024、:723 listener8、PendingIO32スロットと取消し完了/quarantine、固定名先取り失敗閉鎖 | closed |
| T-04-04 | Tampering | DoD | medium | mitigate | test_gsd_dod.py:149 現行section/名称/件数/日付/SUMMARY照合、:234 archive維持 | closed |
| T-04-05 | Tampering | 要求 | high | mitigate | startup_control.py:146 型/ID/世代/期限、:109/:219副作用直前再確認 | closed |
| T-04-06 | Denial of Service | queue/ACK | high | mitigate | control:52 queue32、:120 cache128、win32:819単一期限、:287/:307有界I/O取消し | closed |
| T-04-07 | Elevation of Privilege | takeover | high | mitigate | control:78 初期化中かつ確認済み死亡のみ1回、win32:591原子的mutex取得・旧identity照合 | closed |
| T-04-08 | Repudiation | ACK | medium | mitigate | control:116 request_id/result/tick、win32:927 acceptedとterminalを検査 | closed |
| T-04-09 | Spoofing | HWND | high | mitigate | startup_focus.py:180以降 root/target/popup/generation再確認、win32:970/:991同一PID/thread | closed |
| T-04-10 | Tampering | 作業状態 | high | mitigate | focus.restoreはwindow/focusのみ。doc/履歴/OCRを書換えない。実PDF履歴/BlobとOCR worker継続試験 | closed |
| T-04-11 | Denial of Service | flash | medium | mitigate | win32:1167 3回/250ms、focus._schedule_stop 1000ms、再前面化callbackなし | closed |
| T-04-12 | Elevation of Privilege | focus | medium | mitigate | focus.restoreのcompleted後のみfocus_set、native modalを保持、強制入力取得APIなし | closed |
| T-04-13 | Information Disclosure | 通知 | medium | mitigate | startup_notice.py:43固定i18n、:85例外本文を出さずreason/os_errorのみ | closed |
| T-04-14 | Denial of Service | NoticeLease | high | mitigate | win32:1181以降原因別mutex/snapshot、:1306期限更新拒否、:1360 0待機、native loop固定10秒 | closed |
| T-04-15 | Tampering | 通知focus | medium | mitigate | win32:1609 WM_MOUSEACTIVATE→MA_NOACTIVATE、CreateWindowExW NOACTIVATE/TOOLWINDOW、SW_SHOWNOACTIVATE | closed |
| T-04-16 | Tampering | harness | high | mitigate | test_startup_windows.py:44原本hash、:59子bootstrap/一時plugins、:110所有Popenのみkill、固定名owner guard | closed |
| T-04-17 | Repudiation | 証拠 | medium | mitigate | EVIDENCEの自動/実測/not-runを分離。VALIDATION実走204件と親の全件1603件結果、Phase6移管正本 | closed |
| T-04-18 | Information Disclosure | backend初期化/案内/診断 | high | mitigate | __main__.py:26-41で構築OSError本文を通知へ渡さず、startup_notice.py:62-74はreasonと数値OS errorのみ記録。固定LANG文言と機密marker試験を確認 | closed |
| T-04-19 | Denial of Service | constructor/部分資源解放 | high | mitigate | startup_win32.py:429-476で取得直後にdescriptor登録・逆順解放、:537-568でpipe_security失敗時にも共通資源を解放、:1176-1225で独立cleanupを継続。token/_Securityの部分取得試験と正常再起動subprocessを確認 | closed |
| T-04-20 | Spoofing | 独立通知とNoticeLease | high | mitigate | Win32NoticeBackendとWin32Backendは同一prefix/SID/LUID/ACLおよびNoticeLeaseを共有。tests/test_startup_windows.py:326-354の旧新8process両順集約、既存ACL/peerの負例を確認 | closed |
| T-04-21 | Tampering | native通知とforeground | medium | mitigate | NativeNoticeLifetimeのNOACTIVATE/MA_NOACTIVATE、表示・手動閉鎖前後のforeground HWND同一性をtests/test_startup_windows.py:280-309で検証 | closed |
| T-04-SC | Tampering | 依存 | high | mitigate | 追加依存・install・pyproject変更なし。標準ctypes実装 | closed |

## Accepted Risks Log

highの受容による閉鎖はない。OS前面化は許可される場合だけ実施する。悪意ある同一logonの資源占有を正常復帰として保証しない。

新NoticeLeaseの権限差/DPI/実入力再受入、別session、実EXEは未実施。2026-10-22承認により06-UAT-CARRYOVERへ移管済み。L1の実装緩和策を確認したことと、最終実機受入passを区別する。constructor中の解放操作そのものがOSで拒否された場合は取得済み他資源の解放を続け、当該processの有限終了で残資源をOSへ返す。LocalFree失敗時の即時再利用は保証しない。

## Security Audit

| Metric | Count |
|---|---|
| Threats found | 22 |
| Closed | 22 |
| Open | 0 |

**Approval:** verified 2026-10-22。リリース承認はPhase6の全必須人手受入まで保留。

04-06後の独立再監査: `tests/test_startup_notice.py` と `tests/test_startup_windows.py` のconstructor/初期化/期限の25件が実走で合格（9.75秒、対象skipなし）。独立通知factory、数値だけの診断、通知不能結果、共通lease名、手動/自動closeと再起動の実コードを照合した。ASVS L1/block_on highで未解決highは0。再委任制約により同一担当がsecure-phase手順をインライン実施した。
