// Evidence preservation and ledger recording only. Does not launch a GUI/build or retry.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const phase=__dirname,repo=path.resolve(phase,'../../..');
const out=path.join(phase,'06-CONNECTION-STOP-20261028-evidence');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n');
if(fs.existsSync(out))throw new Error('Preservation directory already exists; do not overwrite first evidence');
fs.mkdirSync(out);
const originals=[];
function preserve(source,dest){
  const info=fs.lstatSync(source);
  if(info.isSymbolicLink())throw new Error('Unexpected link: '+source);
  if(info.isDirectory()){fs.mkdirSync(dest,{recursive:true});for(const n of fs.readdirSync(source))preserve(path.join(source,n),path.join(dest,n));}
  else {fs.mkdirSync(path.dirname(dest),{recursive:true});const before=sha(source);fs.copyFileSync(source,dest);if(sha(source)!==before||sha(dest)!==before)throw new Error('Preservation hash mismatch');originals.push({source,copy:dest,sha256:before,size:info.size});}
}
const baselineFiles=['06-PROTECTION-EVIDENCE.json','06-BUILD-EVIDENCE.json','06-MANUAL-EVIDENCE.json','06-UAT-PREPARATION.md','06-UAT.md','06-RESUME-20261028.md','06-RESUME-CHECKPOINT-20261028.md','.continue-here.md','06-CONNECTION-SANDBOX-NOT-VISIBLE-20261028.json'];
for(const name of baselineFiles)preserve(path.join(phase,name),path.join(out,'before',name));
for(const name of ['STATE.md','state.json'])preserve(path.join(repo,'.planning',name),path.join(out,'before',name));
const root='C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g3_unreadable_8433fc4ee5324234931fb80ac0f310d1/runs';
const runs=[['d04061c65a42406c90736c4a3e183368',null],['0d73a0cdf5b8465f9970b3702c2653e7','ocr-single'],['cf52cf1df4db42a3b384db6f13a6c103','w05b-modal']];
for(const [id] of runs){const dir=path.join(root,'release-uat-'+id);for(const n of fs.readdirSync(dir))if(n!=='dist')preserve(path.join(dir,n),path.join(out,'runs','release-uat-'+id,n));}
write(path.join(out,'original-hashes.json'),{at:new Date().toISOString(),files:originals,note:'distは再copyせず固定配布hashと照合。run metadata/evidence/fixture/overlay-sourceは原本copy。'});
function invoke(args){const r=cp.spawnSync(path.join(repo,'.venv/Scripts/python.exe'),args,{cwd:repo,encoding:'utf8',windowsHide:true,timeout:60000,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONIOENCODING:'utf-8'}});return {exit:r.status,stdout:r.stdout,stderr:r.stderr,error:r.error?.message};}
const build=read(path.join(phase,'06-BUILD-EVIDENCE.json'));
const protPath=path.join(phase,'06-PROTECTION-EVIDENCE.json'),prot=read(protPath);
if(prot.generation!==3||prot.connection.length)throw new Error('Unexpected generation or existing connection rows');
const clarification={recorded_at:new Date().toISOString(),run_id:runs[2][0],kind:'w05b-modal',source:'親担当が受領した利用者チャット原文',question:'2 回目の起動後の見え方を確認させてください。確認ダイアログへ PageFolio が自動で戻りましたか、それとも自分で PageFolio に切り替えて確認しましたか？',user_answer:'自分で PageFolio に切り替えて確認した',interpretation:'最初の「同じ確認ダイアログが前面に戻っている」を自動復帰成功と解釈しない。元sessionの4回答は書き換えず、補足として別保持。自動復帰未実証、製品原因と検証手順の影響は未分離。'};
const clarificationPath=path.join(out,'w05b-user-clarification.json');write(clarificationPath,clarification);
const helper=path.join(phase,'06-04-drivers/assemble_protection.py');
const python='import importlib.util,json,sys; from tests import release_uat_support as S; spec=importlib.util.spec_from_file_location("pf_connection_evidence",sys.argv[1]); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); session=m.load_session(sys.argv[2]); row=m.build_connection(session,sys.argv[3]); print(json.dumps(row,ensure_ascii=False))';
const derived=[];
for(const [id,kind] of runs.filter(x=>x[1])){
  const source=path.join(root,'release-uat-'+id,'evidence','session-'+kind+'.json');
  const session=read(source),r=invoke(['-c',python,helper,source,kind]);
  write(path.join(out,'helper-'+kind+'.json'),r);
  if(r.exit!==0)throw new Error('Existing helper failed: '+kind);
  const row=JSON.parse(r.stdout);
  if(row.binary_sha256!==build.final_release.exe_sha256||row.tree_sha256!==build.final_release.tree_sha256)throw new Error('Binary/tree mismatch');
  row.entry_derived_at=row.observed_at;row.observed_at=session.finished_at;
  row.source_session={path:source,sha256:sha(source),started_at:session.started_at,finished_at:session.finished_at,selftest:session.selftest};
  row.cleanup_note=kind==='ocr-single'?'primary terminatedとstop診断を原文保持。正常終了とは記録しない。':'primary closed、peer already-exited。設定overlayの正当な終了時変化と配布不変を分離。';
  if(kind==='w05b-modal'){
    if(row.peer_returned_to_modal!==false)throw new Error('Expected first mismatch is absent; stop for evidence review');
    row.clarification_ref={path:path.relative(repo,clarificationPath).split(path.sep).join('/'),sha256:sha(clarificationPath)};
    row.preparation_result='not-established';
    row.automatic_return_interpretation='withdrawn-after-user-clarification';
    row.unresolved='同じmodalは存在するが、peer後の実foregroundはChatGPT側。利用者は手動でPageFolioへ切替。自動復帰は未実証。原因・製品関与と回答手順の影響は未確定。';
  }else row.preparation_result='ocr-connection-observed-with-forced-cleanup';
  derived.push(row);
}
prot.connection.push(...derived);
prot.status='blocked-w05b-automatic-return-unverified';
prot.connection_pending=['w05b-modal'];
prot.connection_stop={at:new Date().toISOString(),run_id:runs[2][0],evidence:path.relative(repo,out).split(path.sep).join('/'),reason:'peer_returned_to_modal=false、利用者補足は手動切替。初回不一致で停止。',retry_allowed:false,phase_complete:false,release_allowed:false};
prot.connection_attempts=[{run_id:runs[0][0],kind:'ocr-single',outcome:'aborted-user-cannot-see-window',record:'06-CONNECTION-SANDBOX-NOT-VISIBLE-20261028.json',connection_pass:false,driver_cleanup:'親がPID/作成時刻/command照合後にStop-Processで26332を回収。元記録を保持し、この追補に回収完了を記す。'}];
write(protPath,prot);
let prep=fs.readFileSync(path.join(phase,'06-UAT-PREPARATION.md'),'utf8');
const labels=new Map([...prep.matchAll(/\| run-ref: ([0-9a-f]{32}) \| ([^\r\n]+?) \|/g)].map(m=>[m[1],m[2]]));
function refs(x,where){if(Array.isArray(x))x.forEach((v,i)=>refs(v,where+'['+i+']'));else if(x&&typeof x==='object')for(const[k,v]of Object.entries(x)){if(k==='run_id'&&v&&!labels.has(v))labels.set(v,'証拠参照 '+where);else if(k!=='run_id')refs(v,where+'.'+k);}}
refs(prot,'protection');labels.set(runs[0][0],'[未成立・sandbox画面不可視] ocr-single');labels.set(runs[1][0],'[世代3] ocr-single実接続・primary強制回収');labels.set(runs[2][0],'[世代3・未成立] w05b-modal自動復帰未実証・手動切替補足');
const start='<!-- run-refs:start (assemble_protection.py が生成。手で編集しない) -->',end='<!-- run-refs:end -->';
const a=prep.indexOf(start),b=prep.indexOf(end);if(a<0||b<a)throw new Error('Missing run-ref markers');
const block=[start,'','| run-ref | 用途 |','|---|---|',...[...labels].map(([id,label])=>`| run-ref: ${id} | ${label} |`),'',end].join('\n');
prep=prep.slice(0,a)+block+prep.slice(b+end.length);fs.writeFileSync(path.join(phase,'06-UAT-PREPARATION.md'),prep);
const audit=invoke(['tests/release_uat_support.py','audit','--phase-dir','.planning/phases/06-release-validation','--preparation-only']);
write(path.join(out,'preparation-only.json'),audit);fs.writeFileSync(path.join(out,'preparation-only.stdout.txt'),audit.stdout);fs.writeFileSync(path.join(out,'preparation-only.stderr.txt'),audit.stderr);
const distCheck=invoke(['-c','import json,sys; from tests import release_uat_support as S; d=S.read_distribution(sys.argv[1]); print(json.dumps({"distribution":d,"owner":S.probe_owner(),"pids":{p:S.process_identity(int(p)) for p in sys.argv[2:]}}))',build.final_release.final_dir,'30532','26332','28824','28104','9920','4192']);
write(path.join(out,'distribution-owner-pids.json'),distCheck);
const rawFiles=originals.filter(r=>path.resolve(r.source).startsWith(path.resolve(root)+path.sep));
const preservation={at:new Date().toISOString(),original_run_files:rawFiles.length,original_run_changed:rawFiles.filter(r=>sha(r.source)!==r.sha256),copies_changed:originals.filter(r=>sha(r.copy)!==r.sha256),old_generations_unchanged:JSON.stringify(prot.previous_generations)===JSON.stringify(read(path.join(out,'before/06-PROTECTION-EVIDENCE.json')).previous_generations),manual_unchanged:sha(path.join(phase,'06-MANUAL-EVIDENCE.json'))===sha(path.join(out,'before/06-MANUAL-EVIDENCE.json')),build_unchanged:sha(path.join(phase,'06-BUILD-EVIDENCE.json'))===sha(path.join(out,'before/06-BUILD-EVIDENCE.json')),audit_exit:audit.exit,run_ids:derived.map(r=>r.run_id),release_allowed:false,phase_complete:false};
write(path.join(out,'preservation.json'),preservation);
console.log(JSON.stringify({out,preservation,audit,connections:derived.map(r=>({kind:r.kind,run_id:r.run_id,modal_shown:r.modal_shown,peer_returned_to_modal:r.peer_returned_to_modal,answered_no:r.answered_no,same_request_completed:r.same_request_completed,stop:r.stop}))},null,2));
