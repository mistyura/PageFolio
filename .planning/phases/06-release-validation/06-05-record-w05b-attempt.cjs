// W05b: passにならなかった回(時間超過・return-not-established・検出失敗・manual-deadline・利用者の中止など)を、
// not-run の attempt として原本copy・hash・理由付きで台帳へ保存する。行のstatusと必須24pass/84not-run/対象外2の集計は変えない。
// 使い方: node 06-05-record-w05b-attempt.cjs <06-05-evidence配下のsessionファイル名> --reason "<利用者の発言や状況を含む理由>" [--dry-run [--session-dir <dir>]]
//   --dry-run は照合だけを行い、台帳・原本copyを一切書き換えない(--session-dir はdry-runのときだけ有効)。
// 制約: outcome が answered の回は対象外(passの記録は 06-05-record-w05b.cjs)。selftest/診断は拒否する。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..'),name=process.argv[2],dry=process.argv.includes('--dry-run');
const assert=(ok,why)=>{if(!ok)throw Error(why);};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const arg=k=>{const i=process.argv.indexOf(k);return i>0?process.argv[i+1]:undefined;};
assert(/^W05b_ocr-close-confirm_at_(script|module|production-exe)-\d{8}T\d{6}Z(-\d+)?\.json$/.test(name||''),'unexpected filename');
const reason=arg('--reason');assert(typeof reason==='string'&&reason.trim().length>=10&&!reason.startsWith('--'),'--reason (10文字以上の理由) is required');
const sessionDir=dry&&arg('--session-dir')?path.resolve(arg('--session-dir')):path.join(phase,'06-05-evidence');
assert(dry||!arg('--session-dir'),'--session-dir requires --dry-run');
const relative='06-05-evidence/'+name,raw=fs.readFileSync(path.join(sessionDir,name)),s=JSON.parse(raw);
assert(s.case==='W05b'&&s.condition==='ocr-close-confirm'&&s.row===`W05b/ocr-close-confirm@${s.entry}`,'row mismatch');
assert(!s.selftest&&!s.diagnostics&&s.acceptance!==false,'selftest/diagnostic session cannot be an attempt');
// answered の回は、人の直接回答が pass 条件(06-05-record-w05b.cjs の expectA と同一)を満たさない場合だけ attempt にできる。
const passAnswers={result_shown:'見えた',auto_return:'自動で出た',manual_switch:'していない',answered_no:'いいえを押した',process_kept:'続いていた',summary_not_run:'していない'};
const failedAnswers=s.outcome==='answered'?Object.entries(passAnswers).filter(([k,v])=>(s.answers||{})[k]!==v).map(([k])=>k):[];
// 回答が全てpass条件どおりの回は、pass helper の dry-run が実際に拒否した場合だけ attempt にできる(拒否理由を保存)。
let passRejection=null;
if(s.outcome==='answered'&&failedAnswers.length===0){
 const args=[path.join(phase,'06-05-record-w05b.cjs'),name,'--dry-run',...(dry&&arg('--session-dir')?['--session-dir',sessionDir]:[])];
 const r=require('node:child_process').spawnSync(process.execPath,args,{encoding:'utf8'});
 assert(r.status!==0,'answered session accepted by 06-05-record-w05b.cjs --dry-run; record it as pass, not as an attempt');
 passRejection=((r.stderr||'').match(/Error: ([^\n]+)/)||[])[1]||'pass helper rejected (no message)';
}
const exe=s.entry==='production-exe',w=s.w05b||{};
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerPath));
const row=ledger.cases.find(c=>c.id==='W05b').subrows.find(r=>r.card===s.row);
assert(ledger.generation===5&&row&&row.status==='not-run'&&row.generation===5&&row.release_requirement==='required','unexpected ledger row (already judged or wrong generation)');
assert(!row.attempts?.some(a=>a.session_file===relative),'attempt already recorded');
const dest=path.join(phase,relative.replace('.json','-raw'));assert(dry||!fs.existsSync(dest),'raw already preserved');
// 原本copy: 存在するものだけ(途中で止まった回はファイルが揃わない)。run外のパスは拒否。
const copies=[],missing=[];
let run=null;
if(s.run){
 run=path.resolve(s.run);assert(run.startsWith(path.join(root,'.planning','tmp')+path.sep),'run outside known temporary root');
 const fixture=path.join(run,'uat-owner-native-ocr');
 const list=[[run,'manifest.json','run']];
 if(exe){
  for(const f of ['evidence/inspect-001.json','evidence/inspect-002.json','evidence/w05b-server.jsonl','fixtures/ocr-one-page.pdf','dist/pagefolio_settings.json'])list.push([run,f,'run']);
  const ev=path.join(run,'evidence');
  if(fs.existsSync(ev))for(const f of fs.readdirSync(ev))if(/^stop-diagnostics-\d+\.json$/.test(f))list.push([run,'evidence/'+f,'run']);
 }else{
  for(const f of ['result.json','focus-result.json','resource-audit.json','ready','stdout.log','stderr.log','traceback.log','manual-ocr-running.json','manual-ocr-close-start.json','manual-ocr-after-peer.json','manual-ocr-close-no.json','manual-ocr-completed.json','manual-ocr-final.json','manual-ocr-server.jsonl','manual-deadline','ocr-one-page.pdf'])list.push([fixture,f,'primary']);
 }
 for(const [dir,f,label] of list){const source=path.join(dir,f);if(!fs.existsSync(source)){missing.push(source);continue;}copies.push({source,label,file:f.replaceAll('/','-'),bytes:fs.readFileSync(source)});}
}
const deadline=!exe&&copies.some(c=>c.file==='manual-deadline');
const attempt={
 status:'not-run',
 reason:reason.trim(),
 outcome:s.outcome,failed_answers:failedAnswers,pass_rejection:passRejection,
 error:s.error||null,
 deadline_marker_present:deadline,
 session_file:relative,session_sha256:hash(raw),run_id:exe?s.run_id:(s.run?path.basename(run):null),
 observed_at:s.finished_at,answer:s.composed_answer||'',answers:s.answers||null,raw_inputs:s.raw_inputs||[],
 procedure_verdict:s.procedure_verdict||null,
 w05b:{budget:w.budget||null,return_assessment:w.return_assessment||null,enter_elapsed_s:w.enter_elapsed_s??null,no_elapsed_s:w.no_elapsed_s??null,release_elapsed_s:w.release_elapsed_s??null,peer:w.peer||null,beep_at:w.beep_at||null},
 last_steps:(s.steps||[]).slice(-4).map(x=>({at:x.at,step:x.step})),
 cleanup:s.cleanup||null,stop:s.stop||null,verify_after:s.verify_after||null,source_distribution_unchanged:s.source_distribution_unchanged??null,owner_after:s.owner_after||null,
 note:'passへ転用しない。製品不合格とも断定しない(原因は理由欄と原本で判断)。',
 raw_copy_manifest:null,missing_raw:missing.map(p=>path.relative(root,p).replaceAll('\\','/'))
};
if(dry){console.log(JSON.stringify({row:row.card,dry_run:true,would_record:true,outcome:s.outcome,copies:copies.length,missing:missing.length,attempts_after:(row.attempts?.length||0)+1,note:'ledger/raw were not modified'}));process.exit(0);}
fs.mkdirSync(dest);
const written=copies.map(c=>{const target=path.join(dest,c.label+'-'+c.file);fs.writeFileSync(target,c.bytes,{flag:'wx'});return {source:c.source,target:path.relative(phase,target).replaceAll('\\','/'),sha256:hash(c.bytes)};});
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify({copies:written,missing:attempt.missing_raw},null,2)+'\n');
attempt.raw_copy_manifest=path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/');
row.attempts??=[];row.attempts.push(attempt);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');
console.log(JSON.stringify({row:row.card,status:row.status,attempts:row.attempts.length,copied:written.length,missing:missing.length}));
