---
status: resolved
trigger: "今回の失敗を調査"
created: 2026-10-28
updated: 2026-10-28
---

# Debug: startup_wakeの前面ウィンドウ不変性テスト失敗

## Symptoms

- expected: `test_native_tcl_getmessage_stall_recovers_with_product_wake[True]` で自スレッドへのWM_NULL投稿によるTcl待ち解除を確認し、非干渉・worker終了・回復時間の検証が通る。
- actual: Phase 06再開前提のPhase 04再検証中、`foreground_unchanged=False` で停止。1810 passed / 1 failed / 1 warning、144.87秒、exit 1。
- errors: `tests/test_startup_wake.py:216` の `assert data["foreground_unchanged"]` に対する `AssertionError: assert False`。removed==1とposted>0は通過、後続worker停止/回復時間assertは未到達。
- timeline: 2026-10-28T00:25:02.117Z〜00:27:28.371Zのnative全件初回。以前のF1ログは2036成功だが採取時入力manifest不在で今回の現行合格へ再利用不可。今回の113入力の前後hashは一致。
- reproduction: `.venv/Scripts/python.exe -m pytest -q -x --basetemp=C:\Users\shdwf\AppData\Local\Temp\pf04-reverify-3a9071d0-3f30-4a48-8f80-e95fef4cb428`。初回証拠を保持済み、同条件の再走はまだ行っていない。

## Scope and Constraints

- ユーザーはこの失敗のGSD調査を依頼した。既存のW02通常操作確認を再度求めず、この新しい試験失敗を対象とする。
- 原本: `.planning/phases/04-startup-control/04-REVERIFY-GATES-20261028.md` と `04-reverify-20261028/native/{pytest-full.txt,run.json,inputs-before.json,inputs-after.json,environment.txt}`。初回ログSHA256 `8fd685d2e2d9c31e28dfe3e38c99cfc730af8273067115737adff530f73aec07`。上書き・削除禁止。
- helper `tests/startup_wake_child.py` は窓なしの `tk.Tcl()` と自スレッドWH_GETMESSAGEを使い、前後のGetForegroundWindowの等値だけを返す。初回失敗では子JSON全体/前後HWND/PID/titleが永続化されていない。この不足を推測で補わない。
- F1製品修正は未commit: `pagefolio/startup_wake.py`、`pagefolio/__main__.py`、`pagefolio/startup_win32.py`。版同期はv1.10.1、Phase 06の実EXE/台帳はv1.10.0世代2。既存dirtyやstagedを混入・取消ししない。
- `AGENTS.md` と `pyproject.toml` を変更しない。全ての返答・記録は日本語。1タスクずつ。Python変更時は必須Ruff/format/AST、commit前は単一全件pytestを実施。同条件の無理由再試行をしない。
- 実験は仮説・期待・観測を記録し新規証拠へ保存する。失敗をskip/閾値緩和で隠さず、外部デスクトップ変化と製品の因果を区別する。
- sandboxのTcl資源到達エラーは初回別attemptに保全済み。native資源が必要な処理はルールに従いrequire_escalatedを使う。
- Phase 04/06完了・出荷停止は維持する。今回の解決を既存DEP05/owner_missing/WR-01等の解決へ流用しない。

## Evidence

- timestamp: 2026-10-28
  checked: tests/test_startup_wake.py、tests/startup_wake_child.py、pagefolio/startup_wake.py の境界だけを読解。開始時git statusとstagedを確認。
  found: helperは窓を作らず、自スレッドのhookと投稿を使う。失敗assertはデスクトップ全体の前景HWND前後一致。製品の通常経路は注入されたPostThreadMessageWだけ。対象2テストファイルは既存untracked、stagedなし。
  implication: 前景前後一致から製品起因を判定できるかを先に実験する。既存2ファイル全体のcommitは既存作業を含むため行わない。原本の真因はまだ未確定。

