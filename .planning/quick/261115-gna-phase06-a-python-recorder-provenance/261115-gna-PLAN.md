---
phase: quick-261115-gna
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/06-release-validation/06-05-python-provenance.cjs
  - .planning/phases/06-release-validation/06-05-record-w01-python.cjs
  - .planning/phases/06-release-validation/06-05-record-w02-settings.cjs
  - .planning/phases/06-release-validation/06-05-record-w03-python.cjs
  - .planning/phases/06-release-validation/06-05-record-w04.cjs
  - .planning/phases/06-release-validation/06-05-record-w05b.cjs
  - .planning/phases/06-release-validation/06-05-record-w12c.cjs
  - .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs
  - .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-reverify.cjs
  - .planning/phases/04-startup-control/04-reverify-20261115-pyrec/
  - .planning/phases/04-startup-control/04-QUALITY-PYREC-20261115.json
  - .planning/phases/04-startup-control/04-REVALIDATION-PYREC-20261115.md
  - .planning/phases/05-config-notification/05-REVALIDATION-PYREC-20261115.md
  - .planning/phases/04-startup-control/04-VERIFICATION.md
  - .planning/phases/05-config-notification/05-VERIFICATION.md
  - 開発履歴.md
autonomous: true
requirements: [V110-QA-02]

estimate:
  tokens: 95000
  raw_tokens: 95000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "区分A Python 18行（W01×4・W02×6・W03×2・W04×2・W05a×2・W05b×2）の recorder は、%TEMP% の final_dir が消失していても loss_incident.restored_final_dir の release-report.json（配布tree hash・EXE hash・rebuild run_id 照合済み）で凍結65入力を照合でき、ENOENT で停止しない"
    - "manifest.formal_provenance を持たない session（旧harness採取）は、dry-run・本記録のどちらでも書込より前に固定文言 formal_provenance欠落 で拒否される"
    - "formal_provenance の source_inputs（集合とhash）・original_plugins・phase04（report sha256・covered_digest・所有CLIのfresh）・provenance-before-stop.json matched のどれか1つでも現行と不一致なら拒否される"
    - "記録対象は台帳内で一意な新有効行（python_input_generation が SUPERSESSION の superseded_by と一致し、supersedes リンクが同じ card を指す）だけで、python_input_generation など既存値は上書きされず、観測時の実入力世代は observation_basis.observed_python_input に別欄で記録される"
    - "CRLF を含む現行 06-UAT.md の card を一意に特定でき（現行 recorder は LF 前提で20行とも card missing になる）、card 以外の行の改行は変わらない"
    - "06-05-record-w12c.cjs の新規記録は environment.elevated を出力する"
    - "検証は隔離temp repo と --dry-run だけで行われ、実台帳・06-UAT.md・06-05-evidence は1byteも変化しない"
    - "Phase04/05 の verification.status が passed で、単一プロセス全件 pytest 1回の結果と入力前後hashが新しい REVALIDATION-PYREC-20261115 文書に記録されている"
  artifacts:
    - path: ".planning/phases/06-release-validation/06-05-python-provenance.cjs"
      provides: "resolveFinalReport / checkFormalProvenance / selectEffectiveRow / locateUatCard / updateUatSummary / treeHash / PROVENANCE_MISSING"
    - path: ".planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs"
      provides: "e2e-w01 / real-report / legacy-reject / static の4モード検証"
    - path: ".planning/phases/04-startup-control/04-REVALIDATION-PYREC-20261115.md"
      provides: "Phase04 再検証記録"
    - path: ".planning/phases/05-config-notification/05-REVALIDATION-PYREC-20261115.md"
      provides: "Phase05 再検証記録"
  key_links:
    - from: ".planning/phases/06-release-validation/06-05-record-w01-python.cjs"
      to: ".planning/phases/06-release-validation/06-05-python-provenance.cjs"
      via: "require('./06-05-python-provenance.cjs') → checkFormalProvenance を session parse 直後に呼ぶ"
    - from: ".planning/phases/06-release-validation/06-05-python-provenance.cjs"
      to: "tests/test_startup_windows.py"
      via: "_formal_source_inputs / _formal_original_plugins / _formal_parent_gate と同じ列挙・照合規則（node 側で再実装、.py は変更しない）"
    - from: ".planning/phases/06-release-validation/06-05-python-provenance.cjs"
      to: ".planning/phases/06-release-validation/06-BUILD-EVIDENCE.json"
      via: "final_release.loss_incident.restored_final_dir 優先 → final_dir フォールバック"
    - from: ".planning/phases/04-startup-control/04-VERIFICATION.md"
      to: ".planning/phases/06-release-validation/06-05-record-w12c.cjs"
      via: "covered_files に含まれる（w12c 変更で stale → Task 3 で digest 再計算）"
---

<objective>
Phase06 区分A（Python 再採取）の正式記録 recorder を、2026-11-06 の再利用監査（06-PYTHON-REUSE-AUDIT-20261106.md）が「証拠不足」とした点を再生産しない形に改修する。利用者は 2026-11-15 に作業tree凍結の解除を承認した（範囲は recorder と Phase04/05 再検証のみ）。

改修内容は5点: (1) 消失した final_dir ではなく restored_final_dir を照合付きで読む、(2) harness が start 時に保存した manifest.formal_provenance（source_inputs / original_plugins / phase04）を記録時に現行treeと照合し、台帳行にも残す、(3) 台帳の新有効行を一意に選び python_input_generation を上書きしない、(4) CRLF を含む現行 06-UAT.md の card を正しく見つける、(5) 全 recorder に書込なしの --dry-run を用意する。あわせて HANDOFF で合意済みの W12c recorder の environment.elevated 出力を入れ、Phase04/05 を再検証する。

