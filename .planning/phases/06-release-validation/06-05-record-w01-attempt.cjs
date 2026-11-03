const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..');
const relative='06-05-evidence/W01_normal_at_script-20261028T095542Z.json';
const raw=fs.readFileSync(path.join(phase,relative));const session=JSON.parse(raw);
if(session.row!=='W01/normal@script'||session.selftest||session.procedure_verdict!=='keys-suspect'||session.cleanup.alive_after.length)throw Error('unexpected attempt');
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json');const ledger=JSON.parse(fs.readFileSync(ledgerPath));
const row=ledger.cases.find(c=>c.id==='W01').subrows.find(r=>r.subrow==='normal@script');
if(ledger.generation!==5||row.status!=='not-run')throw Error('unexpected ledger');
if(row.attempts?.some(a=>a.session_file===relative))throw Error('attempt already recorded');
const run=path.resolve(session.run);
if(!run.startsWith(path.join(root,'.planning','tmp')+path.sep))throw Error('run outside known temporary root');
const dest=path.join(phase,'06-05-evidence/W01-normal-script-20261028T095542Z-raw');
if(fs.existsSync(dest))throw Error('raw already preserved');fs.mkdirSync(dest);
const copies=[];
for(const [label,dir,names] of [['run',run,['manifest.json']],['primary',path.join(run,'uat-owner-normal'),['result.json','focus-result.json','resource-audit.json','ready','stderr.log','stdout.log','traceback.log']]]){
 for(const name of names){const source=path.join(dir,name);if(!fs.existsSync(source))continue;
  const bytes=fs.readFileSync(source),target=path.join(dest,label+'-'+name);fs.writeFileSync(target,bytes,{flag:'wx'});
  copies.push({source,target:path.relative(phase,target).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(bytes).digest('hex')});
 }
}
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
row.attempts??=[];row.attempts.push({status:'not-run',reason:'二次起動前のawaiting-enter中にPageFolio前景でEnter(vk13)を検出。driverのrerun_required=trueを保持。表示回答・機械的復帰は良好だが本受入passへ転用しない。',session_file:relative,session_sha256:crypto.createHash('sha256').update(raw).digest('hex'),run_id:path.basename(run),observed_at:session.finished_at,answer:session.composed_answer,raw_inputs:session.raw_inputs,procedure_assessment:session.procedure_assessment,cleanup:session.cleanup,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/')});
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');
console.log(JSON.stringify({row:row.card,status:row.status,attempts:row.attempts.length,copied:copies.length}));
