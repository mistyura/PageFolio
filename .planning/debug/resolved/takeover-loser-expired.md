---
status: resolved
trigger: "takeover-loser-expired: 06-04 全件pytest(単一プロセス)で tests/test_startup_windows.py::test_takeover_two_candidates_after_confirmed_initialization_death が失敗。初期化中ownerの死亡確認後、2候補の引継ぎ競合で勝者takeover-1はready、敗者takeover-0はobservedが約5秒遅れ5000msでexpired案内(AssertionError: 正常tracerで失敗案内: expired)。1 failed/1968 passed/468.79s(06-03同条件361s)。証拠: .planning/phases/06-release-validation/06-04-STOP.md、06-04-task1-full.txt、basetemp C:\\Users\\shdwf\\AppData\\Local\\Temp\\pf06_04_full_8495defe95524f18a9f6a77372280aab。DEP-05/owner_missing/通知前景/Tclとは未分類。再実行greenを合格扱いにしない。"
created: 2026-10-24
updated: 2026-10-24
---

# Debug: takeover-loser-expired

## Symptoms

- **期待:** 初期化中 owner の死亡確認後、2 候補のどちらが引継いでも両 child が returncode 0（敗者は勝者へ正常に合流）。
- **実際:** 敗者 takeover-0 が observed を約 5 秒遅らせて書き（16:30:54.344、起動から約 48.9 秒）、5000ms で expired 案内。勝者 takeover-1 は ready。
- **エラー:** `AssertionError: 正常tracerで失敗案内: expired`（`tests/test_startup_windows.py:193` `assert child.returncode == 0`、呼出元 1168 `_finish`）。出力 `起動引継ぎ: 6228 / existing / deadline=28915453`。takeover-0 の resource-audit.json: owner_result=existing、death_confirmed=true、takeover_claim=existing、terminal_result=expired、elapsed=5000、notice_reason=expired。死亡確認 owner は state=initializing、pid=6228。
- **時期:** 2026-10-24 の 06-04 全件で初観測。06-01〜06-03 の全件 6 回では合格。今回の全件は 468.79s で 06-03 同条件（361.39s）より約 30% 長い。
- **再現:** 単一プロセスの全件 pytest。単体再現は未確認。

## 制約

