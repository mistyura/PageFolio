// W12cの本人起動/実入力証拠。未取得EXE内部APIをpassへ昇格させない。
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const phase=__dirname, root=path.resolve(phase,'../../..');
const check=(v,s)=>{if(!v)throw Error(s);};
const raw=p=>fs.readFileSync(p), json=p=>JSON.parse(raw(p).toString('utf8'));
const sha=v=>crypto.createHash('sha256').update(v).digest('hex');
const stamp=v=>{const n=Date.parse(v);check(Number.isFinite(n),'時刻不正');return n;};
const consent=new Set(['採用','採用。','採用してよい','採用してよい。']);
const rows=new Set(['explorer-python@script','terminal-python@script',
  'explorer-exe@production-exe','terminal-exe@production-exe']);
const dry=process.argv.includes('--dry-run');
check(process.argv.length===(dry?4:3),'usage: answer.json [--dry-run]');
const name=process.argv[2];
check(/^W12c_(explorer|terminal)-(python|exe)_at_(script|production-exe)-\d{8}T\d{6}Z\.json$/.test(name||''),'回答名不正');
const evidence=path.join(phase,'06-05-evidence');
const safe=(base,relative)=>{
  check(typeof relative==='string'&&relative&&!path.isAbsolute(relative)&&
    !relative.includes('\\')&&!relative.split('/').includes('..'),'相対path不正');
  const full=path.resolve(base,relative);
  check(full.startsWith(path.resolve(base)+path.sep)&&
    fs.realpathSync.native(full).startsWith(fs.realpathSync.native(base)+path.sep)&&
    !fs.lstatSync(full).isSymbolicLink(),'範囲外path/link');
  return full;
};
const answerPath=safe(evidence,name), answerRaw=raw(answerPath), a=JSON.parse(answerRaw.toString('utf8'));
check(a.schema==='w12c-answer-v1'&&rows.has(a.condition)&&a.row===`W12c/${a.condition}`&&
  name.startsWith(`W12c_${a.condition.split('@')[0]}_at_${a.condition.split('@')[1]}-`),
  '対象W12c行不一致');
const run=path.resolve(a.run||''), tmp=path.join(root,'.planning/tmp');
check(run.startsWith(tmp+path.sep)&&/^(pagefolio-uat|release-uat)-[0-9a-f]{32}$/.test(path.basename(run))&&
  fs.realpathSync.native(run).startsWith(fs.realpathSync.native(tmp)+path.sep)&&
  !fs.lstatSync(run).isSymbolicLink(),'run範囲外');
const machinePath=safe(run,'w12c-machine.json'), machineRaw=raw(machinePath), m=JSON.parse(machineRaw.toString('utf8'));
const [route,kind]=a.condition.split('@')[0].split('-');
check(sha(machineRaw)===a.machine_sha256&&m.schema==='w12c-machine-v1'&&
  m.row===a.row&&m.run===run&&m.route===route&&m.kind===kind&&
  m.entry===a.condition.split('@')[1]&&!m.error&&!m.stop_error&&
  m.provenance_after_stop?.matched===true,'機械採取/回収不一致');
check(kind==='python'&&m.api_return?.status!=='unsupported',
  'EXE内部API戻り未取得/unsupported。正式採用不可');
const steps=m.events?.map(e=>e.step).join(',');
check(steps==='start,input-preparation,peer-observed,foreground,input-observed,inspect,stop'&&
  m.events.every(e=>e.at)&&m.events.every((e,i)=>i===0||stamp(m.events[i-1].at)<=stamp(e.at))&&
  stamp(m.events[1].at)-stamp(m.events[0].at)>=19000&&
  stamp(m.events.at(-1).at)<=stamp(m.finished_at),'操作/回収時系列不一致');