対象は18行。W05c script/module の2行は本計画では扱わない（理由は「本計画で扱わないもの」を参照。判断待ち）。

Purpose: 区分Aの実機再採取（利用者同席）を始める前に、記録の段階で入力同一性と Phase04 鮮度の証拠が機械的に強制され、台帳に残る状態にする。
Output: 共通 provenance module、改修済み recorder 6本、隔離検証スクリプト、Phase04/05 再検証の証拠一式と REVALIDATION 文書2本、更新済みの 04/05-VERIFICATION.md。
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/HANDOFF.json
@.planning/phases/06-release-validation/06-PYTHON-REUSE-AUDIT-20261106.md
@.planning/phases/06-release-validation/06-05-record-w01-python.cjs
@.planning/phases/04-startup-control/04-REVALIDATION-W12B-PID-20261109.md
@.planning/phases/05-config-notification/05-REVALIDATION-G4-20261107.md

<planning_facts>
（計画者が 2026-11-15・HEAD=aceed78 で実測した事実。executor は再調査せずこれを前提にしてよい）

対象行と recorder の対応（ファイル名の正規表現で確定）:
- 06-05-record-w01-python.cjs → W01 normal/zoomed × script/module（4行）
- 06-05-record-w02-settings.cjs → W02 settings/thumb/preview と W05a nested-settings の script/module（8行。case は s.case）
- 06-05-record-w03-python.cjs → W03 pdf-3page script/module（2行）
- 06-05-record-w04.cjs → W04 ocr-1page script/module/production-exe（Python 2行。EXE 行は pass 済み）
- 06-05-record-w05b.cjs → W05b ocr-close-confirm script/module/production-exe（Python 2行。--dry-run あり）
- 06-05-record-w05c-python.cjs → W05c quit-no script/module（2行。本計画では変更しない）

