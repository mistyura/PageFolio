---
status: investigating
trigger: "phase06-w05b-manual-switch"
created: 2026-10-28
updated: 2026-10-28
---

## Current Focus

2026-10-28 世代5追加観測: `31d4388e2cbb4f80944a015b67bc3234` は同modalへ自動復帰後約2.4秒でChatGPTへ戻った。利用者補足「案内を待たず、自分でChatGPTへ切り替えた」と時系列が整合し、終端snapshot不一致の原記録を `06-08-w05b-interrupted-session.json` / `06-08-W05B-OBSERVATION.md` に保持。自動復帰後10秒無操作を明示した別run `af629ccbe3514294a7814e1de2e98463` は同確認HWND3867420の自動復帰・いいえ・同1POST完了・通常終了を機械観測と利用者原文で確認。世代5準備監査exit0。製品/driver/期限/判定条件は変更なし。この観測中断の説明を旧世代3の根本原因確定へ拡張しない。

2026-10-28 再開: 利用者「出荷停止状態を解消して」により、追加観測と必要な修正・検証を再開する。以下の「限定調査のみ・再開指示待ち」は前回のスコープ履歴。CR-03 は先行して v1.10.2 で修正し全件2083 passed（`.planning/debug/ocr-off-summary.md`）。新しい診断と旧EXE原本を分離し、旧runをpassへ変更しない。未実施の人手受入と出荷承認は維持する。

hypothesis: ChatGPT前景のままdriverから合成peerを起動した条件で前景化の許可委譲または前景化が拒否された可能性がある。ただしAPI戻り・activation結果・対象HWND・連続前景記録がなく、製品側の処理不成立と分離できない。
test: 限定調査は完了。保存証拠の時系列・ハッシュ・同一modal/requestを照合し、現在のdriver/製品コードとWindows公式仕様を読み取り確認した。
expecting: 後続でAPI戻りと実foregroundを同時採取できれば、権限拒否・処理未到達・対象選択・一時復帰後の再切替を区別できる。今回の記録だけで原因確定・合格化はできない。
next_action: 世代4実EXEで自動復帰・いいえ・同1POST完了を実測し準備監査exit0。接続準備の停止を解除し06-05へ。旧世代原因は未確定のため診断は履歴として保持。06-04g4-CHECKPOINT.md参照。

## Scope

既存の06-CONNECTION-STOP-20261028.md / 06-RESUME-CHECKPOINT-20261028.md / STATE.mdの再開指示による限定調査。症状はこれらの記録から引き継いだ。新規試行・driver/製品修正・追加GUI/build・06-05/06実行・commitは禁止。既存dirty/index・原本・判定を保全する。親エージェントが直接調査する。

## Symptoms

expected: hold中のOCR閉じる確認がpeer後に同じnative modalへ自動復帰し、いいえでOCRを維持して同一requestを完了する。
actual: 同modal HWND6753582は保持。peer後の前景はChatGPT側PID18044でprimary9920と不一致。利用者補足は「自分で PageFolio に切り替えて確認した」。自動復帰は未実証。
errors: preparation-only exit1「接続(w05b-modal): native modal→peer→いいえ→同処理完了の観測が不足です」。製品例外を原因とする証拠は提示されていない。
reproduction: 世代3 native W05b run cf52cf1df4db42a3b384db6f13a6c103。1page OCRをholdし閉じる確認表示をチャット回答、driverがpeer起動、観察回答、いいえ、同request完了。再実行しない。
started: 2026-10-28の接続実証で観測。発症開始時期・同条件で以前成功していたかは未確定。

## Eliminated

- hypothesis: 最初の「前面に戻っている」という回答だけで自動復帰成功を確定できる。
  evidence: 手動切替の補足があり、2番目の回答受領はpeer後inspect記録から44.949435秒後。inspectと直後のforeground_after_peerはいずれもPID18044。
  timestamp: 2026-10-28

- hypothesis: 2番目のチャット回答操作が、先行するpeer後inspectのChatGPT前景を生じさせた。
  evidence: driverはpeer後採取を終えてから2番目の質問を表示する。回答は採取後。今回の利用者補足でも最初の回答からpeer完了案内まで切替/クリックはしていない。
  timestamp: 2026-10-28