const owner=m.owner;
const ownerAfterCreated=machineRaw.toString('utf8').match(/"owner_after_peer"\s*:\s*\{[\s\S]*?"created"\s*:\s*(\d+)/)?.[1];
check(Number.isInteger(owner?.pid)&&owner.pid>0&&/^\d{15,20}$/.test(owner.created)&&
  m.owner_after_peer?.pid===owner.pid&&m.owner_after_peer?.alive===true&&
  ownerAfterCreated===owner.created&&
  m.input_target_before?.pid===owner.pid&&m.input_target_before?.hwnd>0&&
  m.input_target_after?.pid===owner.pid&&
  m.input_target_after?.hwnd===m.input_target_before.hwnd&&
  m.actual_foreground?.hwnd>0,'一次身元/実入力先/実foreground不一致');
const manifestPath=safe(run,'manifest.json'), manifestRaw=raw(manifestPath), manifest=JSON.parse(manifestRaw.toString('utf8'));
const exact=bytes=>bytes.toString('utf8').match(/"process_created"\s*:\s*(\d+)/)?.[1];
check(manifest.run===run&&manifest.w12a_schema==='w12a-v1'&&
  manifest.w12a_primary==='script'&&manifest.w12b_mixed===true&&
  manifest.namespace==='fixed-production'&&manifest.expected_owner?.pid===owner.pid&&
  exact(manifestRaw)===owner.created&&
  m.stop?.['result.json']?.result==='primary'&&
  m.inspection?.originals_unchanged===true&&
  m.owner_after_peer.session_id===manifest.environment?.session_id&&
  JSON.stringify(manifest.formal_provenance?.source_inputs)===JSON.stringify(m.provenance.source_inputs)&&
  JSON.stringify(manifest.formal_provenance?.original_plugins)===JSON.stringify(m.provenance.original_plugins)&&
  JSON.stringify(manifest.formal_provenance?.phase04)===JSON.stringify(m.provenance.phase04)&&
  JSON.stringify(manifest.originals_before)===JSON.stringify(m.provenance.originals)&&
  json(safe(run,'provenance-before-stop.json')).matched===true&&
  json(safe(run,'inspection.json')).originals_unchanged===true,
  '一次実Python/固定namespace/停止不一致');
const peerPath=path.resolve(m.peer_fixture||'');
check(peerPath.startsWith(run+path.sep)&&/^peer-[0-9a-f]{32}$/.test(path.basename(peerPath))&&
  fs.realpathSync.native(peerPath).startsWith(fs.realpathSync.native(run)+path.sep),
  '二次fixture範囲外');
const peerRel=path.basename(peerPath), auditRaw=raw(safe(run,`${peerRel}/resource-audit.json`));
const auditTime=fs.statSync(safe(run,`${peerRel}/resource-audit.json`)).mtimeMs;
const resultTime=fs.statSync(safe(run,`${peerRel}/result.json`)).mtimeMs;
check(auditTime>=stamp(m.events[1].at)&&auditTime<=stamp(m.events[2].at)+1000&&
  resultTime>=stamp(m.events[1].at)&&resultTime<=stamp(m.events[2].at)+1000,
  '二次実行物と本人起動時序不一致');
const audit=JSON.parse(auditRaw.toString('utf8'));
const peerCreated=auditRaw.toString('utf8').split('"verified_owner"')[0].match(/"process_created"\s*:\s*(\d{15,20})/)?.[1];
const result=json(safe(run,`${peerRel}/result.json`));
const expectedRaw=raw(safe(run,`${peerRel}/expected-owner.json`));
const expected=JSON.parse(expectedRaw.toString('utf8'));
check(result.constructed===0&&['completed','foreground_denied'].includes(result.result)&&
  expected.pid===owner.pid&&exact(expectedRaw)===owner.created&&
  audit.owner_result==='existing'&&audit.verified_owner?.pid===owner.pid&&
  auditRaw.toString('utf8').match(/"verified_owner"\s*:\s*\{[\s\S]*?"process_created"\s*:\s*(\d+)/)?.[1]===owner.created&&
  Number.isInteger(audit.pid)&&audit.pid!==owner.pid&&
  peerCreated&&peerCreated!==owner.created&&
  audit.allow_foreground?.pid===owner.pid&&typeof audit.allow_foreground.allowed==='boolean'&&
  Number.isInteger(audit.allow_foreground.os_error)&&
  JSON.stringify(m.peer_identity)===JSON.stringify(audit)&&
  JSON.stringify(m.peer_result)===JSON.stringify(result)&&
  JSON.stringify(m.api_return)===JSON.stringify(audit.allow_foreground),
  '実Python二次/API監査/FILETIME不一致');
const artifact=m.launch_route;
check(artifact?.route===route&&artifact.kind===kind&&
  path.resolve(artifact.target||'')===path.join(root,'.venv/Scripts',
    route==='explorer'?'pythonw.exe':'python.exe')&&
  /^[0-9a-f]{64}$/.test(artifact.target_sha256||'')&&
  artifact.target_sha256===sha(raw(safe(root,`.venv/Scripts/${route==='explorer'?'pythonw.exe':'python.exe'}`)))&&
  artifact.arguments?.join('\n')===[path.join(root,'tests/test_startup_windows.py'),
    '_test_scenario_bootstrap',peerPath,'fixed-production','entry-script'].join('\n'),
  '二次実入口/経路準備不一致');
if(route==='explorer'){
  check(path.resolve(artifact.shortcut||'')===path.join(run,'W12c-Python.lnk')&&
    artifact.shortcut_sha256===sha(raw(safe(run,'W12c-Python.lnk'))),'Explorer shortcut原本不一致');
}else{
  const quote=v=>`'${String(v).replaceAll("'","''")}'`;
  const expectedCommand='& '+[artifact.target,...artifact.arguments].map(quote).join(' ');
  check(artifact.terminal_command===expectedCommand,
    '端末実行コマンド欠落');
}
const walk=(base,relative='',suffix=null)=>{
  const found=[];
  const visit=rel=>{
    for(const item of fs.readdirSync(rel?safe(base,rel):base,{withFileTypes:true})){
      check(!item.isSymbolicLink(),'入力treeにsymlink');
      const key=rel?`${rel}/${item.name}`:item.name;
      if(item.isDirectory())visit(key);
      else if(item.isFile()&&(!suffix||item.name.endsWith(suffix)))found.push(key);
      else if(!item.isFile())throw Error('入力tree特殊ファイル');
    }
  };visit(relative);return found.sort();
};
const sourceNames=['pagefolio.py','.planning/phases/06-release-validation/06-05-w12a-driver.py'];
for(const dir of ['pagefolio','tests'])sourceNames.push(...walk(root,dir,'.py').filter(n=>!n.split('/').includes('__pycache__')));
const p=m.provenance, sources=p?.source_inputs;
check(sources&&sourceNames.sort().join('\n')===Object.keys(sources).sort().join('\n')&&
  sourceNames.every(k=>sha(raw(safe(root,k)))===sources[k]),'現行Python全集合/hash不一致');
const collectors=fs.readdirSync(phase,{withFileTypes:true}).filter(x=>x.name.startsWith('06-05-')&&
  (x.name.endsWith('.py')||x.name.endsWith('.cjs'))).map(x=>{
    check(x.isFile()&&!x.isSymbolicLink(),'collector link不正');
    return `.planning/phases/06-release-validation/${x.name}`;
  }).sort();
check(p.collector_inputs&&collectors.join('\n')===Object.keys(p.collector_inputs).sort().join('\n')&&
  collectors.every(k=>sha(raw(safe(root,k)))===p.collector_inputs[k])&&
  p.helper_sha256===sha(raw(__filename))&&
  p.w12b_helper_sha256===sha(raw(path.join(phase,'06-05-record-w12b.cjs')))&&
  p.collection_doc_sha256===sha(raw(path.join(phase,'06-W12C-COLLECTION.md'))),
  'collector/helper全集合/hash不一致');
check(Object.keys(p.python_executables||{}).sort().join(',')==='python.exe,pythonw.exe'&&
  ['python.exe','pythonw.exe'].every(n=>
    p.python_executables[n]===sha(raw(safe(root,`.venv/Scripts/${n}`))))&&
  artifact.target_sha256===p.python_executables[route==='explorer'?'pythonw.exe':'python.exe'],
  '開始時Python実行体hash不一致');
check(['pagefolio_settings.json','ocr_custom_prompt.md','ocr_summary_prompt.md'].every(n=>
  p.originals?.[n]===(fs.existsSync(path.join(root,n))?sha(raw(path.join(root,n))):null)),
  '元設定/2prompt変化');
const pluginRoot=path.join(root,'plugins'), pluginFiles=fs.existsSync(pluginRoot)?walk(pluginRoot):[];
check(pluginFiles.join('\n')===Object.keys(p.original_plugins||{}).sort().join('\n')&&
  pluginFiles.every(k=>sha(raw(safe(pluginRoot,k)))===p.original_plugins[k]),'元plugins変化');
const reportRaw=raw(path.join(root,'.planning/phases/04-startup-control/04-VERIFICATION.md'));
check(p.phase04?.status==='passed'&&sha(reportRaw)===p.phase04.report_sha256&&
  reportRaw.toString('utf8').match(/^covered_digest: "([^"]+)"\r?$/m)?.[1]===p.phase04.covered_digest,
  '親Phase04報告不一致');
const gsd=path.join(process.env.USERPROFILE||'','.codex/gsd-core/bin/gsd-tools.cjs');
check(fs.existsSync(gsd),'親fresh CLIなし');
const gate=JSON.parse(execFileSync(process.execPath,[gsd,'query','verification.status',
  path.join(root,'.planning/phases/04-startup-control'),'--raw'],
  {cwd:root,encoding:'utf8',timeout:15000}));
check(gate.status==='passed','親Phase04 freshでない');
const build=json(path.join(phase,'06-BUILD-EVIDENCE.json'));
check(build.generation===5&&build.version==='v1.10.2','世代5不一致');
const finalDist=path.resolve(build.final_release.loss_incident?.restored_final_dir||build.final_release.final_dir);
check(!fs.lstatSync(finalDist).isSymbolicLink(),'最終配布root link');
const files=walk(finalDist), hashes=Object.fromEntries(files.map(k=>[k,sha(raw(safe(finalDist,k)))]));
const dirs=[];const collectDirs=rel=>{for(const item of fs.readdirSync(rel?safe(finalDist,rel):finalDist,{withFileTypes:true})){
  check(!item.isSymbolicLink(),'最終配布link');if(item.isDirectory()){const k=rel?`${rel}/${item.name}`:item.name;dirs.push(k);collectDirs(k);}
}};collectDirs('');
check(hashes['PageFolio.exe']===build.final_release.exe_sha256&&
  sha(Buffer.from(JSON.stringify({dirs:dirs.sort(),files:hashes})))===build.final_release.tree_sha256,
  '最終配布tree/hash変化');
const human=a.direct_answer;
const routeWord=route==='explorer'?'Explorer':'端末';
check(human?.source==='user-direct'&&human.row===a.row&&
  human.text===`${a.row}: ${routeWord}から起動した/同じ入力先に実入力した/画面は1つ`&&
  human.source_ref?.trim()&&human.observations?.launch_route===route&&
  human.observations?.real_input_target_kept==='はい'&&
  human.observations?.one_primary_screen==='はい'&&
  stamp(human.captured_at)>stamp(m.finished_at), '回収後の利用者直接観察回答不足');
const adoption=a.adoption;
check(adoption?.decision==='採用'&&adoption.approved_by==='利用者'&&
  adoption.source==='user-direct'&&adoption.source_ref?.trim()&&
  adoption.source_ref!==human.source_ref&&consent.has(adoption.text?.trim())&&
  adoption.answer_sha256===sha(Buffer.from(human.text))&&
  stamp(adoption.approved_at)>Math.max(stamp(human.captured_at),stamp(m.finished_at),
    fs.statSync(manifestPath).mtimeMs,fs.statSync(machinePath).mtimeMs),
  '回収後別承認不足');
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),uatPath=path.join(phase,'06-UAT.md');
const ledger=json(ledgerPath), row=ledger.cases.find(c=>c.id==='W12c')?.subrows.find(r=>r.card===a.row);
check(row?.status==='not-run'&&row.generation===5&&row.entry==='script'&&
  row.condition===`${route}-python`&&row.evidence_kind==='python-real'&&
  row.required_observations?.join(',')==='launch_route,api_return,actual_foreground,real_input_target_kept',
  '正式対象行不一致/既採用');
