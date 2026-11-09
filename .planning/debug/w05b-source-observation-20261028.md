# W05b ソース診断（2026-10-28）

判定: 修正版ソースの人工 native modal で自動復帰成功を実測。配布EXE・実OCR保持・W05b本受入の合格ではない。旧世代3の原因は未確定。

## 条件と原本

- 利用者「出荷停止状態を解消して」「今、画面確認できる」により追加観測を再開。
- `tests/test_startup_windows.py --uat start --case native-ocr` を1回実行。隔離設定・専用namespace、人工showinfo「isolated OCR」「operation continues」。実OCR要求をholdする試験ではない。
- run: `.planning/tmp/pagefolio-uat-_cj5uxgz`、保全コピー: `.planning/debug/w05b-source-observation-20261028/`。
- primary PID17648、peer PID29092。namespace `a79cd15118484e678caf9d17b9f8bb29`。ソースHEAD `55eb3b7e4f3511463e511ec2e30f999a371b45cf` と既存dirtyを含む v1.10.2。
- 外部観測 `.planning/debug/w05b-observe.py`: 50ms周期でforeground HWND/PIDを読み、既存harnessのpeerを1回実行。入力・前景変更APIは観測器から呼ばない。前後の一次window集合、peer原文stdout/stderr、87サンプルを保存。ポーリング間の短い遷移は保証しない。

## 利用者原文

1. 「今、画面確認できる」
2. 「表示された。ChatGPTへ切り替えた」
3. 「自動で同じ確認画面に戻った」

質問は表示確認後にChatGPTへ戻り、二次起動の観測終了まで操作せず待つもの。回答は観測後に受領し、機械観測の代用にしていない。

## 観測

- 起動前からの前景: ChatGPT側 HWND396656/PID18044 が22サンプル、その後 native modal HWND15667372/PID17648 が65サンプル。採取エラー0。
- peerの `allow_foreground.allowed=true`、`os_error=0`、`terminal_result=completed`、47ms、constructed0、exit0。
- 一次の `focus-result.json`: result=completed、activated=native=15667372、expected_tk=4984816、state_preserved/target_correct/focus_correct=true。
- 同じnative HWNDへの実foreground復帰と利用者観察が一致。少なくとも「ChatGPT前景の合成peerなら必ず失敗する」は成り立たない。
- 回収inspect: originals_unchanged=true、一次result=primary/constructed1/restored1/status_preserved=true。一次elapsed122781msで既存120秒安全終了の時期に達しており、stop要求だけによる終了とは断定しない。強制killは実行していない。
- 追加の製品修正はなし。診断器の全体Ruff check/format --no-cache、AST成功。

## 残り

旧世代3実EXEの同OCR request・閉じる確認の自動復帰失敗原因は、この人工showinfoで確定できない。現行入力のPhase05再検証（23/23 passed・fresh）を終えて、v1.10.2実EXEの新世代build・接続実証・本受入へ進む。旧110行not-runと出荷未承認を維持。