- timestamp: 2026-10-28T00:36:33Z
  checked: red-sandboxとred-nativeで観測値だけを-1→-2へ変更する最小実験。実ウィンドウへの前景・入力操作なし。
  found: sandboxはinit.tcl到達不可で停止し、同一処理をnativeで1回実施。製品未変更、removed=1、posted=7、回復119.8374ms、worker_stopped=true、実HWND396656/PID18044は前後同じでも、旧foreground_unchanged assertだけがFalseで失敗。
  implication: 旧assertは外部変化の観測だけで偽陽性になることを実証。原本の外部変化発生は証明していない。raw JSONは今回専用basetempに保存済み、原本に存在しない情報を逆算しない。

- timestamp: 2026-10-28T00:43:56Z
  checked: 担当2ファイルへ厳格API境界・全投稿引数/呼出TIDの確認・観測診断永続化を追加した対象試験。
  found: 初回targeted-nativeは追加helperのimportパス誤りで収集停止（記録保持）、tests.startup_wake_childへ修正。targeted-native-fixedは23 passed / 1 warning / 4.13秒。禁止前景API・ctypes迂回・別TID・別メッセージ・owner呼出の負対照がすべて通過。native対照/見張り/観測変化注入の3子JSONを保存。
  implication: デスクトップ観測に依存しない副作用境界を検証。400ms/600ms、worker停止、removed/posted条件は維持。製品は未変更。

- timestamp: 2026-10-28T00:44:54Z
  checked: 修正済みhelperのまま判定1行だけを旧foreground一致assertへ戻す反証実験。
  found: legacy-oracle-redが同じFalse assertで1 failed。厳格API境界違反なしで再現し、修正判定へ再適用済み。
  implication: RED→GREEN→旧判定REDまで確認。再適用後の単一全件pytestをfull-nativeとして実行中。

- timestamp: 2026-10-28
  checked: Ruff全体check/format、AST、無関係変更の除外。
  found: sandbox formatはアクセス拒否3件でexit1（成功扱いせず）。既存資料の整形61件を初期clean trackedだけHEAD bytesへ戻した。nativeの全体check/formatはexit0。ruff-correctedでは無関係61件を実行直前bytesとhash完全一致で復元。既存dirtyのmtimeは未変化。113入力の開始時hash比較で差分は担当2テストのみ。pagefolio.pyと担当2ファイルのAST成功。
  implication: 製品・原本Phase04報告・06台帳・AGENTS/pyprojectを保持。formatterの未整形資料は今回の修正へ混入しない。

- timestamp: 2026-10-28T00:45:23Z
  checked: 最終の単一全件pytest（full-native）。原本の最初の失敗で停止。
  found: 198 passed / 1 failed / 1 warning / 16.60秒。test_gsd_dod.py:293がPhase04のstatus=draftを検出。現行ROADMAP.md:117はPhase4チェック済み、:249は6/6 Complete・2026-10-22のまま。同試験は現行Phaseの完了チェック/進捗/PLAN-SUMMARY整合を確認した後、完了Phaseにvalidatedを要求する。nyquist_compliantは参照しない。開始時dirtyの04-VALIDATION.mdは本調査で未編集。
  implication: 今回wake試験とは別のGSD正本整合性による停止。全件成功とは扱わず、指示どおり修復/skip/再走はしない。113入力は前後一致。原本ログhashは4a07386e73e161878f269a5a13994af16daf47ef458c69983b6ffff9ccba74ce。親がこの状態不整合を別途引き取る。

- timestamp: 2026-10-28
  checked: Phase 04初回native全件ログ、run.json、停止報告。
  found: foreground_unchanged=Falseの事実だけが判明。原本の113入力前後hash一致。製品の前景変更を示す原因証拠はない。
  implication: 初回失敗の原因は未確定。試験の観測契約と製品の呼出先を確認し、反証可能な実験を行う必要がある。

## Eliminated

- 観測変化そのものが見張りの回復失敗を意味する、という解釈: native実測前景不変・119.84ms回復でも観測値注入だけで旧assertが失敗するため反証。
- 製品の前景操作が今回再現実験に必須、という仮説: 製品未変更のまま旧assertの失敗を作れるため反証。ただし原本での製品起因は証拠不足で肯定も否定もしない。
- nativeのinit.tcl破損: sandboxのみ到達不可、同処理nativeではTcl試験が動くため今回環境のインストール破損とは判定しない。

