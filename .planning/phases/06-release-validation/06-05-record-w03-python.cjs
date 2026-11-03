// W03: 利用者が実行した4手の直接回答と、復帰前後のDocument/履歴保持を照合する。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2];
const assert=(ok,why)=>{if(!ok)throw Error(why);};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
assert(/^W03_pdf-3page_at_(script|module)-\d{8}T\d{6}Z\.json$/.test(name||''),'unexpected session filename');
const relative='06-05-evidence/'+name,raw=fs.readFileSync(path.join(phase,relative)),s=JSON.parse(raw);
assert(s.case==='W03'&&s.condition==='pdf-3page'&&s.row===`W03/pdf-3page@${s.entry}`,'row mismatch');
assert(!s.selftest&&!s.diagnostics&&!s.error&&s.outcome==='answered','not a human acceptance run');
assert(s.procedure_verdict==='clean'&&!s.procedure_assessment.rerun_required,'procedure not clean');
assert(s.harness_peer.returncode===0&&s.harness_inspect.returncode===0&&s.harness_stop.returncode===0,'harness error');
assert(s.cleanup.alive_after.length===0&&s.cleanup.terminated_owned.length===0&&s.cleanup.left_after_harness_stop.length===0,'cleanup not normal');
const i=s.harness_inspect.json,f=i['focus-result.json'],peer=s.harness_peer.json.result,prepared=i['manual-pdf-ready.json'];
assert(peer.result==='completed'&&peer.constructed===0&&peer.status_preserved,'peer did not restore owner');
assert(f.result==='completed'&&f.state_preserved&&f.target_correct&&f.focus_correct,'state or target mismatch');
assert(f.document_pages===3&&JSON.stringify(f.page_rotations)==='[90,0,0]','edited PDF missing');
assert(prepared&&prepared.pages===3&&prepared.undo===3&&prepared.redo===0&&JSON.stringify(prepared.rotations)==='[90,0,0]','manual history preparation missing');
const before=s.steps.find(x=>x.step==='prepared').windows,after=s.steps.find(x=>x.step==='after-peer');
assert(before.length===1&&after.windows.length===1,'window count mismatch');
const b=before[0],w=after.windows[0];
assert(b.hwnd===w.hwnd&&b.pid===w.pid&&w.visible&&!w.iconic&&after.foreground.hwnd===w.hwnd&&w.hwnd===f.expected_tk,'actual target foreground missing');
assert(s.raw_inputs.length>0&&s.raw_inputs.every(x=>!x.rejected&&!x.selftest),'rejected or synthetic inputs');
const a=s.answers,steps=['undo_1','redo_1','undo_2','redo_2'];
const followup=name==='W03_pdf-3page_at_script-20261028T124500Z.json'?{question:'今回、自動で戻った直後、最初のCtrl+Zを押す前は、3ページで1ページ目が横向きでしたか？',answer:'3ページで1ページ目が横向きだった',source:'request_user_input_async/call_ddaf7104dc6e46d29753c23963cadf86'}:null;
assert((['見える','はい'].includes(a.edit_visible_after_restore)||(followup&&a.edit_visible_after_restore==='分からない'))&&['合成PDFのみ','合成のみ'].includes(a.original_pdf_untouched),'human preparation answer is not a pass');
const counts=a.page_counts.normalize('NFKC').replace(/[\s・,、/]/g,'');
assert(counts==='4343'&&['すべて横','全て横'].includes(a.orientations),'human sequence is not a pass');
for(const key of ['edit_visible_after_restore','page_counts','orientations','original_pdf_untouched']) assert(s.raw_inputs.some(x=>x.key===key&&x.text.trim()===a[key]),'direct answer missing: '+key);
const trace=i['manual-pdf-trace.json'];
assert(trace&&JSON.stringify(trace.map(x=>x.state.pages))==='[3,4,3,4,3]','actual page transitions missing');
assert(trace.every((x,n)=>x.state.rotations[0]===90&&x.state.undo===(n%2===0?3:2)&&x.state.redo===(n%2===0?0:1)),'actual history transitions mismatch');
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
const row=ledger.cases.find(c=>c.id==='W03').subrows.find(r=>r.card===s.row);
assert(row&&row.status==='not-run'&&row.generation===5&&row.release_requirement==='required','row already judged or wrong generation');
const uatPath=path.join(phase,'06-UAT.md'),uat=fs.readFileSync(uatPath,'utf8'),marker='### '+s.row+'\n',start=uat.indexOf(marker);assert(start>=0,'card missing');
const end=uat.indexOf('\n### ',start+marker.length),stop=end<0?uat.length:end,card=uat.slice(start,stop);assert(card.includes('- **状態**: not-run'),'UAT row already judged');
const run=path.resolve(s.run);assert(run.startsWith(path.join(root,'.planning','tmp')+path.sep),'unexpected run root');
assert(!fs.existsSync(path.join(run,'uat-owner-pdf','continued')),'automatic Undo/Redo is not human acceptance');
assert(!fs.existsSync(path.join(run,'uat-owner-pdf','manual-deadline')),'manual safety deadline fired');
const dest=path.join(phase,'06-05-evidence',name.replace('.json','-raw'));assert(!fs.existsSync(dest),'raw already preserved');
const pending=[];
for(const [label,dir,names] of [['run',run,['manifest.json']],['primary',path.join(run,'uat-owner-pdf'),['result.json','focus-result.json','manual-pdf-ready.json','manual-pdf-trace.json','resource-audit.json','ready','stderr.log','stdout.log','traceback.log',...(fs.existsSync(path.join(run,'uat-owner-pdf','manual-pdf-keys.json'))?['manual-pdf-keys.json']:[])]]]){
 for(const file of names){const source=path.join(dir,file);assert(fs.existsSync(source),'raw missing: '+file);pending.push({source,target:path.join(dest,label+'-'+file),bytes:fs.readFileSync(source)});}
}
const primary=JSON.parse(pending.find(p=>p.target.endsWith('primary-result.json')).bytes);
assert(primary.result==='primary'&&primary.constructed===1&&primary.restored===1&&primary.status_preserved,'primary did not exit normally');
fs.mkdirSync(dest);const copies=[];
for(const p of pending){fs.writeFileSync(p.target,p.bytes,{flag:'wx'});copies.push({source:p.source,target:path.relative(phase,p.target).replaceAll('\\','/'),sha256:hash(p.bytes)});}
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
row.status='pass';row.preparation={status:'prepared',run_id:path.basename(run),note:'合成3ページPDFを回転・複製・削除し未保存状態で復帰。manualでは自動Undo/Redoを行わず利用者が4手を実行。'};
row.observations={edit_visible_after_restore:true,...Object.fromEntries(steps.map((key,n)=>[key,{pages:Number(counts[n]),first_page_orientation:'横',answer_source:`page_counts[${n}] and orientations`} ])),original_pdf_untouched:true};
row.observation_basis={session_file:relative,session_sha256:hash(raw),state:'snapshotのDocument/描画/Undo・Redo・Blob identityが復帰前後で一致。4手は利用者の数字4つと向きの直接回答、および読み取り専用状態traceで照合。',window:{before:b,after:w,foreground:after.foreground},focus_result:f,manual_preparation:prepared,manual_trace:trace,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),frozen_input_files:Object.keys(report.input_manifest).length};
row.answer=s.composed_answer;row.raw_inputs=s.raw_inputs;row.answer_provenance='利用者が可視PowerShellへ直接入力。担当による代理入力なし。';row.run_id=path.basename(run);row.observed_at=s.finished_at;
if(followup){row.answer+=' / 追加回答: '+followup.answer;row.observation_basis.followup=followup;row.answer_provenance+=' 復帰直後の表示だけ説明を具体化し、同runの追加回答をChatGPTで受領。元の分からない回答は原本のまま保持。';}
row.environment={...i.manifest.environment,elevated:i.manifest.environment.is_admin};row.input_manifest_sha256=build.final_release.input_manifest_sha256;row.source_commit=i.manifest.source_commit;
const passed=ledger.cases.flatMap(c=>c.subrows).filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
const updated=card.replace(/- \*\*状態\*\*: not-run[^\n]*/,`- **状態**: pass / 利用者直接入力・機械観測一致。根拠: ${relative}\n- **回答原文**: ${row.answer}`);
let finalUat=uat.slice(0,start)+updated+uat.slice(stop);
finalUat=finalUat.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/,`本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');fs.writeFileSync(uatPath,finalUat);
console.log(JSON.stringify({row:s.row,status:'pass',required_pass:passed,required_not_run:108-passed,deferred:2,copied:copies.length}));
