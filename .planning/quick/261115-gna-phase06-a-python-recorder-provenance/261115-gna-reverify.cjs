// Phase04/05 再検証 runner（04-reverify-current.cjs を手本にした単一全件pytest）。
// 使い方:
//   node 261115-gna-reverify.cjs run     ... 入力前hash → 単一全件pytest → 入力後hash → result.json
//   node 261115-gna-reverify.cjs checks  ... ruff check / ruff format --check / AST を checks.json に保存
//   node 261115-gna-reverify.cjs hash <out-json> ... 現在の入力集合を再hashして保存（開発履歴追記後の差分確認用）
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');

const root = path.resolve(__dirname, '../../..');
const outDir = path.join(root, '.planning/phases/04-startup-control/04-reverify-20261115-pyrec');
const basetemp = path.join(process.env.LOCALAPPDATA || os.tmpdir(), 'Temp', 'pf04-04-reverify-20261115-pyrec');
const python = path.join(root, '.venv', 'Scripts', 'python.exe');
const ruff = path.join(root, '.venv', 'Scripts', 'ruff.exe');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

// 入力集合: 直近の再検証の inputs-before のキー + 04-reverify-current.cjs と同じ探索規則 + 共通 provenance module。
function inputSet() {
  const previous = Object.keys(JSON.parse(fs.readFileSync(path.join(root,
    '.planning/phases/04-startup-control/04-reverify-20261109-w12b-pid/inputs-before.json'), 'utf8')));
  const excluded = new Set(['.git', '.venv', '.planning', 'build', 'dist', '__pycache__', '.pytest_cache']);
  const found = [];
  const visit = dir => {
    for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
      if (excluded.has(entry.name)) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) visit(full);
      else if (entry.isFile() && (entry.name.endsWith('.py') || ['AGENTS.md', 'pyproject.toml', '.ruff.toml'].includes(entry.name))) {
        found.push(path.relative(root, full).replaceAll('\\', '/'));
      }
    }
  };
  visit(root);
  return [...new Set([...previous, ...found, '.planning/phases/06-release-validation/06-05-python-provenance.cjs'])].sort();
}
function snapshot(inputs) {
  const hashes = {}, missing = [];
  for (const file of inputs) {
    const full = path.join(root, file);
    if (fs.existsSync(full)) hashes[file] = sha(fs.readFileSync(full)); else missing.push(file);
  }
  return {hashes, missing};
}

function run() {
  if (fs.existsSync(outDir)) throw Error('証拠ディレクトリが既に存在: ' + outDir);
  if (fs.existsSync(basetemp)) throw Error('basetempが既に存在: ' + basetemp);
  fs.mkdirSync(outDir, {recursive: true});
  const inputs = inputSet();
  const before = snapshot(inputs);
  fs.writeFileSync(path.join(outDir, 'inputs-before.json'), JSON.stringify(before.hashes, null, 2));
  fs.writeFileSync(path.join(outDir, 'environment.txt'), [
    spawnSync(python, ['--version'], {encoding: 'utf8'}).stdout.trim().replace(/^Python /, '') + ' (venv: ' + python + ')',
    python,
    os.platform() + ' ' + os.release(),
    '2026-11-15 にvenvを再作成（git cloneをやり直したため消失）。requirements.txtの固定版: PyMuPDF 1.28.2 / Pillow 13.0.0 / Tk 9.0。',
  ].join('\n') + '\n');
  const argv = [python, '-m', 'pytest', '-q', '-rA', '-p', 'no:cacheprovider', `--basetemp=${basetemp}`,
    `--junitxml=${path.join(outDir, 'junit.xml')}`];
  const stdout = fs.openSync(path.join(outDir, 'stdout.txt'), 'wx');
  const stderr = fs.openSync(path.join(outDir, 'stderr.txt'), 'wx');
  const started = new Date().toISOString();
  let finished = false;
  const finish = (error, code, signal) => {
    if (finished) return;
    finished = true;
    fs.closeSync(stdout); fs.closeSync(stderr);
    const after = snapshot(inputs);
    fs.writeFileSync(path.join(outDir, 'inputs-after.json'), JSON.stringify(after.hashes, null, 2));
    const changed = inputs.filter(f => before.hashes[f] !== after.hashes[f]);
    const result = {started, finished: new Date().toISOString(), argv, code, signal, error: error && String(error),
      inputCount: inputs.length, missing: [...new Set([...before.missing, ...after.missing])], changed};
    fs.writeFileSync(path.join(outDir, 'result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
    process.exitCode = error ? 1 : code ?? 1;
  };
  const child = spawn(argv[0], argv.slice(1), {cwd: root, stdio: ['ignore', stdout, stderr], windowsHide: true});
  child.on('error', finish);
  child.on('exit', (code, signal) => finish(null, code, signal));
}

function checks() {
  const results = [];
  for (const args of [[ruff, 'check', '.', '--no-cache'], [ruff, 'format', '--check', '--no-cache', '.'],
    [python, '-c', "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"]]) {
    const r = spawnSync(args[0], args.slice(1), {cwd: root, encoding: 'utf8'});
    results.push({argv: args, exit: r.status, stdout: r.stdout, stderr: r.stderr});
  }
  fs.writeFileSync(path.join(outDir, 'checks.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results.map(r => ({exit: r.exit, stdout: r.stdout.trim().slice(0, 80)}))));
  process.exitCode = results.every(r => r.exit === 0) ? 0 : 1;
}

function hashOnly(target) {
  const snap = snapshot(inputSet());
  fs.writeFileSync(path.resolve(root, target), JSON.stringify({count: Object.keys(snap.hashes).length, missing: snap.missing, hashes: snap.hashes}, null, 2));
  console.log(Object.keys(snap.hashes).length);
}

const mode = process.argv[2];
if (mode === 'run') run();
else if (mode === 'checks') checks();
else if (mode === 'hash') hashOnly(process.argv[3]);
else throw Error('usage: run | checks | hash <out-json>');
