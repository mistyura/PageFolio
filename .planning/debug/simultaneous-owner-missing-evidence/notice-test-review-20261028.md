# 通知の前景非干渉試験・見直し案

状態: **局所native検証・単一全件pytest完了、現行品質停止を解除**。2026-10-28。

最新の利用者指示「既存の停止条件を解消する修正をする。」に従い、診断スクリプトの原本保存・AST不変の整形、全体Ruff137件、実OS接続/9プロセス各1回、単一全件2071件の成功を確認した。記録ベース24件も全件に含む。証拠は `../quality-gate-unblock.md` と `../quality-gate-unblock-20261028/`。本書後半の初回停止結果とJSON原本は当時の記録として保持する。Phase 6の再開前入力照合・未実施受入・出荷承認は別条件。

利用者選択: 「試験見直し案を具体化し、変更内容を確認してから実装する」。今回承認された範囲は設計まで。試験コード変更・試験起動・全件再実行・Phase後続・commit・出荷の許可とは扱わない。

その後の承認: 「この案で実装と局所検証へ進む」。以下の手順1〜3を承認範囲とする。実装した試験コードの合格確定には未実施のnative検証が必要。

## 目的と根拠

承認済み契約は `04-CONTEXT.md` D-12「失敗案内を表示してもキーボードの操作先を変えない」。製品が入力先を奪う回帰を検出しつつ、待機中に別の窓が前景になった観測と、切替要求元が製品である証拠を区別する。

現行 `tests/test_startup_windows.py:784` は約1.8秒の待機前後のHWNDを比較する。別窓への切替でも失敗し、逆に短時間の前景奪取後に元の窓へ戻ると、この比較だけでは検出できない。既存WinEvent監査と表示・破棄前後の4値は保存されるが、現在の合否はこれらを十分利用していない。

元失敗では公開578ms後にTerminalからVS Codeへ変化した。前景先は分かるが要求元は分からない。後続の単発probeは未再現であり、この提案の根拠を「環境原因確定」「製品に問題なし」としない。

## 変更対象

| ファイル | 提案する変更 |
|---|---|
| `tests/test_startup_windows.py` | 対象試験の子プロセスへ限定監査を組み込み、重複抑制・寿命・期限の判定と前景判定を分離。前後2値、局所4値、全WinEvent、API記録から最終判定する |
| `tests/startup_foreground_audit.py`（新規案） | 試験用の記録・判定ヘルパー。前景を変えるAPIを実行する機能は持たず、製品コードからimportしない |
| `tests/test_startup_foreground_audit.py`（新規案） | 保存記録・欠落・故障注入による判定試験。未検証の切替分岐と、短時間奪取後に元へ戻る回帰を検証 |
| 既存デバッグ文書 | 実装承認・検証結果・未解決事項を追記。元失敗と新しい試験世代を区別する |

製品コード、版番号、`pyproject.toml`、既存の期限・寿命許容幅は変更対象に含めない。既存probeの過去実行と原本は保持し、今回案の実装済み成果物には流用しない。

## 観測の具体案

1. 各子の`Win32Backend`構築前に試験専用のラッパーを入れる。既存probeの`_bind`方式を参考に、後から動的にbindされる関数も含める。対象PID・生成時刻・role、通知HWNDの生存区間を記録する。ownerと8 peerで監査の開始・終了・エラー有無を確認する。
2. 通知経路の`CreateWindowExW`、`SetWindowPos`、`ShowWindow`、`DestroyWindow`の引数・結果・時刻・呼出位置を保存する。`WS_EX_NOACTIVATE`、`SWP_NOACTIVATE`、`SW_SHOWNOACTIVATE`を検証する。既知の通知経路から`SetForegroundWindow`等の前景/入力先変更要求が呼ばれたら、OSが拒否した場合も不合格にする。実装時に到達可能なbindを照合し、監視APIの固定一覧だけを完全な証明としない。
3. ownerのWinEvent監査を維持し、通知の表示前から破棄後のqueue回収まで記録する。通知HWNDまたは対象試験子の窓が一瞬でも前景になった記録を不合格にする。HWNDの再利用を扱うため、時刻・所有PID/thread・生成時刻と対応づける。イベントは要求元の証拠として扱わない。
4. 表示・破棄それぞれの直前/直後の前景値と時刻を記録する。同じ短区間で未知の切替があれば、値の不一致だけで製品原因を確定しない。通知の前景化、禁止要求、または監査不足として別の判定根拠を残す。
5. ラッパーは引数・返却値・ctypesのlast-error・例外を保ち、採取失敗を空記録へ読み替えない。native callbackからTkへ再入しない。hook解除、記録完結、必須API到達、子9件の終了を確認し、監査エラーは不合格にする。追加時間も記録し、期限/timeoutは延長しない。

