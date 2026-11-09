# W05c v2 計測・回収手順（2026-11-05）

`06-05-02` の継続実装。設計正本は `06-W05C-RETRY-POLICY.md`。新規正式script候補は1回未完了、追加試行0回、ready_for_retry=false。現行停止は `06-W05C-CANDIDATE-STOP-20261105.md` を優先する。元runのNo不成立の原因を修復したという判定ではない。製品、実EXE、moduleの既存pass、正式台帳28pass/80not-run・対象外2は保持する。

## 実装

- `tests/w05c_evidence.py`: native callbackはメモリへ追記して元WndProcへ委譲する。Tk操作、入力、前面化、同期ファイルI/Oをcallbackへ追加しない。通常timerでUTC/単調時計/seq/run/PID/生成時刻/HWNDと観測失敗を記録し、終了時の未書出し件数・hashを残す。
- `tests/test_startup_windows.py`: manual native-quitだけに計測を接続（自動対照は明示flag）。元askyesno/quit/readyのマーカー生成は保持する。No、戻り、元マーカー、peer、stop/cleanup/watchdog/root破棄、Tk例外を区別する。
- `w05c-check --stage before_peer|before_stop`: 同ownerをOSで再照合し、原文と意味対応、期限、マーカー、編集状態、イベントprefixのhashを検査する。各段階1回限り。失敗は記録し、自動再試行しない。台帳とカードへの書込みはない。
- `stop`: 同ownerのprocess handleを保持し、ログ/stack/native窓/前景/編集snapshotを回収前後の別ディレクトリへ固定する。OSの実終了を確認する。異常時もこの回収経路を使用する。stop後に初めて現れたFalse/マーカーはhelperが拒否する。
- `06-05-w05c-evidence.cjs` と既存正式記録helper: script新候補にv2ログ・2段階検査・前後原本・終了確認を必須化。正常dry-runも失敗dry-runもファイルを書き換えない。古いmodule記録をscriptの証拠にしない。
- `.gitignore`: 過去の意図的な不正文法fixtureを含む `04-reverify-20261105-full/basetemp/` とpytest cacheだけを走査対象外にした。製品・試験・tools・診断Pythonは全てRuff対象のまま。過去153fixtureの整形事故の原bytesは不明のままで、推測復元や事故resolvedへの変更は行わない。
- `06-07-quality.cjs`: 計測/対照/helper/.gitignoreを05品質入力に登録し、既存診断を含む144Pythonの対象集合を明示確認する。05の新規basetempはrepo内 `.planning/tmp/` に置く。

## 候補停止後の見直し

`06-W05C-COLLECTION-REVIEW.md` を現行の実装/検証正本とする。v3採取runner/契約を実装し、対象79件・最終全件2333件成功（170入力前後不変）。既存pytest自動GUIのみ利用者許可済み。新規v3 Windows統合は未検証、全体formatは既存tmpアクセス拒否で未通過。元主因未解決、ready_for_retry=false、台帳28pass/80not-run・対象外2、06-06未開始・出荷不可。全体formatの既存検証tmpアクセス拒否を解消し、新規v3 Windows統合の範囲/許可・実測予算を確定する。再開前に06-03 resume_contractで親ゲート鮮度を照合。新規統合/正式試行/期限延長/正常診断反復/製品推測修正/commitは自動実行しない。 下記v2操作順は保存履歴であり直接再実行しない。

## v2候補開始前の操作順（履歴）

