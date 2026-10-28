// 既存の未コミット差分を保持し、案Bに属する差分だけをindexへ適用する。
const fs=require('node:fs'), path=require('node:path'), cp=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const git=(...args)=>cp.execFileSync('git',args,{cwd:root,encoding:'utf8',windowsHide:true});
if(git('diff','--cached','--name-only').trim()) throw Error('index is not empty; preserve existing staging');
if(git('branch','--show-current').trim()!=='feature/v1.10.0') throw Error('unexpected branch');
const temp=path.join(root,'.planning/tmp/06-07-stage');fs.mkdirSync(temp,{recursive:true});
const phase='.planning/phases/06-release-validation/';
const live=JSON.parse(fs.readFileSync(path.join(root,phase+'06-MANUAL-EVIDENCE.json')));
const changes=[];
const stage=(file,transform)=>{
 const original=git('show','HEAD:'+file);const candidate=transform(original);
 const old=path.join(temp,'old'), fresh=path.join(temp,'new');
 fs.writeFileSync(old,original);fs.writeFileSync(fresh,candidate);
 const diff=cp.spawnSync('git',['diff','--no-index','--no-ext-diff','--',old,fresh],{cwd:root,encoding:'utf8',windowsHide:true});
 if(diff.status!==1) throw Error('expected nonempty isolated diff');
 const patch=diff.stdout.split(/\r?\n/).map(line=>line.startsWith('diff --git ')?`diff --git a/${file} b/${file}`:line.startsWith('--- ')?`--- a/${file}`:line.startsWith('+++ ')?`+++ b/${file}`:line).join('\n');
 changes.push(patch);
};
stage(phase+'06-MANUAL-EVIDENCE.json', text=>{
 const data=JSON.parse(text);data.release_scope=live.release_scope;
 for(const c of data.cases) for(const s of c.subrows){
  const current=live.cases.find(x=>x.id===c.id).subrows.find(x=>x.subrow===s.subrow);
  s.release_requirement=current.release_requirement;
  if(current.release_requirement==='deferred'){s.approval_id=current.approval_id;s.deferred_reason=current.deferred_reason;}
 }
 return JSON.stringify(data,null,2)+'\n';
});
stage(phase+'06-UAT.md',text=>{
 const note='今回の保証対象外（release_requirement=deferred、承認W11-B-20261028）。status=not-runのまま保持する。別セッションの動作は未確認で、下記は将来保証を拡大する際の受入条件。今回のpassへ換算しない。';
 text=text.replace('## 受入対象と進め方','## 承認済みの保証範囲\n\n案B（W11-B-20261028）によりWindowsの単一ログインセッション利用に限定する。31ケース/110行を保持し、W11の別セッション2行はnot-run/deferred、他108行と品質・安全条件は必須。承認記録は06-W11-SCOPE-APPROVAL.md、機械契約は06-RELEASE-SCOPE.json。未実施を合格へ換算しない。\n\n## 受入対象と進め方');
 for(const entry of ['script','production-exe'])text=text.replace(`### W11/other-session@${entry}`,`### W11/other-session@${entry}\n\n${note}`);
 return text;
});
const testFile='tests/test_release_contract.py';
const diff=git('diff','--',testFile);const chunks=diff.split(/(?=^@@ )/m);
if(chunks.length!==4 || !chunks[1].includes('test_app_version_is_v1_10_2'))throw Error('unexpected test-contract hunks');
changes.push(chunks[0]+chunks.slice(2).join(''));
const patchPath=path.join(temp,'scope-only.patch');fs.writeFileSync(patchPath,changes.join('\n'));
git('apply','--cached','--check',patchPath);git('apply','--cached',patchPath);
git('add','--','tests/release_uat_support.py','tests/test_release_uat_support.py',phase+'06-RELEASE-SCOPE.json',phase+'06-W11-SCOPE-APPROVAL.md');
console.log(git('diff','--cached','--stat'));