const uat=raw(uatPath).toString('utf8'), marker=`### ${a.row}`;
const start=uat.indexOf(marker), end0=uat.indexOf('\n### ',start+marker.length);
check(start>=0&&(start===0||uat[start-1]==='\n'),'UAT card欠落');
const end=end0<0?uat.length:end0, card=uat.slice(start,end);
check(card.includes('- **状態**: not-run'),'UAT card既採用');
const count=/本受入は必須108行中(\d+)行pass・(\d+)行not-run・W11対象外2行not-run。/;
check(count.test(uat),'UAT集計欠落');
const target=path.join(evidence,name.replace(/\.json$/,'-raw'));
check(!fs.existsSync(target),'raw上書き禁止');
const inputs=['manifest.json','w12c-machine.json',`${peerRel}/resource-audit.json`,
  `${peerRel}/result.json`,`${peerRel}/expected-owner.json`,
  'entry-owner-script/ready','entry-owner-script/result.json','entry-owner-script/resource-audit.json',
  'inspection.json','provenance-before-stop.json',
  ...(route==='explorer'?['W12c-Python.lnk']:[])];
const copies=inputs.map(n=>({name:n,bytes:raw(safe(run,n))}));
const output={row:a.row,status:'pass',run:path.basename(run),dry_run:dry};
if(dry){console.log(JSON.stringify(output));process.exit(0);}
fs.mkdirSync(target);
const copyManifest=copies.map(({name:n,bytes})=>{
  const dest=path.join(target,n.replaceAll('/','-'));
  fs.writeFileSync(dest,bytes,{flag:'wx'});
  return {source:n,sha256:sha(bytes),target:path.relative(phase,dest).replaceAll('\\','/')};
});
fs.writeFileSync(path.join(target,'copies.json'),JSON.stringify(copyManifest,null,2)+'\n',{flag:'wx'});
row.status='pass';row.preparation={status:'prepared',run_id:path.basename(run),note:'本人の実経路起動を外部監視。'};
row.observations={launch_route:route,api_return:audit.allow_foreground,
  actual_foreground:m.actual_foreground,real_input_target_kept:true};