- hypothesis: modal消失またはOCRの別リクエストへの置換が、今回の自動復帰未実証を説明する。
  evidence: peer前後のvisible #32770 HWNDは同じ6753582。1POSTでreceived/released/completedのrequest_idはすべて7df81778edb94ac8be9ddf78d7bb3261、expiredなし。ただし前景化処理の到達自体は未確認。
  timestamp: 2026-10-28

## Evidence

- timestamp: 2026-10-28
  checked: .planning/phases/06-release-validation/06-CONNECTION-STOP-20261028.md および保存済み w05b-user-clarification.json
  found: 原文4回答と手動切替補足は別保持。peer_returned_to_modal=false、準備監査exit1、全110行not-run、出荷停止。
  implication: 同modal存続・同request完了を、自動復帰成功の代わりにはできない。

- timestamp: 2026-10-28
  checked: .planning/phases/06-release-validation/06-04-drivers/conn_session.py:234-242,403-415,442-462
  found: askはinput返却後に回答時刻を保存。最初の回答受領後にmodal-up前景を採取し、peer起動から4秒待ってinspectし、さらに前景採取後に2番目の回答を求める。
  implication: 回答時刻は目視時刻ではない。2番目の回答より前にpeer後前景が採取されるため、採取前後の操作は区別が必要。

- timestamp: 2026-10-28
  checked: 保全済みW05b session-w05b-modal.json:658,688,1002,1183 および inspect-002.json / manifest.json
  found: 最初の回答受領05:20:10.008272Z、modal-up記録05:20:10.010587ZはChatGPT側PID18044。peerの生成05:20:10.071818Z、起動記録05:20:10.077879Z、inspect記録05:20:14.100892ZもPID18044。2番目の回答受領05:20:59.050327Z。
  implication: peer前からChatGPTが前景。起動記録から約4.023秒後にもChatGPTが前景だが、この間の連続観測はない。started_atはPopen後のprocess識別・hash取得後、inspectのatもforeground採取後の記録時刻であり、API呼出し瞬間の厳密な時刻ではない。

- timestamp: 2026-10-28
  checked: このdebugセッションで受領した利用者の追加回答
  found: 質問「前回のW05bで『確認ダイアログが表示された』とチャットへ回答してから、次の『2つ目の起動を行いました』の案内までの間、PageFolioへの切替やクリックをしましたか？」に対し、原文「ChatGPTを開いたまま、操作していない」。
  implication: この区間で利用者がPageFolioへ切り替えたという仮説を支持しない。これは後日の申告であり、連続foregroundログやAPI戻りを補完する機械証拠ではない。以前の手動切替補足は撤回されていない。

- timestamp: 2026-10-28
  checked: tests/release_uat_support.py:885-921,960-990,1014-1059 および現在の pagefolio/startup_win32.py:950-951,1146-1160 / pagefolio/__main__.py:43-48
  found: driverはsubprocess.Popen(shell=False)でpeerを起動し、stdout/stderrはDEVNULL。保存manifestのpeer親PID15148は前景PID18044と異なる。現在の製品実装にはAllowSetForegroundWindowによる委譲とSetForegroundWindowの結果をcompleted/foreground_deniedに分ける経路がある。保存session/inspectにはこれらのAPI結果やactivation結果の記録がない。
  implication: peer起動・終了や追加通知がないことはactivation成功の証明にならない。現在のソースは仮説の根拠であり、当該EXEでその分岐を通過したことの証拠ではない。

- timestamp: 2026-10-28
  checked: Microsoft LearnのAllowSetForegroundWindow / SetForegroundWindow公式リファレンス（下記リンク）
  found: 許可委譲元自身が前景化可能である必要がある。前景プロセス・前景プロセスからの起動・最終入力等が条件に関係し、条件を満たしても拒否される場合がある。
  implication: ChatGPT前景でdriver起動した合成peerと、利用者がExplorerから実ダブルクリックしたpeerを同条件とは扱えない。今回の拒否を断定できるAPI実測はない。

- timestamp: 2026-10-28
  checked: .planning/phases/06-release-validation/06-04-drivers/assemble_protection.py:374-395 および保全済みpreparation-only.json
  found: 同modal HWND集合の共通要素に加えてforeground PIDがprimaryと一致する条件。今回PID18044と9920は不一致でfalseは記録と整合。別の潜在的制限として、条件自体はforeground HWNDがmodal自身かまでは比較していない。
  implication: 今回のfalseを手動回答でtrueへ書換えない。後続観測はPIDだけでなく同modal HWNDを確認する必要があるが、今回driver/判定式は変更しない。

