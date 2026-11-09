// 1回の正式候補の未完了を記録する。受入台帳・製品・品質入力は変更しない。
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '../../../..'), phase = path.join(root, '.planning/phases/06-release-validation');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const name = 'W05c_quit-no_at_script-20261105T072535Z';
const raw = path.join(phase,'06-05-evidence',name+'-incomplete-raw');
const run = path.join(root,'.planning/tmp/pagefolio-uat-73sihnga');
const owner = path.join(raw,'run/uat-owner-native-quit');
const events = fs.readFileSync(path.join(owner,'w05c-events.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const final = read(path.join(owner,'w05c-observer-final.json'));
const manifest = read(path.join(raw,'run/manifest.json'));
const copies = read(path.join(raw,'copies.json'));
if (copies.some(c=>hash(fs.readFileSync(path.join(raw,c.path)))!==c.sha256)) throw Error('archive changed');
const answerPath = path.join(phase,'06-05-evidence',name+'.json'), answerBytes=fs.readFileSync(answerPath);
fs.writeFileSync(path.join(raw,'answer-original.json'),answerBytes,{flag:'wx'});
fs.writeFileSync(path.join(raw,'answer-copy.json'),JSON.stringify({source:answerPath,sha256:hash(answerBytes)},null,2)+'\n',{flag:'wx'});
const event = name => events.find(e=>e.event===name);
const no=event('native_no'), returned=event('ask_return'), marker=event('marker_created'), watchdog=event('watchdog_enter');
if (!(no && returned?.result===false && marker && watchdog && no.seq<returned.seq && returned.seq<marker.seq && marker.seq<watchdog.seq)) throw Error('timeline differs');
const incomplete = {case:'W05c',condition:'quit-no',entry:'script',row:'W05c/quit-no@script',status:'not-run',
  run:path.relative(root,run).replaceAll('\\','/'), owner:manifest.expected_owner,
  formal_candidate_attempt:1,additional_attempts:0,ready_for_retry:false,
  reason:'No→False→元マーカーは成立したが、回答後peer/回収前snapshotより前に120秒watchdogが開始した。受入全体は未完了。',
  timeline:{shown:event('native_shown').utc,peer_during:event('peer_during_confirm').utc,native_no:no.utc,ask_return:returned.utc,marker:marker.utc,watchdog:watchdog.utc,closed:event('observer_closed').utc},
  answer_original:read(answerPath).answer_original,answer_captured_at:read(answerPath).answer_captured_at,
  answer_source:'同じNo操作の結果についての利用者直接回答。原文・記録時刻を保持し、遡及して時刻を付け替えない。',
  stage:'before_peer_owner_validation_rejected',peer_after_answer:false,pre_collection_snapshot:false,
  observer:{events:final.events,written:final.written,pending:final.pending,errors:final.errors,sha256:final.sha256},
  recovery:{owner_running:false,basis:'native CIMでexpected PID2844なし。result/observer_closedあり。後続OpenProcess WinError87。',
    errors:['before_peer: OpenProcess [WinError 87] パラメーターが間違っています。','collect: OpenProcess [WinError 87] パラメーターが間違っています。'],
    inspection_originals_unchanged:read(path.join(raw,'run/inspection.json')).originals_unchanged},
  archive:path.relative(phase,raw).replaceAll('\\','/'),original_archive_files:copies.length,
  old_run_cause:'unresolved; 今回は元マーカー欠落が再現していない。今回の未完了と元runの主因を混同しない。',
  phase_complete:false,release_allowed:false};
fs.writeFileSync(path.join(phase,'06-05-evidence',name+'-incomplete.json'),JSON.stringify(incomplete,null,2)+'\n',{flag:'wx'});
const next='$gsd-debug continue phase06-w05c-no-marker。保存済み新runの時系列から、120秒以内に回答後peer/回収前採取を完了させる実行手順を見直す。期限延長/追加GUI/追加試行/製品推測修正/commitなし。';
const hpath=path.join(root,'.planning/HANDOFF.json'),h=read(hpath);
h.timestamp=new Date().toISOString();h.status='blocked';h.next_action=next;
Object.assign(h.w05c_retry_policy,{status:'candidate_incomplete_debug_required',implementation_status:'validated',ready_for_retry:false,machine_gates_passed:true,awaiting:null,gui_attempts_this_revision:1,next_action:next});
Object.assign(h.current_session_validation,{w05c_script:'1 candidate incomplete: No/False/marker succeeded, watchdog before after-answer peer/snapshot; not-run',owner_running:false,incomplete_evidence:'.planning/phases/06-release-validation/06-05-evidence/'+name+'-incomplete.json'});
Object.assign(h.current_stop,{report:'.planning/phases/06-release-validation/06-W05C-CANDIDATE-STOP-20261105.md',run:incomplete.run,next_command:'$gsd-debug continue phase06-w05c-no-marker',next_action:next,ready_for_retry:false,owner_running:false,formal_candidate_attempts:1});
h.context_notes='計測39件/全件2293件成功・167入力不変、Phase04/05 fresh passed。新候補1回でNo/False/元マーカー成立。回答後処理前にwatchdog終了してnot-run、原本30ファイル＋回答copyを保全。追加試行0、元主因未解決。';
if(h.blockers?.[0])Object.assign(h.blockers[0],{description:incomplete.reason,type:'technical',workaround:next});
if(h.completed_tasks?.[1])h.completed_tasks[1].progress=h.context_notes;
if(h.remaining_tasks?.[0])h.remaining_tasks[0].name='W05c候補1回は期限内未完了。debugで進行手順を見直す。';
fs.writeFileSync(hpath,JSON.stringify(h,null,2)+'\n');
const statePath=path.join(root,'.planning/STATE.md');let state=fs.readFileSync(statePath,'utf8');
for(const [k,v]of Object.entries({status:'blocked',stopped_at:'W05c/script候補1回はNo/False/元マーカー成立後、120秒watchdogで未完了。debugへ戻す。',last_updated:h.timestamp,last_activity:'W05c新候補1回not-run、原本保全・追加試行0',last_activity_desc:'No成立を確認、回答後peer前に期限終了。2293件成功と親鮮度を保持しdebugへ。'}))state=state.replace(new RegExp('^'+k+':.*$','m'),k+': '+v);
state=state.replace('## 2026-11-05 現行再開点（計測実装後）','## 2026-11-05 現行停止点（候補1回未完了）\n\n'+h.context_notes+'\n\n'+next+' 正式台帳28pass/80not-run・対象外2、06-06未開始、出荷不可。正本は `phases/06-release-validation/06-W05C-CANDIDATE-STOP-20261105.md`。以下の開始待ちは過去の履歴。\n\n## 2026-11-05 再試行前の再開点（履歴）');
state=state.replace(/^Status: Waiting for human action.*$/m,'Status: Blocked — W05c/script candidate incomplete; debug required');
fs.writeFileSync(statePath,state);
console.log(JSON.stringify({status:'not-run',no: no.utc,marker:marker.utc,watchdog:watchdog.utc,archive_files:copies.length,additional_attempts:0}));
