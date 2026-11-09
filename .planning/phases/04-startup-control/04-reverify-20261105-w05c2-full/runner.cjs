// Phase 04 再検証用の単一全件ランナー（06-07-quality.cjs plan05 と 04-reverify-current.cjs の方式を統合）
// 製品・試験コードは変更しない。ruff format は --check（非破壊）で実行する。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');
const root = 'C:\\Users\\shdwf\\work\\project\\PageFolio';
const run = process.argv[2];
if (!/^[a-z0-9-]+$/.test(run || '')) throw Error('unique run ID required');
const dir = path.join(root, '.planning/phases/04-startup-control', run);
if (fs.existsSync(dir)) throw Error('preserve previous evidence: ' + dir);
fs.mkdirSync(dir, {recursive: true});

// 入力集合: 06-07-quality.cjs plan05 の集合 ∪ 04-reverify-current.cjs の走査集合
const baseline = JSON.parse(fs.readFileSync(path.join(root, '.planning/debug/ocr-off-summary-evidence/native-20261028/before.json')));
const inputs = new Set([...Object.keys(baseline), 'tests/release_uat_support.py', 'tests/test_release_uat_support.py', 'tests/test_release_contract.py', '.ruff.toml', ...['06-RELEASE-SCOPE.json','06-W11-SCOPE-APPROVAL.md','06-MANUAL-EVIDENCE.json','06-UAT.md'].map(n=>'.planning/phases/06-release-validation/'+n)]);
for (const f of ['tests/w05c_evidence.py','tests/test_w05c_evidence.py','.gitignore','tests/w05c_runner.py','tests/test_w05c_runner.py']) inputs.add(f);
for (const n of ['06-05-w05c-v3.cjs','06-05-record-w05c-python.cjs','06-05-w05c-evidence.cjs','06-05-record-w03-python.cjs','06-05-record-w04.cjs','06-05-record-w05b.cjs','06-05-record-w05b-attempt.cjs','06-07-quality.cjs','06-05-record-w01-python.cjs','06-05-record-w01-exe.cjs','06-05-record-w02-attempt.cjs','06-05-record-w02-settings.cjs','06-05-record-w02-exe.cjs','06-05-record-w02-exe-attempt.cjs','06-05-drivers/uat_row.py']) inputs.add('.planning/phases/06-release-validation/'+n);
inputs.add('.planning/debug/w01-exe-observe.py');
const excluded = new Set(['.git', '.venv', '.planning', 'build', 'dist', '__pycache__', '.pytest_cache']);
(function visit(d) {
  for (const e of fs.readdirSync(d, {withFileTypes: true})) {
    if (excluded.has(e.name)) continue;
    const full = path.join(d, e.name);
    if (e.isDirectory()) visit(full);
    else if (e.isFile() && (e.name.endsWith('.py') || ['AGENTS.md','pyproject.toml','.ruff.toml'].includes(e.name))) inputs.add(path.relative(root, full).replaceAll('\\','/'));
  }
})(root);
const inputList = [...inputs].filter(p => fs.existsSync(path.join(root, p))).sort();
const missing = [...inputs].filter(p => !fs.existsSync(path.join(root, p)));
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const hashes = () => Object.fromEntries(inputList.map(p => [p, hash(fs.readFileSync(path.join(root, p)))]));

const python = path.join(root, '.venv/Scripts/python.exe');
const ruff = path.join(root, '.venv/Scripts/ruff.exe');
const before = hashes();
fs.writeFileSync(path.join(dir, 'inputs-before.json'), JSON.stringify(before, null, 2), {flag: 'wx'});

const discovery = spawnSync(ruff, ['check','.','--show-files','--no-cache'], {cwd: root, encoding: 'utf8', windowsHide: true});
const files = discovery.stdout.trim().split(/\r?\n/).filter(p => p.endsWith('.py')).sort();
let prevFiles = null;
try { prevFiles = JSON.parse(fs.readFileSync(path.join(root, '.planning/phases/06-release-validation/06-05-evidence/w05c-instrumentation-native-20261105/ruff-discovery.json'))).files; } catch (e) { prevFiles = null; }
fs.writeFileSync(path.join(dir, 'ruff-discovery.json'), JSON.stringify({exit: discovery.status, stderr: discovery.stderr, count: files.length, sameAsW05cInstrumentation: prevFiles ? JSON.stringify(prevFiles) === JSON.stringify(files) : null, files}, null, 2));
const checks = [];
for (const [exe, args] of [[ruff,['check','.','--no-cache']], [ruff,['format','--check','--no-cache',...files]], [python,['-c',"import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"]]]) {
  const r = spawnSync(exe, args, {cwd: root, encoding: 'utf8', windowsHide: true});
  checks.push({argv: [exe, ...(args.length > 6 ? [...args.slice(0,3), `<${files.length} files>`] : args)], exit: r.status, stdout: r.stdout, stderr: r.stderr});
}
fs.writeFileSync(path.join(dir, 'checks.json'), JSON.stringify(checks, null, 2));
const env = spawnSync(python, ['-c','import sys,platform; print(sys.version); print(sys.executable); print(platform.platform())'], {cwd: root, encoding: 'utf8', windowsHide: true});
fs.writeFileSync(path.join(dir, 'environment.txt'), env.stdout, {flag: 'wx'});

const basetemp = path.join(process.env.LOCALAPPDATA, 'Temp', 'pf04-' + run);
const args = ['-m','pytest','-q','-rA','-p','no:cacheprovider',`--basetemp=${basetemp}`,`--junitxml=${path.join(dir,'junit.xml')}`];
const started = new Date().toISOString();
const out = fs.openSync(path.join(dir, 'stdout.txt'), 'wx');
const err = fs.openSync(path.join(dir, 'stderr.txt'), 'wx');
const child = spawn(python, args, {cwd: root, windowsHide: true, stdio: ['ignore', out, err], env: {...process.env, PYTHONIOENCODING: 'utf-8'}});
console.log(JSON.stringify({started, pid: child.pid, dir, inputCount: inputList.length, missing, checks: checks.map(c => c.exit)}));
let done = false;
const finish = (error, code, signal) => {
  if (done) return; done = true;
  fs.closeSync(out); fs.closeSync(err);
  const after = hashes();
  fs.writeFileSync(path.join(dir, 'inputs-after.json'), JSON.stringify(after, null, 2), {flag: 'wx'});
  const changed = inputList.filter(p => before[p] !== after[p]);
  const result = {started, finished: new Date().toISOString(), argv: [python, ...args], code, signal, error: error && String(error), inputCount: inputList.length, missing, changed};
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify(result, null, 2), {flag: 'wx'});
  console.log(JSON.stringify(result));
  console.log(fs.readFileSync(path.join(dir, 'stdout.txt'), 'utf8').split(/\r?\n/).slice(-5).join('\n'));
  process.exitCode = code || (changed.length ? 1 : 0);
};
child.on('error', e => finish(e, null, null));
child.on('exit', (code, signal) => finish(null, code, signal));
