---
phase: 06-release-validation
plan: "04"
subsystem: release-validation
tags: [pyinstaller, real-build, sha256, file-protection, connection-proof, fake-ocr, evidence-audit]

requires:
  - phase: 06-release-validation
    provides: 06-01 の配布CLI、06-02 の版同期、06-03 の検証CLI(release_uat_support)と resume_contract
provides:
  - "06-BUILD-EVIDENCE.json: 製品修正後の新世代(世代2)で実PyInstaller 初回/再buildを2回取り直した最終binary/tree hash(世代1は保持)"
  - "06-PROTECTION-EVIDENCE.json: 保護停止3種・起動時保持3種・更新コピー2種・設定障害X01〜X05・接続実証2種(ocr-single/w05b-modal)の実測"
  - "06-UAT-PREPARATION.md: 世代2のrun参照"
  - "06-04-drivers/assemble_protection.py: 生記録から保護証拠を機械的に組み立てる(補足JSON対応)"
affects: [06-05, 06-06]

plan_head_before: e9d2170c9891f1a55b5ab569aa725d09b819e149
plan_head_after: b27eacaf7b76b0c3ae1011bec377ac14e7d1321d

actuals:
  tokens: 148382
  tasks: 2
  commits: 16

tech-stack:
  added: []
  patterns:
    - "接続実証の端末回答が誤貼り付けなどで観測にならない場合、session原本は編集せず、補足回答を『出所(chat relay)・理由』付きで別キーに保持する"
    - "無効試行(中断・誤入力)は failed_connection_attempts に分離し、証拠(run_id走査)に含めない"
    - "監査の機械判定は弱めない。成立の読みが分かれる点は status=recorded-audit-failing として未解決のまま次工程へ渡す"

key-files:
  created:
    - .planning/phases/06-release-validation/06-04g2-connection-supplement.json
    - .planning/phases/06-release-validation/06-04g2-audit-preparation-only.json
    - .planning/phases/06-release-validation/06-04g2-audit-preparation-only-3dab246a-failed.json
    - .planning/phases/06-release-validation/06-04g2-task2-full.txt
  modified:
    - .planning/phases/06-release-validation/06-BUILD-EVIDENCE.json
    - .planning/phases/06-release-validation/06-PROTECTION-EVIDENCE.json
    - .planning/phases/06-release-validation/06-UAT-PREPARATION.md
    - .planning/phases/06-release-validation/06-04-drivers/assemble_protection.py

key-decisions:
  - "接続実証の途中で製品バグ(OCRダイアログがollama選択時もLM Studioへ送信)が見つかったため、利用者判断で製品を修正し、06-03 resume_contract に従い build/保護/接続を新世代で取り直した。世代1の証拠は previous_generations に原文保持"
  - "引継ぎ敗者の expired(takeover-loser-expired)は試験側の前提誤りと確定し、利用者判断(案A)で試験のみ是正。製品コードと5000ms期限(D-06)は不変"
  - "ocr-single の端末回答『--- Page 1 ---』は複数行クリップボードの誤貼り付けとして観測に採らず、原本のまま保持。利用者がチャットで述べた『5.期待通りの表示を確認』を出所明記で補足"
  - "w05b-modal は先の有効試行(3dab246a…)が準備監査(--preparation-only)の peer_returned_to_modal=false で不成立だった。判定を弱めず保持したうえで、利用者の判断で同じ未変更シナリオを再実行した 9cea6581… を準備証拠として採用し、監査は exit 0 で成立した。実際のダブルクリック起動での前景挙動は 06-05-02 の W05b 本受入で人手確認する"

requirements-completed: []

duration: 約5時間(2世代・debug迂回2件・製品修正を含む。待機を除く実作業時間は未計測)
completed: 2026-10-24
status: complete
---

# Phase 06 Plan 04: 実build・ファイル保護・接続実証 Summary