row.answer=human.text;row.raw_inputs=[{key:'direct_answer',text:human.text,at:human.captured_at},
  {key:'adoption',text:adoption.text,at:adoption.approved_at}];
row.answer_provenance=`${human.source_ref}; 回収後別回答 ${adoption.source_ref}`;
row.run_id=path.basename(run);row.observed_at=human.captured_at;
row.environment=manifest.environment;row.binary_sha256=build.final_release.exe_sha256;
row.input_manifest_sha256=build.final_release.input_manifest_sha256;
row.observation_basis={answer_file:`06-05-evidence/${name}`,answer_sha256:sha(answerRaw),
  raw_copy_manifest:path.relative(phase,path.join(target,'copies.json')).replaceAll('\\','/'),
  owner:{pid:owner.pid,process_created:owner.created},peer_fixture:peerRel,
  source_inputs:sources,collector_inputs:p.collector_inputs,phase04:p.phase04};
const newCard=card.replace(/- \*\*状態\*\*: not-run[^\n]*/,
  `- **状態**: pass / 本人実経路・入力回答と外部証拠を照合。根拠: 06-05-evidence/${name}\n- **回答原文**: ${human.text}`);
check(newCard!==card,'UAT card更新不能');
const nextUat=uat.slice(0,start)+newCard+uat.slice(end);
const nextCount=nextUat.replace(count,(_,pass,notrun)=>
  `本受入は必須108行中${Number(pass)+1}行pass・${Number(notrun)-1}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');
fs.writeFileSync(uatPath,nextCount);
console.log(JSON.stringify(output));
