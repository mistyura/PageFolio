const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const dir = __dirname;
const root = path.resolve(dir, '../../..');
const read = p => JSON.parse(fs.readFileSync(path.join(dir,p),'utf8'));
const write = (p,v) => fs.writeFileSync(path.join(dir,p),JSON.stringify(v,null,2)+'\n');
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const old = read('06-BUILD-EVIDENCE.json');
if (old.generation !== 3) throw Error('expected generation 3');
const fresh = read('06-04g4-BUILD-RAW.json');
if (fresh.version !== 'v1.10.2' || fresh.final_release.runs.length !== 2 ||
    fresh.final_release.runs.some(r=>r.cli_exit!==0 || r.pyinstaller_exit!==0) ||
    Object.values(fresh.final_release.bundled_matches_canonical).some(v=>!v) ||
    !fresh.old_dist.unchanged || !fresh.final_release.history_matches_initial_tree) throw Error('build evidence incomplete');
const cli = 'C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs';
const dependency = {};
for (const [num,name,score] of [['04','startup-control','21/21'],['05','config-notification','23/23']]) {
  const phaseDir = `.planning/phases/${num}-${name}`;
  const verdict = JSON.parse(cp.execFileSync(process.execPath,[cli,'query','verification.status',phaseDir],{cwd:root,windowsHide:true,encoding:'utf8'}));
  if (verdict.status !== 'passed') throw Error(`${num} is not fresh passed`);
  const report = `${phaseDir}/${num}-VERIFICATION.md`;
  const digest = fs.readFileSync(path.join(root,report),'utf8').match(/^covered_digest: "([^"]+)"/m)[1];
  dependency[`phase${Number(num)}`] = {verification_status:'passed',result:score,covered_digest:digest,verification_report:report,verification_report_sha256:hash(path.join(root,report)),status_command:'gsd-tools query verification.status '+phaseDir,w_human_items:'Phase6の未実施受入はnot-runを維持'};
}
const qualityPath = '.planning/debug/ocr-off-summary-evidence/native-20261028/result.json';
const q = JSON.parse(fs.readFileSync(path.join(root,qualityPath),'utf8'));
if (q.code !== 0 || q.changed.length) throw Error('quality failed');
// 検証ゲートの追記文書以外の実装/試験/依存入力を再照合する。
const changed = Object.keys(q.after).filter(p=>/^(pagefolio[\\/]|tests[\\/]|tools[\\/]|pagefolio\.py$|requirements\.txt$|pyproject\.toml$)/.test(p) && hash(path.join(root,p))!==q.after[p]);
if(changed.length) throw Error('quality inputs changed: '+changed.join(','));
for(const name of ['06-BUILD-EVIDENCE.json','06-PROTECTION-EVIDENCE.json','06-MANUAL-EVIDENCE.json','06-UAT.md','06-UAT-PREPARATION.md']) {
  fs.copyFileSync(path.join(dir,name),path.join(dir,'06-04g4-preserved-'+name),fs.constants.COPYFILE_EXCL);
}
const prior = {...old}; delete prior.previous_generations;
fresh.generation=4;
fresh.generation_note='CR-03修正v1.10.2。旧世代の原本・失敗・未実施を保持し、旧観測を新hashへ結び替えない。';
fresh.previous_generations=[...(old.previous_generations||[]),{generation:3,status:'superseded',superseded_reason:'CR-03修正・v1.10.2により新世代で再検証',evidence:prior}];
fresh.dependency=dependency;
fresh.quality={current_gate_status:'passed',ruff_check:'All checks passed (--no-cache)',ruff_format:'138 files unchanged (--no-cache)',ast:'OK',pytest:{result:'2083 passed, 2 warnings in 463.98s',exit:0,passed:2083,failed:0,errors:0,skipped:0,single_process:true,excluded:false,crashed:false,log:'.planning/debug/ocr-off-summary-evidence/native-20261028/stdout.txt',evidence:qualityPath,reuse:{product_test_configuration_unchanged:true,changed_inputs:changed}}};
write('06-BUILD-EVIDENCE.json',fresh);
const manual=read('06-MANUAL-EVIDENCE.json');
const previousManual={...manual}; delete previousManual.previous_generations;
manual.previous_generations=[...(manual.previous_generations||[]),{generation:3,status:'superseded',superseded_reason:'CR-03修正に伴う世代4移行',evidence:previousManual}];
manual.generation=4;
manual.updated_at=new Date().toISOString();
manual.target={version:fresh.version,role:'final-release-candidate',exe_sha256:fresh.final_release.exe_sha256,tree_sha256:fresh.final_release.tree_sha256,input_manifest_sha256:fresh.final_release.input_manifest_sha256,final_run_id:fresh.final_release.runs.find(r=>r.order==='rebuild').run_id,final_dir:fresh.final_release.final_dir};
for(const item of manual.cases) for(const row of item.subrows) {
  if(row.status!=='not-run') throw Error('unexpected current pass: preserve before migration');
  row.generation=4;
  row.preparation={status:'not-prepared',note:'世代4の保護/接続実証後に準備する。旧観測は原本保持。'};
  if('expected_binary_sha256' in row) row.expected_binary_sha256=manual.target.exe_sha256;
}
write('06-MANUAL-EVIDENCE.json',manual);
let cards=fs.readFileSync(path.join(dir,'06-UAT.md'),'utf8');
const tableStart=cards.indexOf('| 主対象(final-release-candidate)');
const tableEnd=cards.indexOf('| 相手側tracer',tableStart);
cards=cards.slice(0,tableStart)+`| 主対象(final-release-candidate) | 実配布EXE ${fresh.version} / EXE sha256 \`${manual.target.exe_sha256}\` |\n| tree sha256 | \`${manual.target.tree_sha256}\` |\n| 隔離元(直接起動しない) | \`${manual.target.final_dir}\` |\n`+cards.slice(tableEnd);
fs.writeFileSync(path.join(dir,'06-UAT.md'),cards);
console.log(JSON.stringify({generation:4,version:fresh.version,dependency:Object.keys(dependency),subrows:manual.cases.reduce((n,c)=>n+c.subrows.length,0)}));
