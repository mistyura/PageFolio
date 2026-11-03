// W05b: 人の直接回答と、確認ダイアログへの『無操作の自動復帰』『いいえ』『同じ要求の完了』の機械観測を照合して台帳へ記録する。
// 使い方: node 06-05-record-w05b.cjs <06-05-evidence配下のsessionファイル名> [--dry-run]
//   --dry-run は全ての照合だけを行い、台帳・UAT・原本copyを一切書き換えない。
// 重要: 準備成功・機械成功・手動切替を人手passへ転用しない。pass条件は下記assertの全成立のみ(条件の緩和禁止)。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2],dry=process.argv.includes('--dry-run');
const assert=(ok,why)=>{if(!ok)throw Error(why);};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const norm=p=>path.resolve(p).toLowerCase();
const RESULT='PageFolio UAT 合成OCR結果';
assert(/^W05b_ocr-close-confirm_at_(script|module|production-exe)-\d{8}T\d{6}Z(-\d+)?\.json$/.test(name||''),'unexpected filename');
// --session-dir は --dry-run のときだけ有効(機構確認用)。実記録は常に 06-05-evidence 配下のsessionだけを対象にする。
const sdi=process.argv.indexOf('--session-dir'),sessionDir=dry&&sdi>0?path.resolve(process.argv[sdi+1]):path.join(phase,'06-05-evidence');
assert(dry||sdi<0,'--session-dir requires --dry-run');
const relative='06-05-evidence/'+name,raw=fs.readFileSync(path.join(sessionDir,name)),s=JSON.parse(raw);
assert(s.case==='W05b'&&s.condition==='ocr-close-confirm'&&s.row===`W05b/ocr-close-confirm@${s.entry}`,'row mismatch');
assert(!s.selftest&&!s.diagnostics&&s.acceptance!==false&&!s.error&&s.outcome==='answered','not a human acceptance run');
const exe=s.entry==='production-exe',run=path.resolve(s.run),w=s.w05b;
assert(w&&w.design&&w.design.auto_no===false,'automatic No is not allowed in acceptance');
assert(w.budget.hold_limit_s===90&&w.budget.release_latest_s<w.budget.hold_limit_s&&w.budget.no_latest_s<w.budget.release_latest_s,'wait budget was extended');
// ---- 無操作の自動復帰(同一native HWND/PIDが実前景) ----
const ret=w.return_assessment,modal=w.modal_before;
assert(ret&&ret.verdict==='clean'&&ret.reasons.length===0,'automatic return not established: '+(ret&&ret.reasons));
// ---- 経由窓・切替キーの独立照合(defense in depth) ----
// driverの判定(return_assessment)とは別に、生の前景遷移と切替キー記録から『人のAlt+Tab』を拒否する。
// 手動切替を自動復帰passにしない: 観測区間(peer, w05b-quiet)の前景遷移がタスク切替UI/ForegroundStagingを経由、
// 同区間のAlt/Tab/Winキー押下、切替キー捕捉が有効でなかった記録(Alt+Tab捕捉の導入前のsessionを含む)は全てpassにしない。
const SWITCH_UI=['XamlExplorerHostIslandWindow','ForegroundStaging'],OBSERVE=['peer','w05b-quiet'];
let monitorsChecked=0;
for(const [label,mon] of [['input_monitor',s.input_monitor],['input_monitor_final',s.input_monitor_final]]){
 if(mon===undefined||mon===null)continue;
 monitorsChecked++;
 assert(mon.enabled===true&&mon.switch_key_capture===true&&mon.switch_key_samples>0,`${label}: Alt/Tab/Win key capture was not active`);
 const via=(mon.foreground_transitions||[]).filter(t=>OBSERVE.includes(t.phase)&&(SWITCH_UI.includes((t.to||{}).class)||SWITCH_UI.includes((t.from||{}).class)));
 assert(via.length===0,`${label}: foreground went through the task switcher / ForegroundStaging during the unattended observation (manual Alt+Tab): ${via.length} transition(s)`);
 assert(!(mon.switch_key_events||[]).some(e=>OBSERVE.includes(e.phase)),`${label}: Alt/Tab/Win key pressed during the unattended observation`);
 // 捕捉の自己検証: セッション中にタスク切替UIが出た(指示されたAlt+Tab)のにAlt/Tab/Winの押下が1つも無いなら、捕捉は盲目。
 const switcherSeen=(mon.foreground_transitions||[]).some(t=>SWITCH_UI.includes((t.to||{}).class)||SWITCH_UI.includes((t.from||{}).class));
 assert(!switcherSeen||(mon.switch_key_events||[]).length>0,`${label}: task switcher UI appeared but no Alt/Tab/Win key was recorded (key capture is blind)`);
}
assert(monitorsChecked>0,'input monitor record missing');
assert(ret.switch_key_capture===true&&ret.returned_via_task_switcher===false&&!SWITCH_UI.includes((((ret.returned_transition||{}).from)||{}).class),'return came through the task switcher or key capture was not recorded in the assessment');
assert(modal.class==='#32770'&&modal.visible&&modal.hwnd===ret.modal.hwnd&&modal.pid===ret.modal.pid,'confirmation window identity mismatch');
const primaryPid=exe?s.primary.pid:(s.owned_pids||[]).map(x=>x.pid);
assert(exe?modal.pid===primaryPid:primaryPid.includes(modal.pid),'confirmation window is not owned by PageFolio');
assert(ret.returned_transition&&ret.returned_transition.to.hwnd===modal.hwnd&&ret.returned_transition.to.pid===modal.pid,'no foreground transition to the same confirmation window');
for(const key of ['foreground_peer_done','foreground_quiet_end'])assert(w[key].hwnd===modal.hwnd&&w[key].pid===modal.pid&&equal(w[key],ret[key]),'actual foreground is not the same confirmation window: '+key);
assert(w.foreground_before_peer?w.foreground_before_peer.hwnd!==modal.hwnd:ret.foreground_before_peer.hwnd!==modal.hwnd,'confirmation window was already foreground before peer');
assert(!ret.mouse_presses_during_observation.length&&!ret.key_presses_during_observation.length,'input during unattended observation');
assert(ret.unattended_seconds_after_return>=2&&ret.monitor.samples>0&&!ret.monitor.errors.length&&!ret.monitor.truncated&&ret.monitor.max_gap_s<=0.5,'unattended observation too short or monitor incomplete');
// ---- 人の直接回答(自己申告)。観測と食い違えばpassにしない ----
const a=s.answers,expectA={result_shown:'見えた',auto_return:'自動で出た',manual_switch:'していない',answered_no:'いいえを押した',process_kept:'続いていた',summary_not_run:'していない'};
if(exe)expectA.real_double_click='ダブルクリックした';
for(const [k,v] of Object.entries(expectA))assert(a[k]===v,`human answer is not pass: ${k}=${a[k]}`);
assert(s.raw_inputs.length>0&&s.raw_inputs.every(x=>!x.rejected&&!x.selftest),'synthetic/rejected input');
for(const key of Object.keys(expectA))assert(s.raw_inputs.some(x=>x.key===key&&x.text.trim()===a[key]),'direct answer missing: '+key);
// ---- 『いいえ』は利用者の実操作(音の後)。自動送信ではない ----
assert(w.beep_at&&w.beep_at<=(w.no_observed_at||w.modal_gone_at),'No was recorded before the beep');
const monitorFinal=exe?s.input_monitor_final:s.input_monitor;
assert(monitorFinal&&monitorFinal.enabled&&!monitorFinal.errors.length&&!monitorFinal.truncated,'input monitor missing');
const answerMouse=monitorFinal.mouse_events.filter(e=>e.phase==='w05b-answer'&&e.kind==='down'&&e.on_pagefolio&&e.under.hwnd===modal.hwnd);
const answerKeys=monitorFinal.key_events.filter(e=>e.phase==='w05b-answer');
assert(answerMouse.length>0||answerKeys.length>0,'no physical user input on the confirmation window after the beep');
// ---- 同一要求・同一OCR windowの保持と、解放後の同一attemptの完了 ----
const start=exe?s.ocr_after_peer:s.ocr_before.server,resumed=exe?s.ocr_after_peer:s.ocr_after_peer.server,afterNo=exe?s.ocr_after_no:s.ocr_close_no.server,done=exe?s.ocr_completed:s.ocr_completed.server;
function received(summary){return summary.events.filter(e=>e.event==='received');}
for(const state of [start,resumed,afterNo,done]){
 assert(state.posts===1&&received(state).length===1&&!state.rejected.length&&!state.retransmissions.length&&!state.expired.length,'not one clean request');
 assert(Object.values(state.attempts_by_image).length===1&&Object.values(state.attempts_by_image)[0]===1,'attempt count mismatch');
}
assert(!resumed.completed.length&&!resumed.released.length&&!afterNo.completed.length&&!afterNo.released.length,'OCR finished before the No answer');
assert(equal(received(start),received(resumed))&&equal(received(start),received(afterNo))&&equal(received(start),received(done)),'page/request/attempt changed');
const request=received(start)[0],manifest=JSON.parse(fs.readFileSync(path.join(run,'manifest.json')));
const runId=exe?manifest.run_id:path.basename(run);
if(exe)assert(path.basename(run)==='release-uat-'+runId,'EXE run directory/id mismatch');
assert(request.page_id==='p1'&&request.mode==='hold'&&request.run_id===runId,'wrong page or run');
assert(equal(done.completed,[request.attempt_id])&&equal(done.released,[request.attempt_id]),'original attempt did not complete');
const completedEvent=done.events.find(e=>e.event==='completed'),releasedEvent=done.events.find(e=>e.event==='released');
assert(completedEvent&&releasedEvent&&completedEvent.status===200,'OCR completion missing');
for(const event of [releasedEvent,completedEvent])for(const key of ['request_id','attempt_id','image_sha256','page_id'])assert(event[key]===request[key],'completion identity mismatch');
const noAt=w.no_observed_at||w.modal_gone_at;
assert(request.time<w.beep_at&&w.beep_at<noAt&&noAt<releasedEvent.time&&releasedEvent.time<=completedEvent.time,'event ordering mismatch');
assert(w.no_elapsed_s<=w.budget.no_latest_s&&w.release_elapsed_s<=w.budget.release_latest_s,'No/release exceeded the fixed budget');
for(const key of Object.keys(expectA))assert(s.raw_inputs.filter(x=>x.key===key).every(x=>x.at>completedEvent.time),'answer typed before the result existed: '+key);
const ocrBefore=w.ocr_window_before,ocrAfterNo=w.after_no_windows.ocr_window,ocrRelease=w.ocr_window_before_release;
assert(ocrBefore&&ocrAfterNo&&ocrRelease&&ocrBefore.hwnd===ocrAfterNo.hwnd&&ocrBefore.hwnd===ocrRelease.hwnd&&ocrBefore.pid===ocrAfterNo.pid,'OCR window changed or closed');
const pending=[];
function collect(label,dir,names){for(const file of names){const source=path.join(dir,file);assert(fs.existsSync(source),'raw missing: '+file);pending.push({source,name:label+'-'+file.replaceAll('/','-'),bytes:fs.readFileSync(source)});}}
let pdf,environment,sourceCommit,focusResult=null,real=null;
if(exe){
 const peer=w.peer;
 // 二次起動は利用者のExplorer実ダブルクリック。driverは合成起動していない(親=explorer.exe、imageは隔離copy)。
 assert(peer.launched_by==='explorer-user-double-click'&&peer.driver_launched===false&&peer.parent_valid&&path.basename(peer.parent_image).toLowerCase()==='explorer.exe','secondary was not a real Explorer launch');
 assert(norm(peer.image)===norm(path.join(manifest.copy,'PageFolio.exe'))&&peer.pid!==s.primary.pid&&peer.pid===s.peer.pid&&peer.created===s.peer.created,'secondary identity mismatch');
 const mp=manifest.processes.find(x=>x.role==='peer');
 assert(mp&&mp.pid===peer.pid&&mp.created===peer.created&&mp.launched_by==='explorer-user-double-click'&&mp.parent_pid===peer.parent_pid,'manifest peer record mismatch');
 assert(s.peer_exit.returncode===0&&s.peer_exit.state==='exited','secondary did not exit normally');
 const modalStep=s.steps.find(x=>x.step==='modal-up'),receivedStep=s.steps.find(x=>x.step==='received'),post=s.steps.find(x=>x.step==='after-peer');
 assert(modalStep&&receivedStep&&post&&request.time<modalStep.at&&modalStep.at<peer.created_iso&&peer.created_iso<w.beep_at,'external observation order mismatch');
 assert(post.foreground.hwnd===modal.hwnd&&post.foreground.pid===modal.pid&&post.foreground.owned_by==='primary','post-peer actual foreground is not the same confirmation window');
 assert(post.owner_probe.length>0&&post.owner_probe.every(x=>x.state==='open'),'owner probe mismatch');
 assert(ret.launch_presses_excused.every(x=>new Date(x.t).getTime()<=new Date(peer.created_iso).getTime()+250),'unexcused press attributed to launch');
 assert(s.source_distribution_unchanged===true&&!s.owner_after.length,'source/owner protection failed');
 assert(s.stop.length===2&&s.stop.every(x=>['closed','already-exited'].includes(x.result))&&s.stop.find(x=>x.pid===s.peer.pid)?.result==='already-exited','cleanup not normal');
 assert(s.user_close?.closed&&s.user_close.pid===s.primary.pid,'user close not established');
 const v=s.verify_after;
 assert(v.ok&&!v.distribution_changed.length&&!v.undeclared.length&&!v.extra_dirs.length&&!v.missing_dirs.length&&v.overlay_changed.every(x=>x==='pagefolio_settings.json'),'distribution changed');
 assert(manifest.status==='stopped'&&manifest.run_id===s.run_id,'unexpected manifest');
 assert(Object.keys(manifest.overlay).length===1&&Object.hasOwn(manifest.overlay,'pagefolio_settings.json')&&manifest.overlay['pagefolio_settings.json']!==null,'OCR settings not declared');
 assert(manifest.overlay_log.some(x=>x.name==='pagefolio_settings.json'&&x.at<manifest.processes.find(p=>p.role==='primary').started_at),'overlay not declared before start');
 assert(equal(s.ocr_final,done),'extra OCR request after completion');
 assert(s.ocr_preparation.ocr_concurrency===1&&s.ocr_preparation.target_pages===1&&s.ocr_preparation.summary_executed===false&&/^http:\/\/127\.0\.0\.1:\d+$/.test(s.ocr_preparation.server_url),'unsafe OCR preparation');
 pdf=s.fixture_pdf;assert(path.resolve(pdf.path)===path.join(run,'fixtures','ocr-one-page.pdf'),'unexpected PDF path');
 assert(manifest.fixtures['ocr-one-page'].sha256===pdf.sha256,'PDF manifest mismatch');
 collect('run',run,['manifest.json','evidence/inspect-001.json','evidence/inspect-002.json','evidence/w05b-server.jsonl','fixtures/ocr-one-page.pdf','dist/pagefolio_settings.json']);
 assert(equal(fs.readFileSync(path.join(run,'evidence/w05b-server.jsonl'),'utf8').trim().split(/\r?\n/).map(JSON.parse),done.events),'raw server log mismatch');
 environment=s.environment;
 real={launched_by:peer.launched_by,parent_image:peer.parent_image,secondary_pid:peer.pid,secondary_created:peer.created_iso,exit:s.peer_exit,foreground_after_launch:post.foreground,foreground_before_launch:ret.foreground_before_peer};
}else{
 assert(s.harness_peer.returncode===0&&s.harness_inspect.returncode===0&&s.harness_stop_early.returncode===0,'harness error');
 assert(!s.cleanup.alive_after.length&&!s.cleanup.terminated_owned.length&&!s.cleanup.left_after_harness_stop.length,'cleanup not normal');
 const i=s.harness_inspect.json,peer=s.harness_peer.json.result;
 focusResult=i['focus-result.json'];
 assert(peer.result==='completed'&&peer.constructed===0&&peer.status_preserved,'peer did not restore owner');
 assert(focusResult.result==='completed'&&focusResult.state_preserved&&focusResult.target_correct&&focusResult.focus_correct&&focusResult.document_pages===1,'harness restore record mismatch');
 assert(focusResult.native===modal.hwnd&&focusResult.activated===modal.hwnd,'harness-activated native popup differs from the externally observed confirmation window');
 for(const key of ['dialog_id','run_gen','engine_id','worker_ids'])assert([s.ocr_close_start,s.ocr_after_peer,s.ocr_close_no,s.ocr_completed].every(x=>equal(s.ocr_before[key],x[key])),'engine/worker identity changed');
 assert(s.ocr_before.worker_ids.length===1&&!s.ocr_before.done&&!s.ocr_after_peer.done&&!s.ocr_close_no.done&&s.ocr_completed.done,'OCR lifecycle mismatch');
 assert(s.ocr_close_no.dialog_exists&&!s.ocr_close_no.cancelled,'No did not keep the OCR dialog');
 assert(equal(s.ocr_completed.results,{'0':RESULT})&&!Object.keys(s.ocr_completed.errors).length,'completion result mismatch');
 for(const state of [s.ocr_before,s.ocr_close_start,s.ocr_after_peer,s.ocr_close_no,s.ocr_completed])assert(state.concurrency===1&&state.summary_executed===false,'OCR concurrency/summary mismatch');
 assert(i.originals_unchanged,'originals changed');
 for(const [file,expected] of Object.entries(manifest.originals_before)){const p=path.join(root,file);assert((fs.existsSync(p)?hash(fs.readFileSync(p)):null)===expected,'original changed after cleanup: '+file);}
 const fixture=path.join(run,'uat-owner-native-ocr');
 assert(path.resolve(manifest.fixture)===fixture&&!fs.existsSync(path.join(fixture,'manual-deadline')),'unexpected fixture or safety deadline');
 const final=JSON.parse(fs.readFileSync(path.join(fixture,'manual-ocr-final.json')));
 assert(equal(final,done),'extra OCR request after completion');
 for(const [file,value] of [['manual-ocr-running.json',s.ocr_before],['manual-ocr-close-start.json',s.ocr_close_start],['manual-ocr-after-peer.json',s.ocr_after_peer],['manual-ocr-close-no.json',s.ocr_close_no],['manual-ocr-completed.json',s.ocr_completed]])assert(equal(JSON.parse(fs.readFileSync(path.join(fixture,file))),value),'raw OCR state mismatch: '+file);
 assert(equal(fs.readFileSync(path.join(fixture,'manual-ocr-server.jsonl'),'utf8').trim().split(/\r?\n/).map(JSON.parse),done.events),'raw server log mismatch');
 collect('run',run,['manifest.json']);
 collect('primary',fixture,['result.json','focus-result.json','ready','stdout.log','stderr.log','traceback.log','manual-ocr-running.json','manual-ocr-close-start.json','manual-ocr-after-peer.json','manual-ocr-close-no.json','manual-ocr-completed.json','manual-ocr-final.json','manual-ocr-server.jsonl','ocr-one-page.pdf']);
 const primary=JSON.parse(fs.readFileSync(path.join(fixture,'result.json')));
 assert(primary.result==='primary'&&primary.constructed===1&&primary.restored===1&&primary.status_preserved,'primary abnormal exit');
 assert(w.enter_elapsed_s<=w.budget.start_latest_s,'peer started after the fixed budget');
 pdf={...s.ocr_before.pdf,path:path.join(fixture,'ocr-one-page.pdf')};
 environment={...manifest.environment,elevated:manifest.environment.is_admin};sourceCommit=manifest.source_commit;
}
assert(pdf.pages===1&&!pdf.has_embedded_text&&pdf.images_on_first_page===1&&hash(fs.readFileSync(pdf.path))===pdf.sha256,'image PDF missing/changed');
const build=JSON.parse(fs.readFileSync(path.join(phase,'06-BUILD-EVIDENCE.json'))),report=JSON.parse(fs.readFileSync(path.join(build.final_release.final_dir,'release-report.json')));
assert(build.generation===5&&s.target_exe_sha256===build.final_release.exe_sha256,'wrong generation');
if(exe)assert(s.binary_sha256===build.final_release.exe_sha256&&s.verify_after.exe_sha256===s.binary_sha256&&s.tree_sha256===build.final_release.tree_sha256,'binary/tree mismatch');
for(const [file,expected] of Object.entries(report.input_manifest))assert(hash(fs.readFileSync(path.join(root,file)))===expected,'frozen input drift: '+file);
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerPath)),row=ledger.cases.find(c=>c.id==='W05b').subrows.find(r=>r.card===s.row);
assert(row&&row.status==='not-run'&&row.generation===5&&row.release_requirement==='required','row already judged/wrong generation');
const uatPath=path.join(phase,'06-UAT.md'),uat=fs.readFileSync(uatPath,'utf8'),marker='### '+s.row+'\n',first=uat.indexOf(marker);assert(first>=0,'card missing');
const next=uat.indexOf('\n### ',first+marker.length),last=next<0?uat.length:next,card=uat.slice(first,last);assert(card.includes('- **状態**: not-run'),'card already judged');
const dest=path.join(phase,relative.replace('.json','-raw'));assert(dry||!fs.existsSync(dest),'raw already preserved');
if(dry){console.log(JSON.stringify({row:s.row,dry_run:true,would_pass:true,note:'ledger/UAT/raw were not modified'}));process.exit(0);}
fs.mkdirSync(dest);const copies=pending.map(p=>{const target=path.join(dest,p.name);fs.writeFileSync(target,p.bytes,{flag:'wx'});return {source:p.source,target:path.relative(phase,target).replaceAll('\\','/'),sha256:hash(p.bytes)};});
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
row.status='pass';row.preparation={status:'prepared',run_id:runId,note:'1ページ画像PDF・並列1・loopback合成OCR。要求待機中の閉じる確認へ、無操作の自動復帰→利用者の「いいえ」→同じ要求の完了。自動Noなし。'};
row.observations={modal_shown:true,peer_returned_to_modal:true,answered_no:true,input_and_process_kept:true,same_request_completed:true,foreground_result:{before_peer:ret.foreground_before_peer,peer_done:w.foreground_peer_done,quiet_end:w.foreground_quiet_end,unattended_seconds_after_return:ret.unattended_seconds_after_return},...(exe?{real_double_click_foreground:real,foreground_after:w.foreground_quiet_end}:{})};
row.observation_basis={session_file:relative,session_sha256:hash(raw),confirmation_window:modal,return_assessment:ret,ocr_window:{before:ocrBefore,after_no:ocrAfterNo,before_release:ocrRelease},request,server_completed:done,focus_result:focusResult,real_double_click:real,fixture_pdf:pdf,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),frozen_input_files:Object.keys(report.input_manifest).length,note:exe?'実EXEの内部には注入せず、Explorerの実ダブルクリックによる二次process(親=explorer.exe)の外部観測、同一HWND/PIDの実前景、利用者の実操作、serverの同一要求完了で照合。':'同一native HWND/PIDの実前景と無操作の連続監視、利用者の実操作(自動Noなし)、同一dialog/engine/worker/run generationの保持と同一request完了で照合。'};
row.answer=s.composed_answer;row.raw_inputs=s.raw_inputs;row.answer_provenance='利用者が可視PowerShellへ直接入力。担当の代理入力なし。';row.run_id=runId;row.observed_at=s.finished_at;row.environment=environment;row.source_commit=sourceCommit;row.input_manifest_sha256=build.final_release.input_manifest_sha256;if(exe)row.binary_sha256=s.binary_sha256;
const passed=ledger.cases.flatMap(c=>c.subrows).filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
const updated=card.replace(/- \*\*状態\*\*: not-run[^\n]*/,`- **状態**: pass / 利用者直接回答・無操作の自動復帰・同じ要求の完了が一致。根拠: ${relative}\n- **回答原文**: ${row.answer}`);
let result=uat.slice(0,first)+updated+uat.slice(last);
result=result.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/,`本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');fs.writeFileSync(uatPath,result);
console.log(JSON.stringify({row:s.row,status:'pass',required_pass:passed,required_not_run:108-passed,deferred:2,copied:copies.length}));
