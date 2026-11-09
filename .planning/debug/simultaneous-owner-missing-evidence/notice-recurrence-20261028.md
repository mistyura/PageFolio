# 通知前景不一致の原本調査（2026-10-28）

## 判定と調査範囲

**未解決。通知待機中の前景先を VS Code のプロセスへ絞り込んだが、切り替えを起こした主体・操作・製品関与は未確定。** 元の owner_missing / DEP-05 との因果も未確定で、解決・品質合格・実装再開とは扱わない。

`$gsd-debug continue simultaneous-owner-missing` による保存証拠・限定的コードの調査。最初に原本を読み取り、その後に親が範囲を確認して外付け診断ラッパーによる対象1件の追加診断を1回だけ実施した（後述）。製品・既存試験コード、期限、assertは未変更。原本を削除・再利用せず、全件再実行・commit・出荷もしない。停止根拠は `06-04-PLAN.md:69` の「通知前景不一致…の同種再発では実装・後続・commitを停止」と `06-04g3-QUALITY-STOP.md:5`。接続人手確認・Phase 06 後続も停止を維持する。

以下の `quality/` は `.planning/phases/06-release-validation/06-04g3-quality-fixed/`、`failure/` はその `failure-notice/` を指す。

## 原本・入力の照合

- `quality/failure-notice-manifest.json` に列挙された **47ファイル・5905 bytes** を、元 basetemp と保存コピーの両方でSHA256再計算。全47件が manifest と一致し、両ディレクトリの実ファイル数も47。原本の読み取りは sandbox で拒否されたため、承認された読み取り専用コマンドを昇格実行した。内容の読み替え・上書きなし。
- `quality/inputs-before.json` と `inputs-after.json` はともに127入力、ファイル自体のSHA256も `635096fee8272cadf1090443a2b76f1483c8dde23b1d6465dce974d2f46287ea` で一致。
- pytestログSHA256は `015e8e3a9dc25ea1db7d4668c1ed41e3cdb08d5884e6511c0ec17ef239aa7777`、環境ログは `574d41cd3f6e3c4d440e790319db9db2d8a6dd2531ffccd4cea63be8b97a6bcf`。いずれも `run.json` の記録と再計算値が一致。
- 調査開始時の作業ツリーを当時の127入力と比較すると122件一致、差分は `.planning/ROADMAP.md`、`.planning/STATE.md`、`06-BUILD-EVIDENCE.json`、`06-UAT-PREPARATION.md`、`開発履歴.md` の既存5文書。試験中の入力不変と、試験後の文書更新を混同しない。既存差分を戻していない。

| 今回参照したコード | 現行SHA256（当時入力と一致） |
|---|---|
| `tests/test_startup_windows.py` | `4daf99286bae31a6f601f30439bda9458b1939f2947bbc2672ad30432675daa0` |
| `pagefolio/startup_win32.py` | `948abe06b494e6907bdec5e2169931e9780eb6dfa23271c5a16e6134546cddae` |
| `pagefolio/startup_notice.py` | `473c8ea1723a350cc445bcef8649c75bd228ec3e37bea12d81ca5a166a4c0c40` |
| `pagefolio/__main__.py` | `efdbc32b2322ee20525fbb9ce5164622109fbacecfd37c36fc41166bfa0e1e06` |

## 今回の時系列

正本は `failure/notice-case-owner/foreground-audit.jsonl:1`（6行）、同 `result.json:1`、同 `ready:1`。

| 観測 | tick | HWND / PID | 読み取れる事実 |
|---|---:|---|---|
| observer開始・表示呼出し | 9957250 | 396656 / 18044 | `CASCADIA_HOSTING_WINDOW_CLASS` |
| 通知公開 | 9957265 | 3738882 / 16616 | 通知窓のidentity。表示直前・直後の前景は396656 |
| 前景WinEvent（event_id=3） | 9957843 | 789312 / 4080 | `Chrome_WidgetWin_1`。公開から578ms後 |
| 表示処理終了・observer解除 | 9959093 | 789312 / 4080 | 破棄直前・直後とも789312、解除成功・errors空 |

WinEvent受信時の `event_tick` と受信時の `tick` はともに9957843。公開から受信までの monotonic 差は約573.9msで、tickによる578msとともに待機中の変化を示す。終了/解除まで1250ms残っている。通知が表示直後や破棄の瞬間に前景になったとの記録はない。

