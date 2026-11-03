// W01のPython入口だけを、直接入力と実観測を照合して記録する。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2];
const assert=(ok,why)=>{if(!ok)throw Error(why);};
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
assert(/^W01_(normal|zoomed)_at_(script|module)-\d{8}T\d{6}Z\.json$/.test(name||''),'unexpected session filename');
const relative='06-05-evidence/'+name,raw=fs.readFileSync(path.join(phase,relative)),s=JSON.parse(raw);
assert(!s.selftest&&!s.diagnostics&&!s.error&&s.outcome==='answered','not an accepted human run');
assert(s.procedure_verdict==='clean'&&!s.procedure_assessment.rerun_required,'procedure not clean');
assert(s.harness_peer.returncode===0&&s.harness_inspect.returncode===0&&s.harness_stop.returncode===0,'harness error');
assert(s.cleanup.alive_after.length===0&&s.cleanup.terminated_owned.length===0&&s.cleanup.left_after_harness_stop.length===0,'cleanup not normal');
const i=s.harness_inspect.json,f=i['focus-result.json'],peer=s.harness_peer.json.result;
assert(peer.result==='completed'&&peer.constructed===0&&peer.status_preserved,'peer did not restore sole owner');
assert(f.result==='completed'&&f.state_preserved&&f.target_correct&&f.focus_correct&&f.placement===s.condition,'state restoration mismatch');
const before=s.steps.find(x=>x.step==='prepared').windows,after=s.steps.find(x=>x.step==='after-peer');
assert(before.length===1&&before[0].iconic&&after.windows.length===1,'single/minimized window missing');
const w=after.windows[0];
assert(w.hwnd===before[0].hwnd&&!w.iconic&&w.zoomed===(s.condition==='zoomed')&&after.foreground.hwnd===w.hwnd,'window or foreground mismatch');
assert(s.raw_inputs.every(x=>!x.rejected&&!x.selftest),'rejected or synthetic input');
const a=s.answers,n=x=>x.normalize('NFKC');
assert(a.state_after===(s.condition==='normal'?'通常':'最大化')&&a.geometry==='はい'&&n(a.single)==='1つ'&&a.status==='見える','human answer is not a pass');
assert(i.originals_unchanged,'originals changed');
for(const [file,expected] of Object.entries(i.manifest.originals_before)){
 const full=path.join(root,file),actual=fs.existsSync(full)?hash(fs.readFileSync(full)):null;
 assert(actual===expected,'original changed after cleanup: '+file);
}
const build=JSON.parse(fs.readFileSync(path.join(phase,'06-BUILD-EVIDENCE.json')));
const report=JSON.parse(fs.readFileSync(path.join(build.final_release.final_dir,'release-report.json')));
assert(build.generation===5&&s.target_exe_sha256===build.final_release.exe_sha256,'generation mismatch');
for(const [file,expected] of Object.entries(report.input_manifest))assert(hash(fs.readFileSync(path.join(root,file)))===expected,'frozen input drift: '+file);
const ledgerFile=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerFile));
const row=ledger.cases.find(c=>c.id==='W01').subrows.find(r=>r.card===s.row);
assert(row&&row.status==='not-run'&&row.generation===5&&row.release_requirement==='required','row already judged or wrong generation');
const run=path.resolve(s.run);assert(run.startsWith(path.join(root,'.planning','tmp')+path.sep),'unexpected run root');
const dest=path.join(phase,'06-05-evidence',name.replace('.json','-raw'));assert(!fs.existsSync(dest),'raw already preserved');fs.mkdirSync(dest);
const copies=[];
for(const [label,dir,names] of [['run',run,['manifest.json']],['primary',path.join(run,'uat-owner-'+s.condition),['result.json','focus-result.json','resource-audit.json','ready','stderr.log','stdout.log','traceback.log']]]){
 for(const file of names){const source=path.join(dir,file);if(!fs.existsSync(source))continue;
  const bytes=fs.readFileSync(source),target=path.join(dest,label+'-'+file);fs.writeFileSync(target,bytes,{flag:'wx'});
  copies.push({source,target:path.relative(phase,target).replaceAll('\\','/'),sha256:hash(bytes)});
 }
}
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
row.status='pass';row.preparation={status:'prepared',run_id:path.basename(run),note:'最小化済み同HWNDを確認し、無操作のままpeerで復元。'};
row.observations={state_before:s.condition,state_after:f.placement,geometry_match:true,status_text_kept:true,single_screen:true};
row.observation_basis={session_file:relative,session_sha256:hash(raw),geometry:'test_startup_windows.pyのnormal geometry一致/zoomed state照合と利用者の位置・大きさ回答',status:'snapshot内status_var一致と利用者の表示回答',window:{before:before[0],after:w,foreground:after.foreground},focus_result:f,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),frozen_input_files:Object.keys(report.input_manifest).length};
row.answer=s.composed_answer;row.raw_inputs=s.raw_inputs;row.answer_provenance='利用者が可視PowerShellへ直接入力。担当による代理入力なし。';row.run_id=path.basename(run);row.observed_at=s.finished_at;
row.environment={...i.manifest.environment,elevated:i.manifest.environment.is_admin};row.input_manifest_sha256=build.final_release.input_manifest_sha256;row.source_commit=i.manifest.source_commit;
const rows=ledger.cases.flatMap(c=>c.subrows),passed=rows.filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
const uatPath=path.join(phase,'06-UAT.md'),uat=fs.readFileSync(uatPath,'utf8'),marker='### '+s.row+'\n',start=uat.indexOf(marker);assert(start>=0,'card missing');
const end=uat.indexOf('\n### ',start+marker.length),stop=end<0?uat.length:end;
const card=uat.slice(start,stop);assert(card.includes('- **状態**: not-run'),'UAT row already judged');
const updated=card.replace(/- \*\*状態\*\*: not-run[^\n]*/,`- **状態**: pass / 利用者直接入力・機械観測一致。根拠: ${relative}\n- **回答原文**: ${s.composed_answer}`);
let finalUat=uat.slice(0,start)+updated+uat.slice(stop);
finalUat=finalUat.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/,`本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerFile,JSON.stringify(ledger,null,2)+'\n');fs.writeFileSync(uatPath,finalUat);
console.log(JSON.stringify({row:s.row,status:'pass',required_pass:passed,required_not_run:108-passed,deferred:2,source_inputs:Object.keys(report.input_manifest).length,copied:copies.length}));
