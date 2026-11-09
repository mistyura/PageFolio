---
status: resolved
trigger: "phase06-w05b-alttab-blindspot: W05b driver (06-05-drivers/uat_row.py) の assess_w05b_return が手動Alt+Tabを自動復帰cleanと誤判定し得る。(1) 入力監視(GetAsyncKeyStateポーリング)がAlt+Tabを一度も記録していない(W05b script run 20261030T235255Z/235905Z/20261031T000340Z の Enter前のAlt+Tabがkey_events空)。(2) run 20261030T235255Z はEnter 0.65秒後に ForegroundStaging→タスクの切り替え(XamlExplorerHostIslandWindow)→確認(#32770) と遷移したのに verdict=clean。run 235905Z/000340Z は PowerShell→確認 の直接遷移。修正方針: peer/quiet区間でタスク切替UI/ForegroundStaging経由の遷移を not-established にする、Alt+Tab未捕捉の原因調査と捕捉(不可なら限界明記)、235255Zを回帰例として --check-w05b に追加。制約: 製品(pagefolio/)・凍結EXE・既存証拠原本・台帳を変更しない、GUI人手受入・全件pytestをしない、commit/addしない、手動切替を自動復帰passにしない。"
created: 2026-10-31T00:05:12Z
updated: 2026-10-31T00:47:00Z
---

# Debug: phase06-w05b-alttab-blindspot

## Symptoms