ownerのFILETIMEはUTC `2026-10-28T01:51:41.7672042Z`。保存コピーのreadyの更新時刻は `01:51:42.1829906Z`、resultと監査の更新時刻は `01:51:44.0070485Z`。これらは人の記憶確認のための **10月28日10:51:42〜44 JSTごろ** という目安であり、WinEventに保存されていない厳密なUTC時刻を復元したものではない。

## 前景先のアプリ同定と限界

1. 先行する別試行 `06-04g3-stop-evidence/normal/manifest.json:140` には、UTC `01:32:16.455636` の `foreground_before` として同じHWND789312 / PID4080、title `Visual Studio Code` が記録されている。これは約19分前の補助証拠であり、その試行の人手回答や終了理由を今回へ転用しない。
2. 今回の調査時（JST 11:06ごろ）に **PID4080のみ** `Get-Process` で読み取り、`ProcessName=Code`、実体 `C:/Users/shdwf/AppData/Local/Programs/Microsoft VS Code/Code.exe`、プロセス生成UTC `2026-10-28T00:20:25.9457540Z` を取得。今回失敗より前に生成された現存プロセスで、前景先のVS Code同定を補強する。`MainWindowHandle=0` だったため、当時のHWNDと現在のHWNDの一致は確認していない。
3. `_ForegroundAudit.mark` は `tests/test_startup_windows.py:667` で受け取ったHWNDに `GetWindowThreadProcessId` を実行し、得た所有者PIDを保存する。`_receive`（同688行）はWinEventのHWND・event_thread_id・event_tickを渡す。したがって **PID4080は前景先の所有者であり、前景切り替えAPIの呼出元を示す記録ではない**。キーボード・マウス入力、呼出stack、要求元PID、切替理由の記録はない。

Microsoftの仕様でも `GetWindowThreadProcessId` は指定窓を作成したthread/processを返す。WinEvent callbackの引数はイベントと関連窓・時刻等で、切替操作の監査stackではない。この仕様と上の実装から、前景先の同定から操作主体を断定できないと判断した。参考: [GetWindowThreadProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid)、[WINEVENTPROC](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nc-winuser-wineventproc)。

## 重複抑制・寿命・終了の切り分け

- 8 peerすべて `acquired=false`。全snapshotがreadyと完全一致（owner PID16616、generation `54826ea590294757b2f6320ed85a1f9f`、HWND3738882、shown_tick9957265、deadline_tick9959065）。peerの前景は全件とも開始/終了789312。elapsedはpeer0〜5が0ms、peer6〜7が16ms。各peerの開始時tickは保存されていないため、プロセス生成や同時進行区間の完全な順序は復元できない。
- owner elapsed1859ms、表示期限差1800ms、finalのdeadline9959065はreadyの期限と一致する。重複通知が期限を延長したという観測はない。
- `tests/test_startup_windows.py:780` のpeer完了、781行の非取得assert、782行のsnapshot一致assert、783行のowner完了を通過し、784行の前景assertで停止した。`_finish`（172行）はreturncode0とJSON decodeを確認するため、全9子プロセスは正常終了結果を返している。
- **785〜795行の寿命・期限・observer結果assertは、この失敗runでは未実行。** 上記数値は保存証拠に対する事後の読み取り照合であり、試験の成功数や全件結果を書き換える根拠にしない。`run.json` の `-x` により失敗後の他テストも未実施。
- 通知のclose入口（`startup_win32.py:1704` のclick/WM_CLOSE、timer、1912行の期限到達/WM_QUIT）は今回の記録に区別して保存されていない。寿命が期限付近という値だけでtimer終了と断定しない。poll/reader診断は `_finish` のTimeoutExpired分岐なので、この正常完了経路では出力されていない。
- ownerの表示は `startup_win32.py:1899` の `SW_SHOWNOACTIVATE`、破棄前後の測定は1635行。peerは `tests/test_startup_windows.py:1969` の `if lease.acquired` 内へ入らず、表示を呼ばない。通知待機・共有snapshot確認の限定的な静的調査では前景切替要求を見つけていない。ただし未保存の入力や他プロセスからの間接作用まで否定する動的証拠はない。

## 仮説の到達点と次の必要情報