- 再実行で green になってもゲート合格の根拠にしない（CLAUDE.md リリースゲート）。
- 初回失敗ログ `.planning/phases/06-release-validation/06-04-task1-full.txt` と basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_04_full_8495defe95524f18a9f6a77372280aab` は原本保持（変更・削除しない）。
- 期限延長・skip・除外でテストを通さない。製品の期限契約（5000ms 等）を無断変更しない。
- 既存 dirty（.planning/STATE.md、config.json、state.json、debug/dep-05-regression.md、debug/simultaneous-owner-missing.md、05-CONTEXT.md、requirements.txt、開発履歴.md）は stage/commit しない。
- 関連する未解決 session: `dep-05-regression.md`、`simultaneous-owner-missing.md`（混同せず、関連があれば根拠付きで記録）。
- pyproject.toml を編集しない。修正時は ruff check/format・AST・単一プロセス全件 pytest を通す。

## Current Focus

status_note: RESOLVED。根因確定（H1）→ 利用者が案Aを選択（テストのみ是正、製品コードと5000ms期限は不変、案Bは今回記録せず、案Cは不採用）→ 修正適用・検証済み（下記 Resolution）。
hypothesis: H1 CONFIRMED = 敗者の結果は「勝者の引継ぎ後の初期化時間（started->ready）」だけで決まる。勝者初期化が約4.9秒を超えると、敗者は自分の起動時刻から数える5000ms期限（D-06）内に勝者のreadyを得られず、仕様どおり expired を返す。テストの正常tracer（takeover-* ロール）は expired を一律AssertionErrorにするため、仕様上正当な結果を失敗として扱う。敗者のロジック欠陥ではない。
test: 完了。8実走の用量反応（下記Evidence）と、過去全件合格7回の敗者elapsed=勝者init+約90〜125msの一致。
expecting: 満たされた（init 4172/4266/4531ms は合格、5250/5953ms は同一シグネチャで失敗、6秒超は別assertion(1160行)で失敗）。
next_action: なし（案A適用・単一プロセス全件 pytest 合格・コミット・アーカイブ済み）。

reasoning_checkpoint:
  hypothesis: "勝者の started->ready が敗者の残り待機時間（約4.9秒）を超えると、敗者は D-06 の5秒待機上限で expired になる。試験の正常tracerは takeover-* で expired を許さず returncode=1 にするため失敗する。"
  confirming_evidence:
    - "06-04 失敗runの実測: 勝者ready_tick(28915531) は敗者deadline(28915453)より78ms遅い。敗者observed mtimeは期限26ms前まで更新（停止せずポーリング）。"
    - "全件合格7回の敗者elapsed = 勝者(ready_tick-started_tick) + 約90〜125ms（例 4375→4469, 3079→3188, 2266→2391）。敗者は勝者のreadyに追随して合流している。"
    - "単体8実走: 勝者init 4172/4266/4531ms → PASS、5250/5953ms → 敗者expired(L193、06-04と同一シグネチャ)、6秒超 → 勝者readyが6秒内に出ずL1160で失敗。いずれも敗者はexpired/5000ms。"
  falsification_test: "勝者initが5秒を大きく超えているのに敗者がexpiredにならない、または勝者initが2〜3秒で敗者がexpiredになる観測があれば反証される。8実走+過去8全件ではどちらも無い。"
  fix_rationale: "未適用。根因は『実アプリ初期化(1〜7秒で変動)』と『固定5000ms待機上限』の結合であり、期限は製品契約(D-06/D-08)。よって製品期限は変えず、(A)試験側を仕様どおりの期待値(expiredを条件付きで許容・待機を30秒化)へ是正する、(B)初期化遅延そのものは別課題とする、が候補。"
  blind_spots: "初期化遅延が1〜7秒に揺れる直接原因は、最初の絵文字(U+1F441)描画時のTkフォント代替探索と特定したが、揺れの外因（Defender・他プロセス負荷・フォントキャッシュ）の寄与割合は復元不能。06-04時点の負荷は再現できない。"
  candidate_causes:
    - "[code/test] 試験oracleの前提誤り: takeover-* の show_notice が expired を許さない（simultaneous-* は dep-05 で許容済み）。確定。"
    - "[environment] 実アプリ初期化が1〜7秒に揺れる（最初の絵文字ボタン生成でTkフォント代替探索が走る）。確定（寄与の主因）。"
    - "[code/product] 敗者のポーリング/合流ロジック欠陥。棄却（過去7回の合流成功、期限直前までのポーリング継続）。"
    - "[config] 5000ms期限の設定。製品契約D-06どおりで誤りではない。"
  and_gate: "yes。失敗には2条件が同時に必要: (1) 環境要因で勝者初期化が約4.9秒超、(2) 試験oracleが expired を許さない。片方だけでは失敗しない（(1)のみ→製品は仕様どおり案内、(2)のみ→初期化が速いので合格）。"

## Eliminated

- hypothesis: 敗者(takeover-0)のobservedが約5秒遅れた（敗者の起動/観測の停止・遅延）。
  evidence: Path.touchは既存ファイルのmtimeを更新する。54.344は最終観測時刻で、初回観測は勝者killより前（testが_wait_fileで確認済み）。敗者は期限26ms前まで25ms間隔で観測を継続していた。
  timestamp: 2026-10-24

- hypothesis: 敗者の合流ロジック（takeover敗北後の再観測・pipe接続）に欠陥がある。
  evidence: 全件合格7回で敗者は勝者ready直後（+約90〜125ms）に foreground_denied/completed で合流。失敗runでも敗者は勝者(pid=19256, initializing)を正しく再観測し、readyが期限後だっただけ。製品コード(pagefolio/)は06-03以降無変更。
  timestamp: 2026-10-24

- hypothesis: 製品コード・依存・takeover scenario の変更が初期化を遅くした。
  evidence: pagefolio/ は06-03コミット以降無変更。.venv依存dist-infoは10-22 19:25以降無変更。3925d5fの追加は simultaneous-*/notice-case-owner 専用で takeover-* 経路は不変。
  timestamp: 2026-10-24

- hypothesis: 新規フォント導入などOS構成変更が原因。
  evidence: C:\Windows\Fonts は689ファイル、最新mtimeは09-30。06-03〜06-04の間に追加なし。
  timestamp: 2026-10-24

## Evidence

- timestamp: 2026-10-24
  checked: basetemp test_takeover_two_candidates_a0 のファイル mtime とresource-audit/ready JSON（原本は読取のみ）
  found: |
    owner(initializing-owner) ready 48.944、takeover-0/1 起動 48.95、takeover-1 observed 49.4168、takeover-0 resource-audit.json 54.370（=期限28915453の到来時刻）、takeover-1 ready 54.4487、stop-all 54.4518。
    takeover-1: started_tick=28910500、elapsed=31（request_activationが31msでprimary）、ready_tick=28915531、takeover_claim=acquired。
    takeover-0: started_tick=28910453、deadline=28915453、takeover_claim=existing（敗北）、terminal_result=expired、elapsed=5000。
    勝者のready_tick(28915531)は敗者のdeadline(28915453)より78ms遅い。
  implication: 敗者はowner死亡直後に引継ぎ競合で敗北し、勝者がreadyを公開する前に自分の5000ms期限が尽きた。勝者の started->ready は5031ms。

- timestamp: 2026-10-24
  checked: 敗者の `observed` mtime が54.344まで更新されている理由（Path.touch は既存ファイルのmtimeを更新する）
  found: Backend._observe_owner が呼ばれる度に touch。敗者は敗北後、勝者(新pid=19256, state=initializing)を観測し続け、25ms間隔で not ready を待機していた。
  implication: 「observedが5秒遅れた」は初回観測の遅延ではなく、最終観測時刻。敗者は期限直前まで正常にポーリングしていた（遅延・停止ではない）。症状記述の「約5秒遅れ」は誤読で、観測遅延は無い。

- timestamp: 2026-10-24
  checked: 同一basetemp内の全 ready JSON（43件）の started_tick->ready_tick 分布 vs 過去の全件合格 basetemp 6回
  found: |
    06-04失敗run: min 2734 / median 4516 / p90 5828 ms（takeover勝者は5031）。
    06-03 t2: median 2969、06-03 t1: 2968、06-02 t2: 3172、06-02 t1: 3563、06-01 task2: 3203、06-01 after_debug: 2360、06-01 task1: 2422 ms。
    過去のtakeover勝者 ready: 2266〜4375 ms（06-02 t1 の4375が最大）。
  implication: 失敗runは実アプリ初期化が過去runの約1.5倍遅く、元々4.4秒まで寄っていた余裕が尽きた。勝者初期化は期限5000msの敗者待機の直接の競合相手。

- timestamp: 2026-10-24
  checked: 製品コード・依存・テストscenarioの差分（06-03 t2 full 15:48 と 06-04 full 16:27 の間）
  found: pagefolio/ 配下は 06-03 のコミット以降無変更。.venv の依存dist-infoは 10-22 19:25 以降無変更（requirements.txt dirty はこの更新と一致、06-01 以前から）。tests/test_startup_windows.py は 3925d5f(+496行)で変更されたが、追加分は simultaneous-* ロール専用の _audit_exit/native監査/_ForegroundAudit(notice-case-owner) で、takeover-* ロールの経路は無変更。
  implication: 製品・依存・takeover scenario の変更は初期化遅延の原因ではない。環境負荷（他プロセス、メモリ、Defender等）が候補。

- timestamp: 2026-10-24
  checked: 現在のマシン状態（調査開始時のスナップショット）
  found: CPU 約35%使用中、空きメモリ 2.85GB/16.4GB、MsMpEng 606MB、codex/claude/Code/chrome 常駐。16論理CPU。
  implication: 調査時点でも他作業の負荷があり、環境ノイズは日常的に存在する（失敗時点の負荷は復元不能）。

- timestamp: 2026-10-24
  checked: 過去の全件合格 basetemp 7回 + 06-04 失敗 run の takeover 敗者/勝者 audit（読取のみ）
  found: |
    合格7回の (勝者 ready_tick-started_tick) → (敗者 elapsed, terminal):
    2266→2391 completed / 2344→2422 foreground_denied / 3079→3188 foreground_denied / 4375→4469 foreground_denied / 3062→3156 fd / 3125→3235 fd / 2922→3031 fd。
    06-04 失敗: 勝者 5031 → 敗者 expired 5000。
  implication: 敗者の終了時刻は勝者init+約90〜125msに追随する。余裕が最小だった06-02 t1でも勝者initは4375msで、5000msまで約530msしか無かった（元々薄い余裕）。

- timestamp: 2026-10-24
  checked: 単体実行（CLAUDE.md 切り分け手順1）。fresh basetemp、tests/test_startup_windows.py::test_takeover_two_candidates_after_confirmed_initialization_death を8回（+事前に6回）
  found: |
    現在の環境では単体でも再現する（再現性あり）。8回の内訳:
    PASS 3回（勝者init 4172 / 4266 / 4531ms、敗者elapsed 4250 / 4344 / 4625ms）。
    L193 失敗 2回（勝者init 5953 / 5250ms、敗者 expired/5000ms）= 06-04 と同一シグネチャ。
    L1160 失敗 3回（勝者readyが kill 後6秒内に出ず `assert 0 == 1`。敗者は expired/5000ms）。
    事前の6回も全て L1160 失敗。
  implication: 失敗は全件実行に固有ではなく、勝者初期化時間のみで決まる決定的な用量反応。単体でgreenになってもゲート根拠にならない（今回は単体でも約半数が失敗）。L1160 の `time.monotonic()+6` も同じ時間結合で、06-04 の L193 と同根（勝者init 5〜6秒域か6秒超域かの違い）。

- timestamp: 2026-10-24
  checked: 初期化が遅い箇所の特定。PDFEditorApp 構築を cProfile とウィジェット単位計時で計測
  found: |
    PDFEditorApp(root) が 9〜11 秒（import 0.5秒、Tk root 1秒未満）。その大半は _tkinter.tkapp.call で、ttk::button 1個（text="👁 閲覧モード"）の生成だけで 6879ms（全体 9.25 秒）。他の28個のTButtonは合計約0.5秒。
    マイクロベンチ（新規プロセスで最初の1回）: U+1F441「👁」を含むボタンは 2901〜5750ms、同一プロセス内の2回目以降や ASCII/日本語/他の絵文字(✂, 📄)は 0.7〜73ms。フォント直接計測(font.measure)でも default 4934/4703/1031ms、Segoe UI Emoji 明示でも 4194/2747/1019ms と大きく揺れる（同一マシン・同一コードで1〜5秒）。
  implication: 実アプリ初期化の揺れの主因は、プロセスごとに1回だけ発生する最初の絵文字(U+1F441)のTkフォント代替探索で、OS側の負荷(Defender/他プロセス/フォントキャッシュ)で1〜7秒に変動する。製品の起動時間自体が環境次第で2〜10秒になるのは別の実害（UX）だが、本件の失敗原因の一部であり、期限契約の問題ではない。

- timestamp: 2026-10-24
  checked: 製品契約（04-CONTEXT D-05〜D-08）と既存の関連試験・関連session
  found: |
    D-05/D-06: 既存画面の準備待ちは最大5秒、超えた場合だけ案内。D-07: 引継ぎは1回のみ。D-08/04-CONTEXT:72: 再試行で5秒の待機期限を更新しない。つまり敗者の expired は初期化が5秒を超えたときの仕様どおりの結果。
    tests/test_startup_windows.py:967 は同族の simultaneous 試験で「初期化が5秒を超えた場合のexpiredは仕様どおり」と明記し、`5000 <= elapsed < 6000` を検証。2648行の tracer も `simultaneous-` ロールの expired だけを許容。待機は _BOOTSTRAP_TIMEOUT(30秒) に分離済み。
    takeover 試験だけがこの是正を受けておらず、(1) show_notice が takeover-* の expired を AssertionError にする（2646-2649行）、(2) 勝者ready待ちが6秒固定（1154行）、(3) 子の終了待ち5秒固定（1161行）。
  implication: dep-05-regression の既解決根因「初期化が5秒を超え得る/正常expiredの不許可という試験の前提誤り」と同族の取りこぼしが takeover 試験に残っていた。同一の事象ではない（dep-05 は focus 失敗と communicate EOF、シグネチャが異なる）。

- timestamp: 2026-10-24
  checked: 関連 session との関係（混同しないための記録）
  found: |
    dep-05-regression: 関連あり（同じ環境変数=初期化の長さ、同じ試験前提誤りの族）。ただし本件の直接原因は takeover 試験の oracle と待機固定で、dep-05 の未解決仮説（H1〜H3: pipe EOF/終了遅延）とは別。dep-05 の再発監視条件には該当しない。
    simultaneous-owner-missing: 根拠のある関連なし（owner_missing は後続二次の owner 不在、本件は敗者の期限切れ expired。シグネチャが異なる）。
    通知前景/Tcl TclError(CLAUDE.md 症状①②): 本件に TclError / STATUS_BREAKPOINT は無い。関連の根拠なし。
  implication: 本件を既存未解決 session の再発として扱わない。dep-05 側の未解決を解除する根拠にも使わない。

- timestamp: 2026-10-24
  checked: 修正前の回帰試験（Red）。勝者初期化を6.5秒遅らせる takeover-slow ロール＋回帰試験を先に追加し、tracerは未修正のまま単体実行（fresh basetemp %LOCALAPPDATA%\Temp\pf_dbg_takeover_fix_red_2249410481）
  found: |
    FAILED（1 failed, 15.14s）。06-04 と同一シグネチャ:
    `AssertionError: 起動引継ぎ: 10648 / existing / deadline=31329484` + `tests\test_startup_windows.py:2715 show_notice: raise AssertionError(f"正常tracerで失敗案内: {reason}")` + `AssertionError: 正常tracerで失敗案内: expired` + `assert 1 == 0`（L193 `_finish`）。
  implication: 勝者初期化が敗者の5秒期限を超える経路を決定的に再現できた。失敗理由は根因（tracerが expired を許さない）と一致し、他の理由ではない。

- timestamp: 2026-10-24
  checked: 修正後（案A）の検証
  found: |
    - 同じ回帰試験 + 既存の自然初期化試験: 2 passed（16.80s）。
    - ruff check . 合格 / `ruff format --check`（git 管理下の全 .py 116 件）合格 / pagefolio.py の AST 構文確認 OK。
    - 単一プロセス全件 pytest（fresh basetemp %LOCALAPPDATA%\Temp\pf_dbg_takeover_fix_full_*）: 1970 passed, 0 failed, 0 error, 429.91s（7:09）。除外なし・再実行なし。06-04 時点は 1969 件（1 failed/1968 passed）で、差分は追加した回帰試験 1 件。
  implication: 同一シグネチャの失敗は Red で再現・修正後に解消。製品コードは未変更。

- timestamp: 2026-10-24
  checked: 修正中の副作用の発見と回復（記録）
  found: |
    CLAUDE.md の `ruff format .` を実行したところ、ruff 0.17.1 が Markdown 内の ```python コードブロックも整形し、62 ファイル（.planning/ 配下の md、docs/*.md、tracked）が書き換わった。
    tracked だった 60 ファイルは `git restore --source=HEAD` で復元（事前 dirty の8ファイルは mtime が古く ruff の対象外であることを確認し、restore 対象から除外）。
    未追跡の `.planning/phases/04-startup-control/04-PATTERNS.md` と `.planning/phases/05-config-notification/05-PATTERNS.md` は git に原本が無く、バイト単位で復元できない（変更は ```python コードブロック内の空行追加等の整形のみ）。
    以降は `ruff format --check $(git ls-files '*.py')` のように .py に限定して実行した。
  implication: 試験コードの修正自体は tests/test_startup_windows.py のみ。上記2つの未追跡 md の整形差分は利用者への申し送り事項。

## Resolution

oracle_type: specified（04-CONTEXT D-05〜D-08: 既存画面の準備待ちは最大5秒、超えた場合だけ案内、引継ぎ後も期限は更新しない）。敗者の expired は「勝者の準備が敗者の期限近傍かそれ以後」の場合に限って合格にし、それ以外は従来どおり失敗にする。

root_cause: |
  （確定）
  takeover の敗者は D-06 の5秒待機上限（自分の起動時刻起点）の中で、勝者が引継ぎ後に実アプリを初期化して ready を公開するのを待つ。勝者の初期化時間（実測 2.3〜7秒超、最初の絵文字 U+1F441 のTkフォント代替探索が環境負荷で1〜7秒に揺れる）が敗者の残り約4.9秒を超えると、敗者は仕様どおり expired になる。
  一方、試験の正常tracer（takeover-* ロール）は expired を AssertionError にし、勝者ready待ちも6秒固定のため、仕様上正当な結果を失敗にする。失敗には「初期化が約4.9秒超」(環境)と「試験が expired を許さない」(試験前提)の2条件が同時に必要（AND）。
  06-04 では勝者 started->ready=5031ms、敗者 deadline の78ms後に ready。
fix: |
  案A（試験側のみ。製品コードと5000ms期限は不変）を tests/test_startup_windows.py に適用（コミット 3e56452）。
  1. takeover-* の tracer `show_notice` は理由が expired の場合のみ許容（他の理由は従来どおり AssertionError）。
  2. 勝者ready待ちを6秒固定から `_BOOTSTRAP_TIMEOUT`(30秒) へ分離。子の終了待ち5秒（ready観測後の待機。敗者はreadyの直後に合流するか自身の5秒期限で終了するため足りる）は据え置き。
  3. 敗者の結果を audit から条件付きで検証: terminal_result が completed/foreground_denied、または expired かつ `5000 <= elapsed < 6000` かつ `勝者 ready_tick - 敗者 started_tick >= 4500`。既存の constructed==1 / takeover_claim acquired==1 / death_confirmed は維持。
  4. 勝者初期化を6.5秒遅らせる `takeover-slow-N` ロールと回帰試験 `test_takeover_loser_expires_when_winner_initialization_exceeds_deadline` を追加（expired経路を決定的に固定）。自然初期化の既存試験は共通ヘルパー `_takeover_race` を使う形へ整理。
verification:
  target_test: { result: pass, detail: "回帰試験は修正前に同一シグネチャで FAIL（L193 正常tracerで失敗案内: expired）、修正後に PASS。既存の自然初期化試験も PASS（2 passed）" }
  mutation_check: { result: skipped, reason_if_skipped: "Stryker は JS 用で Python/pytest プロジェクトに未導入。代替としてtracerの許容を外した状態（=修正前）で回帰試験が FAIL することを確認済み", mutant_killed: "tracer許容を外した変異は回帰試験が検出（Red）" }
  no_op_deletion: { result: pass, deletion_justified_by_rca: true, note: "差分は +58/-7 で追加主体。oracleの緩和（expired許容）はD-06契約に基づくRCAで正当化し、緩和は expired・5000<=elapsed<6000・勝者ready-敗者開始>=4500 の条件付き。expired以外の失敗案内は従来どおり AssertionError" }
  adjacent_tests: { result: pass, suites_run: ["単一プロセス全件 pytest 1970 passed / 0 failed / 0 error / 429.91s（7:09）、除外・-k・--ignore・再実行なし"] }
  revert_and_reconfirm: { result: pass, bug_returned_on_revert: true, fixed_on_reapply: true, note: "tracer未修正の状態で回帰試験が FAIL（Red）、案A適用後に PASS" }
  guardrail_verdict: accepted
files_changed:
  - tests/test_startup_windows.py

## 修正案（案Aを利用者が選択し適用済み。案Bは今回記録せず、案Cは不採用）

- 案A（採用・試験側のみ。製品と5000ms期限は不変）: tests/test_startup_windows.py の takeover 試験を、simultaneous 試験で既に確立済みの仕様どおりの期待値へ揃える。
  1. 2646-2649行の tracer: `role.startswith(("simultaneous-", "takeover-")) and reason == "expired"` を許容（それ以外の理由は従来どおり AssertionError）。
  2. 1154行の勝者ready待ちを `_BOOTSTRAP_TIMEOUT`(30秒)へ分離（dep-05 と同じ扱い）。
  3. 敗者の結果を無条件に許すのではなく、audit から条件付きで検証: `terminal_result in {completed, foreground_denied}` か、`expired` の場合は `5000 <= elapsed < 6000` かつ `勝者ready_tick - 敗者started_tick >= 4500`（勝者の準備が本当に期限近傍/後だったときだけ許容）。それ以外は失敗のまま。既存の `constructed==1` / `takeover_claim acquired==1` / `death_confirmed` は維持。
  4. 追加で、勝者初期化を決定的に遅らせる役割（simultaneous-slow と同様のsleep）で expired 経路を固定し、速い場合の合流経路は自然な初期化で検証する二面の回帰試験にする。
- 案B（別課題・製品側）: 初期化の揺れの主因（最初の絵文字ボタン生成で1〜7秒）の軽減。起動時間のUXとして独立に価値があるが、UI文言/フォントに触れるため /gsd-quick か別debugで扱う。本件の修正としては採らない。
- 案C（不採用推奨）: 待機期限の延長/引継ぎ時の期限更新。D-06/D-08/04-CONTEXT:72 に反し、製品契約を変える。

## 調査で作成したもの（原本は不変）

- スクリプト（scratchpad）: scan_ready.py / phase_time.py / prof_init.py / widget_time.py / tk_bench.py / glyph_bench.py / glyph2.py / dose.py
- 単体実行の basetemp: %LOCALAPPDATA%\Temp\pf_dbg_takeover_*（調査用。不要なら削除可）
- 調査段階では製品コード・テストは未変更。修正はコミット 3e56452（tests/test_startup_windows.py のみ）。
- 修正検証の basetemp: %LOCALAPPDATA%\Temp\pf_dbg_takeover_fix_red_*（Red）/ pf_dbg_takeover_fix_green_*（単体Green）/ pf_dbg_takeover_fix_full_*（全件）。不要なら削除可。06-04 の原本（06-04-task1-full.txt と basetemp pf06_04_full_8495defe...）は未変更。
- 案B（初期化の揺れの主因＝最初の絵文字 U+1F441 のTkフォント代替探索の軽減）は今回別課題として記録していない（利用者判断）。