1. 親が品質・鮮度・凍結配布物・通常owner/前run/lock不在を照合する。利用者が操作可能と回答するまでは起動しない。120秒watchdog・peer期限を延長しない。
2. script候補を1回だけ開始する。確認中peerの返したfixture名を `peers.during_confirm` に記録する。
3. 利用者が同じ確認の「いいえ」を一度押し、確認消失・全3ページ・1/2ページ横/3ページ縦・1画面を直接回答する。
4. 実行担当は回答JSONへ `answer_original`（原文）、`answer_source`、`answer_captured_at`（実際の取得UTC）、`answer_run_id`（同run名）、`answer_semantics` を記録する。意味対応は人の確認を根拠にし、曖昧なら追加回答を待つ。各項目は原文中の引用 `quote` と `confirmed: true`、承認者 `approved_by`、実承認UTC `approved_at` を持つ。項目キーは `answered_no`, `confirm_closed`, `three_pages`, `rotations_kept`, `single_window`。旧回答は流用しない。
5. `w05c-check ... --stage before_peer` が成功した場合だけ回答後peerを1回実行する。返った名前を `peers.after_answer` へ追加できる。原文・出所・取得時刻・意味対応等の他の回答欄は変更しない。
6. `w05c-check ... --stage before_stop` → `inspect` → `stop`。`stop`は前後の原本・owner終了を保存する。各段階で欠落/異常なら回答後peerや後続へ進まず、証拠を保存して同じstopで回収しdebugへ戻す。
7. 正式helper `node .planning/phases/06-release-validation/06-05-record-w05c-python.cjs <回答JSONのbasename> --dry-run` → 成功時だけ同コマンドから `--dry-run` を外す → 指定行監査。回答JSONのcase/condition/row/entry/run/observation_record/hash/adoption等は従来契約も満たす。回答ファイルは `06-05-evidence/W05c_quit-no_at_script-<UTC>.json` に保存する。observation_recordはrun直下で原文を記す。

実EXEには内部計測や試験引数を注入しない。script正式採用後に専用の外部観測/helperを別契約で整備する。EXE手順未整備のためまだ開始しない。

## 検証と残ゲート

- 対象39件成功（`06-w05c-instrumentation-20261105/target.xml`）。同じNo確認の観測あり/なし実process対照、回収前snapshotの実hash、native窓の外部読取・同owner終了まで含む。自動Noは機構検証専用で正式受入ではない。
- 正常な正式helper dry-runで全fixture不変、欠落No/回収開始が先の拒否、owner/HWND/run不一致・時系列逆転・期限・記録失敗・原文不一致・旧module/診断転用等を検査した。
- 全体Ruff check、`ruff format .`（144Python変更なし）、AST成功。アクセス拒否により見かけ上exit0となった初回と、nativeで確認した旧fixtureの構文エラー/format panicも原本保持。新しい除外後の成功と混同しない。
- 新native全件: `06-05-evidence/w05c-instrumentation-native-20261105/result.json` と `junit.xml`。2293 passed / 2 warnings / 1191.69秒、failure/error/skip各0、167一意入力の前後・現行一致。runnerの配列表示168には重複1があり、実hash集合は167。旧2254件を付け替えていない。
- Phase04→05の必須ゲートとgoalを独立再検証し、公式statusは両方passed/fresh（21/21、23/23）。根拠は各phaseの `*-REVALIDATION-W05C-20261105.md` と `*-VERIFICATION.md`。現在cleanのRuffは `04-QUALITY-RECHECK-W05C-20261105.json` にargv/exit/空stderr/167入力照合を保存。開始前Ruffの一過性警告と原因path未特定も同JSONに保持する。
- build-only監査exit0、凍結配布物と65入力の一致。production owner（読取probe）なし、所有検証processなし（native CIM読取）、参照配布先のbuild lockなし。製品・版・同梱文書の変更/再build/正式script候補/commitは0。開始直前にもowner/lock・入力・利用者の操作可能時間を再確認する。
- 親の機械的再開条件は成立。利用者が操作可能と回答するまでは `ready_for_retry=false` としてGUIを起動しない。利用者Noを代理入力しない。

既存の意図外整形、配布元消失、tracer消失、元No不成立、既知の未確定原因は未解除。06-05未完了・06-06未開始・出荷不可を維持する。
