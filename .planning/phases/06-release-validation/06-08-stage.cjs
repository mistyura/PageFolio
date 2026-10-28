// 既存dirtyを戻さず、今回担当したCR-03/06-08だけをindexへ組み立てる。
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const git=(...args)=>cp.execFileSync('git',args,{cwd:root,encoding:'utf8',windowsHide:true});
const mode=process.argv[2];
if(!['cr03','scope'].includes(mode))throw Error('cr03 or scope required');
if(git('diff','--cached','--name-only').trim())throw Error('preserve existing index');
if(git('branch','--show-current').trim()!=='feature/v1.10.0')throw Error('unexpected branch');
const tmp=path.join(root,'.planning/tmp/06-08-stage-'+mode);fs.mkdirSync(tmp,{recursive:true});
const patches=[];
const live=file=>fs.readFileSync(path.join(root,file),'utf8');
function stage(file,transform){
 const original=git('show','HEAD:'+file),candidate=transform(original);
 const before=path.join(tmp,'old'),after=path.join(tmp,'new');fs.writeFileSync(before,original);fs.writeFileSync(after,candidate);
 const diff=cp.spawnSync('git',['diff','--no-index','--no-ext-diff','--',before,after],{cwd:root,encoding:'utf8',windowsHide:true});
 if(diff.status!==1)throw Error('expected isolated change: '+file);
 patches.push(diff.stdout.split(/\r?\n/).map(line=>line.startsWith('diff --git ')?`diff --git a/${file} b/${file}`:line.startsWith('--- ')?`--- a/${file}`:line.startsWith('+++ ')?`+++ b/${file}`:line).join('\n'));
}
const history='開発履歴.md';
const section=live(history).split('## v1.10.2')[1].split('\n## v1.10.1')[0];
const scopedLine=section.split('\n').find(line=>line.startsWith('- Phase 6 の案B'));
const guarantee=live('README.md').split('\n').find(line=>line.startsWith('- 今回のリリース保証は'));
if(!scopedLine||!guarantee)throw Error('scope text missing');
if(mode==='cr03'){
 for(const file of ['README.md','distribution/はじめに.md'])stage(file,()=>live(file).replace(guarantee+'\n',''));
 stage(history,text=>{
  const ownSection='## v1.10.2'+section.split('\n').filter(line=>!line.startsWith('- Phase 6 の案B')&&!line.startsWith('- Phase 4 の既存受入')).join('\n');
  const firstHeading=text.indexOf('\n## ');if(firstHeading<0)throw Error('history heading missing');
  const candidate=text.slice(0,firstHeading)+'\n'+ownSection+'\n'+text.slice(firstHeading);
  const footer=live(history).split('\n').find(line=>line.startsWith('> **最終更新**: v1.10.2'));
  if(!footer)throw Error('current version footer missing');
  return candidate.replace(/^> \*\*最終更新\*\*:.*$/m,footer);
 });
 stage('tests/test_release_contract.py',text=>text.replace('test_app_version_is_v1_10_0','test_app_version_is_v1_10_2').replace('assert app_version() == "v1.10.0"','assert app_version() == "v1.10.2"'));
}else{
 if(!git('show','HEAD:pagefolio/constants.py').includes('APP_VERSION = "v1.10.2"'))throw Error('CR-03 commit required first');
 stage('README.md',text=>text.replace('### 保証範囲と未実施の確認\n\n','### 保証範囲と未実施の確認\n\n'+guarantee+'\n'));
 stage('distribution/はじめに.md',text=>text.replace('## 保証範囲\n\n','## 保証範囲\n\n'+guarantee+'\n'));
 stage(history,text=>text.replace('- APP_VERSION・README・配布手順の版表記を v1.10.2 に同期。',scopedLine+'\n- APP_VERSION・README・配布手順の版表記を v1.10.2 に同期。'));
 stage('tests/test_release_contract.py',()=>live('tests/test_release_contract.py'));
}
const patch=path.join(tmp,'owned.patch');fs.writeFileSync(patch,patches.join('\n'));
git('apply','--cached','--check',patch);git('apply','--cached',patch);
if(mode==='cr03')git('add','--','pagefolio/constants.py','pagefolio/ocr_dialog.py','tests/test_ocr.py','tests/test_ocr_dialog_provider_refresh.py');
git('diff','--cached','--check');console.log(git('diff','--cached','--stat'));