- **expected:** W05b の自動復帰判定（`assess_w05b_return`）は、確認ダイアログ(#32770)の同一 HWND/PID が「無操作のまま」実前景へ戻った場合だけ clean とする。手動の Alt+Tab による前景移動は必ず not-established にする。入力監視は観測区間のキー押下（Alt+Tab を含む）を記録する。
- **actual:**
  - 入力監視 `key_events` が Alt+Tab を一度も記録していない。利用者は各 run の Enter 前に Alt+Tab で PowerShell へ移っており、前景遷移には「タスクの切り替え(XamlExplorerHostIslandWindow)」「ForegroundStaging」が記録されているが、key_events は空。
  - run `W05b_ocr-close-confirm_at_script-20261030T235255Z.json`: Enter(23:52:48.551Z) の 0.65 秒後に PowerShell→ForegroundStaging→タスクの切り替え(23:52:49.212Z)→確認#32770(23:52:49.355Z) と遷移。タスク切替UIの表示は約0.14秒（素早い Alt+Tab の形）。それでも `return_assessment.verdict=clean`、`returned_transition.from` がタスク切替UI。
  - 対照: run `...20261030T235905Z.json`（PowerShell→確認 23:57:10.905Z 直接）、run `...20261031T000340Z.json`（PowerShell→確認 00:03:09.334Z 直接。その2.19秒後に 確認→ForegroundStaging→タスクの切り替え→PowerShell で not-established）。
- **errors:** なし（誤判定。例外ではない）。
- **timeline:** 2026-10-31 の W05b script 人手受入（4 run、全て not-run attempt として記録済み、pass 0）で発覚。driver の W05b 対応は同日に追加。W01〜W05a でも同じ InputMonitor を使用しており、Alt+Tab 未捕捉が過去行にも及ぶかは未確認。
- **reproduction:** 上記 3 run の session JSON（`.planning/phases/06-release-validation/06-05-evidence/`）の `input_monitor.foreground_transitions` / `key_events` / `w05b.return_assessment` を読む。`--check-w05b` は偽サンプラのみで Alt+Tab 経由の遷移ケースを持たない。

## 制約

- 製品（pagefolio/）・凍結 EXE（世代5 SHA256 66be5df6…）・既存証拠原本・台帳（06-MANUAL-EVIDENCE.json）・UAT を変更しない。
- GUI を伴う人手受入・全件 pytest を実行しない。git commit / add しない。
- 手動切替を自動復帰 pass にしない（blocking anti-pattern）。判定を緩めない。
- InputMonitor は読み取り専用（SendInput / SetForegroundWindow 等を使わない）を維持。
- 変更後は `--check-w05b` / `--check-monitor`、関係する対象テスト、Ruff check / format --check / AST を通す。

## Current Focus

- hypothesis: (確定) (A) `InputMonitor.poll_once` は、前景の所有PIDが PageFolio のときだけ `keys_down()` を呼び、さらに Alt 押下中の押下を明示的に除外し、前面化の瞬間の押下中キーを基準線として捨てる。この設計のため Alt+Tab は(APIの能力ではなく)コード上の構造で key_events に入り得ない。(B) `assess_w05b_return` は「確認ダイアログへ到達した最初の遷移」の `to` しか見ず、その `from`・途中の経由窓(タスク切替UI/ForegroundStaging)を一切見ない。
- reasoning_checkpoint:
    hypothesis: "W05b の clean 誤判定は、(B) assess_w05b_return が観測区間の経由窓(from/to がタスク切替UI/ForegroundStaging)を見ないことと、(A) InputMonitor の key_events が構造上 Alt+Tab を記録できないことの二つが重なって起きた。"
    confirming_evidence:
      - "235255Z の returned_transition.from.class=XamlExplorerHostIslandWindow なのに verdict=clean・reasons=[](assess_w05b_return のコードに from/経由窓の参照が無い)"
      - "poll_once のキー読取りは前景の所有PIDがPageFolioのときのみ+alt中は除外+前面化直後は基準線で捨てる。3 run の samples は 4379〜15039・max_gap 0.011〜0.019 で取りこぼしではなく構造"
      - "修正前ロジックを実記録の再生で確認: 記録時の判定は 235255Z=clean(誤)。修正後は同じ記録が経由窓の理由1件だけで not-established"
    falsification_test: "経由窓(切替UI/ForegroundStaging)を無効化した変異で、235255Z 形の回帰が落ちること(M1: 7件FAIL)。切替キー捕捉を無効化した変異で再現テストが落ちること(M4: 10件FAIL)。"
    fix_rationale: "(B) 観測区間の遷移が切替UI/中継窓を from/to に持つなら不成立にする規則を足す(症状でなく『人のAlt+Tabの形』そのものを判定)。(A) key_events は W01〜W05a の手順汚染判定の目的に合っているので変えず、前景に関係なく Alt/Tab/Win の押下エッジを別系列 switch_key_events に残す。"
    blind_spots: "実機で GetAsyncKeyState が Alt+Tab の Alt/Tab を読めることは人の操作が要るため未確認。素早い Alt+Tab(切替UIなし・null 9ms)は遷移の形では製品の正当な復帰と区別できず、キー捕捉にのみ依存する。"
    candidate_causes:
      - "code: key_events の構造(前景ゲート・Alt除外・基準線破棄)と assess_w05b_return の経由窓非参照"
      - "environment: Win11 の Alt+Tab は explorer.exe の XamlExplorerHostIslandWindow/ForegroundStaging を経由する(OS仕様)。UIPI/管理者権限でキー状態が読めない可能性は未確認"
      - "data: 該当なし(証拠 JSON は正しく経由窓を記録している)"
    and_gate: "yes: 誤判定には (A) キー証拠の不在 と (B) 経由窓の非参照 の両方が必要だった(どちらか一方が有効なら 235255Z は落とせた)。root_cause は2件の連結。"
- test: 修正後の --check-w05b / --check-monitor / --check-diagnostics、変異テスト、記録 helper の dry-run を実施済み。
- expecting: 全て合格・変異で FAIL(達成済み)。
- next_action: 利用者の次回 W05b 実走(人手)で、awaiting-enter の指示された Alt+Tab が session JSON の input_monitor.switch_key_events に載ることを確認する(載らなければ switch-key-capture-blind で自動的に不成立になる)

## Evidence

- timestamp: 2026-10-31T00:10Z
  checked: uat_row.py `InputMonitor.poll_once`（L403-446）, `Win32Sampler.keys_down`（L276-279）, `EdgeTracker.feed_keys`（L307-321）
  found: キーは `if self._fg_info.get("pid") in self._owned:`（前景がPageFolio所有のときだけ）でしか読まない。PageFolio以外が前景の間は `tracker.feed_keys(None)` で基準線を捨てる。前景がPageFolioになった最初のサンプルは基準線（押下中のキーは数えない）。さらに `if not alt:` で Alt 押下中のキー押下は記録しない（コメント「Alt+Tab などのシステムショートカットは入力先を変えない」）。
  implication: Alt+Tab は (1) PowerShell/タスク切替UIが前景の間は読まれない (2) 確認画面が前景になった最初のサンプルは基準線で捨てられる (3) その後 Alt が押されたままの Tab は alt 判定で除外される、の三重で key_events に絶対に入らない。GetAsyncKeyState の取りこぼしではなく設計上の構造。この設計は W01〜W05a の目的(PageFolio内の入力先が動く押下の検出)では妥当だが、W05b の目的(人が前景を動かしていないこと)には不適合。

- timestamp: 2026-10-31T00:12Z
  checked: 3 run の session JSON（W05b_ocr-close-confirm_at_script-20261030T235255Z / 20261030T235905Z / 20261031T000340Z）の `input_monitor.foreground_transitions` / `key_events` / `phase_log` / `w05b.return_assessment`
  found: |
    235255Z: Enter→phase peer=23:52:48.553。peer内で seq7 PowerShell→ForegroundStaging(49.204)、seq8 →XamlExplorerHostIslandWindow「タスクの切り替え」(49.212)、seq9 →確認#32770(49.356)。切替UI表示約0.144秒。returned_transition.from=XamlExplorerHostIslandWindow。verdict=clean・reasons=[]。key_events=[]。samples=4379, max_gap=0.016, errors=[]。
    235905Z: peer内は seq6 PowerShell→確認#32770 の直接遷移(23:57:10.905, peer開始+0.68秒)。verdict=clean。切替UIはawaiting-enter(setup)とw05b-answer(回答後)にのみ存在。key_events=[]。
    000340Z: peer内は seq7 PowerShell→確認#32770 の直接遷移(00:03:09.334)。その後 w05b-quiet内で 確認→ForegroundStaging→切替UI→ForegroundStaging→PowerShell(seq8-11, 00:03:11.52〜13.97)。verdict=not-established・reasons=[foreground-left-modal-after-return, foreground-not-modal-at-quiet-end]。key_events=[]。
    3 run とも awaiting-enter 区間の Alt+Tab(PowerShellへ移る操作。手順で指示している)は切替UI/ForegroundStaging 遷移として記録されているが key_events は 0 件。
  implication: 経由窓が前景遷移に残っているのに判定が見ていない。235255Z の「Enter の0.65秒後の Alt+Tab」は手動の戻しで、自動復帰ではない。key_events 空は仮説 (A) と一致。

- timestamp: 2026-10-31T00:15Z
  checked: uat_row.py `assess_w05b_return`（L747-857）
  found: `returned = [t for t in transitions if t.to.hwnd==hwnd and t.to.pid==pid]` の最初の1件 `first` を取り、`left`（first以後に別窓へ移った遷移）と終端前景だけを見る。`first["from"]`、および観測区間内で SWITCHER_CLASSES / STAGING_CLASSES（L909-910。W05bの判定より後に定義）を経由した遷移は一切参照しない。`key_events`（alt除外の上記構造）も Alt+Tab を含まない。
  implication: 仮説 (B) 確認。経由窓が観測区間内に有っても、返却先が同一HWNDで終端前景が一致し、押下・キーが空なら clean になる。235255Z がこの経路で clean になった。

- timestamp: 2026-10-31T00:20Z
  checked: 過去 pass 24 行（台帳 06-MANUAL-EVIDENCE.json の status=pass, generation 5）の session JSON の前景遷移を読み取りだけで走査（scratchpad に出力）
  found: |
    監視付き23行（W02/settings@production-exe のみ入力監視なし=enabled:false。実EXE行は利用者がPageFolio内を操作する手順のため）。
    いずれも peer 区間(Enter〜harness peer 完了)の遷移は 1 件の「PowerShell→PageFolio側の窓」直接遷移。peer 区間に ForegroundStaging/XamlExplorerHostIslandWindow が現れる行は 0 件。
    例外形は W03/pdf-3page@production-exe のみ: PowerShell→null(hwnd0)→PageFolio（9ms、peer開始+0.22秒、driverが二次起動した約0.35秒の監視）。
    切替UI遷移が現れる区間は awaiting-enter(指示された PowerShell への移動)・w03-preparation(同)・post-peer(観測後に PowerShell へ戻る操作)に限られる。
    実EXE行(W01〜W05a の production-exe)は driver が二次起動し、監視は peer の約0.35秒だけ(41 samples前後)。人の Alt+Tab が入る余地は実質ない。
  implication: 過去 pass が Alt+Tab 由来の偽の復帰に依存した痕跡は見つからない。ただし key_events は Alt+Tab を一度も取れていなかったため「無い」ことの直接証拠は持てず、遷移の形(切替UIの有無)だけが根拠。W01〜W04 の pass 条件は状態・幾何・undo/redo・OCR結果・focus_result で、「無操作の自動復帰」自体を pass 条件にした行は W05b のみ。W05a は利用者の直接回答 foreground=出た を含む。

- timestamp: 2026-10-31T00:22Z
  checked: null(hwnd=0) 経由遷移の扱いの妥当性（W03 exe の例と W01/normal@module awaiting-enter の例）
  found: 素早い Alt+Tab(切替UIが出ない短押し)は PowerShell→null→対象 の形(約9ms)。同じ形が W03 exe の製品側の正当な復帰(PowerShell→null→PageFolio、9ms)にも現れる。
  implication: null 経由の遷移を一律不成立にすると正当な自動復帰も落とす可能性があり、時間幅でも区別できない(いずれも約9ms)。null 経由は遷移の形では判別不能なので、遷移ベースの規則には入れない。素早い短押し Alt+Tab は Alt キー押下エッジの捕捉(新設)で拾う。捕捉が効かない場合の限界として明記する。

- timestamp: 2026-10-31T00:26Z
  checked: ForegroundStaging / XamlExplorerHostIslandWindow を含む前景遷移の形を、証拠・診断 JSON 82 本(06-05-evidence 配下全体と .planning/debug 配下)で分類
  found: ForegroundStaging は必ず XamlExplorerHostIslandWindow と一組で現れ、単独の遷移は 0 件。形は 行き(X→中継→切替UI→…)と戻り(…→中継→PowerShell)に集中。製品の自動復帰(過去 pass 23 行・W05b 直接遷移 2 回)には現れない。
  implication: 観測区間(peer, w05b-quiet)の遷移が切替UI/中継窓を from か to に持てば、人の Alt+Tab(またはタスクビュー)とみなして不成立にしてよい。製品の正当な復帰を落とす実例はない(過去 pass 23 行に 0 件)。

- timestamp: 2026-10-31T00:35Z
  checked: 修正の実装と自己検証(--check-w05b 42 件 ok / --check-monitor 48 件 ok / --check-diagnostics 全合格)、変異テスト、記録 helper の dry-run
  found: |
    変異テスト(driver のソースをメモリ上で書き換えて実行。実ファイルは不変):
      M1 経由窓の規則を無効化 -> --check-w05b が 7 件 FAIL(235255Z 形の回帰・実記録の再生を含む)
      M2 切替キー押下エッジの規則を無効化 -> 5 件 FAIL
      M3 捕捉欠落の規則を無効化 -> 3 件 FAIL
      M4 監視の切替キー捕捉を無効化 -> --check-monitor が 10 件 FAIL
      M5 held-at-phase-start を無効化 -> 1 件 FAIL
      M6 監視クラスに SetForegroundWindow を混入 -> 静的確認が検出して FAIL(ソースを差し替えて確認)
      M7 自己検証(switch-key-capture-blind)を無効化 -> 1 件 FAIL
    記録 helper(06-05-record-w05b.cjs)を --dry-run --session-dir で scratchpad 上の改変複製に通した結果:
      235255Z(捕捉済み仮定)-> "foreground went through the task switcher / ForegroundStaging ... 3 transition(s)" で拒否
      235255Z(捕捉なしの旧記録)-> "Alt/Tab/Win key capture was not active" で拒否
      235905Z(捕捉済み仮定・直接遷移)-> 新規照合は通過し、記録どおりの人の回答 manual_switch=した で拒否(これは既存の照合)
      235905Z に peer 区間の Alt 押下 -> "Alt/Tab/Win key pressed during the unattended observation" で拒否
      235905Z で ret.returned_via_task_switcher を true に手書き -> 拒否
      235905Z で切替UIが出たのにキー記録が空 -> "key capture is blind" で拒否
  implication: 新規の回帰は、規則を外すと確かに落ちる(自己検証が空振りしていない)。記録 helper は driver の判定とは独立に、生の前景遷移・キー記録から手動切替を拒否する。

- timestamp: 2026-10-31T00:40Z
  checked: 過去行 W01〜W05a(台帳 status=pass 24 行)への影響
  found: |
    (1) Alt+Tab を key_events が一度も捕捉できなかったのは全行共通(設計上の構造)。ただし W01〜W04 の pass 条件は 状態・幾何・undo/redo・OCR結果・focus_result で、「人が前景を動かしていない」ことは pass 条件ではない。W05a は利用者の直接回答 foreground=出た を含む。「無操作の自動復帰」自体を pass 条件にした行は W05b だけ。
    (2) 前景遷移の実測(上の走査): 監視付き 23 行の peer 区間は、1 件の「PowerShell→PageFolio 側の窓」直接遷移(22 行)か、null 9ms を挟む 1 件(W03/pdf-3page@production-exe。peer 開始+0.22 秒・driver が二次起動した約0.35秒の監視で、人の Alt+Tab が入る余地は実質なし)。peer 区間にタスク切替UI/ForegroundStaging の遷移は 0 件。切替UI遷移は awaiting-enter(指示された PowerShell への移動)・w03-preparation(同)・post-peer(観測後に PowerShell へ戻る操作)に限られる。
    (3) 監視されていない行: W02/settings@production-exe は input_monitor.enabled=false(実EXE行は利用者が PageFolio 内を操作する手順のため。設計どおり)。実EXE行(production-exe)の監視は peer の約0.35秒だけ。
  implication: 過去 pass が Alt+Tab 由来の偽の復帰に依存した痕跡は見つからない。ただし key_events に Alt+Tab が載らないため「無かった」ことの直接証拠は無く、根拠は遷移の形(切替UIの有無)に限られる。素早い Alt+Tab(切替UIなし)の形は null 9ms で、W03 exe の正当な復帰と区別できないため、W03/pdf-3page@production-exe は『形としては排除できないが、時間的に人の操作は考えにくい』と注記する。台帳・証拠は書き換えない(報告のみ)。

## Eliminated

- hypothesis: null(hwnd=0)経由の遷移を一律に不成立にすれば素早い Alt+Tab も遷移の形だけで拾える。
  evidence: 製品の正当な復帰(W03/pdf-3page@production-exe の pass)にも PowerShell→null(9ms)→PageFolio が現れ、人の短押し Alt+Tab(W01/normal@module の awaiting-enter)も同じ約9ms。時間幅でも区別できない。一律不成立は正当な復帰を落とす。キー押下エッジの捕捉(switch_key_events)に任せ、限界を明記した。
  timestamp: 2026-10-31T00:22Z

- hypothesis: GetAsyncKeyState のポーリング間隔(8ms)や API の能力不足で Alt+Tab を取りこぼした。
  evidence: 監視は samples 4379〜15039・max_gap 0.011〜0.019秒・errors 空で、間隔は十分に細かい。Alt+Tab の取りこぼし以前に、コード上 PageFolio 前景以外ではキーを読まず、Alt 押下中は記録しない構造(上記 Evidence 1)。
  timestamp: 2026-10-31T00:12Z

- hypothesis: 235255Z の clean は製品の自動復帰が ForegroundStaging 経由で起きた(製品由来)。
  evidence: 製品の復帰を含む過去 pass 23 行の peer 区間に切替UI/ForegroundStaging 遷移は 0 件、W05b の直接遷移 2 run(235905Z/000340Z)も直接。切替UIが約0.14秒だけ出る形は人の素早い Alt+Tab の形で、利用者の申告(各 run の Alt+Tab)とも整合する。
  timestamp: 2026-10-31T00:20Z

## Resolution

- root_cause: 二つの欠陥の連結(AND-gate)。(A) InputMonitor のキー記録(key_events)は『PageFolio前面中・Alt非押下中』のキーだけを残す設計で、Alt+Tab を構造的に記録できない(前景が PageFolio 以外の間はキーを読まない / 前面化の最初のサンプルは基準線として捨てる / Alt 押下中の押下は除外)。これは W01〜W05a の手順汚染判定(PageFolio内の入力先が動く押下)には妥当だが、W05b の『人が前景を動かしていない』には不適合。(B) assess_w05b_return は、確認ダイアログへ到達した最初の遷移の `to` と終端前景、押下・キーだけを見て、遷移の `from` や観測区間の経由窓(XamlExplorerHostIslandWindow / ForegroundStaging)を一切見ない。このため 235255Z(Enter の0.65秒後の人の Alt+Tab による戻し)は、返却先が同一HWND・終端前景が確認画面・押下/キー無しの全条件を満たして clean と誤判定された。GetAsyncKeyState の能力不足・ポーリング間隔の問題ではない(samples 4379〜15039・max_gap ≤0.019 秒・errors 空)。
- fix: |
    uat_row.py(planning側 driver のみ。製品・凍結EXE・証拠原本・台帳・UAT は不変):
      1. 観測区間(peer, w05b-quiet)の前景遷移が ForegroundStaging / XamlExplorerHostIslandWindow を from か to に持てば `task-switcher-during-observation` で不成立(到着遷移の from がそれらの場合も含む。phase をまたぐ Alt+Tab も拾う)。判定結果に task_switcher_transitions_during_observation / returned_via_task_switcher を残す。
      2. InputMonitor に、前景に関係なく Alt/Tab/Win の押下エッジを記録する別系列 switch_key_events を追加(読み取りのみ。Win32Sampler.switch_keys + switch_combo。kind は down / held-at-start / held-at-phase-start。summary に switch_key_capture / switch_key_samples)。key_events と assess_procedure は不変(W01〜W05a の判定は変わらない)。
      3. assess_w05b_return: 観測区間の切替キー押下は `switch-key-during-observation`。捕捉が無い記録・旧形の summary は `switch-key-capture-missing`。さらに自己検証として、セッション中にタスク切替UIが出た(指示された Alt+Tab)のにキー押下が1つも無ければ `switch-key-capture-blind`(キー不在を根拠にした clean を出さない)。
      4. W05B_REASON_TEXT に日本語の理由文、briefing に『Alt+Tab・Winキーも不成立』の注記を追加。SWITCHER_CLASSES / STAGING_CLASSES を W05b 判定の近くへ移動(定義の重複なし)。
      5. --check-monitor(再現・修正・held-at-start / held-at-phase-start・旧形sampler・失敗・上限・静的な読み取り専用確認・実API)と --check-w05b(235255Z 形の回帰・235905Z/000340Z 形の対照・phaseをまたぐ形・切替キー・捕捉欠落/盲目・実記録3 runの再生)を追加。
    06-05-record-w05b.cjs(pass 記録 helper。defense in depth): driver の判定とは独立に、生の input_monitor(/input_monitor_final)から (i) 切替キー捕捉が有効 (ii) 観測区間の前景遷移が切替UI/ForegroundStaging を経由していない (iii) 観測区間に Alt/Tab/Win 押下が無い (iv) 切替UIが出たのにキー記録が空でない(盲目でない) (v) ret.returned_via_task_switcher=false、を満たさなければ pass を記録しない。
- verification: |
    - `.venv\Scripts\python.exe .planning\phases\06-release-validation\06-05-drivers\uat_row.py --check-w05b` : 42 件 [ok]・FAIL 0・exit 0(修正前の基準線は全合格。新規回帰を含む)
    - `... --check-monitor` : 48 件 [ok]・FAIL 0・exit 0(実API部は読み取りのみ。switch_key_capture=true・全サンプルで読めることを確認)
    - `... --check-diagnostics` : 全合格(InputMonitor/_FakeSampler を使う既存の診断自己検証が不変)
    - 変異テスト M1〜M7 : 規則を外すとそれぞれ FAIL(Evidence 参照)。静的確認は SetForegroundWindow の混入を検出
    - `ruff check` / `ruff format --check`(uat_row.py): 合格 / 整形済み。AST parse: OK。`node --check 06-05-record-w05b.cjs`: OK
    - 記録 helper の --dry-run(scratchpad の改変複製。台帳・UAT・原本は不変): 手動切替の複製 6 種を期待どおりの理由で拒否(Evidence 参照)
    - tests/ に uat_row.py / 06-05-drivers を参照するテストは無い(grep 0 件)ため、対象テストの実行は無し。全件 pytest は制約により未実行
    - 残プロセス: 無し(python/node/PageFolio の生存 0 件を確認)
    - 未検証(人の操作が必要): 実機で GetAsyncKeyState が Alt+Tab の Alt/Tab を読めること。次回の人手 W05b 実走で、awaiting-enter の指示された Alt+Tab が input_monitor.switch_key_events に載ることを確認する。載らなければ switch-key-capture-blind で自動的に不成立になり、クリーンを誤って出さない。
- files_changed:
    - .planning/phases/06-release-validation/06-05-drivers/uat_row.py
    - .planning/phases/06-release-validation/06-05-record-w05b.cjs
    - .planning/debug/phase06-w05b-alttab-blindspot.md

## 人手検証（2026-10-31）

- script 合格 run `W05b_ocr-close-confirm_at_script-20261031T003108Z.json`: awaiting-enter の Alt+Tab が `switch_key_events` に記録された（実機で Alt/Tab 押下エッジ捕捉を確認）。peer は PowerShell→確認 の直接遷移、観測区間の切替キー 0、verdict=clean、pass 記録。
- module 合格 run `...module-20261031T003956Z.json`、production-exe 合格 run `...production-exe-20261031T004536Z.json`（Explorer→確認 の直接遷移）も同様に pass。
- 途中の module run `...003637Z` は Alt+N 推定で物理入力を裏付けられず、pass helper が正しく拒否（attempt 記録）。Alt 押下中の文字キーは key_events に載らない既知の限界として残る。
