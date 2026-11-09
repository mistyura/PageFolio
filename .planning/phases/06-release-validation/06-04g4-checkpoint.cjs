const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const at=new Date().toISOString();
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const write=(p,s)=>fs.writeFileSync(path.join(root,p),s);
const phase='.planning/phases/06-release-validation/';
const manual=JSON.parse(read(phase+'06-MANUAL-EVIDENCE.json'));
const w11=manual.cases.find(c=>c.id==='W11');
for(const row of w11.subrows){
  row.preparation={status:'not-prepared',note:'既存別ユーザー/別セッションを利用できない（利用者確認2026-10-28）。現行必須条件を免除しない。'};
  row.preparation_user_answer={at,text:'使える別ユーザー・別セッションがない',channel:'ChatGPT',purpose:'environment-preparation-only'};
}
const w01=manual.cases.find(c=>c.id==='W01').subrows.find(s=>s.subrow==='normal@script');
const sessionFile='06-05-evidence/W01_normal_at_script-20261028T073252Z.json';
const session=JSON.parse(read(phase+sessionFile));
w01.preparation={status:'prepared',note:'実行・回収済み。回答/観測はattemptに保持。本受入判定は保留。'};
w01.attempts=[...(w01.attempts||[]),{
  session_file:sessionFile,started_at:session.started_at,finished_at:session.finished_at,
  status:'recorded-not-accepted',channel:'ChatGPT-relayed-by-agent',
  user_answers:['通常','はい・1つ・見える。ほかに気づいた点はない'],
  reason:'準備時は最小化。peer前にPageFolio前景への遷移があり、peer直前の最小化維持を外部記録で確定できない。チャット中継と本人端末入力を区別し、passにしない。',
  peer_result:session.harness_peer.json.result,
  focus_result:session.harness_inspect.json['focus-result.json'],cleanup:session.cleanup
}];
manual.updated_at=at;
write(phase+'06-MANUAL-EVIDENCE.json',JSON.stringify(manual,null,2)+'\n');
let uat=read(phase+'06-UAT.md');
uat=uat.replace('status: cards-written-all-not-run','status: acceptance-pending-environment');
uat=uat.replaceAll('C:\\Users\\shdwf\\AppData\\Local\\Temp\\pf06_final_8433fc4ee5324234931fb80ac0f310d1\\out\\PageFolio-v1.10.1','C:\\Users\\shdwf\\AppData\\Local\\Temp\\pf06_final_07447e7e5cfc42988b80fb84c58293ae\\out\\PageFolio-v1.10.2');
uat=uat.replaceAll('隔離copy。最終v1.10.0','隔離copy。最終v1.10.2');
uat=uat.replace('## 受入対象と進め方','## 現行の観測と未達\n\n世代4の接続準備監査は合格。W01/normal@scriptの回答・生観測1件は記録したが、本受入判定は保留しnot-runを維持する。全110行の人手passは0。W11は利用者回答「使える別ユーザー・別セッションがない」により準備不能。再計画案は06-W11-REPLAN-DRAFT.md（未承認）。詳細は06-04g4-CHECKPOINT.md。\n\n## 受入対象と進め方');
uat=uat.replace('EXEがclose要求(WM_CLOSE)で終了せず所有handleで強制終了された観測(ocr-single/w05b-modal/X04)。','旧世代のEXEがclose要求(WM_CLOSE)で終了せず所有handleで強制終了された観測(ocr-single/w05b-modal/X04)。世代4接続2件は利用者が通常終了、X04は強制回収の観測を保持。');
write(phase+'06-UAT.md',uat);
let prep=read(phase+'06-UAT-PREPARATION.md');
prep=prep.replace('status: preparation-pending-generation4-connection','status: preparation-complete-acceptance-pending');
prep=prep.replace('実EXEのocr-single/W05b接続はこれから実施。','実EXEのocr-single/W05b接続2件は成立。W05bはChatGPTから同確認HWND10686146へ自動復帰し、いいえで処理維持、同1POST完了を利用者回答と50ms観測で照合。両runは利用者が通常終了し残存ownerなし。準備監査exit0（phase_complete=false/release_allowed=false）。');
write(phase+'06-UAT-PREPARATION.md',prep);
let state=read('.planning/STATE.md');
state=state.replace('current_plan: 4','current_plan: 5').replace(/^stopped_at:.*$/m,'stopped_at: 世代4接続準備監査合格、本受入未完了、W11別セッション準備不能の判断待ち');
state=state.replace(/^last_updated:.*$/m,'last_updated: '+JSON.stringify(at)).replace(/^last_activity_desc:.*$/m,'last_activity_desc: CR-03 fixed、2083件成功、W05b実EXE自動復帰確認・準備監査合格、W11環境不足');
state=state.replace(/^state_head:.*$/m,'state_head: '+execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim());
state=state.replace('**Phase 05 再検証（2026-10-28）:**','**過去のPhase 05 再検証（CR-03修正前）:**');
state=state.replace(/\*\*2026-10-28 出荷停止解消作業の現行再開点:\*\*[^\n]*/, '**2026-10-28 現行再開点:** CR-03修正/v1.10.2/全件2083 passed、Phase04/05 fresh passed。世代4の実build2回・保護・接続2件と準備監査合格。W05bは同確認画面へ自動復帰し、いいえ後も同requestを完了。旧世代の原因は未確定のまま原本保持。人手pass0/110。W01/normal@scriptの観測1件は判定保留。W11は利用者回答「使える別ユーザー・別セッションがない」で準備不能。06-W11-REPLAN-DRAFT.mdは未承認。Phase06と出荷は未完了、commit/pushなし。正本: phases/06-release-validation/06-04g4-CHECKPOINT.md。以下の旧停止記録は履歴。');
state=state.replace('Current Plan: 4','Current Plan: 5').replace('Plan: 4 of 6（現行世代の06-04-02を再実施）','Plan: 5 of 6（06-04世代4の準備完了、本受入を継続）');
state=state.replace(/^Status: 06-04-02.*$/m,'Status: 本受入未完了。W11の検証環境または保証範囲の再計画について利用者判断待ち');
state=state.replace(/^Last activity: 2026-10-28 — 世代3.*$/m,'Last activity: 2026-10-28 — 世代4接続/準備監査合格、W01観測保存、W11準備不能を確認');
state=state.replaceAll('**現行再開点（2026-10-28 W05b接続実証停止）:**','**過去の再開点（世代3 W05b接続実証停止）:**').replaceAll('**現行再開点（2026-10-28品質停止解除後）:**','**過去の再開点（CR-03修正前の品質停止解除後）:**');
write('.planning/STATE.md',state);
const machine=JSON.parse(read('.planning/state.json'));
machine.next={command:'$gsd-execute-phase 06',label:'本受入継続とW11準備不能の判断',reason:'CR-03修正・2083件成功・Phase04/05 fresh passed・世代4準備監査合格。W11は別セッションなし。再計画案は未承認、110行の本受入未完了。'};
machine.updated_at=at;write('.planning/state.json',JSON.stringify(machine,null,2)+'\n');
let project=read('.planning/PROJECT.md');
project=project.replace('## Current Milestone: v1.10.0 多重起動防止・起動操作の改善','## Current Milestone: v1.10.0 多重起動防止・起動操作の改善\n\n**2026-10-28 現行:** アプリv1.10.2でCR-03修正、2083件成功・Phase04/05 fresh passed。世代4の実build2回、保護/接続準備監査合格。W05b実EXE自動復帰を確認。本受入pass0/110、W11は利用者回答により別セッションを準備できない。06-W11-REPLAN-DRAFT.mdは未承認。Phase06/出荷は未完了。詳細はphases/06-release-validation/06-04g4-CHECKPOINT.md。以下の同日記録は履歴。');
project=project.replace('アプリ版番号は既存v1.10.1を維持し、再生成EXEとの同期をPhase 6リリースゲートで確認する。','アプリ版番号は現行v1.10.2で、新世代EXEとの同期を確認済み。最終出荷判定は本受入後に行う。');
write('.planning/PROJECT.md',project);
let debug=read('.planning/debug/phase06-w05b-manual-switch.md');
debug=debug.replace(/^next_action:.*$/m,'next_action: 世代4実EXEで自動復帰・いいえ・同1POST完了を実測し準備監査exit0。接続準備の停止を解除し06-05へ。旧世代原因は未確定のため診断は履歴として保持。06-04g4-CHECKPOINT.md参照。');
write('.planning/debug/phase06-w05b-manual-switch.md',debug);
console.log(JSON.stringify({updated_at:at,manual_pass:manual.cases.flatMap(c=>c.subrows).filter(r=>r.status==='pass').length,total_rows:manual.cases.flatMap(c=>c.subrows).length,release_allowed:false}));
