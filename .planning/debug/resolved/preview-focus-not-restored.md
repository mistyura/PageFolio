---
status: resolved
trigger: "06-05 G1 人手受入 W02/preview@script で、二次起動による既存画面復帰後の入力先が preview_canvas ではなく右ペインのボタン(.!panedwindow.!frame3.!canvas.!frame.!frame2.!button)になった(focus_correct=false)。同手順の W02/thumb@script・W02/settings@script は正しく復帰。"
created: 2026-10-24
updated: 2026-10-25T15:05:00+09:00
---

# Debug: preview-focus-not-restored

## 作業条件(coordinator 経由の利用者指示・2026-10-25 01:2x JST に追加。最優先で読むこと)

- 利用者は **2026-10-25 02:00 JST まで PC を操作しない**(01:20 JST 時点で通知)。この無操作の時間帯だけが、前景・フォーカス・ポインタ・入力を観測する実験の「クリーンな窓」。
- 実験・実OSテストは **1つずつ直列**。並行実行しない(別の実験プロセス・pytest が走っている間は次を始めない)。pytest を回すときは毎回 **新規の --basetemp**(再利用しない)。
- **02:00 JST を越える作業、または利用者の操作が必要になった時点で止めて** CHECKPOINT を返す(02:00 以降に前景を奪う実験を走らせない)。
- 終了時に **孤児プロセスが 0**(診断 owner/peer・decoy・pytest 子プロセスが残っていないこと。残っていたら自分が起動したものだけ停止して報告)。
- 製品修正は従来どおり、CHECKPOINT で承認を得た後のみ。tests/ や Phase 4 の covered ファイルは触らない。
- 下の Evidence「重複の可能性あり・判定に使わない」の実験群は、分岐 A/B/C の判定根拠にしない。クリーンな窓(01:20〜02:00)で取り直した結果だけを判定に使う。

## Symptoms

- **期待:** 入力先をプレビュー(`app.preview_canvas`)にした状態で別ウィンドウ(PowerShell)が前面になり、二次起動で既存画面が復帰したとき、入力先は最後に操作していたプレビューのキャンバスへ戻る(Phase 4 V110-FOCUS-02 / D-04)。
- **実際:** 画面は前面に戻り(activated=expected_tk=46141210、target_correct=true、state_preserved=true、result=completed)、しかし `immediate_focus = None`、`settled_focus = .!panedwindow.!frame3.!canvas.!frame.!frame2.!button`(右ペインのボタン)で `focus_correct=false`。`expected_focus = .!panedwindow.!frame2.!frame2.!canvas`。
- **エラー:** なし(観測値の不一致のみ)。
- **時期:** 2026-10-24 23:40 JST の人手受入で初観測。自動試験(tests/test_startup_windows.py の focus ケース、preview を含む parametrize)は単一プロセス全件(2024 passed)で合格している。
- **再現:** `uat_row.py --row W02/preview@script`(Python入口 script、PDFなし)。流れ: harness が owner を起動し `preview_canvas.focus_set()`(tests/test_startup_windows.py:1843 付近の preview ケース) → 利用者が PowerShell で Enter(PowerShellが前面になり PageFolio は非アクティブ) → harness が peer を起動 → 復帰 → `after_idle` で settled_focus を記録(利用者の F5 操作より前)。
- **対照:** 同じ流れで thumb(`thumb_canvas`)は settled_focus=サムネイル canvas、focus_correct=true。settings(設定ダイアログの入力欄)も正しく復帰。

## 証拠(原本保持・変更削除禁止)

- `.planning/phases/06-release-validation/06-05-evidence/W02_preview_at_script-20261024T144058Z.json`(commit 8a3d486)
- 対照: `W02_thumb_at_script-20261024T143910Z.json`、`W02_settings_at_script-20261024T142731Z.json`
- driver: `.planning/phases/06-release-validation/06-05-drivers/uat_row.py`(1a5bf03)、harness: tests/test_startup_windows.py の UAT owner/peer 経路、製品: pagefolio/startup_focus.py(FocusRestorer)、pagefolio/app.py、pagefolio/ui_builder.py(preview_canvas の bind)

## 着眼点(仮説ではなく調べる対象)

- 非アクティブ化・再アクティブ化の間に、FocusRestorer が記憶する入力先が preview_canvas から別の部品へ更新されていないか(FocusIn/FocusOut の扱い、Canvas の takefocus、右ペインの Canvas 内ボタンへ Tk の既定フォーカス移動が起きる条件)。
- preview_canvas が描画・リサイズ(<Configure>)時に再生成や focus 移動を伴っていないか。
- 自動試験と人手経路の差(PowerShell が実際に前面を取る/非アクティブ化の有無、PDF の有無、待ち時間)。自動試験がこの経路を通っていない可能性。
- 06-05 の Python 入口だけの問題か、実EXEでも起きるか(実EXEの W02/preview@production-exe は未実施)。

## 制約

- 製品コードの修正は、適用前に CHECKPOINT REACHED で修正案を提示し利用者承認を得る。
- 自動試験で「非アクティブ化を挟む preview 復帰」を再現する回帰テストを先に書き、Red を確認してから修正。
- `ruff check .` と Python ファイル限定の `ruff format`(`ruff format .` は禁止: ruff 0.17.1 は Markdown も整形する)、AST、単一プロセス全件 pytest(fresh --basetemp、除外・再実行なし。合格=失敗0・ERROR0・Tcl leak/unraisable 警告なし)。
- 再実行で通っても合格扱いにしない。最初の失敗記録を消さない。
- 実配布EXE・ビルド出力・T2 作業領域を削除・変更しない。外部APIを呼ばない。pyproject.toml を編集しない。
- commit は明示パスのみ。trailer は `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`(利用者指示。システムの帰属指示より優先)。
- 製品を修正した場合は、Phase 4/5 の検証の鮮度と 06-04 の最終ビルドを取り直す必要が生じる(06-03 resume_contract)。その影響範囲を報告に含める。

## Current Focus