harness の formal_provenance（tests/test_startup_windows.py:56-160, 3470-3520, 3570, 3730-3740）:
- start 時に manifest.formal_provenance = {source_inputs, original_plugins, phase04} を保存する（W12a の時だけ w12a_helper_sha256 が追加）。
- source_inputs は pagefolio.py・pagefolio/**/*.py・tests/**/*.py・.planning/phases/06-release-validation/06-05-w12a-driver.py の sha256（__pycache__ 除外）。.cjs recorder と 06-05-drivers/*.py は含まれない。
- phase04 は {status:'passed', covered_digest（04-VERIFICATION.md の covered_digest 行）, report_sha256（04-VERIFICATION.md 全体）}。取得時に所有CLI verification.status が passed であることを要求。
- peer/inspect で _check_formal_provenance を assert、stop で run/provenance-before-stop.json に {matched:true} か {matched:false,error} を保存。
- inspect の出力（session の harness_inspect.json）は manifest 全体を含む。旧 session 18件はすべて harness_inspect.json.manifest を持つが formal_provenance を持たない（W01_normal_at_script-20261028T100202Z.json 等で確認済み）。旧 run dir（.planning/tmp/pagefolio-uat-*）は全て消失。
- node 側の列挙・照合の手本は 06-05-record-w12a.cjs:108-148（enumeratePython・plugins・phase04 report/CLI）。

final_release:
- 06-BUILD-EVIDENCE.json の final_release.final_dir（%TEMP%配下）は消失（release-report.json ENOENT）。
- final_release.loss_incident.restored_final_dir（%LOCALAPPDATA%\PageFolio-release\pf06_final_3f96a37a7cef4ee1ab3a1c1b2f2c435f\PageFolio-v1.10.2）の release-report.json は存在し、run_id c04825cf60054565970f9a6a997523d3 が final_release.runs の order==='rebuild' と loss_incident.restoration_verification.embedded_report_run_id の両方に一致。input_manifest 65件（tests/ を含まない）は現行bytesと drift 0。
- 配布tree照合の手本は 06-05-record-w12b.cjs の walk/treeHash（final_release.tree_sha256 と PageFolio.exe の exe_sha256）。restored 優先の書き方は 06-05-record-w05c-python.cjs:188 と 06-05-record-w12b.cjs:125。

台帳・UAT:
- 06-MANUAL-EVIDENCE.json（LF）の Python 20行は status not-run・generation 5・evidence_kind python-real・python_input_generation "python-input-0b788cdf0b1c"・supersedes {path:"06-05-evidence/PYTHON-INPUT-SUPERSESSION-20261106.json", row_index:N}。各 card は台帳内で1件だけ。
- python_input_generation の意味: PYTHON-INPUT-SUPERSESSION-20261106.json の superseded_by（= "python-input-" + current_harness_sha256 の先頭12桁。current_harness_sha256 は 2026-11-06 時点の tests/test_startup_windows.py 全体の sha256）。supersession が作った「新有効行の世代ラベル」であり、将来の観測入力のhashではない。現行 tests/test_startup_windows.py は 751de11ba93e… で、G4/W12b 修正で正当に変わった。
- 06-UAT.md は CRLF/LF 混在で、Python 20行の card 見出しは全て "### <card>\r\n"。現行6 recorder は marker を '### '+row+'\n' で探すため、20行とも 'card missing' で停止する（未発見の潜在不具合）。集計行は "本受入は必須108行中23行pass・85行not-run・W11対象外2行not-run。"。
- release_uat_support.py:1748-1751 は pass 行に environment.os / elevated / session_id を要求（elevated=false は可）。行の未知キーは拒否しない。

Phase04/05 の鮮度:
- 両 phase とも verification.status は passed。04-VERIFICATION.md の covered_files（167件）と 05-VERIFICATION.md（250件）は 06-05-record-w12c.cjs と 06-05-record-w05c-python.cjs を含むが、w01-python / w02-settings / w03-python / w04 / w05b は含まない。05 は 開発履歴.md も含む。
- node ~/.codex/gsd-core/bin/gsd-tools.cjs query verification.fingerprint <phaseDir> <covered_files...> は読取専用で、現行 covered_files を渡すと現行 covered_digest を再現する（両 phase で一致を確認済み）。
- 直近の再検証（04-reverify-20261109-w12b-pid）は 186入力（inputs-before.json のキー）・argv「-m pytest -q -rA -p no:cacheprovider --basetemp=%LOCALAPPDATA%\Temp\pf04-04-reverify-20261109-w12b-pid --junitxml=…」・2488 passed・732秒。成果物は checks.json / environment.txt / inputs-before.json / inputs-after.json / junit.xml / result.json / ruff-discovery.json / stderr.txt / stdout.txt。

pytest で recorder を直接動かす既存試験:
- tests/test_w05c_evidence.py・tests/test_w05c_runner.py は 06-05-record-w05c-python.cjs と 06-05-w05c-evidence.cjs の2ファイルだけを隔離fixtureに複製し、formal_provenance のない manifest で dry-run 成功を期待する。
- tests/test_w12c_evidence.py は 06-05-record-w12c.cjs を単独で複製し、fixture の manifest.environment は {"session_id": 1}（is_admin なし）。
- w01-python / w02-settings / w03-python / w04 / w05b を動かす pytest は無い。
</planning_facts>
</context>

<tasks>

<task type="tracer">
  <name>Task 1: 共通 provenance module と W01 recorder を端から端まで通す（隔離temp repo で検証）</name>
  <files>.planning/phases/06-release-validation/06-05-python-provenance.cjs, .planning/phases/06-release-validation/06-05-record-w01-python.cjs, .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs</files>
  <read_first>
    - .planning/phases/06-release-validation/06-05-record-w01-python.cjs（全57行）
    - .planning/phases/06-release-validation/06-05-record-w12a.cjs:1-30, 100-240（safe()・enumeratePython・plugins・phase04 CLI・dry-run の作法）
    - .planning/phases/06-release-validation/06-05-record-w12b.cjs:80-130（walk/treeHash、restored_final_dir 優先）
    - tests/test_startup_windows.py:56-140（_formal_source_inputs / _formal_original_plugins / _formal_parent_gate / _check_formal_provenance）
    - tests/test_w12a_evidence.py:28-60, 230-260（隔離fixtureの組み方と USERPROFILE 差し替えで偽 CLI を使う方法。読むだけで変更しない）
  </read_first>
  <action>
共通 module `.planning/phases/06-release-validation/06-05-python-provenance.cjs` を新規作成する。Node 標準モジュール（fs/path/crypto/child_process）だけを使い、module.exports で次を公開する。root と phase は呼出側の __dirname から渡す（module は自分の位置から実台帳を推測しない。これにより recorder を temp repo に複製すれば temp repo だけを読む）。

- 定数 PROVENANCE_MISSING: 文言は「formal_provenance欠落（旧harness採取のため再採取が必要）」。
- resolveFinalReport({phase, build}): final_release.loss_incident?.restored_final_dir を優先し、無ければ final_release.final_dir を使う。使う dir が symlink でないこと、treeHash(dir).hash === final_release.tree_sha256、dir の PageFolio.exe の sha256 === final_release.exe_sha256、release-report.json の run_id === final_release.runs の order==='rebuild' の run_id（loss_incident がある場合は restoration_verification.embedded_report_run_id とも一致）を要求する。戻り値は {finalDir, report, source:'restored_final_dir'|'final_dir'}。dir が無い・照合不一致はすべて throw。
- treeHash(dir): 06-05-record-w12b.cjs の walk/treeHash と同じ規則（dirs と files を sort し、files は相対path→sha256、hash は JSON.stringify({dirs,files}) の sha256）で実装し export する（検証スクリプトの fixture 生成にも使う）。
- checkFormalProvenance({root, run, manifest}): 次の順に照合し、最初の不一致で throw する。(1) manifest.formal_provenance が object で、source_inputs・original_plugins・phase04 が object であること。無ければ PROVENANCE_MISSING で throw（これを必ず最初に行い、旧 session は run dir に触れる前に拒否されるようにする）。(2) run は path.resolve 後に root/.planning/tmp 直下であること、run/manifest.json の formal_provenance が渡された manifest.formal_provenance と JSON.stringify で完全一致すること、run/provenance-before-stop.json の matched === true であること。(3) 現行 Python 入力を tests/test_startup_windows.py の _formal_source_inputs と同じ規則（06-05-record-w12a.cjs の enumeratePython を手本、symlink 拒否・__pycache__ 除外）で列挙し、キー集合が完全一致かつ各 sha256 一致。(4) root/plugins 配下の全ファイルを列挙し original_plugins とキー集合・hash 一致（plugins が無ければ空 object と一致）。(5) phase04.status === 'passed'、root/.planning/phases/04-startup-control/04-VERIFICATION.md の sha256 === phase04.report_sha256、その covered_digest 行（正規表現は w12a と同じ）=== phase04.covered_digest、さらに path.join(process.env.USERPROFILE||'', '.codex/gsd-core/bin/gsd-tools.cjs') を process.execPath で `query verification.status <root>/.planning/phases/04-startup-control --raw` 実行（timeout 15000）して status === 'passed'。戻り値は {formal: manifest.formal_provenance, observed:{label:'python-input-'+harness先頭12桁, harness_sha256: source_inputs['tests/test_startup_windows.py'], source_inputs_sha256: キーを sort した [key,hash] 配列の JSON の sha256, source_input_count, plugin_count}, provenance_before_stop:true}。
- selectEffectiveRow({phase, ledger, caseId, card, entry}): ledger.cases で id===caseId が丁度1件、その subrows で card===card が丁度1件であることを assert。行は status==='not-run'・generation===5・release_requirement==='required'・evidence_kind==='python-real'・entry===entry であること。さらに phase/06-05-evidence/PYTHON-INPUT-SUPERSESSION-20261106.json を読み、row.supersedes.path がそのファイルの phase 相対path と一致、supersession.rows[row.supersedes.row_index].card === card、row.python_input_generation === supersession.superseded_by を要求する（python_input_generation は現行 harness hash と比較しない・書き換えない。理由は planning_facts の意味づけ。旧 pass 行は subrows から外れて SUPERSESSION に退避済みなので、この条件で新有効行だけが選ばれる）。行オブジェクトを返す。
- locateUatCard(uat, card): 見出し "### "+card の直後が "\r\n" または "\n" で、直前が文字列先頭か "\n" である出現を数え、丁度1件であることを assert。card の範囲（次の "\n### " まで）と、その見出し行の改行コード eol を返す。card に "- **状態**: not-run" が含まれることも assert。
- updateUatSummary(uat, passed): 集計行の正規表現（w01 recorder の既存パターン）が丁度1回一致することを assert してから置換した文字列を返す。

`06-05-record-w01-python.cjs` を次のとおり改修する（既存の判定条件は弱めない・順序以外は変えない）。
- 引数は process.argv.length === (dry ? 4 : 3) を要求し、--dry-run を受け付ける（usage 文言は w12a と同じ形）。entry はファイル名の _at_(script|module)- から取る。
- session を JSON.parse した直後、他の assert より前に checkFormalProvenance({root, run: s.run, manifest: s.harness_inspect.json.manifest}) を呼ぶ。
- 28行目の final_dir 直読みを resolveFinalReport に置き換える（既存の generation・exe_sha256・凍結65入力 drift 照合はそのまま残す）。
- 台帳行の選択を selectEffectiveRow({caseId:'W01', card:s.row, entry}) に置き換える。
- UAT は locateUatCard / updateUatSummary を使い、状態行の置換は `- **状態**: not-run[^\r\n]*` に一致させて既存の改行を保ち、追加する「回答原文」行には eol を使う。置換結果が元と同じなら throw。
- raw の copy 対象に run の provenance-before-stop.json と inspection.json（存在すれば）を加える。copy bytes は先にメモリへ読み、--dry-run ならここで {row, status:'validated', dry_run:true, final_report_source, observed_python_input} を出力して exit 0（mkdir・writeFile は一切しない）。
- 本記録時は既存の欄に加え、row.observation_basis に formal_provenance（source_inputs / original_plugins / phase04 の全体）、observed_python_input（上の observed）、provenance_before_stop:true、final_report_source、recorder_sha256（自ファイル）、provenance_module_sha256 を追加する。row.python_input_generation と row.supersedes は変更しない。
- 書込順は従来どおり raw copy → ledger → UAT。

検証スクリプト `.planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs` を新規作成する（Task 2・3 でも使うので4モードを今まとめて書く。.py ではないので tests/ の source_inputs に影響しない）。どのモードも失敗時は理由を出して exit 1、成功時は JSON 要約を出して exit 0。
- e2e-w01: fs.mkdtempSync(path.join(os.tmpdir(),'pf-gna-')) に temp repo を作り、repo/.planning/phases/06-release-validation/ に実物の 06-05-record-w01-python.cjs と 06-05-python-provenance.cjs を複製する。fixture として pagefolio.py・pagefolio/__main__.py・tests/test_startup_windows.py・06-05-w12a-driver.py（小さな内容）、plugins/page_info.py、04-VERIFICATION.md（covered_digest 行あり）、USERPROFILE 差し替え先の偽 gsd-tools.cjs（{"status":"passed"} を出力）、06-BUILD-EVIDENCE.json（generation 5、final_dir は存在しないpath、loss_incident.restored_final_dir は temp 内の dir、PageFolio.exe と release-report.json を置き tree_sha256 は export した treeHash で計算）、SUPERSESSION JSON、台帳（W01 case に該当行1件、python_input_generation と supersedes 付き）、CRLF の 06-UAT.md（card と集計行）、.planning/tmp/<run>/ に manifest.json（formal_provenance は fixture の実hashで生成）・provenance-before-stop.json・uat-owner-normal/ の結果ファイル、06-05-evidence/ に W01_normal_at_script-<UTC>.json（現行 w01 recorder の全 assert を満たす session）を作る。その上で次を確認する。(p1) --dry-run が exit 0 で、temp repo の全ファイル bytes が前後で同一。(p2) 本記録が exit 0 で、変化したのは台帳・06-UAT.md・raw dir だけ、行が pass・python_input_generation と supersedes が不変・observation_basis.formal_provenance.source_inputs が fixture と一致・observed_python_input.label が 'python-input-'+fixture harness 先頭12桁・environment.elevated が boolean、UAT は card 以外の CRLF 行が不変で集計行が更新。(p3) 同じ session の再実行が拒否される。続いて fixture を毎回作り直して次の改変がすべて exit≠0 かつ temp repo 無変化であることを確認する: formal_provenance 削除（stderr に formal_provenance欠落）、tests/test_startup_windows.py の内容変更、tests/new_input.py 追加、plugins 変更、偽 CLI が stale を返す、04-VERIFICATION.md の covered_digest 変更、provenance-before-stop.json の matched:false、run/manifest.json の formal_provenance 改変、同 card の重複行、python_input_generation 改変、supersedes.path 改変、restored_final_dir 削除（final_dir も無い）、restored の release-report.json 改変（tree 不一致）。最後に temp dir を削除する。
- real-report: 実 repo の 06-BUILD-EVIDENCE.json に resolveFinalReport を読取専用で適用し、source==='restored_final_dir'・input_manifest 65件・現行bytes drift 0 を確認する。
- legacy-reject [recorder…|all]: 実 repo の 06-05-evidence にある旧 pass session（06-PYTHON-REUSE-AUDIT-20261106.md の表の W01〜W05b の18件。W05c 2件は除外）を、対応する recorder に --dry-run 付きで1件ずつ渡し、全件 exit≠0 かつ stderr に formal_provenance欠落 を含むことを確認する。引数 w01 なら W01 4件だけ、all なら18件。実行前後で実 repo の 06-MANUAL-EVIDENCE.json・06-UAT.md の sha256 と、06-05-evidence 配下の再帰的なファイル名一覧が同一であることを確認する。
- static: 改修5 recorder が require('./06-05-python-provenance.cjs') を含み、コメント行を除いて final_release.final_dir を直接含まず、--dry-run を受け付けること。06-05-record-w12c.cjs が elevated:manifest.environment.is_admin を含むこと。06-05-record-w05c-python.cjs・06-05-record-w05c-exe.cjs・06-05-record-w12a.cjs・06-05-record-w12b.cjs・06-05-w12a-driver.py・06-05-drivers/*.py の sha256 が `git show aceed78:<path>` と一致すること。引数 w01 では「w01 recorder の3条件」と「変更禁止ファイルの hash 不変」だけを確認し（Task 1 用）、引数 all ではそれに w02-settings・w03-python・w04・w05b の3条件と w12c の elevated を加える（Task 2 用）。

禁止: pagefolio/・tests/ の .py、06-05-w12a-driver.py、06-05-drivers/*.py、pyproject.toml、06-05-record-w12a.cjs・w12b.cjs・w05c-python.cjs・w05c-exe.cjs の変更。実台帳・06-UAT.md・06-05-evidence・SUPERSESSION への書込。GUI や `tests/test_startup_windows.py --uat` の起動。

完了後コミット（日本語・末尾に Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>）: 「Phase06区分A: W01 recorderにformal_provenance照合・restored_final_dir・新有効行選択・CRLF対応・dry-runを追加」。
  </action>
  <verify>
    <automated>node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs e2e-w01 && node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs real-report && node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs legacy-reject w01 && node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs static w01</automated>
    <automated>grep -v '^\s*//' .planning/phases/06-release-validation/06-05-record-w01-python.cjs | grep -c 'final_release.final_dir' # [HEAD=1 EXPECT==0]</automated>
    <automated>git diff --exit-code --name-only aceed78 -- '*.py' pyproject.toml # [HEAD=absent EXPECT==absent @aceed78 GUARD MUTATION: pagefolio/ か tests/ の .py を1byte変えると名前が出て exit 1 になる]</automated>
  </verify>
  <done>e2e-w01 の正例3件と改変13件がすべて期待どおりの結果（正例は exit 0、改変は exit≠0 かつ temp repo 無変化）になる。real-report が restored_final_dir・65件・drift 0 を返す。旧 W01 session 4件が dry-run で formal_provenance欠落 として拒否され、実台帳・UAT・evidence が無変化。.py と pyproject.toml に差分が無い。コミット済み。</done>
