const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../../..');
const run = process.argv[2];
if (!/^[a-z0-9-]+$/.test(run || '')) throw Error('unique run ID required');
const dir = path.join(__dirname, '06-07-evidence', run);
fs.mkdirSync(dir, {recursive:true});
if (fs.readdirSync(dir).length) throw Error('preserve previous evidence');
const baseline = JSON.parse(fs.readFileSync(path.join(root, '.planning/debug/ocr-off-summary-evidence/native-20261028/before.json')));
const inputs = [...new Set([...Object.keys(baseline), 'tests/release_uat_support.py', 'tests/test_release_uat_support.py', 'tests/test_release_contract.py', '.ruff.toml', ...['06-RELEASE-SCOPE.json','06-W11-SCOPE-APPROVAL.md','06-MANUAL-EVIDENCE.json','06-UAT.md'].map(n=>'.planning/phases/06-release-validation/'+n)])];
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const hashes = () => Object.fromEntries(inputs.map(p=>[p,hash(fs.readFileSync(path.join(root,p)))]));
const python = path.join(root,'.venv/Scripts/python.exe');
const ruff = path.join(root,'.venv/Scripts/ruff.exe');
const checks = [];
// ディレクトリwalkの断続的OSエラーを避け、同じ全Python集合を明示する。
const discovery = spawnSync(ruff,['check','.','--show-files','--no-cache'],{cwd:root,encoding:'utf8',windowsHide:true});
const files = discovery.stdout.trim().split(/\r?\n/).filter(p=>p.endsWith('.py')).sort();
const previousFiles = JSON.parse(fs.readFileSync(path.join(__dirname,'06-07-evidence/ruff-files.json'))).sort();
fs.writeFileSync(path.join(dir,'ruff-discovery.json'),JSON.stringify({exit:discovery.status,stderr:discovery.stderr,files,previousFiles},null,2));
if (discovery.status || discovery.stderr || JSON.stringify(files)!==JSON.stringify(previousFiles)) throw Error('Ruff target set changed or incomplete');
for (const [exe,args] of [[ruff,['check','.','--no-cache']], [ruff,['format','--no-cache',...files]], [ruff,['check','.','--no-cache']], [python,['-c',"import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"]]]) {
  const r = spawnSync(exe,args,{cwd:root,encoding:'utf8',windowsHide:true});
  checks.push({argv:[exe,...args],exit:r.status,stdout:r.stdout,stderr:r.stderr});
  fs.writeFileSync(path.join(dir,'checks.json'),JSON.stringify(checks,null,2));
  if (r.status !== 0) {
    const lines = r.stderr.split(/\r?\n/);
    console.log(JSON.stringify({exit:r.status,stdout:r.stdout,errors:lines.flatMap((line,i)=>/Encountered error|os error/.test(line)?lines.slice(Math.max(0,i-3),i+3):[])}));
    process.exit(r.status || 1);
  }
}
const before = hashes();
fs.writeFileSync(path.join(dir,'before.json'),JSON.stringify(before,null,2),{flag:'wx'});
const env = spawnSync(python,['-c','import sys,platform; print(sys.version); print(sys.executable); print(platform.platform())'],{cwd:root,encoding:'utf8',windowsHide:true});
fs.writeFileSync(path.join(dir,'environment.txt'),env.stdout,{flag:'wx'});
const args = ['-m','pytest','-q','-x','-rA','-p','no:cacheprovider',`--basetemp=${path.join(process.env.LOCALAPPDATA,'Temp','pf06-scope-'+run)}`,`--junitxml=${path.join(dir,'junit.xml')}`];
const started = new Date().toISOString();
const out = fs.openSync(path.join(dir,'stdout.txt'),'wx');
const err = fs.openSync(path.join(dir,'stderr.txt'),'wx');
const child = spawn(python,args,{cwd:root,windowsHide:true,stdio:['ignore',out,err],env:{...process.env,PYTHONIOENCODING:'utf-8'}});
console.log(JSON.stringify({started,pid:child.pid,dir,inputCount:inputs.length}));
child.on('error', e=>{console.error(e);process.exitCode=1;});
child.on('close', code=>{
  fs.closeSync(out);fs.closeSync(err);
  const after = hashes();const changed=inputs.filter(p=>before[p]!==after[p]);
  fs.writeFileSync(path.join(dir,'result.json'),JSON.stringify({started,finished:new Date().toISOString(),argv:[python,...args],code,changed,before,after},null,2),{flag:'wx'});
  console.log(JSON.stringify({code,changed,dir}));
  console.log(fs.readFileSync(path.join(dir,'stdout.txt'),'utf8').split(/\r?\n/).slice(-5).join('\n'));
  process.exitCode=code || (changed.length?1:0);
});