| 仮説 | 現在の根拠と限界 |
|---|---|
| 通知表示/破棄が直接前景を変更 | 表示前後と破棄前後はそれぞれ一致し、唯一の保存WinEventは公開578ms後の別窓。今回の直接的な表示/破棄時変化を支持しない |
| peerによる重複表示・期限延長 | 全peer非取得・同じsnapshot、期限不変。今回の保存結果で支持されない |
| 人の操作・VS Code・他の外部処理が切替 | 前景先はVS Codeへ絞れたが、入力/要求元の証拠はない。いずれかを確定しない |
| 元owner_missing/DEP-05と同じ原因 | 今回は全9子が正常終了し、元事例の終了要求stackとは別の観測。因果の連結証拠なし |

利用者には **今回の10月28日10:51:42〜44 JSTごろにTerminalからVS Code等へ切り替えた/操作した記憶があるか** を親から確認し、次の回答を受領した。これは今回時刻への回答として記録する。

```text
DATA_START
覚えていない／不明
DATA_END
```

回答は操作の実施/不実施どちらも確定しない。同じ質問を再度出さない。別試行の「手動で閉じた／終了した」という回答や、10月23日の「閉じていない」を今回への回答にしない。

**今回の限定調査の結論: 保存済み47原本と今回の回答だけでは切替操作の因果を確定できない。** 前景先の窓所有者・変化区間・重複抑制/期限の整合性までを確定範囲とし、製品欠陥・環境要因・人の操作のいずれにも原因を確定しない。全件結果は引き続き **1846 passed / 1 failed / 1 warning / 180.20秒**、Phase 06未完了、DEP-05等未解除。

## 採取案の履歴（以下は単発診断の実施前に整理）

既存の保存証拠から過去の入力や切替要求元を新たに作ることはできない。次の観測が必要なら、以下の限定的な採取範囲と一回の実行可否を親で判断する。今回のcontinueではコード変更・試験起動を行っていない。

1. **既存原本を固定**: 今回の47原本・失敗ログ・127入力manifestを維持し、新しい診断には別ディレクトリと別basetempを使う。成功しても今回の失敗を置き換えない。
2. **前景変化の観測を補強**: 既存WinEventに前景先processの生成時刻/実行体、前後HWNDとUTC/monotonic対応を保存する。入力を切り分ける場合は、その観測区間に限って入力の時刻・種別・注入フラグを保存する案を検討する。時刻の一致だけで操作主体を確定できるわけではなく、情報がない外部アプリによる要求は引き続き未確定となる。
3. **製品関与と終了入口を観測**: 対象通知経路で到達可能な前景変更APIと表示/破棄の入口をテスト側でラップし、呼出時刻・対象HWND・試験PID/thread・stackを採取する。通知closeにはWM_CLOSE/click/timer/deadline/WM_QUIT/例外の区別を記録する。APIの引数・返却・寿命・合否条件は維持し、native callbackからTkへ再入しない。
4. **再開が明示された場合のみ限定1回**: 診断追加の静的確認後、対象 `test_notice_dedup_eight_processes_keep_original_deadline` を一度だけ実行して停止し、保存結果を比較する。全件再実行やPhase後続へ自動で進めない。再現しない場合も原因解決・品質合格にせず、今回の停止を継続する。

この案のうちglobal input hookや入力種別の採取を除いた最小範囲を、下記のとおり一回だけ実施した。案の記述を追加実行の指示とは扱わない。

## 追加診断1回の結果（auto-resume #2、12:15 JST）

実行範囲の再確認: `06-04-PLAN.md:69` と `06-VALIDATION.md` は再発時にPhase実装・後続・commitを停止してgsd-debugへ戻す契約であり、デバッグ診断を一律禁止する文ではない。親が今回のcontinueに含まれる限定診断として実施範囲を確定。外付け `probe_notice_once.py` を新設し、既存テストの子起動だけをラップして、同じ対象テスト・期限・assertで1回実行した。製品のファイル、既存テスト、版番号は変更していない。

正本ディレクトリ: `notice-probe-20261028-4186632ffba54d25b37703d6e2db059a/`（以下 `probe/`）。親への引継ぎ前に出した昇格要求は中断され、出力ディレクトリ0件を確認後に親が一度だけ実行した。run数は1であり、成功までの反復ではない。