</task>

<task type="auto">
  <name>Task 2: W02/W05a・W03・W04・W05b の Python 経路へ同じゲートを広げ、W12c に elevated を出す</name>
  <files>.planning/phases/06-release-validation/06-05-record-w02-settings.cjs, .planning/phases/06-release-validation/06-05-record-w03-python.cjs, .planning/phases/06-release-validation/06-05-record-w04.cjs, .planning/phases/06-release-validation/06-05-record-w05b.cjs, .planning/phases/06-release-validation/06-05-record-w12c.cjs</files>
  <read_first>
    - 上記5ファイル（w02-settings 75行・w03-python 70行・w04 111行・w05b 171行・w12c は 190-246 行）
    - Task 1 で作った .planning/phases/06-release-validation/06-05-python-provenance.cjs と改修後の 06-05-record-w01-python.cjs（書き方をそろえる）
    - tests/test_w12c_evidence.py:55-70, 320-340（fixture の environment と改変試験。読むだけ）
  </read_first>
  <action>
4つの Python recorder（w02-settings・w03-python・w04・w05b）に Task 1 と同じ改修を入れる。各ファイルの行固有の判定（W02 の snapshot 照合、W03 の4手、W04 の OCR 要求、W05b の自動復帰判定など）は変えない。

- --dry-run を受け付ける（w02-settings・w03-python・w04 は新規、w05b は既存の --dry-run と --session-dir の挙動を維持）。dry-run はすべての照合を行い、raw dir 作成・台帳・UAT 書込の前に JSON 要約を出して exit 0。
- Python 経路（entry が script|module）では、session を parse した直後、他の照合や run dir の読込より前に checkFormalProvenance({root, run: s.run, manifest: s.harness_inspect.json.manifest}) を呼ぶ。w04 と w05b は run/manifest.json を早い段階（w04:18 付近、w05b:74 付近）で読むので、Python 経路ではその読込より前に呼ぶ。production-exe 経路にはこのゲートを適用しない（EXE 行は pass 済みで、harness manifest を持たない）。
- final_dir の直読み（w02-settings:36、w03-python:38、w04:91、w05b:150）を resolveFinalReport に置き換える。この置換は共通コードなので EXE 経路にも及ぶが、既存の照合（generation・EXE hash・凍結入力）はそのまま残す。
- 台帳行の選択を selectEffectiveRow に置き換える（caseId は w02-settings では s.case、他は固定の case ID。entry はファイル名から取る）。Python 経路だけで使い、EXE 経路は従来の選択のまま。
- UAT card の特定と集計行の更新を locateUatCard / updateUatSummary に置き換え、状態行置換は `[^\r\n]*` で既存の改行を保つ（W01 と同じ）。EXE 経路にも同じ関数を使ってよい（CRLF 対応の改善で、判定は弱めない）。
- Python 経路の本記録では、observation_basis に W01 と同じ6欄（formal_provenance・observed_python_input・provenance_before_stop・final_report_source・recorder_sha256・provenance_module_sha256）を加え、raw copy に provenance-before-stop.json と inspection.json を加える。python_input_generation と supersedes は変更しない。

