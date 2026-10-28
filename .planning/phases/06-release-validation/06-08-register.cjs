const fs=require('node:fs'), path=require('node:path'), cp=require('node:child_process'), crypto=require('node:crypto');
const root=path.resolve(__dirname,'../../..');
const read=n=>JSON.parse(fs.readFileSync(path.join(__dirname,n),'utf8'));
const write=(n,v)=>fs.writeFileSync(path.join(__dirname,n),JSON.stringify(v,null,2)+'\n');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const old=read('06-BUILD-EVIDENCE.json'), fresh=read('06-08-BUILD-RAW.json');
const scopeFreeze=read('06-08-SCOPE-FREEZE.json');
if(scopeFreeze.build_input_digest!==fresh.final_release.input_manifest_sha256)throw Error('scope/build freeze mismatch');
for(const record of Object.values(scopeFreeze.scope))if(hash(record.source)!==record.sha256||hash(record.frozen)!==record.sha256)throw Error('scope freeze changed');
if(old.generation!==4 || fresh.final_release.runs.length!==2 || fresh.final_release.runs.some(r=>r.cli_exit!==0||r.pyinstaller_exit!==0))throw Error('expected generation4 and two successful new runs');
if(Object.values(fresh.final_release.bundled_matches_canonical).some(v=>!v)||!fresh.old_dist.unchanged||!fresh.final_release.history_matches_initial_tree)throw Error('incomplete build evidence');
const qualityPath='.planning/phases/06-release-validation/06-08-evidence/native-docs-20261028/result.json';
const quality=JSON.parse(fs.readFileSync(path.join(root,qualityPath)));
if(quality.code!==0||quality.changed.length)throw Error('quality failed');
const changed=Object.keys(quality.after).filter(p=>hash(p)!==quality.after[p]);
if(changed.length)throw Error('quality input drift: '+changed.join(','));
const dependency={};
for(const [num,name,score] of [['04','startup-control','21/21'],['05','config-notification','23/23']]){
 const phaseDir=`.planning/phases/${num}-${name}`;
 const status=JSON.parse(cp.execFileSync(process.execPath,['C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs','query','verification.status',phaseDir],{cwd:root,windowsHide:true,encoding:'utf8'}));
 if(status.status!=='passed')throw Error('stale dependency '+num);
 const report=`${phaseDir}/${num}-VERIFICATION.md`;
 const digest=fs.readFileSync(path.join(root,report),'utf8').match(/^covered_digest: "([^"]+)"/m)[1];
 dependency[`phase${Number(num)}`]={verification_status:'passed',result:score,covered_digest:digest,verification_report:report,verification_report_sha256:hash(report),status_command:'gsd-tools query verification.status '+phaseDir,w_human_items:'必須108行とW11未確認2行はPhase06で追跡'};
}
const manual=read('06-MANUAL-EVIDENCE.json');
if(manual.cases.reduce((n,c)=>n+c.subrows.length,0)!==110||manual.cases.some(c=>c.subrows.some(s=>s.status!=='not-run')))throw Error('preserve observations: unexpected current acceptance status');
for(const name of ['06-BUILD-EVIDENCE.json','06-PROTECTION-EVIDENCE.json','06-MANUAL-EVIDENCE.json','06-UAT.md','06-UAT-PREPARATION.md'])fs.copyFileSync(path.join(__dirname,name),path.join(__dirname,'06-08-preserved-'+name),fs.constants.COPYFILE_EXCL);
const priorBuild=structuredClone(old);delete priorBuild.previous_generations;
fresh.generation=5;fresh.generation_note='承認済み単一ログインセッション保証を同梱文書へ反映。旧世代の観測を新hashへ付け替えない。';
fresh.previous_generations=[...(old.previous_generations||[]),{generation:4,status:'superseded',superseded_reason:'保証範囲の配布文書更新に伴う世代5',evidence:priorBuild}];
fresh.release_scope=structuredClone(manual.release_scope);
fresh.scope_freeze={path:'.planning/phases/06-release-validation/06-08-SCOPE-FREEZE.json',sha256:hash('.planning/phases/06-release-validation/06-08-SCOPE-FREEZE.json')};
fresh.dependency=dependency;
const logPath='.planning/phases/06-release-validation/06-08-evidence/native-docs-20261028/stdout.txt';
const log=fs.readFileSync(path.join(root,logPath),'utf8');
const result=log.match(/(\d+) passed, (\d+) warnings in ([\d.]+)s/);
if(!result)throw Error('missing full-suite result');
fresh.quality={current_gate_status:'passed',ruff_check:'全体check成功',ruff_format:'同一全140 Pythonファイルを明示して成功',ast:'OK',pytest:{result:result[0],exit:0,passed:Number(result[1]),failed:0,errors:0,skipped:0,single_process:true,excluded:false,crashed:false,log:logPath,log_sha256:hash(logPath),evidence:qualityPath,input_count:Object.keys(quality.after).length}};
const previousManual=structuredClone(manual);delete previousManual.previous_generations;
manual.previous_generations=[...(manual.previous_generations||[]),{generation:4,status:'superseded',superseded_reason:'配布文書更新後の新世代。旧attemptはこの原本に保持',evidence:previousManual}];
manual.generation=5;manual.updated_at=new Date().toISOString();
manual.target={version:fresh.version,role:'final-release-candidate',exe_sha256:fresh.final_release.exe_sha256,tree_sha256:fresh.final_release.tree_sha256,input_manifest_sha256:fresh.final_release.input_manifest_sha256,final_run_id:fresh.final_release.runs.find(r=>r.order==='rebuild').run_id,final_dir:fresh.final_release.final_dir};
for(const c of manual.cases)for(const s of c.subrows){
 s.generation=5;s.preparation={status:'not-prepared',note:s.release_requirement==='deferred'?'承認済み保証対象外。未確認のまま保持。':'世代5の保護・接続確認後に本受入。旧attemptはprevious_generationsに保持。'};
 delete s.attempts;
 if('expected_binary_sha256' in s)s.expected_binary_sha256=manual.target.exe_sha256;
 if(c.id==='W12b'){
  s.subject.binary_sha256=manual.target.exe_sha256;s.subject.version=fresh.version;
  if(s.peer.role==='same-version-copy'){s.peer.binary_sha256=manual.target.exe_sha256;s.peer.version=fresh.version;}
 }
}
let cards=fs.readFileSync(path.join(__dirname,'06-UAT.md'),'utf8');
const start=cards.indexOf('| 主対象(final-release-candidate)'),end=cards.indexOf('| 相手側tracer',start);
if(start<0||end<start)throw Error('target table missing');
cards=cards.slice(0,start)+`| 主対象(final-release-candidate) | 実配布EXE ${fresh.version} / EXE sha256 \`${manual.target.exe_sha256}\` |\n| tree sha256 | \`${manual.target.tree_sha256}\` |\n| 隔離元(直接起動しない) | \`${manual.target.final_dir}\` |\n`+cards.slice(end);
cards=cards.replace('## 現行の観測と未達','## 現行の観測と未達\n\n世代5の実初回/再buildが完了。保護・接続準備は未完了で、本受入は必須108行not-run・W11対象外2行not-run。以下の世代4記録は履歴。');
write('06-BUILD-EVIDENCE.json',fresh);write('06-MANUAL-EVIDENCE.json',manual);fs.writeFileSync(path.join(__dirname,'06-UAT.md'),cards);
console.log(JSON.stringify({generation:5,version:fresh.version,exe:manual.target.exe_sha256,tree:manual.target.tree_sha256,quality:result[0],required:108,deferred:2}));
