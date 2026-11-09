// 差分だけをレビュー可能な形で保存し、原本と既存入力の保持を最終照合する。
const fs=require('fs'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const root=path.resolve(__dirname,'../../..');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const original=JSON.parse(fs.readFileSync(path.join(__dirname,'baseline/inputs-before.json')));
const changed=Object.keys(original).filter(p=>hash(p)!==original[p]);
const owned=['tests/test_startup_wake.py','tests/startup_wake_child.py'];
if(changed.some(p=>!owned.includes(p)))throw Error('unowned input changed');
for(const p of owned){
  const old=path.join(__dirname,'baseline',path.basename(p)+'.original');
  const r=cp.spawnSync('git',['diff','--no-index','--',old,path.join(root,p)],{cwd:root});
  if(r.status!==1)throw Error('unexpected diff result');
  fs.writeFileSync(path.join(__dirname,path.basename(p)+'.patch'),r.stdout);
}
const failure='.planning/phases/04-startup-control/04-reverify-20261028/native/pytest-full.txt';
const expected='8fd685d2e2d9c31e28dfe3e38c99cfc730af8273067115737adff530f73aec07';
const originalLogMatches=hash(failure)===expected;
if(!originalLogMatches)throw Error('original log changed');
const dodSources=['.planning/ROADMAP.md','.planning/phases/04-startup-control/04-VALIDATION.md','tests/test_gsd_dod.py'].map(p=>({path:p,sha256:hash(p),mtime_utc:fs.statSync(path.join(root,p)).mtime.toISOString()}));
const additionalEvidence=['red-native/child.json','ruff-corrected/ruff-check-native.txt','ruff-corrected/ruff-format-native.txt'].map(p=>({path:p,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,p))).digest('hex')}));
const report={changed_inputs:changed,original_input_count:Object.keys(original).length,product_inputs_unchanged:!changed.some(p=>p.startsWith('pagefolio/')),original_failure_log_unchanged:originalLogMatches,original_failure_log_sha256:expected,dod_sources:dodSources,additional_evidence:additionalEvidence};
fs.writeFileSync(path.join(__dirname,'final-scope.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