06-05-record-w12c.cjs は232行目の row.environment=manifest.environment だけを、row.environment={...manifest.environment,elevated:manifest.environment.is_admin} に変える（HANDOFF の合意事項。値の出どころは 06-W12C-ENV-CORRECTION-20261109.md の補正と同じ manifest.environment.is_admin）。is_admin が boolean かどうかの新しい拒否条件は入れない（tests/test_w12c_evidence.py の fixture は is_admin を持たず、変更禁止の試験が失敗するため。pass 行の elevated 欠落は release_uat_support の構造監査が引き続き検出する）。w12c はこの1行以外を変えず、共通 module も require しない（試験 fixture は w12c 単体しか複製しない）。

注意: 06-05-record-w12c.cjs は 04/05-VERIFICATION.md の covered_files に含まれるので、このコミットの時点で Phase04/05 の verification.status は stale になる。Task 3 で再検証して戻す。また W12b/W12c の採取 driver は 06-05-*.py/.cjs 全体の hash を collector_inputs として保存するため、本変更より前に始めた W12b/W12c run は今後記録できなくなる（未記録の run は無い。新しい run は新しい hash を保存するので影響しない）。

禁止事項は Task 1 と同じ。06-05-record-w05c-python.cjs には触れない（CRLF の不具合も含めて「本計画で扱わないもの」を参照）。