**製品修正後の新世代で、v1.10.0 の実PyInstaller 初回/再buildを取り直し、保護停止・起動時保持・更新コピー・障害X01〜X05と接続実証2種を実配布EXE上で実測・記録した。w05b-modal は先の試行で peer 後の前景が PageFolio 本体に戻らず準備監査が不成立だったが、利用者の判断で同じ未変更シナリオを再実行した run `9cea6581…` を採用し、準備監査(`--preparation-only`)は exit 0 で成立した。ただし受入ではなく(`phase_complete=false` / `release_allowed=false`)、実ダブルクリックでの前景挙動は 06-05 へ持ち越す。**

## Performance

- **Duration:** 約5時間(2026-10-24。世代1の途中停止・debug 2件・製品修正・世代2取り直しを含む)
- **Tasks:** 2/2(自動部分と人手確認の記録まで。ただし下記の未達1件あり)
- **Commits (plan_head_before..HEAD, 測定値):** 15(debug迂回・製品修正・再検証コミットを含む。本SUMMARYのコミットは含まない)

## Accomplishments

- **実build(世代2、最終):** 初回(run `262b0f30…`)と再build(run `c937c5a3…`)の2回とも PyInstaller 6.22.3 が実行され exit 0。入力manifest hash は同一(`0874f357…`)、最終tree `3436ac39…`、最終EXE `b3d4a07e…`。2サンプルと正本のSHA-256は双方で一致。初回のtree hash(`757d2d54…`)は履歴ディレクトリに保持。built EXE は自動起動していない。
- **保護停止:** 利用者ファイル(`ocr_custom_prompt.md` / `pagefolio_settings.json` / `ocr_summary_prompt.md`)を置いた再buildは、3種とも build subprocess 開始前の preflight で exit 1 停止し、前後の存在・bytes・hash が一致。
- **起動時保持:** 完全copy内の未改変EXEを normal / corrupt / unreadable の3条件で起動し、起動前→起動安定後の hash が不変、corrupt/unreadable は終了後も原本が起動前と一致。
- **更新コピー:** 同名衝突ありでは選択前にコピーを止め、旧・新とも前後hashが不変。衝突なしではコピー後hash一致かつ旧保持。
- **設定障害X01〜X05:** 外部lock/probe/tmp衝突で成立(X03/X05 は共有違反32で拒否される外部probe、X04 は tmp排他衝突と DELETE拒否probe)。通知文・内部DEBUGログから分類を推測していない。
- **接続実証(世代2):**
  - `ocr-single`(run `cd4dc81a…`): 合成サーバー received → peer → released → completed、attempt `6ee70ff9d65d-1`、POST 1件、再送・拒否・expired なし。
  - `w05b-modal`(採用: run `9cea6581…`): 確認ダイアログ(#32770「確認」 hwnd 57283200)表示・peer 後も同 hwnd が可視かつ foreground が PageFolio 本体(pid 18604)・『いいえ』・同一attempt `6ee70ff9d65d-1` の released → completed(POST 1件、再送・expired なし、completed_seen=True)。利用者の端末入力4件(`ステータス準備中のまま、結果の表示なし ` / `消えずに同じものが前面に出る` / `準備中` / `PageFolio UAT 合成OCR結果`)を逐語で保持。1件目は確認ダイアログではなく OCR ダイアログの状態を述べたもので、確認ダイアログが見えていた根拠は同時刻の自動 window 一覧である(正直に区別して記録)。
  - `w05b-modal`(先の有効試行、superseded: run `3dab246a…`): server は同様に成立したが peer 後の foreground が入力中の PowerShell(pid 24068)のままで `peer_returned_to_modal=false`(原因未確定。入力中の PowerShell が前景だったためとみられる)。破棄せず `failed_connection_attempts` に保持。
- **現行の全件pytest:** 単一プロセス・新規basetemp・除外/再実行なしで `2014 passed, 1 warning in 508.31s`、exit 0。Tcl leak / unraisable / Traceback は 0 件(`06-04g2-task2-full.txt`)。ruff check 合格、Python 124 ファイル format 済み、AST 合格。

## Task Commits

1. **Task 06-04-01: 実PyInstaller初回・再build**
   - 世代1: `1bdd572`(後に superseded)
   - 世代2(最終): `e71ffae`
2. **Task 06-04-02: 保護・起動・更新・障害・接続の実測**
   - 世代1: `78dcfe8`(後に superseded)、`e24c9cc`(宣言済みoverlayの排他lock中も配布copy照合を止めずに記録)
   - 世代2 自動部分: `f62c5ac`
   - 世代2 接続実証の記録: `81e63cd`

**迂回コミット(本計画の測定範囲内):** `89582df` / `cab687e`(tcl-leak-test-ocr)、`52258de` / `7fb41a2` / `202b2c0`(ocr-ollama-uses-lmstudio-url)、`404538a`(Phase 4 再検証)、`94c5fb7`(Phase 5 再検証)、`570b931` / `f169171`(依存版同期・作業記録)。
**測定範囲の直前(`e9d2170` 以前):** `3e56452` / `40cc1be`(takeover-loser-expired)、`dd10ce7` / `6bbaad3`(Phase 4 再検証・Nyquist)。

## Files Created/Modified

- `06-BUILD-EVIDENCE.json` - 世代2の実build2回と最終hash。世代1を previous_generations に原文保持
- `06-PROTECTION-EVIDENCE.json` - 世代2の保護/起動/更新/障害/接続の実測。世代1と不成立試行を保持。status は `complete`(準備段階の接続実証2種が成立。受入ではなく release_allowed=false)
- `06-UAT-PREPARATION.md` - 世代2のrun参照ブロック
- `06-04-drivers/assemble_protection.py` - 生記録から機械的に証拠を組み立て。補足JSON(`--supplement-json`)追加、既存キー上書きと complete への変更を拒否
- `06-04g2-connection-supplement.json` - 補足回答・不成立/superseded 試行(7e4629e4…, 3dab246a…)の入力。状態格下げ(status_override)は 9cea6581… 採用により不要となり削除
- `06-04g2-audit-preparation-only.json` - 準備監査の結果(採用試行 `9cea6581…` で exit 0・ok=true・reasons なし。`phase_complete=false` / `release_allowed=false`)
- `06-04g2-audit-preparation-only-3dab246a-failed.json` - 先の試行(`3dab246a…`)時点の不成立結果(保持)
- `06-04g2-task2-full.txt` - 現行の全件pytest生ログ

## Decisions Made

key-decisions を参照。要点は、(1) 製品バグ発見後は新世代で取り直す、(2) 試験側の誤りと製品側の誤りを分けて扱う、(3) 観測にならない端末回答は原本を保持して補足で補う、(4) 監査の不成立は弱めず未解決として渡す。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 引継ぎ敗者の expired を一律失敗にする試験(takeover-loser-expired)**
- **Found during:** Task 06-04-01(世代1の前提となる全件pytest)
- **Issue:** `test_takeover_two_candidates_after_confirmed_initialization_death` が敗者の expired を失敗扱いにしていた。敗者は自分の起動から5000ms(D-06)で勝者のreadyを待つ仕様で、勝者の初期化が約4.9秒を超えれば仕様どおり expired になる。製品の欠陥ではなく試験の前提誤り
- **Fix:** 利用者判断(案A)で試験のみ是正。製品コードと5000ms期限は不変。回帰試験は修正前 Red を確認
- **Files modified:** `tests/test_startup_windows.py`
- **Commit:** `3e56452`、アーカイブ `40cc1be`

**2. [Rule 1 - Bug] Tcl leak 警告の誤帰属(tcl-leak-test-ocr)**
- **Found during:** Task 06-04-01/02(全件pytest)
- **Issue:** 実Tkテストが残す循環ガベージが、run_parallel のワーカースレッド内GCで回収されると Tcl leak 警告・Variable.__del__ の RuntimeError になる(GC発火位置依存の潜在バグ)
- **Fix:** 利用者選択のテスト基盤のみの是正。`tests/conftest.py` の teardown 直後にメインスレッドで `gc.collect()`、回帰ガード `tests/test_gc_barrier_guard.py` を新設。製品コード変更なし
- **Commit:** `89582df`、アーカイブ `cab687e`

**3. [Rule 1 - Bug] ollama選択時もOCRダイアログがLM Studioの接続先へ送信(ocr-ollama-uses-lmstudio-url)**
- **Found during:** Task 06-04-02(世代1の接続実証。利用者の2回の試行)
- **Issue:** `_start_ocr` が常に lm_studio_url/model を渡し、`OCRDialog._on_run` の再生成がそれを真値として OllamaProvider を作るため、ollama 選択時の送信先が LM Studio のポートになった。接続エラー文言も「LM Studio」固定。06-03 の fake OCR 検証は OllamaProvider を直接呼んでおり、ダイアログ経路を通っていなかった
- **Fix:** `resolve_local_endpoint` を追加して接続先を一本化、エラー文言を `{provider}/{url}` 化(`52258de`)。関連して LLM 設定変更後に表示が古いまま残る問題(別根因)を `7fb41a2` で修正。回帰試験は修正前 Red(28 FAIL / 5 FAIL)→ Green
- **Files modified:** `pagefolio/ocr.py`、`pagefolio/ocr_dialog.py`、`pagefolio/lang.py` ほか
- **Commit:** `52258de`、`7fb41a2`、アーカイブ `202b2c0`

**4. [Rule 3 - Blocking] 宣言済みoverlayの排他lock中に配布copy照合が止まる**
- **Found during:** Task 06-04-02(世代1の障害X03〜X05の実測)
- **Fix:** 保持者(観測側)の handle から読んだ hash を実hashとして使い、照合を止めずに記録
- **Commit:** `e24c9cc`

### 世代の取り直し(計画どおりの扱い)

製品修正が入ったため、06-03 resume_contract に従い Phase 4(`404538a`)・Phase 5(`94c5fb7`)を再検証したうえで、実build・保護・接続を新世代で取り直した。世代1の証拠(`78dcfe8`)は上書きせず `previous_generations` に原文保持。世代1の不成立試行2件(`release-uat-c75a19aa…` = 表示と実送信先の不一致、`release-uat-034578b2…` = LM Studio への接続失敗)も保持している。

### 運用上の注意

現行 ruff 0.17.1 の `ruff format .` は Markdown 内の python コードブロックも整形する。debug 中に未追跡の `04-PATTERNS.md` / `05-PATTERNS.md` が整形され原本復元不能になった(追跡対象60件は HEAD から復元済み)。以後の format は Python 対象に限定している。

## Auth Gates

なし。実OCRプロバイダへの外部API呼び出しは行っていない(合成サーバーは127.0.0.1専用)。世代1の試行1で利用者が LLM 設定を Gemini に切り替えた結果、実 Gemini へ合成画像のみが送信された疑いがある(製品バグの発見経緯。`.planning/todos/pending/2026-10-24-ocr-dialog-provider-stale.md` 参照)。

## Issues Encountered

- **ocr-single の端末回答:** 利用者が複数行クリップボードを誤って貼り付け、端末の `user_answer` は `--- Page 1 ---`(結果テキストの1行目)になった。観測として採らず、session原本は編集していない。
- **w05b-modal の先の有効試行(3dab246a…):** peer 後の前景が入力中の PowerShell のままで準備監査が不成立。利用者の判断で再実行し、9cea6581… を採用。3dab246a… は「peer後前景不成立(入力中のPowerShellが前景のためとみられる、原因未確定)」として superseded のまま保持。
- **w05b-modal の無効試行:** run `release-uat-7e4629e4…` で、クリップボードの複数行貼り付け(`--- Page 1 ---` / `PageFolio UAT 合成OCR結果`)が端末の問い2件へ自動回答として入り、orchestrator の指示で利用者が中断した。server は received → expired(hold_limit 420) → completed、released なし。成立の証拠に使っていない(`failed_connection_attempts` に分離)。

## Known Gaps(完了条件の未達と持ち越し)

1. **【解消】準備監査 `--preparation-only`:** 先の試行(`3dab246a…`)で `接続(w05b-modal): native modal→peer→いいえ→同処理完了の観測が不足です`(`peer_returned_to_modal=false`)と不成立だった点は、利用者の判断で同じ未変更シナリオ(コミット済み `conn_session.py` の w05b-modal。途中で放棄したダブルクリック版の試作は破棄済みで未使用)を再実行した run `release-uat-9cea65811a8c4db998d9dfcf54e849e6` を採用して解消した。`foreground_after_peer` は hwnd 57283200「確認」 pid 18604(primary、owned_by primary)、監査は exit 0。**監査の判定は弱めておらず、証拠の読み替えもしていない。** ただし 9cea6581… は合成 peer(別プロセスからの2度目起動)による観測であり、**利用者の実際のダブルクリック起動での前景挙動は未確認**。これは 06-05-02 の W05b 本受入で『許可API戻りと実foreground』を別記して人手確認する(利用者判断)。先の不成立原因(入力中の PowerShell が前景のためとみられる)は未確定のまま。
2. **補足回答の出所:** ocr-single の `supplementary_user_answer`(`5.期待通りの表示を確認`)は利用者本人の端末入力ではなく、orchestrator 経由のチャット中継。端末の `user_answer`(誤貼り付け)はそのまま残っている。
   - w05b-modal(9cea6581…)の1件目の回答は OCR ダイアログの状態を述べたもので、確認ダイアログ自体の記述ではない。確認ダイアログの可視は自動 window 一覧による(利用者の言葉としては記録していない)。
3. **EXE が close 要求で終了しない観測:** ocr-single(pid 32156)/ w05b-modal(9cea6581…: pid 18604)とも停止時に `[0] terminated`(所有handleで強制終了)、`[1] already-exited`。X04(write/replace)でも同系統の観測がある。合否判定ではなく観測として 06-05-02 へ持ち越す(製品が保存失敗後の終了で確認を保留する仕様どおりかの判定を含む)。
4. **要件は完了にしない:** V110-DIST-01/02/03・V110-QA-01/02/03 は、人手受入(06-05/06-06)と最終ゲートが未了のため mark-complete しない(`requirements-completed: []`)。`release_allowed=false`。

## Known Stubs

なし。

## Threat Flags

なし(新しいネットワーク入口は追加していない。合成サーバーは127.0.0.1専用で画像を保存しない)。

## Next Phase Readiness

- 06-05(人手受入)へは、上記 Known Gaps 2〜3 と、Gap 1 の持ち越し事項(実ダブルクリック起動での前景確認を 06-05-02 の W05b 本受入で行う)を渡す。準備監査自体は成立済み。
- 世代2の最終EXE(`b3d4a07e…`)・tree(`3436ac39…`)が受入対象。製品コードを変更した場合は 06-03 resume_contract に従い再取得が必要。

## Self-Check: PASSED

- 作成物の存在: 06-PROTECTION-EVIDENCE.json、06-BUILD-EVIDENCE.json、06-04g2-connection-supplement.json、06-04g2-audit-preparation-only.json、06-04g2-task2-full.txt、assemble_protection.py を確認
- コミットの到達性: `1bdd572` `e71ffae` `78dcfe8` `e24c9cc` `f62c5ac` `81e63cd` を確認(上記Task Commits)
- 追記(9cea6581… 採用後): 準備監査 `--preparation-only` を再実行し exit 0 / ok=true / reasons なしを確認(出力は `06-04g2-audit-preparation-only.json`)。`.py` の変更はないため全件 pytest は再実行していない(直近の全件実行は `06-04g2-task2-full.txt` の 2014 passed)
