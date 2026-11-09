// 現行入力と実行ログを結び付ける一回限りの Phase 04 再検証採取器。
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const cp = require('child_process');
const root = path.resolve(__dirname, '../../..');
const attempt = process.argv[2] || 'sandbox';
if (!/^[a-z0-9-]+$/.test(attempt)) throw new Error('invalid attempt');
const evidence = path.join(__dirname, '04-reverify-20261028', attempt);
fs.mkdirSync(evidence, {recursive: true});
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function walk(dir) {
  return fs.readdirSync(path.join(root, dir), {withFileTypes: true}).flatMap(e => {
    const p = path.posix.join(dir, e.name);
    return e.isDirectory() ? (e.name === '__pycache__' ? [] : walk(p)) : (/\.(py|json|toml|ini|cfg)$/.test(p) ? [p] : []);
  });
}
const files = [...new Set([...walk('pagefolio'), ...walk('tests'), 'pagefolio.py', 'pyproject.toml', 'requirements.txt', 'conftest.py'].filter(p => fs.existsSync(path.join(root, p))))].sort();
const snapshot = () => Object.fromEntries(files.map(p => [p, hash(path.join(root, p))]));
const py = path.join(root, '.venv/Scripts/python.exe');
const basetemp = path.join(os.tmpdir(), 'pf04-reverify-' + crypto.randomUUID());
const command = ['-m', 'pytest', '-q', '-x', '--basetemp=' + basetemp];
const before = snapshot();
const started = new Date().toISOString();
const environment = cp.spawnSync(py, ['-c', 'import sys,platform,pytest,tkinter; print(sys.version); print(platform.platform()); print("pytest="+pytest.__version__); print("Tcl="+str(tkinter.TclVersion)+" Tk="+str(tkinter.TkVersion)); print("executable="+sys.executable)'], {cwd:root, encoding:'utf8', windowsHide:true});
fs.writeFileSync(path.join(evidence, 'environment.txt'), environment.stdout + environment.stderr);
fs.writeFileSync(path.join(evidence, 'inputs-before.json'), JSON.stringify(before, null, 2) + '\n');
const fd = fs.openSync(path.join(evidence, 'pytest-full.txt'), 'wx');
const child = cp.spawn(py, command, {cwd:root, windowsHide:true, stdio:['ignore', fd, fd], env:{...process.env, PYTHONUTF8:'1'}});
child.on('error', err => { fs.writeSync(fd, String(err)); });
child.on('close', (code, signal) => {
  fs.closeSync(fd);
  const after = snapshot();
  fs.writeFileSync(path.join(evidence, 'inputs-after.json'), JSON.stringify(after, null, 2) + '\n');
  const changes = files.filter(p => before[p] !== after[p]);
  const report = {started, finished:new Date().toISOString(), executable:py, executable_sha256:hash(py), command, basetemp, code, signal, environment_exit:environment.status, inputs_unchanged:changes.length===0, changed_inputs:changes, inputs_before_sha256:hash(path.join(evidence,'inputs-before.json')), inputs_after_sha256:hash(path.join(evidence,'inputs-after.json')), environment_sha256:hash(path.join(evidence,'environment.txt')), log_sha256:hash(path.join(evidence,'pytest-full.txt')), file_count:files.length};
  fs.writeFileSync(path.join(evidence, 'run.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = code === 0 && changes.length === 0 ? 0 : 1;
});