## Current Focus

- bug_class: concurrency（観測と外部デスクトップ変化の合法な割込み。原本での発生は未確認）
- hypothesis: helperのデスクトップ全体のHWND前後一致は外部変化を製品干渉と混同し、製品のAPI呼出が同一でも偽陽性になる。
- test: 実デスクトップは変えず、前景観測値だけへ外部変化を注入した正負対照を作る。旧assertの失敗と、許可API/自スレッドWM_NULL境界の成立を同時保存する。
- expecting: 製品を変えず同じforeground_unchanged=Falseを作れる。原本の原因の断定はしない。
- next_action: 確認した試験欠陥の修正と全件品質検証は完了。次は `$gsd-execute-phase 04` で独立ゲートと失効したverificationを更新し、その後Phase06へ戻る。初回原本の前景変化の原因は採取欠落で未確定のまま保持し、Phase04/06完了や出荷合格へ読み替えない。

### reasoning_checkpoint

- hypothesis: デスクトップ全体の前景一致を製品非干渉の判定に使う試験契約が不適切であり、外部変化の観測だけで偽陽性になる。
- confirming_evidence: 旧assertを保持した観測値注入で同じFalse失敗。製品は未変更で7投稿・119.84ms回復・worker停止。native前景実測は同一。
- falsification_test: 観測変化の有無で投稿/回復が変化する、または独立したAPI境界で禁止API・別スレッド投稿・WM_NULL以外を検出すれば、製品非干渉の仮説を棄却する。
- fix_rationale: 前景の前後観測は診断として保持し、製品非干渉を許可APIの厳格な境界と全投稿引数・呼出スレッドで独立に強制する。禁止API/別スレッド/別メッセージを負対照として拒否できることも確認する。
- blind_spots: 初回原本のHWND/PID/子JSONが無いため初回発生原因は特定不能。観測値注入は実OSの前景切替の再現ではない。将来の別ライブラリ直呼出しをすべて網羅するOSレベル監視ではなく、現在の製品のctypes/API境界を対象とする。
- candidate_causes: code=試験契約の混同/製品の前景API誤呼出し; environment=外部デスクトップ変化またはTcl到達不可; data=初回子JSON欠落。
- and_gate: 試験の偽陽性は誤った判定契約と前景観測の変化が同時に必要（今回の注入実験では両者を実証）。初回原本で後者が発生したかは未確定で、原本の根本原因として確定しない。

## Specialist Review

- python-expert-best-practices-code-reviewは利用可能スキル一覧およびローカル2スキルルートの検索で未検出。再委任禁止のため追加エージェントは作らず、狭い境界・例外/後始末・負対照を自分で確認する。外部専門家レビュー実施済みとは記録しない。

## Resolution

