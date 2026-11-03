// W02の実EXEを直接回答・同一窓への復帰・配布物保護から記録する。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2];
const assert=(ok,why)=>{if(!ok)throw Error(why);},hash=b=>crypto.createHash('sha256').update(b).digest('hex');
assert(/^(W02_(settings|thumb|preview)|W03_pdf-3page|W05a_nested-settings)_at_production-exe-\d{8}T\d{6}Z\.json$/.test(name||''),'unexpected filename');
const relative='06-05-evidence/'+name,raw=fs.readFileSync(path.join(phase,relative)),s=JSON.parse(raw);
// この1件は終了前の瞬間観測でerrorになったが、その後の同runで通常終了が実測された。
// 他のerrorを一般許容せず、原エラーと利用者の終了順補足を別欄に残す。
const reviewedCleanup=name==='W02_thumb_at_production-exe-20261028T114227Z.json'&&s.outcome==='error'&&s.error==="NotEstablished('PageFolioの通常終了を確認できませんでした')"&&s.user_close?.closed===false&&s.stop.find(r=>r.pid===s.primary.pid)?.result==='closed';
const pdfHistory=s.case==='W03'&&s.condition==='pdf-3page';
const nested=s.case==='W05a'&&s.condition==='nested-settings';
assert((nested||pdfHistory||(['settings','thumb','preview'].includes(s.condition)&&s.case==='W02'))&&s.row===`${s.case}/${s.condition}@production-exe`&&!s.selftest&&!s.diagnostics&&((!s.error&&s.outcome==='answered')||reviewedCleanup),'not a human completed run');
const settings=nested||s.condition==='settings';
assert(s.acceptance!==false&&s.source_distribution_unchanged===true&&s.owner_after.length===0,'isolation/owner mismatch');
const primaryStop=s.stop.find(r=>r.pid===s.primary.pid)?.result;
assert(s.stop.length===2&&(primaryStop==='closed'||(primaryStop==='already-exited'&&s.user_close?.closed&&s.user_close.pid===s.primary.pid))&&s.stop.find(r=>r.pid===s.peer.pid)?.result==='already-exited','not a normal cleanup');
if(!settings||nested){
 assert(s.procedure_verdict==='clean'&&!s.procedure_assessment.rerun_required&&s.peer_exit?.returncode===0,'peer observation incomplete');
 assert(s.input_monitor.enabled&&!s.input_monitor.errors.length&&!s.input_monitor.truncated&&!s.procedure_assessment.all_window_presses_during_observation.length,'interrupted observation');
 assert(s.peer_exit.at<=s.steps.find(x=>x.step==='after-peer').at,'observation preceded peer exit');
 assert(s.user_close&&s.user_close.requested_at<s.user_close.observed_at&&(s.user_close.closed||primaryStop==='closed'),'normal exit missing');
}
const v=s.verify_after;
assert(v.ok&&v.distribution_changed.length===0&&v.undeclared.length===0&&v.extra_dirs.length===0&&v.missing_dirs.length===0,'copy verification failed');
assert(v.overlay_changed.every(n=>n==='pagefolio_settings.json'),'unexpected overlay change');
const a=s.answers;
if(nested){assert(a.inner_closed==='はい'&&s.raw_inputs.some(x=>x.key==='inner_closed'&&x.text.trim()==='はい'),'inner LLM close not confirmed');assert(s.procedure_verdict==='clean'&&!s.procedure_assessment.rerun_required&&s.peer_exit.returncode===0&&s.peer_exit.at<=s.steps.find(x=>x.step==='after-peer').at&&s.user_close?.closed,'nested observation/normal close missing');}
if(pdfHistory){
 assert(['はい','見える'].includes(a.edit_visible_after_restore)&&['合成PDFのみ','合成のみ'].includes(a.original_pdf_untouched),'human preparation not confirmed');
 assert(a.page_counts.normalize('NFKC').replace(/[\s・,、/]/g,'')==='4343'&&['すべて横','全て横'].includes(a.orientations),'human Undo/Redo sequence did not pass');
}else{
 assert(a.foreground==='出た'&&a.kept==='保たれた'&&a.single.normalize('NFKC')==='1つ','human observations did not pass');
 assert(settings?a.input==='入った':a.key_reached==='変わった'&&a.restored==='戻った','actual keyboard probe did not pass');
}
assert(s.raw_inputs.length>0&&s.raw_inputs.every(r=>!r.rejected&&!r.selftest),'synthetic/rejected input');
for(const key of pdfHistory?['page_counts','orientations','edit_visible_after_restore','original_pdf_untouched']:['foreground','kept','single',...(settings?['input']:['key_reached','restored'])])assert(s.raw_inputs.some(x=>x.key===key&&x.text.trim()===a[key]),'direct answer missing: '+key);
const pre=s.steps.find(x=>x.step==='target-ready'),post=s.steps.find(x=>x.step==='after-peer');
assert(pre.windows.length===(settings?2:1)&&post.windows.length===pre.windows.length,'window count mismatch');
const before=settings?pre.windows.find(w=>w.title==='設定'):pre.windows[0],after=settings?post.windows.find(w=>w.title==='設定'):post.windows[0];
assert(before&&after&&before.hwnd===after.hwnd&&before.pid===s.primary.pid&&after.pid===s.primary.pid&&!after.iconic,'target window identity changed');
assert(pre.windows.every(b=>post.windows.some(w=>w.hwnd===b.hwnd&&w.pid===b.pid)),'window identity changed');
assert(post.foreground.hwnd===after.hwnd&&post.foreground.owned_by==='primary','actual target foreground mismatch');
const build=JSON.parse(fs.readFileSync(path.join(phase,'06-BUILD-EVIDENCE.json')));
assert(build.generation===5&&[s.binary_sha256,s.target_exe_sha256,v.exe_sha256].every(h=>h===build.final_release.exe_sha256),'binary mismatch');
assert(s.tree_sha256===build.final_release.tree_sha256,'distribution tree mismatch');
const report=JSON.parse(fs.readFileSync(path.join(build.final_release.final_dir,'release-report.json')));
for(const [file,expected] of Object.entries(report.input_manifest))assert(hash(fs.readFileSync(path.join(root,file)))===expected,'frozen input drift: '+file);
const run=path.resolve(s.run);assert(run.startsWith(path.join(root,'.planning','tmp')+path.sep),'unexpected run root');
const manifest=JSON.parse(fs.readFileSync(path.join(run,'manifest.json')));
assert(manifest.run_id===s.run_id&&manifest.status==='stopped','unexpected manifest');
assert(Object.keys(manifest.overlay).length===1&&Object.hasOwn(manifest.overlay,'pagefolio_settings.json')&&manifest.overlay['pagefolio_settings.json']===null,'settings absence not declared');
const declaration=manifest.overlay_log.find(x=>x.name==='pagefolio_settings.json');
assert(declaration&&declaration.at<manifest.processes.find(r=>r.role==='primary').started_at,'missing prior overlay declaration');
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerPath));
const row=ledger.cases.find(c=>c.id===s.case).subrows.find(r=>r.card===s.row);
assert(row&&row.status==='not-run'&&row.generation===5&&row.release_requirement==='required','row already judged or wrong generation');
const uatPath=path.join(phase,'06-UAT.md'),uat=fs.readFileSync(uatPath,'utf8'),marker='### '+s.row+'\n',start=uat.indexOf(marker);assert(start>=0,'card missing');
const next=uat.indexOf('\n### ',start+marker.length),end=next<0?uat.length:next,card=uat.slice(start,end);assert(card.includes('- **状態**: not-run'),'card already judged');
const dest=path.join(phase,'06-05-evidence',name.replace('.json','-raw'));assert(!fs.existsSync(dest),'raw already preserved');
const files=['manifest.json','evidence/inspect-001.json','evidence/inspect-002.json','dist/pagefolio_settings.json'];
if(!settings){
 const pdf=s.fixture_pdf,expected=path.join(run,'fixtures','edit-three-page.pdf');
 assert(pdf&&path.resolve(pdf.path)===expected&&pdf.pages===3&&hash(fs.readFileSync(expected))===pdf.sha256,'fixture PDF missing or changed');
 assert(manifest.fixtures['edit-three-page'].sha256===pdf.sha256,'fixture manifest mismatch');
 files.push('fixtures/edit-three-page.pdf');
}
const contents=files.map(n=>({source:path.join(run,n),bytes:fs.readFileSync(path.join(run,n)),name:n.replaceAll('/','-')}));
fs.mkdirSync(dest);const copies=contents.map(({source,bytes,name})=>{const target=path.join(dest,name);fs.writeFileSync(target,bytes,{flag:'wx'});return {source,target:path.relative(phase,target).replaceAll('\\','/'),sha256:hash(bytes)};});
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
row.status='pass';row.preparation={status:'prepared',run_id:s.run_id,note:settings?'事前に設定不存在を宣言した世代5隔離copy。利用者が実フォントサイズ欄に13を入力し末尾3だけ選択。':'事前に設定不存在を宣言した世代5隔離copy。利用者が3ページPDFを開き指定対象を選択。'};
row.observations=settings?{typed_text_kept:true,selection_kept:true,cursor_kept:true,input_target_kept:true,foreground_result:'settings-restored'}:{foreground_result:'main-restored',key_reached_window:true,mode_restored:true,selection_kept:true};
row.observation_basis={session_file:relative,session_sha256:hash(raw),windows:{before,after,foreground:post.foreground},input:settings?'利用者が13と末尾3の選択保持を目視し、マウスを使わず2を押して12になるか確認した直接回答。内部widget状態は実EXEへ注入していない。':'利用者が実PDFの表示/選択保持とマウスを使わないF5でのモード切替・復帰を直接回答。内部Canvas identityはPython行の別根拠で、実EXEへ注入していない。',...(settings?{}:{fixture_pdf:s.fixture_pdf}),verify_after:v,stop:s.stop,source_distribution_unchanged:s.source_distribution_unchanged,owner_after:s.owner_after,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),frozen_input_files:Object.keys(report.input_manifest).length};
row.answer=s.composed_answer;row.raw_inputs=s.raw_inputs;row.answer_provenance='利用者が可視PowerShellへ直接入力。担当による代理入力なし。';row.run_id=s.run_id;row.observed_at=s.finished_at;row.environment=s.environment;row.binary_sha256=s.binary_sha256;row.input_manifest_sha256=build.final_release.input_manifest_sha256;
if(pdfHistory){
 row.preparation.note='世代5隔離copyと合成3ページPDFを用い、利用者が回転・複製・削除を行って未保存のまま二次起動。';
 row.observations={edit_visible_after_restore:true,original_pdf_untouched:true,foreground_after:post.foreground,...Object.fromEntries(['undo_1','redo_1','undo_2','redo_2'].map((key,n)=>[key,{pages:n%2===0?4:3,first_page_orientation:'横',answer_source:`page_counts[${n}] and orientations`}]))};
 row.observation_basis.input='利用者による4手の各ページ数と1ページ目の向きの直接回答。内部Document/Undo identityはPython行の別根拠であり、実EXEへ注入していない。合成PDF原本のhash不変を検証。';
}
if(nested){row.preparation.note='利用者が外側フォントサイズ13を入力し、内側LLM設定を変更せず閉じた後に13の保持を確認。末尾3を選択し二次起動後はマウスなしで2を入力。';row.observations={outer_input_kept:true,selection_kept:true,grab_released_after_inner_close:true,foreground_after:post.foreground};row.observation_basis.inner_closed_answer=a.inner_closed;}
if(reviewedCleanup)row.cleanup_review={original_outcome:s.outcome,original_error:s.error,early_check:s.user_close,final_stop:s.stop,reason:'W02の自動復帰・F5往復・選択保持はcleanな監視と直接回答で成立。最後のEnter後に利用者が終了確認はいを押し、同runのS.stopが12秒以内にclosedを観測。強制終了なし・owner空・配布元不変。終端前の一時点判定によるharness errorであり、原ログは変更せず最終の正常終了証拠で受入する。',followup:{answer:'PowerShellでEnterを押した後、終了確認の「はい」を押した',source:'request_user_input_async/call_326977f2fc1143c1a1341b1592f5c4fe'}};
const passed=ledger.cases.flatMap(c=>c.subrows).filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
const updated=card.replace(/- \*\*状態\*\*: not-run[^\n]*/,`- **状態**: pass / 利用者直接入力・外部観測・配布物保護が一致。根拠: ${relative}\n- **回答原文**: ${s.composed_answer}`);
let result=uat.slice(0,start)+updated+uat.slice(end);
result=result.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/,`本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');fs.writeFileSync(uatPath,result);
console.log(JSON.stringify({row:s.row,status:'pass',required_pass:passed,required_not_run:108-passed,deferred:2,copied:copies.length}));