- timestamp: 2026-10-28
  checked: original-hashes.jsonに記録されたW05bの8ファイル、および保存JSONに対するオフライン整合性確認
  found: W05bの原本8/8・保全コピー8/8が記録済みSHA256と一致。native session・同modal・peer前後ChatGPT前景・回答/起動/採取/回答の時系列・同一request完了・sessionトップレベルにAPI結果項目なし、の6項目がtrue、検証コマンドexit0。
  implication: 保存証拠の整合性を確認。自動復帰の動作試験合格を意味しない。コード未編集・commitなしのためRuff/pytest/GUI/buildは実行していない。以前の47件/2071件成功は今回の再検証結果として扱わない。

## Timeline（2026-10-28、日本時間）

| 時刻 | 記録 | 読み取れる事実 |
|---|---|---|
| 14:19:44.522 | received step | primary9920のOCR HWND12456400が前景 |
| 14:20:10.008 | 1番目の回答受領 | 確認表示の回答をdriverへ転送済み。実際の目視時刻は不明 |
| 14:20:10.010 | modal-up step | modal6753582はvisible、前景はChatGPT側18044 |
| 14:20:10.071 / .077 | peer生成 / 起動記録 | peer4192、親driver15148 |
| 14:20:14.100 | after-peer inspect | 同modal存続、前景はChatGPT側18044 |
| 14:20:14.181 | peer step | inspectで採った前景を再利用した記録。独立した追加採取ではない |
| 時刻未記録（コード上peer step後） | foreground_after_peer | 別採取でもChatGPT側18044 |
| 14:20:59.050 | 2番目の回答受領 | 前面に戻っているとの回答。後に手動切替と補足 |
| 14:21:23.483 | いいえ後の回答受領 | OCR・処理・入力の維持を申告 |
| 14:21:24.595 / .601 | released / completed | 同一request完了 |

## 結論と残る仮説

確定したのは、チャット回答後にChatGPTを前景にしたまま合成peerを起動し、約4秒後もChatGPTが前景だったことと、その後の目視には手動切替が入ったこと。回答手順と測定時点の分離は確認できたが、「チャットが原因で自動復帰に失敗した」「製品不具合だった」のいずれも確定しない。

残る可能性は、前景化権限拒否、activation未到達/期限切れ、native modal対象選択や処理経路の問題、一時復帰後の別プロセスによる再前景化。保存された2時点と後日の申告だけでは切り分けできない。過去のowner_missing/DEP-05/startup-wake修正の原因と同一視しない。

## 次に必要な観測案（未実装・未実行）

1. 現行の停止を解除する範囲が決まった場合に限り、06-04準備調査用の独立runとして扱う。本受入の実ダブルクリック試験（06-UAT.md:814-845）を合成peerで代用しない。
2. 起動前に観測・回答の順を固定する。チャット回答で開始合図を受けた後は、観測終了まで切替/クリック/チャット回答を挟まない。利用者の回答は採取完了後に受け、回答受領時刻と目視・手動切替時刻を別に記録する。
3. peer前から処理終了までforeground HWND/PID/時刻の遷移を外部記録し、peerの親PID/生成時刻、primaryの同modal HWND、操作イベントも対応づける。単一の4秒後snapshotで一時的な遷移の不存在を証明しない。
4. 取得手段を先にレビューし、AllowSetForegroundWindowの戻り、activation応答、SetForegroundWindowの戻りと対象HWNDを実foregroundと別記する。現在の証拠を埋めるために推測値を作らず、製品/driver変更が必要なら既存禁止の解除前に行わない。
5. API拒否なら起動条件・OS制約、要求未到達ならIPC/wake、対象違いならmodal選択、API成功と実foreground不一致なら遷移時系列をそれぞれ検討する。同条件の無目的な反復はしない。

## References

- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow

## Resolution

root_cause: 自動復帰未実証の根本原因は未確定。測定時点と回答時点の分離、およびチャット前景でのdriver合成peer起動条件を特定。OS拒否と製品処理の区別に必要な証拠が不足。
fix: 未実施（限定調査）
verification: W05b原本8/8・保全コピー8/8のSHA256一致、オフライン整合性6項目成功。製品/driver/tests/版/STATE/UAT台帳/indexを変更せず、再試行/GUI/build/commitなし。peer_returned_to_modal=false・準備監査exit1・全110行not-run・出荷停止を維持。
files_changed: [.planning/debug/phase06-w05b-manual-switch.md]