- root_cause: 確認した試験欠陥はデスクトップ全体の前景観測と製品の副作用の混同。初回原本で前景が変化した原因は採取欠落で未確定。
- confirmed_test_defect: デスクトップ全体のHWND前後一致は製品非干渉の必要条件でも十分条件でもなく、観測変化で偽陽性になる。原本の前景変化の発生原因は子JSON/HWND情報欠落で未確定。
- fix: 担当2テストのみ。前景値を診断として保存し、API境界/全投稿先・種別/呼出TIDの検査へ置換。外部観測変化の模擬正対照と禁止副作用の負対照を追加。
- verification: 対象23 passed / 1 warning / 4.13秒。旧判定差戻し1 failed / 22 deselectedでRED再確認。全件初回の198 passed / 1 failedはGSD正本不整合による停止として保持。Phase04の完了表示をIn Progressへ戻した後、DoD19 passed、最終の単一全件2047 passed / 1 warning / 427.01秒 / exit0。118入力前後hash一致。Ruff native全体check/format exit0、AST成功。今回試験修正の品質確認であり、初回原本原因の確定・Phase完了・出荷承認ではない。
- guardrail_target_test: pass（観測変化模擬を含む対象23件）
- guardrail_mutation_check: skipped（Stryker未構成。禁止API等の5負対照は別途実施し、mutation成功へ代用しない）
- guardrail_no_op_deletion: pass（旧判定除去は実証した誤った因果判定を置換するため。診断値/回復閾値/worker停止を保持し、厳格API検査と正負対照を追加）
- guardrail_adjacent_tests: 対象ファイル内の既存寿命/entry例外後始末/対照群はpass。GSD正本整合修正後、リポジトリ全件2047 passed。
- guardrail_revert_and_reconfirm: pass（旧判定への一時差戻しで同じFalse失敗。再適用後hashは対象成功時と同一）
- guardrail_verdict: accepted（今回確認した試験欠陥の修正に限定。初回原本原因/実機受入/出荷判定は含めない）
- files_changed: tests/test_startup_wake.py; tests/startup_wake_child.py; このデバッグファイル; startup-wake-foreground-evidence/ 配下の今回専用採取器・証拠。親によるGSD正本整合修正はROADMAP.md/STATE.md、開発履歴.mdには既存v1.10.1節へ追記。製品Python/版/README/配布物は変更なし。
- commit: 既存untrackedの2テスト全体をstageすると今回以前の作業を含むためcommitしない。親へ引き継ぐ。
- release_scope: Phase04の完了表示を現行検証未完了の実態へ戻した。04-VALIDATION draftと04-VERIFICATION staleは保持、Phase06実機受入・EXE再生成・出荷は未実施。原本失敗報告/台帳は変更していない。

## 親による最終品質確認（2026-10-28）

- 原因: 全件初回のDoD失敗は、前回Phase04ゲート失敗でVALIDATIONをdraftへ戻した際にROADMAPの完了チェックが残ったGSD正本不整合。DoDやVALIDATIONを緩和せず、6/6 SUMMARYを保持してPhase04をIn Progressへ戻し、STATEの正式完了数を1/3へ整合した。
- DoD確認: `startup-wake-foreground-evidence/dod-state/pytest.txt`、19 passed / 2 warnings / 0.53秒。
- 最終全件: `startup-wake-foreground-evidence/full-native-after-state/pytest.txt`、2047 passed / 1 warning / 427.01秒。既知のPyMuPDF ByteString警告1件のみ。
- 最終実行: 2026-10-28T00:51:00.888Z〜00:58:09.305Z。`.venv/Scripts/python.exe -m pytest -q -x --basetemp=C:\Users\shdwf\AppData\Local\Temp\pf-debug-wake-dd4f021d-884c-48bf-8487-40bea658c42d`。採取器はcollect-final.cjs（以前のcollect.cjsと証拠は保持）。
- 118入力の前後manifest SHA256は `2b6844acd19961efb6e052b2318b2406b248c84d4389945fa595cd38f83e22bb`、ログSHA256は `b66139731b42ca2ce2a47432ece06a1170c6bde80b8018bf661b68da7acada55`。子JSON3件をchildrenへ保存、環境/実行コマンド/collectorとPythonのhashはrun.jsonに記録。
- 統合確認: 親の開始時保護14ファイルとの比較で、差分は担当2テストと開発履歴への今回追記のみ。indexは不変。AGENTS.md/pyproject.toml・製品入力・README/ガイド・既存driverは保持。既存untracked作業と分離できないためcommitなし。
- 限定完了: 実証した試験欠陥を修正し、全件検証済みとしてこのdebugをresolvedにする。初回原本で前景が変化した発生原因は未確定、正式Phase検証と出荷条件は未解除。

## Prevention（今回確認した試験契約の欠陥に限定）

- why_not_caught: 副作用に起因する前景変化と外部観測の変化を分ける正負対照が無かった。初回子JSONの保存もassert後だったため証拠が不足した。
- recurrence_guard: tests/test_startup_wake.pyの非干渉正負試験・native外部観測変化模擬、tests/startup_wake_child.pyの厳格API境界と投稿記録、assert前の子stdout/stderr全体保存。
- limitation: 実OSの前景切替を能動再現していない。将来別ライブラリ経由の全ネイティブ呼出しを監視するOSレベル保証ではなく、現在の見張りのctypes/注入API境界の保証。初回原本原因を回顧的に断定できない。