採取は対象試験の窓・API・時刻・プロセスidentityに限定する。global入力hook、キー内容、他アプリのタイトル一覧、他プロセスへの注入は使用しない。監査で未知の間接作用まで否定できるとは主張しない。

## 合否と停止の扱い

| 保存証拠 | 診断上の判定 | 自動ゲート |
|---|---|---|
| 完全な監査、局所前景維持、前景奪取/禁止要求なし、未説明切替なし、重複抑制・期限も成立 | `pass` | 成功 |
| 通知/試験子の窓が前景化、禁止API要求、activationを許すフラグへの変更 | `violation` | 失敗して停止 |
| 監査の開始/終了/必須記録欠落、callback/回収エラー、identity不足、前景が取得できない | `audit_error` | 失敗して停止 |
| 別窓への切替があり、要求元を説明する独立証拠がない。局所前後差も帰属不能 | `unexplained_transition` | **失敗して停止**。製品原因は未確定と報告 |
| 専用対照試験が宣言した窓間切替だけを、要求/実測の対応つきで観測 | `controlled_transition` | 対照試験だけで許容。通常の通知試験へ自動適用しない |

`unexplained_transition`は診断用の区分であり、pytestのskip/xfailや成功には変換しない。通常試験は最終的に`pass`だけを成功とする。開始/終了HWNDも保存し、未知の外部窓への切替を自動的に環境ノイズとして免除しない。

重複抑制・snapshot一致・owner/peer正常終了・1700ms以上3000ms未満の寿命・期限不変・hook解除を個別に評価してから、全体を集約する。これにより前景不一致でも残りの観測を記録できる。新たな期限やassertの緩和は導入しない。

## 必須の回帰試験

| 条件 | 期待する検出 |
|---|---|
| 前景不変で、owner1件/peer8件の記録が完全 | 成功候補。全既存条件も成立して初めて成功 |
| 通知が一瞬前景になり、終了時には元の窓へ戻る | 前後2値が同じでも`violation` |
| 前景API要求がOSに拒否され、前景は不変 | 要求自体を`violation`として検出 |
| ShowWindow/SetWindowPosの非activation指定を試験記録上で破壊 | `violation` |
| VS Code等への未説明切替、通知窓への切替なし | `unexplained_transition`で失敗。原因は未確定 |
| hookが受信しない、解除失敗、記録途中欠落、必須bindを監視できない | `audit_error`。空の記録を成功にしない |
| peerが取得/表示、snapshot変更、寿命または期限延長 | 既存の重複抑制/期限条件で失敗 |
| owner/peer/例外終了経路 | 監査解除・子回収・namespace解放、既存設定/入力の保持 |

記録ベースの故障注入だけを実OS監査の検証にはしない。実装承認後は、対象プロセスだけを監査するnative試験でhook・bindラッパー・記録経路の接続を確認する。

## 実装承認後の検証順と境界