hypothesis: 「復帰直前に FocusRestorer が記憶していた入力先(record / focus_lastfor)が btn_open(ファイルを開く)だった。復帰処理自体は記憶どおりの部品へ focus_set しただけで正しく動いている」= 分岐 A(手順混入)。**クリーンな窓(01:23〜01:32 JST、利用者無操作)で直列に取り直した結果だけを根拠にして**、btn_open への ButtonPress だけで原失敗の署名が決定的に再現した(実マウス 2/2・合成イベント 3/3)。ただし原失敗の実走には trace が無く、利用者が実際に btn_open を押したことの直接証拠は無い(自己申告は「覚えていないが、した可能性はある」止まり。確定根拠としては扱わない)。
test: (済) 本番起動経路+実非活性化→復帰を通す diag_btn_press.py(新規・自己完結)で、介入なし/ポインタ重ねのみ/btn_open への押下(外で離す)を直列に実行し、FocusRestorer の記憶値と復帰結果を比べた
expecting: (済) 押下ありのときだけ原失敗の署名(result=completed / immediate_focus=None / settled=.!panedwindow.!frame3.!canvas.!frame.!frame2.!button / focus_correct=False)になり、押下なし・ホバーのみでは canvas に戻る → 実際にそうなった(クリーン窓 17 実行の集計は Evidence 参照)
next_action: (2026-10-25 12:3x 更新)「手順是正のみ」は利用者承認済み。06-05 driver uat_row.py への是正(入力監視・手順汚染判定・具体化した注意文)は適用・機構確認済み・commit 済み。**利用者による W02/preview@script の再走待ち**(CHECKPOINT human-action を返した)。再走結果を次の規則で評価する: 押下ログが空 かつ settled=canvas(focus_attribution=product-focus-ok)→ 分岐 A を確認、resolved へ(archive_session)/ 押下ログが空 かつ settled=btn_open(focus_attribution=product-focus-failure-candidate)→ A 反証、B/C を再検討(製品変更の検討に戻る)/ procedure_verdict=contaminated(PageFolio 上の押下あり)→ 手順汚染で製品失敗ではない、再々走。原失敗の証拠 W02_preview_at_script-20261024T144058Z.json は原本保持(再走は別ファイル名のタイムスタンプ付き JSON)。製品・tests/・Phase 4 被覆ファイルは触っていない(Phase 4/5 の鮮度・06-04 最終ビルドは影響なし)。

分類方針(trace 読み取り後):
  A. Open への FocusIn/focus 呼出しが復帰より前で、直前に利用者のキー/マウス入力(KeyPress/ButtonPress、Tcl 側の ttk::clickToFocus 等)が届いている = 手順上の混入。製品は記憶どおり復帰しており正しい。是正対象は 06-05 の手順/期待値(利用者が最後に触った部品へ戻るのが正)。製品変更なし・Phase 4/5 再検証不要。
  B. Open への FocusIn が入力なしで、非アクティブ化〜再アクティブ化の間(復帰より前)に起きる = OS/Tk 側の入力先移動。FocusRestorer が「非アクティブ化の瞬間の入力先」を確定して持つ設計への変更を検討(製品変更)。
  C. Open への focus 呼出しが restore() の中・直後(restore-before〜settled)に起きる = 復帰処理自身の欠陥。製品変更。

判定(2026-10-25 01:3x JST): **A(機構は決定的に実証。原失敗の実走で押したことだけは未実証)**。B はクリーン窓の入力なし 7 実行+利用者診断 3 件(T1)で 0 件(不支持。ただし原セッションを完全には排除できない)。C は restore-before 時点で record が既に btn_open であり、focus 呼出し(startup_focus.py:227)の対象が記憶値と一致するため棄却。