完了後コミット: 「Phase06区分A: W02/W03/W04/W05a/W05bのPython recorderにformal_provenance照合を展開、W12c recorderにelevated出力を追加」。
  </action>
  <verify>
    <automated>node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs legacy-reject all && node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs static all && node .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs e2e-w01</automated>
    <automated>for f in w02-settings w03-python w04 w05b; do node --check .planning/phases/06-release-validation/06-05-record-$f.cjs || exit 1; done</automated>
    <automated>.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_w12c_evidence.py tests/test_w05c_evidence.py tests/test_w05c_runner.py tests/test_release_contract.py</automated>
    <automated>grep -c 'elevated' .planning/phases/06-release-validation/06-05-record-w12c.cjs # [HEAD=0 EXPECT>=1]</automated>
    <automated>git diff --exit-code --name-only aceed78 -- '*.py' pyproject.toml # [HEAD=absent EXPECT==absent @aceed78 GUARD MUTATION: pagefolio/ か tests/ の .py を1byte変えると名前が出て exit 1 になる]</automated>
  </verify>
  <done>旧 pass session 18件（W01〜W05b）が全件 dry-run で formal_provenance欠落 として拒否され、実台帳・UAT・evidence が無変化。static all が5 recorder の module 利用・final_dir 直読み無し・dry-run 対応、w12c の elevated、変更禁止ファイルの hash 不変を確認する。e2e-w01 が引き続き通る。w12c/w05c/release_contract の既存 pytest が通る。.py と pyproject.toml に差分が無い。コミット済み。</done>
</task>

<task type="auto">
  <name>Task 3: Phase04/05 の再検証（単一全件 pytest 1回・入力前後hash・REVALIDATION 文書・digest 更新）</name>
  <files>.planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-reverify.cjs, .planning/phases/04-startup-control/04-reverify-20261115-pyrec/, .planning/phases/04-startup-control/04-QUALITY-PYREC-20261115.json, .planning/phases/04-startup-control/04-REVALIDATION-PYREC-20261115.md, .planning/phases/05-config-notification/05-REVALIDATION-PYREC-20261115.md, .planning/phases/04-startup-control/04-VERIFICATION.md, .planning/phases/05-config-notification/05-VERIFICATION.md, 開発履歴.md</files>
  <read_first>
    - .planning/phases/04-startup-control/04-reverify-current.cjs（全58行。runner の手本。このファイル自体は変更しない）
    - .planning/phases/04-startup-control/04-REVALIDATION-W12B-PID-20261109.md と .planning/phases/05-config-notification/05-REVALIDATION-G4-20261107.md（文書の書き方）
    - .planning/phases/04-startup-control/04-QUALITY-W12B-PID-20261109.json（集約JSONの欄）
    - .planning/phases/04-startup-control/04-VERIFICATION.md と 05-VERIFICATION.md の frontmatter（current_execution・prior_execution_*・re_verification の書き方）
    - 開発履歴.md の先頭20行（v1.10.2 節の日付付き箇条書きの形式）
  </read_first>
  <action>
runner `.planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-reverify.cjs` を、04-reverify-current.cjs を手本に新規作成する。違いは次のとおり。出力先は .planning/phases/04-startup-control/04-reverify-20261115-pyrec/（既存なら拒否）。入力集合は、04-reverify-20261109-w12b-pid/inputs-before.json のキー（186件）と、04-reverify-current.cjs と同じ探索規則で今見つかるファイルと、.planning/phases/06-release-validation/06-05-python-provenance.cjs の和集合。存在しないものは missing に記録する。pytest の argv は直近の再検証にそろえ、.venv/Scripts/python.exe -m pytest -q -rA -p no:cacheprovider --basetemp=<LOCALAPPDATA>\Temp\pf04-04-reverify-20261115-pyrec --junitxml=<出力先>/junit.xml とする（basetemp は既存なら拒否。%LOCALAPPDATA%\Temp\pf_pytest_tmp は削除できず全件 ERROR になった既知問題があるため使わない）。出力は inputs-before.json・inputs-after.json・stdout.txt・stderr.txt・environment.txt（python の version・executable・platform）・result.json（started・finished・argv・code・signal・error・inputCount・missing・changed）。

