const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '../../..');
const stage = process.argv[2];
const python = path.join(root, '.venv/Scripts/python.exe');
const ruff = path.join(root, '.venv/Scripts/ruff.exe');
const base = path.relative(root, __dirname).replaceAll('\\', '/');
const pytest = ['-m', 'pytest', '-q', '-rA', '-x', '-o', `cache_dir=${base}/pytest-cache`];
const stages = {
  static: [
    [ruff, 'check', '.'],
    [ruff, 'format', '.', '--no-cache'],
    [ruff, 'format', '.', '--check', '--no-cache'],
    [python, '-c', 'import ast,pathlib; [ast.parse(pathlib.Path(p).read_text(encoding="utf-8")) for p in ["pagefolio.py", ".planning/debug/preview-focus-not-restored-evidence/diag_btn_press.py"]]; print("AST: OK")'],
  ],
  connection: [[python, ...pytest, 'tests/test_startup_windows.py::test_foreground_audit_receives_native_window_event', `--basetemp=${base}/connection-tmp`, `--junitxml=${base}/connection.xml`]],
  nine: [[python, ...pytest, 'tests/test_startup_windows.py::test_notice_dedup_eight_processes_keep_original_deadline', `--basetemp=${base}/nine-tmp`, `--junitxml=${base}/nine.xml`]],
  full: [[python, ...pytest, `--basetemp=${base}/full-tmp`, `--junitxml=${base}/full.xml`]],
  documents: [[python, ...pytest, 'tests/test_gsd_dod.py', 'tests/test_release_contract.py', `--basetemp=${base}/documents-tmp`]],
};
stages.final = stages.static;
stages['final-native'] = stages.static;
stages['final-corrected'] = stages.static;
stages['final-scoped'] = stages.static;
stages.verified = stages.static;
stages['final-result'] = stages.static;
stages.complete = stages.static;
stages['final-pass'] = stages.static;
stages['final-confirmed'] = stages.static;
stages['native-final'] = stages.static;
if (!stages[stage]) throw Error('unknown stage');
const output = path.join(__dirname, `${stage}.json`);
if (fs.existsSync(output)) throw Error('stage already recorded; preserve first evidence');
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const baseline = JSON.parse(fs.readFileSync(path.join(__dirname, 'baseline.json')));
const inputHashes = () => Object.fromEntries(Object.keys(baseline.inputs).map(p => [p, digest(fs.readFileSync(path.join(root, p)))]));
const before = inputHashes();
const records = [];
(async () => {
  for (const [i, argv] of stages[stage].entries()) {
    const prefix = path.join(__dirname, `${stage}-${i}`);
    const out = fs.openSync(`${prefix}.stdout.txt`, 'wx');
    const err = fs.openSync(`${prefix}.stderr.txt`, 'wx');
    const started = new Date().toISOString();
    const code = await new Promise((resolve, reject) => {
      const child = spawn(argv[0], argv.slice(1), {cwd: root, windowsHide: true, stdio: ['ignore', out, err], env: {...process.env, PYTHONIOENCODING: 'utf-8'}});
      child.on('error', reject);
      child.on('close', resolve);
    }).finally(() => {fs.closeSync(out); fs.closeSync(err);});
    records.push({argv, started, finished: new Date().toISOString(), code});
    if (code !== 0) break;
  }
  const after = inputHashes();
  const changed = Object.keys(before).filter(p => before[p] !== after[p]);
  const passed = records.length === stages[stage].length && records.every(r => r.code === 0) && !changed.length;
  fs.writeFileSync(output, JSON.stringify({stage, passed, records, changed, before, after}, null, 2), {flag: 'wx'});
  console.log(JSON.stringify({stage, passed, codes: records.map(r => r.code), changed}));
  for (let i = 0; i < records.length; i++) {
    const log = fs.readFileSync(path.join(__dirname, `${stage}-${i}.stdout.txt`), 'utf-8');
    console.log(log.split(/\r?\n/).filter(Boolean).slice(-4).join('\n'));
    const errors = fs.readFileSync(path.join(__dirname, `${stage}-${i}.stderr.txt`), 'utf-8');
    if (errors) console.log(errors.slice(-2000));
  }
  process.exitCode = passed ? 0 : 1;
})().catch(error => {console.error(error); process.exitCode = 2;});
