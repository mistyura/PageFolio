// W12bの外部観測を現行入力と照合し、取得不能なAPI値をpassへ昇格させない。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const phase = __dirname;
const root = path.resolve(phase, '../../..');
const fail = reason => { throw Error(reason); };
const check = (ok, reason) => { if (!ok) fail(reason); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const raw = file => fs.readFileSync(file);
const json = file => JSON.parse(raw(file).toString('utf8'));
const stamp = value => { const t = Date.parse(value); check(Number.isFinite(t), '時刻不正'); return t; };
const consent = new Set(['採用', '採用。', '採用してよい', '採用してよい。']);
const rows = new Set(['exe-exe-samecopy@production-exe','exe-script@production-exe',
  'script-exe@script','exe-module@production-exe','module-exe@module',
  'exe-tracer@production-exe','tracer-exe@tracer',
  'exe-relocated-copy@production-exe','relocated-copy-exe@relocated-copy']);
const dry = process.argv.includes('--dry-run');
check(process.argv.length === (dry ? 4 : 3), 'usage: answer.json [--dry-run]');
const name = process.argv[2];
check(/^W12b_[a-z-]+_at_[a-z-]+-\d{8}T\d{6}Z\.json$/.test(name || ''), '回答ファイル名不正');
const evidence = path.join(phase, '06-05-evidence');
const safe = (base, relative) => {
  check(typeof relative === 'string' && relative && !path.isAbsolute(relative) &&
    !relative.includes('\\') && !relative.split('/').includes('..'), '相対path不正');
  const full = path.resolve(base, relative);
  check(full.startsWith(path.resolve(base) + path.sep) &&
    fs.realpathSync.native(full).startsWith(fs.realpathSync.native(base) + path.sep) &&
    !fs.lstatSync(full).isSymbolicLink(), '範囲外path/link');
  return full;
};
const answerPath = safe(evidence, name);
const answerRaw = raw(answerPath);
const answer = JSON.parse(answerRaw.toString('utf8'));
check(answer.schema === 'w12b-answer-v1' && rows.has(answer.condition) &&
  answer.row === `W12b/${answer.condition}` &&
  name.startsWith(`W12b_${answer.condition.split('@')[0]}_at_${answer.condition.split('@')[1]}-`),
  '対象W12b行不一致');
const run = path.resolve(answer.run || '');
const tmp = path.join(root, '.planning/tmp');
check(run.startsWith(tmp + path.sep) &&
  /^(release-uat|pagefolio-uat)-[0-9a-f]{32}$/.test(path.basename(run)) &&
  fs.realpathSync.native(run).startsWith(fs.realpathSync.native(tmp) + path.sep) &&
  !fs.lstatSync(run).isSymbolicLink(), 'run範囲外');
const machinePath = safe(run, 'w12b-machine.json');
const machineRaw = raw(machinePath);
const m = JSON.parse(machineRaw.toString('utf8'));
check(answer.machine_sha256 === sha(machineRaw) && m.schema === 'w12b-machine-v1' &&
  m.row === answer.row && m.run === run && !m.error && !m.stop_error &&
  m.provenance_after_stop?.matched === true, '機械回収/来歴不一致');
const steps = m.events.map(e=>e.step).join(',');
check(steps === 'start,state-preparation,peer,foreground,direct-answer,inspect,stop' &&
  m.prepeer_seconds===20 &&
  m.events.every(e=>e.at) &&
  m.events.every((e,i)=>i===0 || stamp(m.events[i-1].at)<=stamp(e.at)) &&
  stamp(m.events[1].at)-stamp(m.events[0].at)>=19000 &&
  stamp(m.events.at(-1).at)<=stamp(m.finished_at), '機械時系列/一回性不一致');
check(m.direct_answer_text===`${answer.row}: はい/はい/はい` &&
  stamp(m.direct_answer_at)<stamp(m.events.at(-1).at), 'stop前の直接観察回答欠落');
check(m.api_return?.status!=='unsupported',
  'EXE二次の真の許可API戻りは未取得/unsupported。正式採用不可');

const walk = (base, relative='', suffix=null) => {
  const files = [], dirs = [];
  const visit = rel => {
    const directory = rel ? safe(base, rel) : base;
    for (const item of fs.readdirSync(directory,{withFileTypes:true})) {
      check(!item.isSymbolicLink(), '入力treeにsymlink');
      const key = rel ? `${rel}/${item.name}` : item.name;
      if (item.isDirectory()) { dirs.push(key); visit(key); }
      else if (item.isFile() && (!suffix || item.name.endsWith(suffix))) files.push(key);
      else if (!item.isFile()) fail('入力treeに特殊ファイル');
    }
  };
  visit(relative);
  return {files:files.sort(),dirs:dirs.sort()};
};
const sourceNames = ['pagefolio.py', '.planning/phases/06-release-validation/06-05-w12a-driver.py'];
for (const dir of ['pagefolio','tests']) {
  const tree = walk(root,dir,'.py');
  sourceNames.push(...tree.files.filter(n=>!n.split('/').includes('__pycache__')));
}
const sources = m.provenance?.source_inputs;
check(sources && sourceNames.sort().join('\n')===Object.keys(sources).sort().join('\n') &&
  sourceNames.every(k=>sha(raw(safe(root,k)))===sources[k]), '現行Python入力集合/hash不一致');
const collectors = fs.readdirSync(phase,{withFileTypes:true})
  .filter(x=>x.name.startsWith('06-05-') && (x.name.endsWith('.py') || x.name.endsWith('.cjs')))
  .map(x=>{check(x.isFile()&&!x.isSymbolicLink(),'collector link不正');
    return `.planning/phases/06-release-validation/${x.name}`;}).sort();
const savedCollectors = m.provenance.collector_inputs;
check(savedCollectors && collectors.join('\n')===Object.keys(savedCollectors).sort().join('\n') &&
  collectors.every(k=>sha(raw(safe(root,k)))===savedCollectors[k]) &&
  m.provenance.helper_sha256===sha(raw(__filename)), 'collector/helper来歴不一致');
const originals = m.provenance.originals;
check(['pagefolio_settings.json','ocr_custom_prompt.md','ocr_summary_prompt.md'].every(n=>
  originals?.[n]===(fs.existsSync(path.join(root,n))?sha(raw(path.join(root,n))):null)),
  '元設定/2prompt変化');
const pluginRoot=path.join(root,'plugins');
const pluginFiles=fs.existsSync(pluginRoot)?walk(pluginRoot).files:[];
check(pluginFiles.join('\n')===Object.keys(m.provenance.original_plugins||{}).sort().join('\n') &&
  pluginFiles.every(k=>sha(raw(safe(pluginRoot,k)))===m.provenance.original_plugins[k]),
  '元plugins変化');
const p4=m.provenance.phase04;
const reportPath=path.join(root,'.planning/phases/04-startup-control/04-VERIFICATION.md');
const reportRaw=raw(reportPath);
check(p4.status==='passed' && sha(reportRaw)===p4.report_sha256 &&
  reportRaw.toString('utf8').match(/^covered_digest: "([^"]+)"\r?$/m)?.[1]===p4.covered_digest,
  '親Phase04報告不一致');