reasoning_checkpoint:
  hypothesis: "原 W02/preview@script の settled_focus=btn_open は、Enter の前(prepared〜peer の約 10 秒)に PageFolio 内で btn_open に Tk 入力先が移った(ttk の <Button-1> binding の ttk::clickToFocus による ButtonPress が最有力)ため、FocusRestorer.windows[root].focus と focus_lastfor が btn_open になり、restore() が記憶どおり btn_open へ focus_set したことで起きた。製品の復帰処理は D-04(最後に操作した部品へ戻す)どおりに動いている。"
  confirming_evidence:
    - "クリーン窓の実マウス(mouse_event+SetCursorPos、ポインタが btn_open 上であることを owner の winfo_containing で確認してから押下→外へ移動→離す)×2 [013039・013059]: 各 ButtonPress=1/ButtonRelease=1(外部入力の混入なし)、Tcl trace に `focus <btn_open> tcl-caller: ttk::clickToFocus`、btn_open の command は未実行(invoke=False)、前景を既存窓(開始時の端末)へ戻してから peer 復帰 → result=completed / immediate_focus=None / settled_focus=.!panedwindow.!frame3.!canvas.!frame.!frame2.!button / focus_correct=False。原失敗の署名と完全一致。"
    - "クリーン窓の合成イベント(同じ class binding を通す event_generate: ButtonPress→Leave(B1)→外で ButtonRelease)×3 [012655・012712・012724]: 3/3 が同署名。"
    - "対照: 介入なし(none)×5・ポインタを btn_open 上へ置くだけ(hover)×2 = 7/7 が settled=preview_canvas・focus_correct=True。さらに利用者本人の診断 3 件(T1、実 PowerShell クリックで戻る)も 3/3 canvas。復帰直前の record が canvas なら canvas、btn_open なら btn_open へ戻る=復帰は記憶値に忠実(restore-before の record と tcl-focus の対象が一致)。"
    - "Tk 9.0.4 の TButton binding: <Button-1> が `ttk::clickToFocus %W; %W state pressed`(押下だけで focus を取る)、<B1-Leave> が `!pressed`(押して外へ出ると離しても invoke されない)。ダイアログも開かず、見た目に残らない。"
    - "製品コードに右ペインのボタンへ focus を移す箇所は無い(grep 済み)。利用者診断 run1 の trace では、利用者は Enter 前に PageFolio 内を実際にクリックしている(t=12.327 に preview_canvas へ ButtonPress、t=14.110 に PowerShell へ戻る、t=15.769 に復帰)のに、その Enter 前クリックは回答 extra_ops(「左ペインをクリック」=復帰後の t=52/73)に出てこない=自己申告では Enter 前の PageFolio 内操作を拾えない。"
  falsification_test: "Enter 前に PageFolio 内へ一切の押下/キーが無いこと(押下エッジ・位置・押下先のログ付き)を担保して W02/preview@script を再走し、それでも settled=btn_open になれば A は反証され B/C を再検討する(製品変更を検討)。逆に押下ログ付きの再走が canvas に戻れば、原失敗は手順混入で説明がつく。"
  fix_rationale: "製品の復帰は仕様どおりで欠陥ではないので製品は変更しない。是正は手順側: (1) uat_row.py(被覆外の Phase 6 driver)が prepared〜Enter の間のマウス左ボタン押下エッジとその位置/押下先ウィンドウ・前景遷移を記録し、PageFolio 上の押下があれば当該行を『手順汚染(再走)』として製品失敗と区別する、(2) 注意文を『PageFolio の画面内は一切クリックしない。PowerShell へはタイトルバーか Alt+Tab で戻る』に具体化する、(3) 原 W02/preview@script の失敗記録は原本として保持し、再走結果を別記録で追加する。"
  blind_spots: "原失敗の実走には trace が無く、利用者が実際に btn_open を押したかは直接確認できない(自己申告も曖昧)。原証拠 JSON にポインタ位置・押下記録は無い。btn_open 以外の経路(Tab を複数回、Space/Enter で別ボタンを押す等)も理論上は同じ署名を作り得る(クリーン窓の Tab 1 回の実験は、Tab の押下が Tk に届かず未確認)。入力なしの OS 起因移動(B)は 10 実行で 0 件だが、原セッション固有の環境差(実 PowerShell・窓配置・ポインタ位置)は完全には排除できない。実マウスの復帰完走は『前景を既存窓へ戻す方式』の 2 実行のみ(新規 decoy 窓方式は harness 側の更新停止で完走せず)。"
  candidate_causes:
    - "[data/operation] Enter 前の利用者による PageFolio 内の押下(btn_open)で記憶入力先が btn_open になった(分岐 A、最有力・機構実証済み)"
    - "[code] 非活性化〜再活性化の間に Tk/OS が入力なしで btn_open へ入力先を移した(分岐 B。クリーン窓 7+利用者診断 3 の入力なし実行で 0 件、不支持)"
    - "[code] restore() 自身が record と別の部品を選ぶ(分岐 C。restore-before で record が既に btn_open、focus 対象は記憶値と一致、棄却)"
    - "[environment] 原セッションの実 PowerShell/配置/ポインタ位置に固有の何か(原証拠にデータが無く検証不能。診断・probe では再現せず)"
  and_gate: "no — 単一の寄与条件(btn_open への押下 = 記憶入力先の変更)で署名は完全に再現し、他条件との同時成立は不要。ただし『押下があった』ことと『G1 の期待値(prepared 時の入力先 = preview_canvas に固定)が、利用者が PageFolio 内で入力先を変えた場合も製品失敗と判定する』ことの 2 つが揃って初めて失敗記録になる。後者は是正(手順側)の対象。"

## Evidence

- timestamp: 2026-10-25（承認後の再走 2 回目・新 driver 9758a3a6…・Alt+Tab のみ）
  checked: .planning/phases/06-release-validation/06-05-evidence/W02_preview_at_script-20261025T060315Z.json
  found: procedure_verdict=clean / focus_attribution=product-focus-ok / outcome=answered。マウス押下 0 件、監視 errors 0・max_gap 0.014s・truncated=false。キーは post-peer(参考記録のみ)の F5(vk116)×4 と Tab(vk9)のみ。focus-result: result=completed / target_correct=true / state_preserved=true / settled_focus=.!panedwindow.!frame2.!frame2.!canvas / focus_correct=true。利用者回答: foreground=出た・key_reached=変わった・restored=戻った・kept=PDFなし・single=１つ。
  implication: falsification_test の「押下ログ空で canvas に復帰」が成立。分岐 A(Enter 前の PageFolio 内ボタン押下で記憶入力先が変わった手順混入)を確定し、製品欠陥ではないと結論する。resolved。

- timestamp: 2026-10-25（承認後の再走 1 回目・新 driver 9758a3a6…）
  checked: .planning/phases/06-release-validation/06-05-evidence/W02_preview_at_script-20261025T055841Z.json の input_monitor・procedure_assessment・harness_inspect focus-result・steps[].windows[].rect
  found: procedure_verdict=contaminated（awaiting-enter で PageFolio 上の左押下 1 回: down (716,243) → up (743,155)）。押下時の窓 rect=[234,228,1450,1067] で y=243 は上端から 15px のタイトルバー（WindowFromPoint の child_hwnd が TkTopLevel 自身＝クライアント領域の Tk 部品ではない）。押下後の窓 rect=[261,140,…] で移動量 (+27,-88) がドラッグ量と一致＝タイトルバーでの窓移動。復帰結果は settled_focus=.!panedwindow.!frame2.!frame2.!canvas / focus_correct=true / result=completed。
  implication: 手順上は汚染判定のため合否には使わない（規則どおり再走が必要）。ただし非クライアント領域の押下では Tk 入力先が変わらず canvas に戻った＝分岐 A（クライアント領域のボタン押下で記憶入力先が変わる）と整合し、反証しない。driver はタイトルバー押下とクライアント領域押下を区別していない（偽陽性の余地）。clean な再走 1 回で A を確認して閉じる。

- timestamp: 2026-10-24
  checked: 06-05 証拠 JSON(preview/thumb/settings)と driver/harness/FocusRestorer のコード
  found: |
    (1) settled_focus の `.!panedwindow.!frame3.!canvas.!frame.!frame2.!button` は右ペイン(frame3)の inner frame の 2 番目の section(ファイル)の最初の button = `btn_open`(ファイルを開く)。実アプリで find して確認済み(exp1 の pre-pointer ログ: widget=.!panedwindow.!frame3.!canvas.!frame.!frame2.!button は text==btn_open)。
    (2) preview 実行だけ `prepared` 時点の前景が PageFolio 自身(46141210)。thumb(143910)は前景が PowerShell(656216)のまま = PageFolio は実OS入力先を一度も持っていない。旧 thumb(142939)は preview と同じく PageFolio が前景だったが settled は正しかった。
    (3) 製品コードに右ペインのボタンへ focus_set する箇所は無い(pagefolio/ 全体を focus_set/focus_force/tk_focus*/takefocus で grep)。
  implication: 製品が明示的に button を選んでいるのではない。Tk の focus 記憶(focus_lastfor)か FocusRestorer.record が Open だったことになる。

