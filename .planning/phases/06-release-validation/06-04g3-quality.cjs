// 世代3の台帳更新後に、単一native全件の入力・環境・初回出力を保持する。
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const cp = require('child_process');
const root = path.resolve(__dirname, '../../..');
const attempt = process.argv[2] || 'initial';
if (!/^[a-z0-9-]+$/.test(attempt)) throw new Error('invalid attempt');
const evidence = path.join(__dirname, '06-04g3-quality' + (attempt === 'initial' ? '' : '-' + attempt));
fs.mkdirSync(evidence, { recursive: true });
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function walk(dir) {
  return fs.readdirSync(path.join(root, dir), { withFileTypes: true }).flatMap(e => {
    const p = path.posix.join(dir, e.name);
    return e.isDirectory() ? (e.name === '__pycache__' ? [] : walk(p)) : (/\.(py|json|toml|ini|cfg)$/.test(p) ? [p] : []);
  });
}
const additional = [
  'pagefolio.py', 'conftest.py', 'pyproject.toml', 'requirements.txt', 'README.md', '開発履歴.md',
  'distribution/はじめに.md', 'docs/CONFIGURATION.md', 'docs/DEVELOPMENT.md',
  '.planning/ROADMAP.md', '.planning/STATE.md',
  '.planning/phases/04-startup-control/04-VALIDATION.md',
  '.planning/phases/06-release-validation/06-MANUAL-EVIDENCE.json',
  '.planning/phases/06-release-validation/06-UAT.md',
  '.planning/phases/06-release-validation/06-BUILD-EVIDENCE.json',
  '.planning/phases/06-release-validation/06-PROTECTION-EVIDENCE.json',
  '.planning/phases/06-release-validation/06-UAT-PREPARATION.md',
];
const files = [...new Set([...walk('pagefolio'), ...walk('tests'), ...walk('tools'), ...additional].filter(p => fs.existsSync(path.join(root, p))))].sort();
const snapshot = () => Object.fromEntries(files.map(p => [p, hash(path.join(root, p))]));
const write = (name, value) => fs.writeFileSync(path.join(evidence, name), JSON.stringify(value, null, 2) + '\n');
const py = path.join(root, '.venv/Scripts/python.exe');
const basetemp = path.join(os.tmpdir(), 'pf06-g3-quality-' + crypto.randomUUID());
const command = ['-m', 'pytest', '-q', '-x', '--basetemp=' + basetemp, '-o', 'cache_dir=' + basetemp + '-cache'];
const before = snapshot();
const started = new Date().toISOString();
const env = { ...process.env, PYTHONUTF8: '1' };
const environment = cp.spawnSync(py, ['-c', 'import sys,platform,pytest,tkinter; print(sys.version); print(platform.platform()); print("pytest="+pytest.__version__); print("Tcl="+str(tkinter.TclVersion)+" Tk="+str(tkinter.TkVersion)); print("executable="+sys.executable)'], { cwd: root, encoding: 'utf8', windowsHide: true, env });
fs.writeFileSync(path.join(evidence, 'environment.txt'), environment.stdout + environment.stderr);
if (environment.status !== 0) throw new Error('environment collection failed');
write('inputs-before.json', before);
const fd = fs.openSync(path.join(evidence, 'pytest-full.txt'), 'wx');
const child = cp.spawn(py, command, { cwd: root, windowsHide: true, stdio: ['ignore', fd, fd], env });
write('started.json', { started, pid: child.pid, command, basetemp });
child.on('error', err => fs.writeSync(fd, String(err)));
child.on('close', (code, signal) => {
  fs.closeSync(fd);
  const after = snapshot();
  write('inputs-after.json', after);
  const changes = files.filter(p => before[p] !== after[p]);
  const report = { started, finished: new Date().toISOString(), executable: py, executable_sha256: hash(py), command, basetemp, code, signal, environment_exit: environment.status, inputs_unchanged: changes.length === 0, changed_inputs: changes, file_count: files.length, inputs_before_sha256: hash(path.join(evidence, 'inputs-before.json')), inputs_after_sha256: hash(path.join(evidence, 'inputs-after.json')), environment_sha256: hash(path.join(evidence, 'environment.txt')), log_sha256: hash(path.join(evidence, 'pytest-full.txt')) };
  write('run.json', report);
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = code === 0 && changes.length === 0 ? 0 : 1;
});