const gsd=path.join(process.env.USERPROFILE||'', '.codex/gsd-core/bin/gsd-tools.cjs');
check(fs.existsSync(gsd),'親fresh CLIなし');
const gate=JSON.parse(execFileSync(process.execPath,[gsd,'query','verification.status',
  path.join(root,'.planning/phases/04-startup-control'),'--raw'],
  {cwd:root,encoding:'utf8',timeout:15000}));
check(gate.status==='passed','親Phase04 freshでない');

const build=json(path.join(phase,'06-BUILD-EVIDENCE.json'));
check(build.generation===5 && build.version==='v1.10.2','世代5不一致');
const treeHash = distribution => {
  const tree=walk(distribution);
  const files=Object.fromEntries(tree.files.map(k=>[k,sha(raw(safe(distribution,k)))]));
  return {files,hash:sha(Buffer.from(JSON.stringify({dirs:tree.dirs,files})))};
};
const final=build.final_release;
const finalDist=path.resolve(final.loss_incident?.restored_final_dir||final.final_dir);
check(!fs.lstatSync(finalDist).isSymbolicLink(),'最終配布root symlink');
const finalTree=treeHash(finalDist);
check(finalTree.files['PageFolio.exe']===final.exe_sha256 &&
  finalTree.hash===final.tree_sha256,'最終配布tree変化');
