// 今回専用の採取器。原本証拠を上書きせず、入力・環境・全出力を対応付ける。
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const cp = require('child_process');
const root = path.resolve(__dirname, '../../..');
const stage = process.argv[2];
if (!/^[a-z0-9-]+$/.test(stage || '')) throw Error('stage required');
const dir = path.join(__dirname, stage);
fs.mkdirSync(dir); // 同名の試行を再利用しない。
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function collectChildren(base, target, relative='') {
  if (!fs.existsSync(base)) return [];
  return fs.readdirSync(path.join(base, relative), {withFileTypes:true}).flatMap(e => {
    const rel = path.join(relative,e.name);
    if (e.isDirectory()) return collectChildren(base,target,rel);
    if (e.name !== 'startup-wake-child.json') return [];
    const dest = path.join(target,rel);
    fs.mkdirSync(path.dirname(dest),{recursive:true});
    fs.copyFileSync(path.join(base,rel),dest);
    return [{path:rel,sha256:hash(dest)}];
  });
}
function walk(p) {
  return fs.readdirSync(path.join(root, p), {withFileTypes:true}).flatMap(e => {
    const f = path.posix.join(p, e.name);
    return e.isDirectory() ? (e.name === '__pycache__' ? [] : walk(f)) : (/\.(py|json|toml|ini|cfg)$/.test(f) ? [f] : []);
  });
}
const files = [...new Set([...walk('pagefolio'), ...walk('tests'), 'pagefolio.py', 'pyproject.toml', 'requirements.txt', 'conftest.py'].filter(f => fs.existsSync(path.join(root, f))))].sort();
const snapshot = () => Object.fromEntries(files.map(f => [f, hash(path.join(root, f))]));
const py = path.join(root, '.venv/Scripts/python.exe');
const basetemp = path.join(os.tmpdir(), 'pf-debug-wake-' + crypto.randomUUID());
const args = process.argv.slice(3);
const before = snapshot();
fs.writeFileSync(path.join(dir, 'inputs-before.json'), JSON.stringify(before, null, 2) + '\n');
if (stage === 'baseline') {
  for (const f of ['tests/test_startup_wake.py', 'tests/startup_wake_child.py']) fs.copyFileSync(path.join(root, f), path.join(dir, path.basename(f)+'.original'));
  const status = cp.spawnSync('git', ['status','--short'], {cwd:root,encoding:'utf8',windowsHide:true});
  fs.writeFileSync(path.join(dir, 'git-status.txt'), status.stdout + status.stderr);
  console.log(JSON.stringify({stage, file_count:files.length, baseline_sha256:hash(path.join(dir,'inputs-before.json'))}));
  process.exit(0);
}
const command = ['-m','pytest',...args,'--basetemp='+basetemp];
const environment = cp.spawnSync(py, ['-c','import sys,platform,pytest,tkinter; print(sys.version); print(platform.platform()); print("pytest="+pytest.__version__); print("Tcl="+str(tkinter.TclVersion)+" Tk="+str(tkinter.TkVersion)); print("executable="+sys.executable)'], {cwd:root,encoding:'utf8',windowsHide:true});
fs.writeFileSync(path.join(dir,'environment.txt'), environment.stdout + environment.stderr);
const started = new Date().toISOString();
const fd = fs.openSync(path.join(dir, 'pytest.txt'), 'wx');
const child = cp.spawn(py, command, {cwd:root,windowsHide:true,stdio:['ignore',fd,fd],env:{...process.env,PYTHONUTF8:'1'}});
let timedOut=false;
const timer=setTimeout(()=>{timedOut=true;child.kill();},360000);
child.on('error', e => fs.writeSync(fd, String(e)));
child.on('close', (code,signal) => {
  clearTimeout(timer);
  fs.closeSync(fd);
  const after = snapshot();
  fs.writeFileSync(path.join(dir,'inputs-after.json'), JSON.stringify(after,null,2)+'\n');
  const changed = files.filter(f => before[f] !== after[f]);
  const children = collectChildren(basetemp,path.join(dir,'children'));
  const report = {started,finished:new Date().toISOString(),collector_sha256:hash(__filename),executable:py,executable_sha256:hash(py),command,basetemp,code,signal,timedOut,environment_exit:environment.status,inputs_unchanged:changed.length===0,changed_inputs:changed,file_count:files.length,inputs_before_sha256:hash(path.join(dir,'inputs-before.json')),inputs_after_sha256:hash(path.join(dir,'inputs-after.json')),environment_sha256:hash(path.join(dir,'environment.txt')),log_sha256:hash(path.join(dir,'pytest.txt')),children};
  fs.writeFileSync(path.join(dir,'run.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
  process.exitCode=code===0&&changed.length===0?0:1;
});