- timestamp: 2026-10-25
  checked: 既存の自動試験 test_focus_restore_real_main_windows[preview/thumb](4件)を単独実行し focus-result.json を読む
  found: 4件とも result=completed、immediate_focus=正しい canvas、settled_focus=正しい canvas。人手の実走行では immediate_focus=None だったのと違う。
  implication: 自動試験の owner は一度も実OS入力先を持たない(または非アクティブ化されない)ため focus_get() が常に記憶値を返す。人手経路の「実アクティブ→非アクティブ→復帰」を通っていない。自動試験が preview を通しているのは経路が違うからで、人手の失敗と矛盾しない。

- timestamp: 2026-10-25
  checked: scratchpad exp1.py(実 PDFEditorApp+FocusRestorer+Win32Backend を単独プロセスで動かし、別プロセスの前景窓 decoy で非アクティブ化→backend.restore_window。Tcl focus をラップして呼出しを記録、FocusIn/Out を記録)
  found: |
    実アクティブ化→focus_set(preview/thumb)→decoy で非アクティブ化(focus_get=None になる、lastfor と record は canvas のまま)→restore(result=completed, immediate=None)→settled=canvas。
    focus_first/activate_first の両順序、preview/thumb 両方、前段で Alt タップ、ポインタを Open ボタン中心へ置く、の変形でもすべて settled=canvas(正しい)。
  implication: 「非アクティブ化→SetForegroundWindow での復帰」という機構それ自体では Open へ移らない。immediate_focus=None も正常側と同じ。FocusRestorer のロジックの単純な欠陥(例: 常に別部品を選ぶ)ではない。

- timestamp: 2026-10-25
  checked: scratchpad exp2.py(実 harness の uat-owner-preview を --uat start で起動→外部から PageFolio を前面化→前景 decoy 窓プロセスの子孫として --uat peer --entry script を実行→--uat inspect)を 5 回
  found: 4回は result=completed(1回 foreground_denied)で immediate_focus=None、settled_focus=canvas、focus_correct=true。1回は decoy が 120 秒返らず実験側が中断(原因未調査、owner は watchdog で終了済み・残存プロセスなし)。
  implication: 利用者の人手走行(settled=Open)は、入力のない自動操作では再現しない。人手の10秒間に何か(利用者の入力、実物理のマウス/キー、または環境差)があった可能性が高い。

- timestamp: 2026-10-25
  checked: Phase 4 の検証対象(04-VERIFICATION.md の covered_files / covered_digest)
  found: tests/test_startup_windows.py と tests/test_startup_focus.py、pagefolio/startup_focus.py などが covered_files に含まれる(covered_digest=v3:sha256:7436bfbe...)。
  implication: 観測用に tests/test_startup_windows.py を編集すると Phase 4 の鮮度が失効する(06-03 resume_contract は Python 行を covered_digest 同一のものだけ再利用可とする)。そのため一度入れた trace 編集は元に戻し(patch は scratchpad に退避)、tests/ に触れない自己完結の診断 owner/peer を .planning/debug/preview-focus-not-restored-evidence/ に作った。回帰テスト追加も同じ covered ファイルを動かす点は、修正段階で orchestrator が判断する必要がある。

- timestamp: 2026-10-25
  checked: 診断 owner/peer(diag_owner.py)を、実アクティブ化→前景 decoy 窓の子孫として peer 実行(実 deactivation)で動作確認(scratchpad exp4.py、preview)
  found: 人手走行と同じ署名(result=completed、immediate_focus=None)で、FocusOut 連鎖(非アクティブ化)→restore-before(tk_focus=None、lastfor/record=canvas)→focus 呼出し(Python 呼出し元 startup_focus.py:227 まで記録)→FocusIn 連鎖→settled=canvas が時系列で取れる。tests/ は無変更。
  implication: 利用者の再実行で、Open ボタンへの入力先移動がいつ・何の後に起きたかを直接読める。

- timestamp: 2026-10-25
  checked: 利用者の診断実走3件(.planning/debug/preview-focus-not-restored-evidence/ の diag-preview-20261025T004750.json / diag-preview-20261025T005032.json / diag-thumb-20261025T005240.json)の要約(orchestrator 経由の利用者回答)
  found: |
    1) diag-preview-20261025T004750.json: focus_correct=True、settled=preview canvas。回答: foreground=出た / switch_method=PowerShellのウィンドウをクリック / extra_ops=左ペインをクリック
    2) diag-preview-20261025T005032.json: focus_correct=True。回答: 出た / PowerShellのウィンドウをクリック / していない。ボタン関連の trace イベントなし
    3) diag-thumb-20261025T005240.json: focus_correct=True、settled=thumb canvas。回答: 出た / PowerShellのウィンドウをクリック / していない
    診断走行3件はいずれも focus_correct=True(原失敗の再現なし)。
  implication: 診断 driver 経由では原失敗(settled=btn_open)は自然発生しなかった。原失敗は復帰処理の欠陥ではなく、Enter 前の PageFolio 内操作の有無に依存する可能性がある(未確定。下の利用者の追加回答と、trace・原本証拠の読み取りで判定する)。

- timestamp: 2026-10-25
  checked: 利用者の追加回答(orchestrator 経由。質問=原 W02/preview@script で Enter を押す前に PageFolio 内・右側(右ペイン)をクリックしたか)
  found: |
    利用者の回答(逐語): 「覚えていないが、した可能性はある。」
    ※ この回答は記憶に基づく曖昧な申告であり、確定根拠としては扱わない。「PageFolio 内の右ペインをクリックした」ことの肯定でも否定でもない。分岐 A/B/C の判定は、trace と再現実験(ButtonPress を btn_open に与えて離す前に外へ出す等)の決定的な証拠で行い、この回答は「A(手順混入)と矛盾しない」程度の補助材料に留める。
  implication: 利用者の記憶だけでは A を確定できない。A を採るなら、決定的な機構再現(右ペインのボタン押下で Tk の focus 記憶が btn_open になり、復帰処理が記憶どおり btn_open へ戻す)と、原失敗の署名(immediate_focus=None、settled=btn_open)との一致を示す必要がある。

