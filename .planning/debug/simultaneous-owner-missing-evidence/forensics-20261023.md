# simultaneous-owner-missing 継続調査

採取日時: 2026-10-23T12:11:30Z。これは既存失敗の読み取り調査であり、新しい再現試験・原因修復の結果ではない。

## 原本と時系列

原本: `C:/Users/shdwf/AppData/Local/Temp/pf_0502_task1_20261023/test_simultaneous_real_process0/`。
通常の読み取りはアクセス拒否となり、承認された昇格読み取りでファイル一覧・CreationTimeUtc・LastWriteTimeUtcを取得した。原本への書き込みなし。

以下は原本のLastWriteTimeUtc。時計の比較には、保存JSONのGetTickCount64由来elapsedも使用した。

| UTC | ファイル / 意味 |
|---|---|
| 11:42:57.5577651 | 一次process_created FILETIMEのUTC変換 |
| 11:42:58.1475405 | simultaneous-0/initializing.json |
| 11:43:01.1820202 | simultaneous-0/ready |
| 11:43:01.3084772 | simultaneous-1/result.json（completed / elapsed=3172） |
| 11:43:01.4120710 | entry-module/expected-owner.json（fresh二次のfixture準備） |
| 11:43:01.4979578 | simultaneous-0/pagefolio_settings.json（終了時の設定保存） |
| 11:43:01.5809493 | simultaneous-0/resource-audit.json と result.json（primary / elapsed=3438） |
| 11:43:01.7927310 | entry-module/traceback.log（bootstrap開始） |
| 11:43:01.8658718 | entry-module/resource-audit.json（owner_missing） |

結論: 一次の終了はfresh fixture準備より後、fresh Python bootstrapより前である。「fresh起動前に一次が消えた」という表現は曖昧であり、freshの所有権確認前に一次が終了した、と限定する。fixture準備から一次resultまでは約169ms、readyから一次resultまでは約399ms。`_save_window_state`の製品内呼出元は`_quit`だけであり、保存済みwindow_geometry/edit_mode/sashはこの経路を支持するが、呼出元のstackは初回に未採取だった。

失敗ディレクトリには`stop`/`stop-all`が無い。成功した後続[8]のstop-allは別の`test_simultaneous_real_process1/`に11:43:07.4725707Z、[slow]は`test_simultaneous_real_process2/`に11:43:20.0662740Zで作成されている。fixture.parentはそれぞれ別であり、後続ケースの通常停止が失敗ケースを止めたという順序・パスの説明は成立しない。外部による一時的なファイル作成・削除は当時の監査なしに否定できない。

## 仮説の切り分け

1. 時刻変更によりTk after(10000)が早発火した: process_createdから得た11:42:57.5577651Zの前後5分でSystemログを検索し、一致イベント0件。Systemログは有効・読み取り可能（45314件）。Kernel-General Id=1の直近記録は2026-10-22で、失敗日の時計変更を支持する記録は無い。Tcl内部タイマーの異常まで否定する結果ではない。
2. 復帰要求自身が一次を閉じた: `startup_win32.py:1025`以降と`startup_focus.py:restore`を読み取り、復帰処理はHWND検証・ShowWindow(SW_RESTORE)・SetForegroundWindow・focus_set・flashのみ。root.destroy/_quit/WM_CLOSE送信を呼ぶ経路は無い。既存restored=1/completedの結果とも整合する。OSから届く別のGUIイベントはこの静的調査の対象外。
3. 他ケースのstop-all/前回ファイルの通常再利用: 上記原本メタデータと`tests/test_startup_windows.py:775`以降を照合。各ケースのfixtureは分離され、fixture.mkdirは既存ディレクトリを無条件再利用しない。同一テストのstop-allはfresh成功のassert後のみ作成され、削除経路も無い。通常のテスト制御による早期停止は支持されない。

## 残る観測の不足

- 初回の`_quit`呼出stackが無いため、WM_DELETE_WINDOW/終了ボタンのイベントと異常なwatchdog発火を遡って区別できない。利用者の手動終了は既に否定済みで、再質問しない。
- 現行exit-auditはstop_poll・watchdogのcallit・Tk command経由を区別できる。Tk commandの場合、WMプロトコルかボタンかは現在のstackだけでは区別できず、必要なら各入口に別event名を付ける追加診断が次の有意味な変更候補になる。
- 別processのTk interpreter警告は今回一次を直接閉じる説明にはならない。タイマーやGUI入力に関する新証拠なしに因果を断定しない。

## 変更・検証

製品コード・テスト・依存・期限・guardの変更なし。pytest/Ruffの追加実行なし（同条件の反復を避けた）。既存コードhashは初回/直前記録と一致:

| ファイル | SHA256 |
|---|---|
| tests/test_startup_windows.py | DC34E678D69EEA86EE53E9399BB3EEC57AC5C3EB08C8ED36998A74A4CDE8ECB4 |
| pagefolio/app.py | 28F73F4CD1F50A9135EDC9071CCF595EF52C25D0AA79F379F784DF508926877D |
| pagefolio/settings.py | 7B6BB2ED3AF80F010DC27F60491BCE24B1B22B2085C759EE54ECBB9448621CB1 |
| tests/test_config_notification.py | 0788CBF8F47AC7499F28223971B09836339A6F14612894476ECA9B7AC6536746 |
| tests/test_settings_keyguard.py | 5A7A88D6DA0D411D6039A9A11D3CF0E13607F63E6ABA19259B54C776FE5B0782 |

Phase 5停止・DEP-05未解除・未コミットを維持する。原因未確定のためresolvedへ移動しない。