1. 既存dirty/indexと対象入力hashを記録し、ヘルパーと判定試験を実装する。Ruff check、format、再lint、`pagefolio.py`と編集PythonのAST確認を行う。全体formatが再びpanicした場合は成功扱いせず停止し、別件整形を混ぜない。
2. 記録ベースの正負試験を1回実行。失敗なら原因を直し、影響する試験だけを再検証する。
3. 新しい実OS採取は新規run/basetempで、接続確認と対象のowner+8 peer試験を各1回だけ実行する。同じ症状の再発、監査不足、未説明切替があれば最初の証拠を保存して停止する。成功するまでの反復はしない。
4. 外部切替分岐の実OS検証が必要な場合は、試験所有の窓2個だけを使う対照試験を別途計画する。既存アプリを操作せず、通常のAPI要求をOSが拒否すれば前提未成立で停止する。OS制約を迂回しない。この実行範囲は今回の設計確認に含めず、別の判断とする。
5. 全件pytest・Phase再検証・commit・再ビルド・OCR接続・出荷はこの設計または局所試験の成功では解除しない。解除の判断後に必須ゲートを実施する。試験変更後は古い成功hashを再利用できない。Phase4/5の検証鮮度と新世代の入力照合を再評価する。

実装承認の対象は手順1〜3の試験コードと局所検証まで。製品修正、手順4の窓切替操作、全件実行、Phase再開は別の判断とする。

## 過去の結果と未解決事項

元の全件結果は**1846 passed / 1 failed / 1 warning**のまま保存する。新しい判定器を元ログに適用しても、当時未採取のAPI記録を補完できず、過去をpassへ変更できない。元の`owner_missing`、DEP-05、当時の切替要求元、全体formatの未確認は未解決のまま。試験改善の完了と製品原因の解明を別々に記録する。

## 実装・局所検証の結果（初回停止時の記録）

証拠: `notice-contract-20261028-implementation/`。`baseline.json`に既存132入力・index・dirty一覧、`test_startup_windows.before.py.txt`に当該試験の編集前原本を保存した。

- 試験3ファイルを実装。監査有効化は対象のowner/peer fixtureのmarkerと接続試験に限定し、他の既存シナリオでは有効にしない。子のruntime PID/生成時刻をstdout結果と監査ファイルで照合する（Windowsのlauncher PIDと同一とは仮定しない）。
- 初回はヘルパーimportの収集エラー。既存の`tests`パッケージ経路へ修正し、初回ログを保持。修正後22件成功、記録欠落/role重複の検出を追加後は**24 passed / 1 warning / 0.65秒**。警告は既存PyMuPDF廃止予告。最新ログは`unit-v3-pytest.txt`。
- 編集Python3ファイルのRuff check/format確認、`pagefolio.py`を含む4ファイルのAST確認は成功。
- 通常権限の全体Ruff checkはアクセス拒否警告5件を伴いexit 0。アクセス不能領域を検証済みとはしない。全体`ruff format . --check`は内部panic `Expected a ruff source file`で異常終了。`static-all.json`と2ログを保存した。
- 手順1の停止条件により、**接続確認とowner+8 peerのnative試験は両方not-run**。OSの前景切替操作、全件pytest、製品修正、Phase後続、commit、出荷も未実施。
- 再開点は全体format異常の切り分け。成功と扱ったり、除外でゲートを迂回したりしてnative試験へ進めない。通常権限でも再発したため、同じコマンドの無理由な反復は行わない。

元の全件失敗、原本47件、単発probeと未解決原因は保持する。この実装は実OS接続が未検証であり、製品の前景非干渉やPhase完了を認定しない。

## 仕様参照（2026-10-28確認）

- [EVENT_SYSTEM_FOREGROUND](https://learn.microsoft.com/en-us/windows/win32/winauto/event-constants): callbackのHWNDは変化後の前景窓。要求元の記録ではない。
- [ShowWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow): `SW_SHOWNOACTIVATE`はactivationなしの表示指定。初回呼出時のSTARTUPINFOによる指定上書きにも留意し、引数だけで実挙動を断定しない。
- [SetWindowPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowpos): `SWP_NOACTIVATE`はactivationを行わない指定。
- [Extended Window Styles](https://learn.microsoft.com/en-us/windows/win32/winmsg/extended-window-styles): `WS_EX_NOACTIVATE`はクリック等による前景化を抑制するが、明示APIによるactivationの禁止まで保証しない。