- timestamp: 2026-10-25 01:2x JST
  checked: 実験の時間的重複の整理(coordinator 経由の利用者指示。「利用者の画面操作とこちらの自動テスト/実験が時間的に重なっていた可能性がある」。利用者は 02:00 JST まで無操作、01:20 JST 時点で通知)。各実験の時刻はファイル mtime(scratchpad=C:/Users/shdwf/AppData/Local/Temp/claude/C--Users-shdwf-work-project-PageFolio/ce16e575-317d-4582-a7f5-f17bbae7daa7/scratchpad/exp_focus、probe 群=.planning/debug/preview-focus-not-restored-evidence/)から採った
  found: |
    【重複の可能性あり・判定に使わない】前景・フォーカス・ポインタ・入力を観測する実験は、いずれも利用者が PC を操作していなかったことを保証できない時間帯に実行している。以下は分岐 A/B/C の判定根拠にしない(参考記録としてのみ残す。削除しない)。
    (T0) 2026-10-24 23:48〜00:17 JST の自動実験(利用者の操作有無が未確認。無操作の指示が出る前)
      - exp1 系(run1〜run5、alt/pointer/altpointer 変形を含む)23:48〜23:58 — 実 PDFEditorApp+FocusRestorer+Win32Backend を別プロセス decoy で非アクティブ化
      - exp2 系(exp2_preview_*/exp2_thumb_2)23:54〜00:04、exp3/exp3b_preview 00:07〜00:08 — 実 harness の uat-owner-preview を外部前景化→decoy 子孫で peer 実行。うち 1 回は decoy が 120 秒返らず中断(これも干渉の疑いに含める)
      - exp4 00:16〜00:17 — 診断 owner/peer の動作確認
      - 既存自動試験 test_focus_restore_real_main_windows[preview/thumb](4 件、basetemp=%TEMP%/pf_dbg_focus_1792853409 は 23:50 台、pf_dbg_focus2_1792854606 は 00:10 台)の単独実行 — 実 OS の前景を使う
      → これにより「機構そのものでは btn_open へ移らない(Eliminated 1・2)」の根拠も、クリーンな窓で取り直すまで暫定扱いに格下げする。
    (T1) 2026-10-25 00:47〜00:53 JST — 利用者の diag 実走 3 件(diag-preview-004750 / 005032 / diag-thumb-005240)。これは利用者本人の操作記録であって自動実験ではない。直前の自動実験は 00:17 で終了、直後の自動 probe は 00:58:15 開始のため、この 3 件と自動実験の時間的重なりは無い(時刻から確認)。観測値として有効。
    (T2) 2026-10-25 00:58〜01:18 JST — 現行デバッガーの probe 群(利用者がチャットで応答していた時間帯。PC 操作の有無が未確認)
      - probe-none ×2(00:58:15 / 00:58:45)、probe-hover(01:09:16)、probe-tab(01:09:28)
      - probe-press-release-outside ×9(01:02:51 〜 01:12:03)、probe-synthetic-press-release-outside ×5(01:12:38 〜 01:18:30)
      - 作成中の diag_btn_press.py(最終更新 01:14:25)による出力。これらはすべて「重複の可能性あり・判定に使わない」。
    クリーンな窓 = 2026-10-25 01:20〜02:00 JST。この窓で直列に取り直した実験・テストだけを判定に使う。
  implication: 現時点で A/B/C を確定する材料は、(T1) の利用者診断 3 件(いずれも原失敗は再現せず focus_correct=True)と原本証拠 JSON のみ。機構確認(btn_open への ButtonPress+外で release → 記憶値・復帰結果)と実 OS テストは、クリーンな窓での直列再取得が必要。

- timestamp: 2026-10-25 01:2x JST
  checked: 利用者診断 3 件(T1・利用者本人の操作記録として有効)の focus_trace 全文(FocusIn/FocusOut・Tcl focus 呼出し+Python 呼出し元・ButtonPress/Release・前景/OS入力先/ポインタ/ポインタ下ウィジェット)
  found: |
    (a) 3 件とも復帰直前の record=lastfor=対象 canvas。tcl-focus の呼出し元は startup_focus.py:227(restore)で対象は記憶値と同一。restore-before〜settled の間に他の部品への focus 呼出しは 0 件。settled=対象 canvas。
    (b) run1(preview・extra_ops=「左ペインをクリック」)は Enter 前に PageFolio 内を実際に操作している: t=12.327 に PowerShell から PageFolio へクリックで戻り preview_canvas へ ButtonPress(631,923)、t=14.110 に再び PowerShell へ、t=15.769 に restore-before。t=13.349〜13.557 には、利用者のポインタが PowerShell へ戻る経路で右ペインのボタン列を横切っている(t=13.449 は btn_open ではなくファイル節 4 番目のボタン `…!frame2.!button4` の上、押下なし)。ポインタ通過だけでは入力先は canvas のまま。報告された「左ペインをクリック」(t=52.828 / 73.633)は復帰後の操作で、Enter 前の preview_canvas クリックは回答に出てこない。
    (c) run2(preview)・run3(thumb)は Enter 前の PageFolio 内入力が 0 件で、復帰は canvas に正しく戻る。ttk Button への ButtonPress は 3 件を通して 0 件。
  implication: 診断 3 件はボタンを押していないので原失敗は再現しない。復帰処理の欠陥ではなく押下の有無に依存することと矛盾しない。また利用者は Enter 前に PageFolio 内を押すことがあり、その自己申告は当てにならない(run1 の実測)。