if (answer.condition.includes('tracer')) {
  const t=json(path.join(phase,'06-W12B-NEW-TRACER-20261107.json'));
  const tracerDir=path.join(phase,'06-resume-20261106/w12b-tracer-prepared');
  for (const [key,file] of [['source_manifest_sha256','new-tracer-source-manifest.json'],
    ['external_report_sha256','new-tracer-report.json'],
    ['embedded_report_sha256','new-tracer-embedded-report.json']]) {
    check(t[key]===sha(raw(path.join(tracerDir,file))), 'tracer証拠原本変化');
  }
  const planPath=path.join(tracerDir,'build-plan.json');
  const plan=json(planPath);
  const execution=json(path.join(tracerDir,'build-execution.json'));
  const sourceManifest=json(path.join(tracerDir,'new-tracer-source-manifest.json'));
  check(Object.keys(sourceManifest).length===64 &&
    execution.plan_sha256===sha(raw(planPath)) &&
    execution.source_archive_sha256===plan.source_archive_sha256 &&
    execution.verified_input_count===64 &&
    plan.source_commit===t.source_commit, 'tracer build plan/execution不一致');
  const sourceDir=path.resolve(plan.source_dir);
  check(!fs.lstatSync(sourceDir).isSymbolicLink(),'tracer source symlink');
  check(Object.entries(sourceManifest).every(([key,hash])=>sha(raw(safe(sourceDir,key)))===hash),
    'tracer現行source bytes不一致');
  const startup=raw(safe(sourceDir,'pagefolio/startup_win32.py')).toString('utf8');
  check(['class Win32Backend','AllowSetForegroundWindow','_allow_foreground','Owner','State']
    .every(value=>startup.includes(value)), 'tracer起動排他/固定namespace/protocol source不一致');
  const tracerDist=path.resolve(t.retained_path);
  check(!fs.lstatSync(tracerDist).isSymbolicLink(),'tracer配布root symlink');
  const tracerTree=treeHash(tracerDist);
  check(tracerTree.files['PageFolio.exe']===t.exe_sha256 &&
    JSON.stringify(Object.entries(tracerTree.files).filter(x=>x[0]!=='release-report.json').sort())===
    JSON.stringify(Object.entries(t.distribution_manifest).sort()), 'tracer配布tree変化');
  check(m.tracer_contract?.run_id===t.run_id && m.tracer_contract?.source_commit===t.source_commit &&
    m.tracer_contract?.exe_sha256===t.exe_sha256 &&
    m.tracer_contract?.source_manifest_sha256===t.source_manifest_sha256,
    'tracer別版来歴不一致');
}
const owner=m.owner;
const observedCreated=machineRaw.toString('utf8').match(/"owner_after_peer"\s*:\s*\{[\s\S]*?"created"\s*:\s*(\d+)/)?.[1];
check(Number.isInteger(owner?.pid) && owner.pid>0 && /^\d{15,20}$/.test(owner.created) &&
  observedCreated===owner.created &&
  m.owner_after_peer?.pid===owner.pid && m.owner_after_peer?.alive===true &&
  m.after_peer?.hwnd>0 && m.after_peer?.pid===owner.pid &&
  m.inspection && m.stop, '一次PID/実前景/回収不足');
const runManifestRaw=raw(safe(run,'manifest.json'));
const runManifest=JSON.parse(runManifestRaw.toString('utf8'));
const primaryCreated=runManifestRaw.toString('utf8').match(/"role"\s*:\s*"primary"[\s\S]*?"created"\s*:\s*(\d+)/)?.[1];
const primaryRecord=runManifest.processes?.find(p=>p.role==='primary'&&p.pid===owner.pid);
const finalSnapshot=runManifest.snapshots?.at(-1);
const finalCopy=finalSnapshot?.copy;
check(runManifest.run===run && runManifest.case==='W12b' &&
  runManifest.status==='stopped' && runManifest.source?.exe_sha256===final.exe_sha256 &&
  runManifest.source?.version==='v1.10.2' &&
  runManifest.source?.tree_sha256===final.tree_sha256 &&
  path.resolve(runManifest.copy||'')===path.join(run,'dist') &&
  primaryCreated===owner.created && primaryRecord?.exit &&
  Object.keys(runManifest.overlay||{}).join(',')==='pagefolio_settings.json' &&
  runManifest.overlay['pagefolio_settings.json']===null &&
  runManifest.overlay_log?.some(x=>x.name==='pagefolio_settings.json' && x.sha256===null &&
    stamp(x.at)<stamp(primaryRecord.started_at)) &&
  finalSnapshot?.source_unchanged===true && finalCopy?.ok===true &&
  ['distribution_changed','missing_dirs','extra_dirs','undeclared','locked_unverified'].every(k=>
    Array.isArray(finalCopy[k]) && finalCopy[k].length===0) &&
  Array.isArray(finalCopy.overlay_changed) &&
  finalCopy.overlay_changed.every(k=>k==='pagefolio_settings.json'),
  '一次run/FILETIME/最終配布身元不一致');
const first=m.events[0].owner;
check((first.pid||first.expected_owner?.pid)===owner.pid,'一次記録不一致');
const observed=m.inspection.processes?.find(p=>p.role==='primary');
check(observed?.pid===owner.pid && observed.identity==='same' && observed.alive===true &&
  observed.session_id===m.owner_after_peer.session_id,
  '一次同session/inspect不一致');
const outcome=Array.isArray(m.stop)?m.stop.find(p=>p.pid===owner.pid)?.result:
  m.stop['result.json']?.result;
check(['closed','terminated','primary'].includes(outcome),'一次終了未確認');
const peer=m.peer_identity;
check(peer?.entry==='script'||peer?.entry==='module'||peer?.role==='peer','二次identity欠落');
if (peer.entry==='script'||peer.entry==='module') {
  const fixture=path.resolve(peer.fixture||'');
  check(fixture.startsWith(run+path.sep) && /^peer-[0-9a-f]{32}$/.test(path.basename(fixture)),
    'Python二次fixture範囲外');
  const audit=json(safe(run,`${path.basename(fixture)}/resource-audit.json`));
  const auditRaw=raw(safe(run,`${path.basename(fixture)}/resource-audit.json`));
  const result=json(safe(run,`${path.basename(fixture)}/result.json`));
  const expectedRaw=raw(safe(run,`${path.basename(fixture)}/expected-owner.json`));
  const expected=JSON.parse(expectedRaw.toString('utf8'));
  const expectedCreated=expectedRaw.toString('utf8').match(/"process_created"\s*:\s*(\d+)/)?.[1];
  const verifiedCreated=auditRaw.toString('utf8').match(/"verified_owner"\s*:\s*\{[\s\S]*?"process_created"\s*:\s*(\d+)/)?.[1];
  check(result.constructed===0 && audit.owner_result==='existing' &&
    expected.pid===owner.pid && expectedCreated===owner.created &&
    audit.verified_owner?.pid===owner.pid && verifiedCreated===owner.created &&
    audit.session_id===observed.session_id &&
    Number.isInteger(peer.pid) && peer.pid>0 && peer.pid!==owner.pid &&
    Number.isInteger(audit.pid) && audit.pid>0 && audit.pid!==owner.pid &&
    JSON.stringify(peer.audit)===JSON.stringify(audit) &&
    // venvではPopen.pid(peer.pid)はlauncher。実二次はその直接の子であること。
    (audit.pid===peer.pid || audit.parent_pid===peer.pid) &&
    audit.allow_foreground?.pid===owner.pid &&
    typeof audit.allow_foreground.allowed==='boolean' &&
    Number.isInteger(audit.allow_foreground.os_error) &&
    JSON.stringify(m.api_return)===JSON.stringify(audit.allow_foreground),
    'Python二次API/排他証拠不一致');
} else {
  // EXE内部の戻り値は外部PID/前景やobserverの別API呼出しから推定しない。
  check(false,'EXE二次の真の許可API戻りは未取得/unsupported');
}
const human=answer.direct_answer;
check(human?.source==='user-direct' && human.row===answer.row &&
  human.text===m.direct_answer_text &&
  human.source_ref?.trim() &&
  ['single_primary_screen','same_session_return','primary_state_kept'].every(k=>
    human.observations?.[k]==='はい') &&
  stamp(human.captured_at)>=stamp(m.direct_answer_at) &&
  stamp(human.captured_at)<stamp(m.events.at(-1).at), '利用者直接回答不足');
const adoption=answer.adoption;
check(adoption?.decision==='採用' && adoption.approved_by==='利用者' &&
  adoption.source==='user-direct' && adoption.source_ref?.trim() &&
  adoption.source_ref!==human.source_ref && consent.has(adoption.text?.trim()) &&
  adoption.answer_sha256===sha(Buffer.from(human.text)) &&
  stamp(adoption.approved_at)>Math.max(stamp(m.finished_at),
    fs.statSync(machinePath).mtimeMs,stamp(human.captured_at)), '回収後の別承認不足');
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json');
const ledger=json(ledgerPath);
const row=ledger.cases.find(c=>c.id==='W12b')?.subrows.find(r=>r.card===answer.row);
check(row?.status==='not-run' && row.generation===5 &&
  row.condition===answer.condition.split('@')[0] &&
  row.entry===answer.condition.split('@')[1] &&
  row.evidence_kind==='production-exe' &&
  row.peer?.role==='python-entry' && row.peer.entry===peer.entry &&
  m.primary==='final' && m.secondary===peer.entry &&
  row.required_observations.join(',')===
  'single_primary_screen,same_session_return,primary_state_kept,api_return,actual_foreground,peer_identity' &&
  row.subject?.binary_sha256===final.exe_sha256,'対象台帳行不一致');
const uatPath=path.join(phase,'06-UAT.md');
const uat=raw(uatPath).toString('utf8');
const marker=`### ${answer.row}`;
const start=uat.indexOf(marker);
check(start>=0 && (start===0||uat[start-1]==='\n'),'UAT card欠落');
const next=uat.indexOf('\n### ',start+marker.length);
const end=next<0?uat.length:next;
const card=uat.slice(start,end);
check(card.includes('- **状態**: not-run'),'UAT card既採用');
const target=path.join(evidence,name.replace(/\.json$/,'-raw'));
check(!fs.existsSync(target),'raw上書き禁止');
if (dry) { console.log(JSON.stringify({row:answer.row,status:'validated',dry_run:true})); process.exit(0); }
fs.mkdirSync(target);
const copies=[['w12b-machine.json',machineRaw],['manifest.json',raw(safe(run,'manifest.json'))]];
if (peer.entry==='script'||peer.entry==='module') {
  copies.push([`${path.basename(peer.fixture)}/resource-audit.json`,
    raw(safe(run,`${path.basename(peer.fixture)}/resource-audit.json`))]);
  copies.push([`${path.basename(peer.fixture)}/result.json`,
    raw(safe(run,`${path.basename(peer.fixture)}/result.json`))]);
  copies.push([`${path.basename(peer.fixture)}/expected-owner.json`,
    raw(safe(run,`${path.basename(peer.fixture)}/expected-owner.json`))]);
}
const copied=copies.map(([key,bytes])=>{const file=path.join(target,key.replaceAll('/','-'));
  fs.writeFileSync(file,bytes,{flag:'wx'});
  return {source:key,sha256:sha(bytes),target:path.relative(phase,file).replaceAll('\\','/')};});
fs.writeFileSync(path.join(target,'copies.json'),JSON.stringify(copied,null,2)+'\n',{flag:'wx'});
row.status='pass';
row.preparation={status:'prepared',run_id:path.basename(run),note:'実入口・外部観測・利用者回答照合'};
row.observations={single_primary_screen:true,same_session_return:true,primary_state_kept:true,
  api_return:m.api_return,actual_foreground:m.after_peer,
  peer_identity:{entry:peer.entry,pid:peer.pid,fixture:path.basename(peer.fixture),
    ...(peer.entry==='script'||peer.entry==='module'?
      {audit_pid:peer.audit.pid,audit_parent_pid:peer.audit.parent_pid}:{})}};
row.answer=human.text;
row.raw_inputs=[{key:'direct_answer',text:human.text,at:human.captured_at},
  {key:'adoption',text:adoption.text,at:adoption.approved_at}];
row.answer_provenance=`${human.source_ref}; 回収後別回答: ${adoption.source_ref}`;
row.run_id=path.basename(run); row.observed_at=human.captured_at;
row.environment={os:runManifest.environment?.os,
  elevated:m.owner_after_peer.elevated,session_id:m.owner_after_peer.session_id};
row.binary_sha256=final.exe_sha256;
row.input_manifest_sha256=final.input_manifest_sha256;
row.observation_basis={answer_file:`06-05-evidence/${name}`,answer_sha256:sha(answerRaw),
  raw_copy_manifest:path.relative(phase,path.join(target,'copies.json')).replaceAll('\\','/'),
  owner:{pid:owner.pid,created:owner.created},provenance:m.provenance};
const newCard=card.replace('- **状態**: not-run',
  `- **状態**: pass / 利用者直接回答と実owner/foreground照合。根拠: 06-05-evidence/${name}`);
const passed=ledger.cases.flatMap(c=>c.subrows).filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
const newUat=(uat.slice(0,start)+newCard+uat.slice(end)).replace(
  /本受入は必須108行中\d+行pass・\d+行not-run・W11対象外2行not-run。/,
  `本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');
fs.writeFileSync(uatPath,newUat);
console.log(JSON.stringify({row:answer.row,status:'pass',dry_run:false}));
