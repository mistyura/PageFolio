// W02 の Python 入口を直接回答・実前景・保持・正常回収から判定する（settings開始時のファイル名を維持）。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2];
const assert=(ok,why)=>{if(!ok)throw Error(why);};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
assert(/^(W02_(settings|thumb|preview)|W05a_nested-settings)_at_(script|module)-\d{8}T\d{6}Z\.json$/.test(name||''),'unexpected session filename');
const relative='06-05-evidence/'+name,raw=fs.readFileSync(path.join(phase,relative)),s=JSON.parse(raw);
const nested=s.case==='W05a'&&s.condition==='nested-settings';
assert((nested||(s.case==='W02'&&['settings','thumb','preview'].includes(s.condition)))&&s.row===`${s.case}/${s.condition}@${s.entry}`,'row mismatch');
const settings=nested||s.condition==='settings';
assert(!s.selftest&&!s.diagnostics&&!s.error&&s.outcome==='answered','not a human acceptance run');
assert(s.procedure_verdict==='clean'&&!s.procedure_assessment.rerun_required,'procedure not clean');
assert(s.harness_peer.returncode===0&&s.harness_inspect.returncode===0&&s.harness_stop.returncode===0,'harness error');
assert(s.cleanup.alive_after.length===0&&s.cleanup.terminated_owned.length===0&&s.cleanup.left_after_harness_stop.length===0,'cleanup not normal');
const i=s.harness_inspect.json,f=i['focus-result.json'],peer=s.harness_peer.json.result;
assert(peer.result==='completed'&&peer.constructed===0&&peer.status_preserved,'peer did not restore existing owner');
assert(f.result==='completed'&&f.state_preserved&&f.target_correct&&f.focus_correct,'state or focus mismatch');
if(!settings)assert(f.document_pages>0&&f.selected_pages?.length>0&&f.selected_pages.every(p=>p>=0&&p<f.document_pages)&&f.current_page>=0&&f.current_page<f.document_pages,'PDF/selection preparation missing');
assert((settings?f.expected_focus==='.!settingsdialog.!entry':f.expected_focus.includes('canvas'))&&f.settled_focus===f.expected_focus&&f.activated===f.expected_tk,'input target mismatch');
const before=s.steps.find(x=>x.step==='prepared').windows,after=s.steps.find(x=>x.step==='after-peer');
assert(before.length===(settings?2:1)&&after.windows.length===before.length,'window count mismatch');
const b=before.find(w=>w.hwnd===f.expected_tk),w=after.windows.find(w=>w.hwnd===f.expected_tk);
assert(b&&w&&b.pid===w.pid&&w.visible&&!w.iconic&&after.foreground.hwnd===w.hwnd,'actual target foreground missing');
assert(before.every(b=>after.windows.some(a=>a.hwnd===b.hwnd&&a.pid===b.pid)),'window identity changed');
assert(s.raw_inputs.length>0&&s.raw_inputs.every(x=>!x.rejected&&!x.selftest),'rejected or synthetic inputs');
const a=s.answers;
assert(a.foreground==='出た'&&a.kept==='保たれた'&&a.single.normalize('NFKC')==='1つ','human answer is not a pass');
assert(settings?a.input==='入った':a.key_reached==='変わった'&&a.restored==='戻った','actual keyboard probe did not pass');
for(const key of ['foreground','kept','single',...(settings?['input']:['key_reached','restored'])])assert(s.raw_inputs.some(x=>x.key===key&&x.text===a[key]),'direct answer missing: '+key);
assert(i.originals_unchanged,'originals changed');
for(const [file,expected] of Object.entries(i.manifest.originals_before)){
 const full=path.join(root,file),actual=fs.existsSync(full)?hash(fs.readFileSync(full)):null;
 assert(actual===expected,'original changed after cleanup: '+file);
}
const build=JSON.parse(fs.readFileSync(path.join(phase,'06-BUILD-EVIDENCE.json')));
const report=JSON.parse(fs.readFileSync(path.join(build.final_release.final_dir,'release-report.json')));
assert(build.generation===5&&s.target_exe_sha256===build.final_release.exe_sha256,'generation mismatch');
for(const [file,expected] of Object.entries(report.input_manifest))assert(hash(fs.readFileSync(path.join(root,file)))===expected,'frozen input drift: '+file);
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerPath));
const row=ledger.cases.find(c=>c.id===s.case).subrows.find(r=>r.card===s.row);
assert(row&&row.status==='not-run'&&row.generation===5&&row.release_requirement==='required','row already judged or wrong generation');
const uatPath=path.join(phase,'06-UAT.md'),uat=fs.readFileSync(uatPath,'utf8'),marker='### '+s.row+'\n',start=uat.indexOf(marker);assert(start>=0,'card missing');
const end=uat.indexOf('\n### ',start+marker.length),stop=end<0?uat.length:end,card=uat.slice(start,stop);
assert(card.includes('- **状態**: not-run'),'UAT row already judged');
const run=path.resolve(s.run);assert(run.startsWith(path.join(root,'.planning','tmp')+path.sep),'unexpected run root');
const dest=path.join(phase,'06-05-evidence',name.replace('.json','-raw'));assert(!fs.existsSync(dest),'raw already preserved');
const pending=[];
const fixture=path.join(run,'uat-owner-'+(nested?'nested':s.condition));
if(nested){
 assert(!fs.existsSync(path.join(fixture,'manual-deadline')),'safety deadline fired');
 const closed=JSON.parse(fs.readFileSync(path.join(fixture,'manual-nested-closed.json'))),input=JSON.parse(fs.readFileSync(path.join(fixture,'manual-nested-input.json')));
 assert(closed.inner_closed&&closed.grab===closed.outer&&closed.text==='unsaved input'&&closed.cursor===5&&JSON.stringify(closed.selection)==='[1,7]','inner close/preparation not established');
 assert(closed.outer===f.expected_focus.slice(0,f.expected_focus.lastIndexOf('.')),'wrong outer dialog');
 assert(input.text==='ux input'&&input.cursor===2,'actual x input did not reach outer entry');
}
for(const [label,dir,names] of [['run',run,['manifest.json']],['primary',fixture,['result.json','focus-result.json','resource-audit.json','ready','stderr.log','stdout.log','traceback.log',...(nested?['manual-nested-closed.json','manual-nested-input.json']:[])]]]){
 for(const file of names){const source=path.join(dir,file);if(!fs.existsSync(source))continue;pending.push({source,target:path.join(dest,label+'-'+file),bytes:fs.readFileSync(source)});}
}
const primary=JSON.parse(pending.find(p=>p.target.endsWith('primary-result.json')).bytes);
assert(primary.result==='primary'&&primary.constructed===1&&primary.restored===1&&primary.status_preserved,'primary did not exit normally');
fs.mkdirSync(dest);const copies=[];
for(const p of pending){fs.writeFileSync(p.target,p.bytes,{flag:'wx'});copies.push({source:p.source,target:path.relative(phase,p.target).replaceAll('\\','/'),sha256:hash(p.bytes)});}
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
row.status='pass';row.preparation={status:'prepared',run_id:path.basename(run),note:settings?'実設定ダイアログ内の未保存文字・選択・カーソルを設定済みの入力欄から、操作なしでpeer復帰。':'PDFと選択を用意し、指定Canvasに入力先を置いて操作なしでpeer復帰。'};
row.observations=settings?{typed_text_kept:true,selection_kept:true,cursor_kept:true,input_target_kept:true,foreground_result:'settings-restored'}:{foreground_result:'main-restored',key_reached_window:true,mode_restored:true,selection_kept:true,input_target_canvas:true};
row.observation_basis={session_file:relative,session_sha256:hash(raw),state:settings?'test_startup_windows.py snapshot のentry文字・insert・sel.first・sel.last一致。利用者の保持回答と実x入力を併用。':'test_startup_windows.py snapshot のPDF・選択・表示ページ一致と対象Canvasのsettled_focus一致。利用者の選択保持・F5切替/復帰の直接回答を併用。',window:{before:b,after:w,foreground:after.foreground},focus_result:f,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),frozen_input_files:Object.keys(report.input_manifest).length};
if(nested){row.preparation.note='設定→内側LLM設定を開いて閉じ、outer入力/選択を準備。復帰後は利用者がxを入力。';row.observations={outer_input_kept:true,selection_kept:true,grab_released_after_inner_close:true};row.observation_basis.nested_closed=i['manual-nested-closed.json'];row.observation_basis.actual_input=i['manual-nested-input.json'];}
row.answer=s.composed_answer;row.raw_inputs=s.raw_inputs;row.answer_provenance='利用者が可視PowerShellへ直接入力。担当による代理入力なし。';row.run_id=path.basename(run);row.observed_at=s.finished_at;
row.environment={...i.manifest.environment,elevated:i.manifest.environment.is_admin};row.input_manifest_sha256=build.final_release.input_manifest_sha256;row.source_commit=i.manifest.source_commit;
const passed=ledger.cases.flatMap(c=>c.subrows).filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
const updated=card.replace(/- \*\*状態\*\*: not-run[^\n]*/,`- **状態**: pass / 利用者直接入力・機械観測一致。根拠: ${relative}\n- **回答原文**: ${s.composed_answer}`);
let finalUat=uat.slice(0,start)+updated+uat.slice(stop);
finalUat=finalUat.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/,`本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');fs.writeFileSync(uatPath,finalUat);
console.log(JSON.stringify({row:s.row,status:'pass',required_pass:passed,required_not_run:108-passed,deferred:2,copied:copies.length}));