- timestamp: 2026-10-25 01:2x JST
  checked: 原失敗の証拠 JSON(W02_preview_at_script-20261024T144058Z.json)と対照 3 行(thumb×2・settings)の再読(ポインタ・時間・前景・窓位置)。実験ではなく既存ファイルの読み取り
  found: |
    prepared→peer の間隔は preview 9.96 s / thumb 8.85 s・8.47 s / settings 6.12 s で目立った差なし。prepared 時の前景は preview=PageFolio(46141210)、thumb 142939=PageFolio(70649558)、thumb 143910=PowerShell 側(656216)、settings=設定ダイアログ。PageFolio が前景だった thumb 142939 は settled が正しい。原証拠 JSON にはポインタ位置・押下記録・FocusIn/Out の記録が存在しない(raw_inputs は PowerShell への文字入力のみ)。窓位置 preview=[182,182,1398,1021]。
  implication: 原証拠は A / B / C を区別する情報を持たない(前景・時間・窓配置のいずれも決め手にならない)。原失敗が『PageFolio 内で btn_open に入力先が移った』ことは settled_focus の結果値からしか読めない。判定は再現実験で補う必要があった。

- timestamp: 2026-10-25 01:2x JST
  checked: Tk 9.0.4 の ttk TButton class binding(root.tk.call('bind','TButton') の実測。静的な事実)と ttk::clickToFocus / ttk::takesFocus
  found: |
    <Button-1> => `%W instate !disabled { ttk::clickToFocus %W; %W state pressed }`(押下だけで focus を取る。btn_open の -takefocus は ttk::takefocus で true)
    <B1-Leave> => `%W state !pressed`、<ButtonRelease-1> => `%W instate pressed { %W state !pressed; %W instate !disabled { %W invoke } }`(押したまま外へ出ると !pressed になり、離しても invoke されない)
    <Enter>/<Leave> は active のみ変更(ホバーは入力先を変えない)。
  implication: 『ttk Button は ButtonPress で入力先を取り、外で離すと invoke されない』は Tk 9.0.4 で成立する。押下だけで『最後に操作した部品』が btn_open になり、ダイアログも開かないので見た目に残らない。

- timestamp: 2026-10-25 01:23〜01:32 JST (クリーンな窓・利用者無操作・直列実行・判定に使う)
  checked: .planning/debug/preview-focus-not-restored-evidence/diag_btn_press.py(新規・自己完結。diag_owner.py を無変更で委譲、tests/ と製品は無変更。出力は probe-clean-*.json)。本番起動経路(pagefolio.py→__main__.main→StartupCoordinator/FocusRestorer)で PageFolio を前面化し preview_canvas に入力先を置く→介入→前景を他窓へ移して実非活性化→peer で復帰→focus-result.json/focus-trace.json を回収。非活性化の方式は 2 つ: decoy=前景 decoy 窓(新規 Tk 窓)の子孫として peer 実行、prev=開始時の既存前景窓(端末)へ前景を戻し制御プロセスから peer 実行(実 UAT で PowerShell 配下から peer を起動する流れに近く、新規窓を作らない)。
  found: |
    クリーン窓 17 実行の集計(全て ButtonPress/Release はこのスクリプトが出した分のみ):
    - 介入なし(none)×5 [012334・012741・012751(decoy)、013109・013118(prev)]: 5/5 result=completed / immediate_focus=None / settled=preview_canvas / focus_correct=True。
    - ポインタを btn_open 中心へ置くだけ(hover)×2 [012350(decoy)、013127(prev)]: 2/2 同上(settled=canvas)。prev 方式は非活性化の直前に Alt 単独タップが PageFolio に入るため、Alt タップ+ポインタの組合せも含む。
    - **実マウス押下(btn_open 上で押す→canvas 中央へ移動→離す)×2 [013039・013059(prev)]**: 2/2 が ButtonPress=1/ButtonRelease=1、`focus <btn_open> tcl-caller: ttk::clickToFocus`、invoke=False、record=lastfor=btn_open → restore-before(record=btn_open)→tcl-focus(startup_focus.py:227 が btn_open へ)→settled。result=completed / immediate_focus=None / settled_focus=.!panedwindow.!frame3.!canvas.!frame.!frame2.!button / expected=.!panedwindow.!frame2.!frame2.!canvas / focus_correct=False = **原失敗の署名と完全一致**。
    - 実マウス押下 ×1 [012546(decoy)]: ButtonPress→ttk::clickToFocus→btn_open に入力先が移るところまで確認。decoy 窓の更新停止で peer が走らず復帰は未完走(下記)。
    - 合成イベント(btn_open へ ButtonPress→Leave(state=B1)→外へ ButtonRelease)×3 [012655・012712・012724(decoy)]: 3/3 が原失敗の署名と完全一致(invoke=False)。
    - Tab 1 回 ×4: decoy [012939] は更新停止、prev [013137・013205・013215] は Tab の押下が Tk に届かず(tk::TabToWindow の focus 呼出しなし)入力先は canvas のまま。Tab の効果はクリーン窓では未確認(下の参考記録を参照)。
    共通の時系列(押下ありの成功例): ButtonPress(btn_open) → ttk::clickToFocus → FocusOut(canvas)/FocusIn(btn_open) → 前景が他窓へ(tk_focus=None・lastfor=record=btn_open) → restore-before(record=btn_open) → tcl-focus(btn_open) → FocusIn(btn_open) → settled=btn_open。
  implication: 「Enter 前に PageFolio 内で btn_open を押すだけ」で原失敗の署名が決定的に再現できる(十分条件の実証、実マウス・合成の両方)。復帰処理は記憶どおりに戻しており、記憶側が btn_open だったことが原因。押下なし・ホバーのみでは btn_open へは移らない(B 不支持、C 棄却)。

- timestamp: 2026-10-25 01:2x〜01:32 JST
  checked: diag_btn_press.py の decoy 方式で起きた停止(harness 側の不安定)
  found: |
    decoy 窓プロセスの Tk update() が 12〜100 秒停止する run がある。faulthandler のダンプは decoy 自身の `tkinter.update`(decoy 側の stack)で止まっていることを示し、PageFolio(owner)の 0.5 秒 heartbeat は継続していた=製品の停止ではない。クリーン窓(利用者無操作)でも起きた[012546・012939]ので利用者の操作が原因ではない。原因は未調査。prev 方式(新規窓を作らない)に切り替えてからは 8 実行で停止 0。
  implication: 実マウスの復帰完走は prev 方式の 2 実行のみ。停止が製品由来の可能性は低いが、原因を特定したわけではない。