- 実行UTC `2026-10-28T03:15:25.890302Z` → `03:15:30.211485Z`、exit 0。
- `pytest.txt`: **1 passed / 1 warning / 2.44秒**。警告は既存PyMuPDF ByteString廃止予告。ログSHA256 `5d9f9f123cbd6d2f6341dd8cee9dcdeadea1d7e20fe1d9485a8822012b762d37` を再照合。
- `inputs-before.json` / `inputs-after.json` の128入力（既存127＋ラッパー）に差分なし。保存56ファイルは実行時コピー元とhash一致（`run.json` の `copied_unchanged=true`）。今回の分析でも保存56件全てをmanifestと照合し、一致。
- ラッパーSHA256 `8921e4652cac6f0421db4915dab9e37cf02c665127c6fe835d485f558725a16f`。

### 今回観測できたこと

`probe/artifacts/test_notice_dedup_eight_proces0/` 配下の9個の `notice-probe.json` を確認。全processで `errors=[]`。ownerは13記録、peer8件は各2記録、合計29観測の前景はすべて **HWND396656 / PID18044 / WindowsTerminal.exe**。既存 `foreground-audit.jsonl` に前景WinEventはなく、observer解除成功・errors空。元失敗のVS Codeへの切り替えは再現しなかった。

| ownerのAPI記録 | 参照stack / 実測 |
|---|---|
| `SetWindowPos` | `startup_win32.py:1883`、通知HWND8130834、flags=20（既存値）、返却1 |
| `ShowWindow` | `startup_win32.py:1899`、同HWND、command=4（既存値） |
| `DestroyWindow` | `startup_win32.py:1913` の期限ループ → 同1637行のdestroy、`remaining_ms=0`、返却1 |

ラップした `SetForegroundWindow` / `AllowSetForegroundWindow` の呼出記録は0件、peerでラップ対象APIの呼出も0件。今回のcloseは保存stackで **期限ループ経由** と判別でき、WM_CLOSE/clickのprocedure経由ではない。元失敗のclose入口は依然として記録がなく、この結果を遡及適用しない。

owner結果はelapsed1891ms、shown_tick14983234、deadline14985034（1800ms差）。破棄呼出tick14985046で期限の12ms後。表示前後・破棄前後・開始終了の前景は全て396656。既存テストが末尾まで成功したため、今回については8 peerの非取得・snapshot一致、owner前後の前景一致、1700≦elapsed<3000、deadline一致、監査開始/解除・必要イベントの各assertが実行され成功した。元失敗runでは前景assert以後が未実行だった点を維持する。

`GetLastInputInfo` はowner開始時14983046、observer開始時には14983109で、その後の表示・破棄・終了まで固定。入力時刻の更新は監査開始前で、今回の前景は不変。入力内容・種別・要求元は採っておらず、人の物理操作を証明する値でもない。Microsoft仕様上もsession内の最終入力時刻であり、SendInput等の影響を含みうる: [GetLastInputInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo)。

診断の追加時間はゼロとみなさない。`record` 内の採取時間の最大は約1.0681msで、stack抽出など関数外の追加時間を含まない。前景変化が起きなかったため、追加したWinEvent時のidentity/last-input採取分岐の実測検証は今回得られていない。

### 静的検証と制限

- 新規ラッパーのRuff check成功、対象format成功、`pagefolio.py` とラッパーのAST確認成功。
- `.venv/Scripts/ruff.exe check .` はアクセス拒否警告2件を伴い成功。アクセスできなかった領域まで検証済みとは扱わない。
- `.venv/Scripts/ruff.exe format --check .` はRuff内部panic `Expected a ruff source file` で異常終了。通常権限での再確認要求は中断され、結果未取得。**全体format成功とは記録しない。** 対象ラッパーは個別整形・再lint済みで、全体formatのために無関係ファイルを変更していない。
- 文書更新の差分/末尾空白を確認。追加の試験・全件再実行・製品変更・commitなし。

### 現時点の到達点

保存原本・回答確認と、承認範囲の追加診断1回およびその分析は完了した。今回の単発は未再現であり、**元失敗の操作主体・製品関与・owner_missing/DEP-05との因果は未確定**。最新の単一全件結果は1846 passed / 1 failedのまま保持し、Phase実装・後続・接続人手確認・commit・出荷の停止も維持する。

利用者への同じ質問は不要で、追加の自動試験・採取も予定しない。これ以上原因を確定するには、元失敗時の未保存情報に代わる新しい再発証拠など外部状態の変化が必要。現資料のみで独立して進められる調査は尽くしており、自然再発等の新証拠が入った場合だけ既存の診断と照合する。調査結果をresolvedや停止解除へ変換しない。
