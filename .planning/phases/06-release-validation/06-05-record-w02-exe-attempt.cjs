// 設定画面を二次起動後に開いた回は準備不成立として原本を保持する。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2]||'W02_settings_at_production-exe-20261028T111715Z.json';
if(!['W02_settings_at_production-exe-20261028T111715Z.json','W02_thumb_at_production-exe-20261028T113526Z.json','W03_pdf-3page_at_production-exe-20261028T125745Z.json','W03_pdf-3page_at_production-exe-20261028T134605Z.json'].includes(name))throw Error('unexpected session');
const relative='06-05-evidence/'+name;
const raw=fs.readFileSync(path.join(phase,relative)),s=JSON.parse(raw),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const canvas=s.row==='W02/thumb@production-exe';
const pdf=s.row==='W03/pdf-3page@production-exe';
const interrupted=name==='W03_pdf-3page_at_production-exe-20261028T134605Z.json';
if((!canvas&&!pdf&&(s.row!=='W02/settings@production-exe'||s.steps.find(x=>x.step==='target-ready').windows.some(w=>w.title==='設定')))||s.selftest||s.owner_after.length||!s.verify_after.ok)throw Error('unexpected attempt');
if(pdf&&((interrupted?s.outcome!=='interrupted'||s.raw_inputs.some(x=>x.key==='page_counts'):!s.raw_inputs.some(x=>x.key==='page_counts'&&x.text==='3 3 3 3'))||s.stop.some(x=>!['closed','already-exited'].includes(x.result))||!s.source_distribution_unchanged))throw Error('unexpected PDF attempt');
if(canvas&&(s.steps.find(x=>x.step==='after-peer').foreground.owned_by!==null||!s.stop.some(r=>r.result==='terminated')))throw Error('unexpected canvas attempt');
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerPath)),row=ledger.cases.find(c=>c.id===(pdf?'W03':'W02')).subrows.find(r=>r.card===s.row);
if(row.status!=='not-run'||row.generation!==5||row.attempts?.some(a=>a.session_file===relative))throw Error('unexpected ledger or duplicate');
const run=path.resolve(s.run);if(!run.startsWith(path.join(root,'.planning','tmp')+path.sep))throw Error('unexpected run root');
const dest=path.join(phase,relative.replace('.json','-raw'));if(fs.existsSync(dest))throw Error('raw already preserved');
const files=['manifest.json','evidence/inspect-001.json','evidence/inspect-002.json',...(canvas?[`evidence/stop-diagnostics-${s.primary.pid}.json`,'fixtures/edit-three-page.pdf']:pdf?['fixtures/edit-three-page.pdf','dist/pagefolio_settings.json']:['dist/pagefolio_settings.json'])];
const contents=files.map(n=>({source:path.join(run,n),bytes:fs.readFileSync(path.join(run,n)),name:n.replaceAll('/','-')}));
fs.mkdirSync(dest);const copies=contents.map(({source,bytes,name})=>{const target=path.join(dest,name);fs.writeFileSync(target,bytes,{flag:'wx'});return {source,target:path.relative(phase,target).replaceAll('\\','/'),sha256:hash(bytes)};});
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
const reason=canvas?'二次起動4秒後の実前景はPowerShell。利用者は5秒を待たずF5を押してPowerShellへ戻ったと回答し、復帰観測が不成立。終了時は確認ダイアログ#32770が残りharnessでterminated。正常終了passへ転用しない。':'二次起動前のtarget-readyと後のafter-peerはメイン1窓のみ。利用者も「Enterの後で設定画面を開いた」と回答し準備不成立。後からの実入力を復帰時の設定保持passへ転用しない。';
const followup=canvas?{answer:'5秒を待たずF5を押してPowerShellへ戻った',source:'request_user_input_async/call_15d7d5f4462943648fb767ba25923a24'}:{answer:'Enterの後で設定画面を開いた',source:'request_user_input_async/call_1a97df354054409b9d734bf129c2f629'};
row.attempts??=[];row.attempts.push({status:'not-run',reason:pdf?'Undo/Redo各直後の直接回答が3 3 3 3で期待4 3 4 3と不一致。利用者はサムネイルと表示番号の両方で確認したと回答。原因未確定のためpassにしない。正常終了・原本保護とは分けて扱う。':reason,session_file:relative,session_sha256:hash(raw),run_id:s.run_id,observed_at:s.finished_at,answer:s.composed_answer,raw_inputs:s.raw_inputs,stop:s.stop,verify_after:s.verify_after,source_distribution_unchanged:s.source_distribution_unchanged,owner_after:s.owner_after,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),followup:pdf?{answer:'1,2',meaning:'サムネイルと表示番号の両方で確認',source:'request_user_input_async/call_78a8c0ae76f2486193927a6cc7e18585'}:followup});
if(interrupted){const attempt=row.attempts.at(-1);attempt.reason='PDFを開く準備段階で利用者が操作できないと回答。rawにはEnterが1回ありpeer起動後にinterruptedとなったが、4手の回答なし。準備不成立として保持し、passにはしない。';attempt.followup={answer:'4ページにならない・操作できない',source:'request_user_input_async/call_2faf1184388f4f3698ad27694cc53f73',clarification:'PDFを開く段階（利用者回答1）'};}
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');console.log(JSON.stringify({row:row.card,status:row.status,copied:copies.length,attempts:row.attempts.length}));