全件 pytest は CLAUDE.md のリリースゲートに従い単一プロセスで1回だけ実行する。所要は約12〜16分で Bash の上限10分を超えるので、run_in_background で起動して完了通知を待つ。

- 結果が exit≠0・failures>0・errors>0・クラッシュのどれかなら、その結果を 04-REVALIDATION-PYREC-20261115.md に失敗として記録して停止する。CLAUDE.md の切り分け手順1（該当ファイル単体の実行）は診断として実行・記録してよいが、全件の再実行で合格扱いにしない。VERIFICATION.md は更新せず、オーケストレータへ報告する。
- 成功時は、出力先に checks.json を作る（.venv/Scripts/ruff.exe check . --no-cache、.venv/Scripts/ruff.exe format --check --no-cache .、python -c の ast.parse(pagefolio.py) の argv・exit・stdout・stderr）。.py は変えていないので ruff は通るはずで、ここで変更が無いことの証拠を残す。

成功時だけ続ける。
1. 開発履歴.md の v1.10.2 節の箇条書きの先頭に「- 2026-11-15: …」を1項目追記する（内容: 区分A Python recorder の formal_provenance 照合・restored_final_dir 対応・新有効行選択・CRLF 対応・dry-run、W12c の elevated 出力、製品・版番号・最終EXEは不変、W05c 2行は判断待ち）。追記後に入力集合を再hashし、差分が 開発履歴.md だけであることを出力先の post-history-inputs.json に保存する（G4 の流儀）。
2. .planning/phases/04-startup-control/04-QUALITY-PYREC-20261115.json を 04-QUALITY-W12B-PID-20261109.json と同じ欄で作る（checked_at・result・totals は junit.xml から tests/errors/failures/skipped/time・warnings・input_count・current_drift（集約時の再hashと inputs-after の差分）・changes_since_w12b_pid_baseline（reason、git diff --name-only aceed78 で得た変更ファイル、product_changed:false・frozen_exe_changed:false・version_changed:false）・checks・raw_hashes（出力先の各成果物の sha256）・reviews（独立コードレビューは未実施である旨を正直に書く）・manual_uat「未変更。台帳23 pass / 85 not-run / W11対象外2 not-run」・release_allowed:false）。
3. 04-REVALIDATION-PYREC-20261115.md と 05-REVALIDATION-PYREC-20261115.md を直近の REVALIDATION 文書の形式（frontmatter の phase・status・reason、要約段落、「変更内容」、Nyquist・Security・UI・Code review・Verification の箇条、台帳状態）で日本語で書く。W05c 2行が未改修であること、区分A の実機採取は本 quick 完了後に始める必要があること（formal_provenance.phase04.report_sha256 は採取開始時の 04-VERIFICATION.md の hash を固定するので、次の 4 で VERIFICATION.md が変わる前に始めた採取は記録できない）を明記する。
4. VERIFICATION.md の digest 更新は、次の3条件がすべて成り立つ場合だけ行う: 全件成功、inputs の changed と missing が空、`git diff --name-only aceed78` の結果と各 VERIFICATION.md の covered_files の共通部分が、04 では 06-05-record-w12c.cjs だけ、05 では 06-05-record-w12c.cjs と 開発履歴.md だけ。成り立たなければ更新せず停止して報告する（独立 verifier が必要）。成り立つ場合は、各 VERIFICATION.md の既存 covered_files 配列をそのまま使い `node ~/.codex/gsd-core/bin/gsd-tools.cjs query verification.fingerprint <phaseDir> <covered_files...>` で新しい covered_digest を得る。frontmatter は Edit で範囲を限って更新する: verified、covered_digest、re_verification の previous_verified と trigger（w12c 1行と開発履歴の変更、全件の件数、入力数）、current_execution は今回の値に置き換え、直前の current_execution は historical:true を付けた prior_execution_20261109_w12b_pid として残す。covered_files・score・truth 本文は変えない。tests_reexecuted_by_verifier:false と、独立 verifier ではなく quick の executor が機械的に再計算した旨を書く。
5. 両 phase で `node ~/.codex/gsd-core/bin/gsd-tools.cjs query verification.status <phaseDir> --raw` が passed であることを確認する。

HANDOFF.json・STATE.md・.continue-here.md・台帳・06-UAT.md は変更しない（オーケストレータが更新する）。

完了後コミット: 「Phase04/05: Python recorder改修後の再検証（単一全件pytest・入力前後hash一致）と検証digestを更新」。
  </action>
  <verify>
    <automated>node -e "const r=require('./.planning/phases/04-startup-control/04-reverify-20261115-pyrec/result.json');if(r.code!==0||r.changed.length||r.missing.length)process.exit(1)"</automated>
    <automated>node ~/.codex/gsd-core/bin/gsd-tools.cjs query verification.status .planning/phases/04-startup-control --raw</automated>
    <automated>node ~/.codex/gsd-core/bin/gsd-tools.cjs query verification.status .planning/phases/05-config-notification --raw</automated>
    <automated>git diff --exit-code --name-only aceed78 -- '*.py' pyproject.toml # [HEAD=absent EXPECT==absent @aceed78 GUARD MUTATION: pagefolio/ か tests/ の .py を1byte変えると名前が出て exit 1 になる]</automated>
  </verify>
  <done>単一全件 pytest が1回で失敗0・ERROR0・クラッシュ無しで完走し、入力前後hashが一致、ruff check / format --check / AST が成功。04-QUALITY-PYREC-20261115.json と REVALIDATION 文書2本があり、開発履歴の追記差分は post-history-inputs.json に記録されている。両 phase の verification.status が passed。失敗した場合は失敗記録と停止報告があり、VERIFICATION.md は変わっていない。コミット済み。</done>
