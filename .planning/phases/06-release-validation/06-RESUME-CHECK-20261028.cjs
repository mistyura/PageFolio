// Phase 06 resume_contract: read-only identity checks; no build or GUI launch.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const repo = path.resolve(__dirname, '../../..');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const build = read(path.join(__dirname, '06-BUILD-EVIDENCE.json'));
const final = build.final_release;
const report = read(final.runs[1].report_path);
const actual = {};
function files(dir, predicate) {
  for (const item of fs.readdirSync(dir, {withFileTypes: true})) {
    const p = path.join(dir, item.name);
    if (item.isDirectory()) files(p, predicate);
    else if (predicate(p)) actual[path.relative(repo, p).split(path.sep).join('/')] = sha(p);
  }
}
for (const rel of ['pagefolio.py', 'pagefolio.ico', 'requirements.txt', 'tools/build_release.py', 'docs/CONFIGURATION.md']) actual[rel] = sha(path.join(repo, rel));
files(path.join(repo, 'pagefolio'), p => p.endsWith('.py'));
files(path.join(repo, 'distribution'), p => p.endsWith('.md'));
const differences = [...new Set([...Object.keys(report.input_manifest), ...Object.keys(actual)])].filter(k => report.input_manifest[k] !== actual[k]).map(k => ({path:k, recorded:report.input_manifest[k] ?? null, current:actual[k] ?? null}));
function invoke(args) {
  const x = cp.spawnSync(path.join(repo, '.venv/Scripts/python.exe'), args, {cwd:repo, encoding:'utf8', windowsHide:true, timeout:60000, env:{...process.env, PYTHONDONTWRITEBYTECODE:'1', PYTHONIOENCODING:'utf-8'}});
  return {exit:x.status, stdout:x.stdout, stderr:x.stderr, error:x.error?.message};
}
const native = invoke(['-c', 'import json,platform,sys,importlib.metadata as m; from tests import release_uat_support as S; print(json.dumps({"python":sys.version,"executable":sys.executable,"os":platform.platform(),"dependencies":{n:m.version(n) for n in ["PyInstaller","pyinstaller-hooks-contrib","PyMuPDF","Pillow","tkinterdnd2","pytest","ruff"]},"production_owner":S.probe_owner()},ensure_ascii=False))']);
function tree(dir) {
  const data = {};
  function walk(root) {for(const e of fs.readdirSync(root,{withFileTypes:true})){const p=path.join(root,e.name);const s=fs.statSync(p,{bigint:true});data[path.relative(dir,p)]={size:String(s.size),mtimeNs:String(s.mtimeNs),sha256:e.isFile()?sha(p):null};if(e.isDirectory())walk(p);}}
  walk(dir); return data;
}
const before = tree(final.final_dir);
const audit = invoke(['tests/release_uat_support.py','audit','--phase-dir','.planning/phases/06-release-validation','--build-only']);
const after = tree(final.final_dir);
const prot = read(path.join(__dirname, '06-PROTECTION-EVIDENCE.json'));
let prep = fs.readFileSync(path.join(__dirname, '06-UAT-PREPARATION.md'),'utf8');
const refs = [];
function collect(x, where) {if(Array.isArray(x))x.forEach((v,i)=>collect(v,`${where}[${i}]`));else if(x&&typeof x==='object')for(const [k,v] of Object.entries(x)){if(k==='run_id'&&v)refs.push({run_id:v,path:where});else collect(v,`${where}.${k}`);}}
collect(prot,'protection');
if (process.argv.includes('--sync-refs')) {
  // Reconcile every nested historical run ID while preserving existing labels.
  const labels = new Map([...prep.matchAll(/\| run-ref: ([0-9a-f]{32}) \| ([^\r\n]+?) \|/g)].map(m=>[m[1],m[2]]));
  for(const r of refs) if(!labels.has(r.run_id))labels.set(r.run_id,`[過去世代 superseded] ${r.path}`);
  const start='<!-- run-refs:start (assemble_protection.py が生成。手で編集しない) -->';
  const end='<!-- run-refs:end -->';
  const block=[start,'','| run-ref | 用途 |','|---|---|',...[...labels].map(([id,label])=>`| run-ref: ${id} | ${label} |`),'',end].join('\n');
  const a=prep.indexOf(start),b=prep.indexOf(end);
  if(a<0||b<a)throw new Error('run-ref markers are missing');
  prep=prep.slice(0,a)+block+prep.slice(b+end.length);
  fs.writeFileSync(path.join(__dirname,'06-UAT-PREPARATION.md'),prep);
}
const manual = read(path.join(__dirname,'06-MANUAL-EVIDENCE.json'));
const counts = {}; for(const c of manual.cases)for(const r of c.subrows)counts[r.status]=(counts[r.status]||0)+1;
const quality = read(path.join(repo,'.planning/debug/quality-gate-unblock-20261028/full.json'));
const qualityDifferences=Object.entries(quality.before).filter(([k,v])=>!fs.existsSync(path.join(repo,k))||sha(path.join(repo,k))!==v).map(([k,v])=>({path:k,recorded:v,current:fs.existsSync(path.join(repo,k))?sha(path.join(repo,k)):null}));
const freeze=read(path.join(path.dirname(final.output_root),'freeze/freeze.json'));
const parsedNative=native.exit===0?JSON.parse(native.stdout):null;
const t2=path.join('C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g3_unreadable_8433fc4ee5324234931fb80ac0f310d1');
const owned=invoke(['-c', 'import json,pathlib; from tests import release_uat_support as S; root=pathlib.Path(r"'+t2+'"); rows=[(p,S.read_json(p)) for p in (root/"runs").glob("*/manifest.json")]; print(json.dumps({"runs":len(rows),"processes":[{"run_id":m["run_id"],"pid":r["pid"],"created":r["created"],"current":S.process_identity(r["pid"])} for p,m in rows for r in m["processes"]]},ensure_ascii=False))']);
const old=prot.previous_generations[0].evidence.previous_generations[0];
const oldRaw=path.join(__dirname,old.raw_observation_log);
const oldText=fs.readFileSync(oldRaw,'utf8');
const oldRefs=refs.filter(r=>r.path.includes('previous_generations[0].evidence.previous_generations[0]'));
const phase4path=path.join(repo,'.planning/phases/04-startup-control/04-VERIFICATION.md');
const phase4text=fs.readFileSync(phase4path,'utf8');
const phase4status=cp.spawnSync(process.execPath,['C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs','query','verification.status','.planning/phases/04-startup-control'],{cwd:repo,encoding:'utf8',windowsHide:true,timeout:60000});
const preimages=path.join(__dirname,'06-resume-preimages-20261028');
const oldBuild=read(path.join(preimages,'06-BUILD-EVIDENCE.json'));
const oldProtection=read(path.join(preimages,'06-PROTECTION-EVIDENCE.json'));
const result = {at:new Date().toISOString(),build_input_count:Object.keys(actual).length,recorded_input_count:Object.keys(report.input_manifest).length,differences,exe_sha256:sha(path.join(final.final_dir,'PageFolio.exe')),expected_exe_sha256:final.exe_sha256,tree_unchanged_during_audit:JSON.stringify(before)===JSON.stringify(after),build_audit:audit,native,environment_matches_freeze:parsedNative&&parsedNative.python===freeze.python&&JSON.stringify(Object.fromEntries(Object.entries(parsedNative.dependencies).sort()))===JSON.stringify(Object.fromEntries(Object.entries(freeze.dependencies).sort())),build_lock_absent:!fs.existsSync(path.join(final.output_root,'.PageFolio-'+build.version+'.lock')),owned_process_check:owned,quality_reuse:{passed:quality.passed,records:quality.records,execution_changed:quality.changed,current_differences:qualityDifferences,python_count:Object.keys(quality.before).filter(k=>k.endsWith('.py')).length,python_differences:qualityDifferences.filter(v=>v.path.endsWith('.py'))},previous_phase4_dependency:build.dependency,manual_counts:counts,missing_preparation_refs:refs.filter(r=>!prep.includes(r.run_id)),old_generation_reference_check:{raw_path:oldRaw,raw_sha256:sha(oldRaw),root_exists:fs.existsSync(old.old_t2_dir_preserved),unique_run_count:new Set(oldRefs.map(r=>r.run_id)).size,ids_absent_from_original_raw:oldRefs.filter(r=>!oldText.includes(r.run_id))},release_allowed:false,phase_complete:false};
result.current_phase4={digest:(phase4text.match(/^covered_digest:\s*"([^"]+)"/m)||[])[1],report_sha256:sha(phase4path),status_command:{exit:phase4status.status,stdout:phase4status.stdout,stderr:phase4status.stderr},resume_reference_matches:build.resume_verification_20261028?.phase4.report_sha256===sha(phase4path)};
result.preservation={original_build_keys_unchanged:Object.keys(oldBuild).every(k=>JSON.stringify(build[k])===JSON.stringify(oldBuild[k])),original_protection_keys_unchanged:Object.keys(oldProtection).every(k=>JSON.stringify(prot[k])===JSON.stringify(oldProtection[k]))};
result.identity_ready=differences.length===0&&result.exe_sha256===final.exe_sha256&&result.tree_unchanged_during_audit&&audit.exit===0&&result.environment_matches_freeze&&parsedNative.production_owner.length===0&&result.build_lock_absent&&qualityDifferences.every(x=>!x.path.endsWith('.py'))&&result.current_phase4.resume_reference_matches&&phase4status.status===0&&JSON.parse(phase4status.stdout).status==='passed'&&Object.values(result.preservation).every(Boolean);
fs.writeFileSync(path.join(__dirname,'06-RESUME-CHECK-20261028.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
if(!result.identity_ready)process.exitCode=1;