- timestamp: 2026-10-25 (参考記録・判定に使わない)
  checked: 01:20 より前に実行した probe-*.json(接頭辞 probe- で probe-clean- ではないもの。T2)
  found: 結果の傾向は上のクリーン窓と同じ(none/hover は canvas、押下ありは btn_open、Tab 1 回は `.!panedwindow.!frame3.!canvas.!frame.!frame.!button`[btn_open ではなく 1 つ前の section の最初のボタン]へ移った run が 1 回[010928])。ただし利用者の操作と重なっていた可能性があり(実マウス run に外部の click が混入したものがある[011115]、decoy の停止も多発)、分岐の判定には使わない。全試行をファイルとして保持している。
  implication: Tab 1 回が btn_open と別のボタンに着地した 1 件は参考記録に留まる。クリーン窓で再確認できなかったので、『Tab では btn_open に移らない』を根拠にはしない。

- timestamp: 2026-10-25 12:3x JST (是正の適用・機構確認)
  checked: 是正案(利用者承認済み「手順是正のみで承認」)を 06-05 driver `.planning/phases/06-release-validation/06-05-drivers/uat_row.py` に適用し、前景を奪わない範囲で機構確認した。製品・tests/・Phase 4 被覆ファイル・pyproject.toml・06-05-evidence/ の既存記録は無変更(git status で確認)。
  found: |
    (1) ruff check / ruff format(当該ファイルのみ。`ruff format .` は未使用)/AST 構文確認 すべて合格。行末は元ファイルと同じ LF(編集中に CRLF 化したのを LF へ戻し、差分は追加 826 行・削除 8 行のみ)。
    (2) `--check-monitor`(新設。窓も入力も作らず前景も変えない)全項目合格: 偽サンプラで 押下エッジ・押下先(PageFolio の所有 PID か)・phase 別の汚染判定・外で離す形(btn_open 再現と同形)・右/中ボタン・held-at-start・前景遷移・PageFolio 前面中のキー押下(Alt+Tab と基準線の除外)・監視の error/観測の空き/0 回の monitor-incomplete・focus_correct の帰属(clean のときだけ product-focus-ok / product-focus-failure-candidate、汚染時は not-judged-contaminated)を確認。実 API は読み取りだけを約 0.6 秒ポーリング(88 サンプル・最大の空き 9 ms・エラー 0)し、subprocess 待機中も止まらないことを確認。SendInput / SetCursorPos / SetForegroundWindow は一切呼んでいない。
    (3) 配線の確認(scratchpad の integ_check.py。偽 harness+偽サンプラで Row.run_python を通す。実 PageFolio は起動しない): 押下なし→clean(focus_correct の真偽で product-focus-ok / failure-candidate)、awaiting-enter 中と start-harness 中の PageFolio 押下→contaminated(outcome=procedure-contaminated、F5 操作と質問を省略、focus-result は記録、cleanup 実行)、書込先は tmp で原本は不変。
    (4) 既存の `--selftest` は未実行: 隔離 PageFolio を実際に起動して peer が SetForegroundWindow を発するため、前景を奪う実走禁止の制約に反する。代わりに上の (2)(3) で新ロジックを確認した。
  implication: 再走で押下ログ付きの判定が得られる状態になった。残る blind spot は、タッチ/ペン入力(GetAsyncKeyState の物理マウスボタンには出ない)、`input()` 待機中の監視継続(console 実機での確認は再走が最初)、06-MANUAL-EVIDENCE.json の driver_sha256 が旧値のまま(下の Resolution に記載)。

## Eliminated

- hypothesis: 「非アクティブ化→再アクティブ化の機構そのもの(FocusRestorer.restore→SetForegroundWindow→Tk の FocusIn)が preview でだけ Open へ移す」
  evidence: exp1/exp2 で preview・thumb とも settled=canvas。実 harness(uat-owner-preview)経由でも 4 回すべて canvas。
  status: 暫定(01:2x JST 付記)— 根拠の実験は T0「重複の可能性あり・判定に使わない」群。クリーンな窓(01:20〜02:00)で取り直すまで棄却の根拠にしない。
  re-verified: 01:23〜01:32 JST のクリーン窓で取り直し済み(none×5 が全て settled=canvas。decoy 方式 3・prev 方式 2)。暫定を解除して棄却。
  timestamp: 2026-10-25

- hypothesis: 「ポインタが Open ボタン上にあること、または Alt 単独タップ(メニューバー活性化)が入力先を Open へ移す」
  evidence: exp1 で PRE=pointer / alt / altpointer(ポインタを Open ボタン中心へ SetCursorPos、Alt keybd_event)を非アクティブ化の前に入れても settled=canvas。
  status: 暫定(01:2x JST 付記)— 根拠の実験は T0「重複の可能性あり・判定に使わない」群。クリーンな窓で取り直すまで棄却の根拠にしない。
  re-verified: 01:23〜01:32 JST のクリーン窓で、ポインタを btn_open 中心へ置く hover×2(decoy 1・prev 1)が settled=canvas。prev 方式は非活性化の直前に Alt 単独タップが PageFolio に入る(Alt+ポインタ相当)。暫定を解除して棄却。
  timestamp: 2026-10-25

- hypothesis: 「製品コードが明示的に右ペインのボタンへ focus_set している」
  evidence: pagefolio/ を focus_set|focus_force|tk_focus|takefocus で grep。該当は page_ops.py:405(preview_canvas)、dialogs の入力欄、*_dialog の existing.focus_force()、viewer.py:621(popup)、startup_focus.py のみ。ボタンへの focus 呼出しは無い。
  timestamp: 2026-10-25

- hypothesis: 「restore() が記憶(record / focus_lastfor)と別の部品を選ぶ、または復帰処理の中・直後で Open へ focus 呼出しが起きる(分岐 C)」
  evidence: クリーン窓の全 trace で restore-before 時点の record=lastfor が最終的な settled と同一。tcl-focus の呼出し元は startup_focus.py:227(restore)のみで、対象は記憶値と同一。record=canvas なら canvas(none×5・hover×2・利用者診断 3)、record=btn_open なら btn_open(実マウス 2・合成 3)へ戻る。btn_open への focus 呼出しが restore で起きるのは record が既に btn_open の場合に限る。
  timestamp: 2026-10-25 01:3x JST