</task>

</tasks>

<out_of_scope>
## 本計画で扱わないもの（判断待ち）

- **W05c script/module の2行（06-05-record-w05c-python.cjs）**: tests/test_w05c_evidence.py と tests/test_w05c_runner.py が、この recorder を 06-05-w05c-evidence.cjs と2ファイルだけ複製し、formal_provenance のない manifest で dry-run 成功を期待している。共通 module の require も formal_provenance の必須化も、変更禁止の tests/*.py を変えない限りこれらの試験を壊す。また marker が LF 前提なので、現行 06-UAT.md では W05c の2行も card missing で停止する（この修正は試験と両立するが、判断と合わせて行う方がよいので保留）。選択肢は2つ: (a) tests/test_w05c_*.py の fixture に formal_provenance と共通 module の複製を加える限定承認を得て、別 quick で W05c recorder に同じゲートと CRLF 対応を入れる（推奨。Phase04/05 の再検証がもう一度必要）。(b) W05c は現行の v3 6入力・凍結65入力の照合のまま記録し、formal_provenance の照合は別の手順で証拠化する（記録時に機械的に強制されないので、監査の「証拠不足」が残る）。
- 実機採取（W01/normal@script 以降）: 利用者の同席が必要。本 quick 完了後にオーケストレータが案内する。各 recorder の正例は実データでしか確かめられないので、W02〜W05b は最初の実 session でまず --dry-run を通してから本記録すること。
- 区分B〜D、06-06、W12a/W12b recorder。
</out_of_scope>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| session JSON / run dir → recorder | driver・harness が書いた採取物。旧採取・改変・取り違えの可能性がある |
| recorder → 06-MANUAL-EVIDENCE.json / 06-UAT.md | 正式受入台帳。誤った pass は出荷判断を誤らせる |
| restored_final_dir → recorder | %LOCALAPPDATA% の復元配布。差し替えや部分破損の可能性がある |
| 検証スクリプト → 実 repo | 検証中に実台帳を書き換えるおそれ |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-gna-01 | Repudiation | 5 Python recorder | high | mitigate | checkFormalProvenance を session parse 直後に必須化し、formal_provenance の無い旧採取を書込前に拒否。legacy-reject で18件の拒否を実測 |
| T-gna-02 | Tampering | source_inputs / plugins / Phase04 | high | mitigate | 現行tree の集合と hash の完全一致、run/manifest.json との一致、provenance-before-stop matched、04-VERIFICATION.md の sha256・digest・所有CLI fresh を照合。e2e-w01 の改変試験で拒否を確認 |
| T-gna-03 | Spoofing | restored_final_dir の release-report.json | high | mitigate | treeHash === tree_sha256、PageFolio.exe の hash、rebuild run_id と embedded_report_run_id の一致を要求。report 改変の試験で拒否を確認 |
| T-gna-04 | Tampering | 台帳の行選択 | high | mitigate | case・card の一意性、not-run・generation 5・python-real・entry、SUPERSESSION リンクと python_input_generation の一致を assert。重複・改変の試験で拒否を確認 |
| T-gna-05 | Tampering | 検証による実台帳の書換 | high | mitigate | 正例は temp repo に複製した recorder で実行（root は __dirname 基準）。実 repo では --dry-run だけ。前後で台帳・UAT・evidence 一覧の hash を比較 |
| T-gna-06 | Repudiation | 06-05-drivers/uat_row.py が formal_provenance に含まれない | medium | accept | harness 仕様で .py を変更できない。driver の不変は Task 2 の static（aceed78 との hash 一致）と Task 3 の入力集合で確認。残存リスクとして REVALIDATION に記載 |
| T-gna-07 | Tampering | w12c の elevated が is_admin 欠落時に未出力 | low | accept | 変更禁止の試験 fixture と両立させるため拒否条件は入れない。pass 行の elevated 欠落は release_uat_support の構造監査（tests/test_release_contract.py）が検出 |
| T-gna-SC | Tampering | npm/pip/cargo installs | high | accept | 本計画はパッケージ導入なし（Node 標準モジュールと既存 .venv のみ）。導入が必要になったら停止して報告 |
</threat_model>

<verification>
- Task 1〜3 の automated がすべて成功する。
- `git diff --name-only aceed78` に出るのが files_modified の範囲だけで、06-MANUAL-EVIDENCE.json・06-UAT.md・06-05-evidence・PYTHON-INPUT-SUPERSESSION-20261106.json・.py・pyproject.toml・w12a/w12b/w05c recorder が含まれない。
- 両 phase の verification.status が passed。
</verification>

<success_criteria>
- 区分A の18行は、現行 harness で採取した session なら restored_final_dir を使って最後まで記録でき、旧採取・入力変化・Phase04 非fresh・行の取り違えでは書込前に拒否される。
- 台帳の既存値（python_input_generation・supersedes）は保たれ、観測時の入力世代は observation_basis に別欄で残る。
- W12c の新規記録が elevated を出す。
- Phase04/05 が fresh passed に戻り、再検証の一次データと文書がそろっている。
- W05c 2行の扱いが判断待ちとして明示されている。
</success_criteria>

<output>
Create `.planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-SUMMARY.md` when done
</output>
