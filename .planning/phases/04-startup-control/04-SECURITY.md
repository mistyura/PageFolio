---
phase: 04-startup-control
status: verified
threats_open: 0
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-10-22
---

## 2026-11-06 CR-02修正後の境界再結合（現行）

Nyquist後、製品同一性と計画時22脅威の緩和を再確認。正式記録の否認値はv3 validator/正式helperで拒否し、隔離した書込モードでもファイル無変更を28ケースで確認した。対象107件と新単一全件2361件（170入力前後/現行一致）が成功。計画時closed22/open0、ASVS L1を維持する。CR-02の修正を人手受入・実EXE・未解除原因の解決へ転用しない。`04-REVALIDATION-20261106.md` 参照。

## 2026-11-06 試験時序修正後の境界再監査（履歴）

Nyquist後にASVS L1で計画時22脅威の緩和先を現行コード・前回製品hashへ照合した。製品コードは前回v3全件入力から不変。native popupの所有・可視・親無効化を待つ試験修正は所有process内に限定し、manualのNoを代理実行しない。新全件2333 passed、Phase04対象299件全てpass。closed22/open0を継承する。実EXE・別権限/session・未解除原因・極端な過負荷モードは受入済みとしない。正本は `04-REVALIDATION-20261106.md` と `04-reverify-20261106-native-fix/`。

## 2026-11-05 W05c計測後の境界再監査

計画時22脅威の対策は現行製品に残り、`threats_open: 0`（ASVS L1）を維持する。新規観測はmanual native-quitの試験processに限定し、native callbackはメモリ記録と元WndProcへの委譲だけで、製品の所有権/通知/設定/機密境界を変えない。現行167入力に一致するnative全件2293件とW05c故障注入39件を確認。新しい未緩和highは検出しない。正式人手No、実EXE、別権限/sessionと原因不明事項は未解除。証拠は`04-REVALIDATION-W05C-20261105.md`。

## 2026-11-05 現行入力の境界再監査

計画時22脅威closed 22 / open 0、ASVS L1 / block_on highを現行のPhase04製品と試験へ再照合した。変更されたWindows試験はnative通知のAPI/前景監査と合成PDF/OCRの観測を追加するが、本番のnetwork endpoint・auth・schemaは増やさない。禁止API要求・途中の前景化・採取不足を成功へ変換しない判定を維持する。新規全件2254 passed、JUnit failures/errors/skipped 0、前後118入力不変（`04-reverify-20261105-full/`）。新たな未緩和highは検出しない。実入力・実EXE・別権限/sessionと未確定の前景切替原因はPhase06移管のまま。詳細は `04-REVALIDATION-20261105.md`。

# Phase 4 セキュリティ監査

全6 PLANの脅威を現コードで確認した。ASVS L1、high以上の未解決脅威0。SUMMARYの記述だけを閉鎖根拠にしない。再委任せずインラインで監査し、コード変更・コミットは行っていない。04-06後の再監査は既存T-04-01〜17とSCの構造的回帰を確認し、新規T-04-18〜21の実装と名前付き試験を照合した。

## 2026-10-28 品質停止解除後の境界監査（最新）

最新入力に対してASVS L1 / block_on highを評価し、計画時 T-04-01〜21 / T-04-SC の closed 22 / open 0 を維持する。旧118入力と比較して全製品ファイルは同じバイト列であり、従来のidentity/ACL/有限I/O/通知/cleanupの緩和策を再利用できる。今回追加された面は試験限定の `NoticeCallAudit` と既存 `_ForegroundAudit` の接続であり、製品のnetwork endpoint、auth、永続schemaを追加していない。

`tests/startup_foreground_audit.py` は試験子processの `_bind` をcontext中だけ監査し、引数/戻り値/例外/last-errorを保存して終了時に元へ戻す。窓名・入力内容は記録せずPID/生成時刻/HWND/activation指定を採取する。`classify_notice_foreground` は9processの欠落・role重複・API復帰欠落・観測不能・hook解除不成立を成功へ変換しない。禁止APIはOSが要求を拒否してもviolationにする。既存の本番固定名/ユーザー設定隔離を変えていない。新たな未緩和highは検出しなかった。

最新の `.planning/debug/quality-gate-unblock-20261028/full.json` / `full.xml` は2071 passed、exit 0、failed/ERROR/skip 0、前後入力不変。現行Python137/137一致を確認し、故障注入・実OS接続・9processを含め再利用した。元のowner_missingや前景切替要求元の原因確定、Wの人手/別権限/session/EXE受入の完了とは扱わない。詳細な証拠hashと文書4件の差分は `04-GATES-CURRENT-20261028.md` / `.json` に記録した。SECURITY threats-openゲートはpass。

## 2026-10-28 前回入力の追加境界監査（履歴）

計画時の脅威台帳 T-04-01〜21 と T-04-SC を現行ソースへ再照合した。ASVS L1、block_on high、22件中 closed 22 / open 0 を維持する。新たな `UiThreadWake` は OS スレッドメッセージの境界を使うため、計画台帳外の追加面として確認した。`pagefolio/startup_wake.py` は生成元UIスレッドIDへの `PostThreadMessageW(..., WM_NULL, 0, 0)` のみを120ms周期で呼び、owner終了と `close()` で停止する。`pagefolio/__main__.py` はTk初期化後に開始し、root破棄前に停止する。`tests/test_startup_wake.py` と `tests/startup_wake_child.py` は禁止前景API・ctypes迂回・別スレッド宛・別メッセージ・UIスレッドからの投稿を負対照で拒否し、Tcl実待機を3条件で確認する。

証拠入力118ファイルは `.planning/debug/startup-wake-foreground-evidence/full-native-after-state/inputs-before.json` と `inputs-after.json` で前後一致し、ゲート報告編集前の現行SHA256とも118/118一致した。`run.json` は exit 0、`pytest.txt` は2047 passed / 1 warning。報告更新後の差分は `04-VALIDATION.md` のみで、DoD19件を別途実行して合格した。安全境界の正負対照は同入力で実行済みの結果を再利用した。初回失敗時のデスクトップ前景変化の発生原因は未確定であり、今回の修正は試験の偽陽性条件を取り除いたもの。実クリック・実OS拒否・別権限/session・実EXEは承認済みの `06-UAT-CARRYOVER.md` の not-run を維持する。計画台帳に未解決highはなく、追加面に現行コード上の未緩和highは見つからなかった。

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

## Security Audit 2026-10-28

| Metric | Count |
|---|---|
| Threats found | 22 |
| Closed | 22 |
| Open | 0 |

## 2026-11-06 constructor同期修正後の再照合

constructor試験の同期修正を差分照合。直前不合格runからの変更はtests/test_startup_windows.pyと開発履歴だけ。製品/起動/通知/権限/固定namespace/依存/保護原本は不変（constructor-notice-dedup-20261106/fix-input-scope.json）。既存22 closed/open0の判定を再利用。新全件2401件成功。DEP-05、owner_missing、通知前景不一致、WR-01等の未解除事項を本成功で解除しない。


## 2026-11-07 G4採取基盤変更後の差分照合

`04-REVALIDATION-G4-20261107.md` と `../04-startup-control/04-QUALITY-G4-20261107.json` を参照。単一全件2481 passed/2 warnings、174入力と追加12入力不変、Ruff/format/AST成功。変更は採取試験基盤と証拠/文書のみで、製品の実装・表示・版番号・固定EXEは不変。G4レビュー7指摘を解消。既存の静的評価と未解除リスクを維持し、正式人手受入・UI capture・出荷承認へ転用しない。独立verificationは後続で現行fingerprintを照合する。