## Resolution

root_cause: |
  (分岐 A・機構は決定的に実証済み / 原失敗の実走で押したことだけ未実証) 原 W02/preview@script で、Enter を押す前の約 10 秒間に PageFolio 内で btn_open(ファイルを開く)へ入力先が移った(ttk Button は押下だけで ttk::clickToFocus により focus を取る)ため、FocusRestorer が記憶する入力先が preview_canvas から btn_open に更新されていた。二次起動による復帰 restore() はその記憶値へ正しく focus_set しており、製品の欠陥ではない。G1 の期待値(prepared 時の入力先 = preview_canvas に固定)が、利用者が PageFolio 内で入力先を変えた場合を製品失敗と誤判定する。クリーン窓で btn_open への押下だけから原失敗の署名が完全に再現した(実マウス 2/2・合成 3/3、押下なしの対照 7/7 は canvas)。
fix: |
  (適用済み・手順是正のみ。製品は変更しない。利用者承認済み 2026-10-25)
  06-05 driver `.planning/phases/06-release-validation/06-05-drivers/uat_row.py`(Phase 4 covered_files 外・tests/ から参照なし)を次のとおり変更した。
  (1) 読み取り専用の入力監視 `InputMonitor`(約 8 ms ポーリングのスレッド。GetAsyncKeyState/GetCursorPos/WindowFromPoint/GetAncestor/GetForegroundWindow のみ)を Python 入口の行全体(隔離 PageFolio 起動前〜F5 観察まで)に被せる。マウス 3 ボタンの押下/離上エッジを、時刻・ポインタ位置・押下先の窓(pid/title/class)・前景窓・phase 付きで記録し、前景窓の遷移と、PageFolio が前面にある間のキー押下(キー番号のみ。Alt 押下中・基準線・修飾キーは除外)も記録する。押下先が PageFolio の所有 PID の窓かは、起動後に分かる所有 PID で事後に判定する。
  (2) phase は start-harness → awaiting-enter(Enter 待ち)→ peer(Enter〜二次起動完了)→ post-peer。start-harness / awaiting-enter / peer の PageFolio 上の押下を「手順汚染」とする(復帰直前の記憶と settled_focus に影響しうる範囲)。post-peer(F5 観察)は参考記録のみ。
  (3) 判定フィールドを分離: session JSON に `input_monitor`(全イベント)・`procedure_assessment`・`procedure_verdict`(clean / contaminated / keys-suspect / monitor-incomplete / not-monitored)・`focus_attribution`(product-focus-ok / product-focus-failure-candidate は clean のときだけ。それ以外は not-judged-<verdict>)を追加。focus_correct=false をそのまま製品失敗とみなさない。contaminated が peer 直後に確定した場合は、利用者に F5 操作と質問を求めず、focus-result だけ記録して終了し「再走が必要」を表示する(outcome=procedure-contaminated)。
  (4) 注意文の具体化: 「Enter を押すまで PageFolio の画面内は一切クリックしない(ボタン・サムネイル・プレビュー・余白も含む)。PowerShell へはタイトルバーをクリックするか Alt+Tab で戻る(隠れているときはタスクバーの PowerShell ボタンでも可)」。準備時の前景が PageFolio かどうかで文を出し分ける。
  (5) 原本保持: session JSON の保存先ファイル名はタイムスタンプ付きで、同名が既にあれば連番を付けて上書きしない。原失敗の W02_preview_at_script-20261024T144058Z.json は一切変更しない。再走は別ファイルとして保存される。
  (6) 新設 CLI `--check-monitor`: 入力監視ロジックの機構確認(窓も入力も作らず前景も変えない)。実EXE 行は利用者が PageFolio 内を操作する手順のため監視対象外(input_monitor.enabled=false・procedure_verdict=not-monitored を記録)。
verification: 合格。再走 2 回目(W02_preview_at_script-20261025T060315Z.json)が procedure_verdict=clean・押下 0 件で settled_focus=preview_canvas・focus_correct=true となり分岐 A を確定。再走 1 回目(…20261025T055841Z.json)はタイトルバーでの窓移動を contaminated と判定(合否不使用。復帰は canvas で正)。機構確認(ruff/AST/--check-monitor/偽 harness 統合確認)も合格。製品・tests/・Phase 4 被覆ファイルの変更なし=Phase 4/5 の鮮度と 06-04 最終ビルドに影響なし。残課題: driver はタイトルバー(非クライアント領域)押下もクライアント押下と同じく汚染判定する(偽陽性。必要なら別途改善)。06-MANUAL-EVIDENCE.json の driver_sha256 更新は 06-05 側で行う。
files_changed:
  - .planning/phases/06-release-validation/06-05-drivers/uat_row.py (sha256 9758a3a67c80c7f93dc465860bd80347668fcc474a5208a3b78588acc63d76b3。旧 ea751632ee4e...。06-MANUAL-EVIDENCE.json の driver_sha256 は旧値のまま=更新が必要)
diagnostic_files_added:
  - .planning/debug/preview-focus-not-restored-evidence/diag_owner.py
  - .planning/debug/preview-focus-not-restored-evidence/diag_preview_focus.py
  - .planning/debug/preview-focus-not-restored-evidence/diag_btn_press.py (オプション: --intervene none|hover|press-release-outside|tab|synthetic-press-release-outside、--deactivate decoy|prev、--tag)
  - .planning/debug/preview-focus-not-restored-evidence/diag-preview-20261025T004750.json
  - .planning/debug/preview-focus-not-restored-evidence/diag-preview-20261025T005032.json
  - .planning/debug/preview-focus-not-restored-evidence/diag-thumb-20261025T005240.json
  - .planning/debug/preview-focus-not-restored-evidence/probe-clean-*.json (01:23〜01:32 JST のクリーン窓 17 実行。判定に使う)
  - .planning/debug/preview-focus-not-restored-evidence/probe-*.json のうち probe-clean- 以外 (01:20 より前の試行。参考記録・判定に使わない。停止した run も含め全て保持)
