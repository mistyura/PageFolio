const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const root = process.cwd();
const relativeOutput = process.argv[2];
const phaseRoot = path.resolve(root, '.planning/phases/04-startup-control');
if (!relativeOutput) {
  throw new Error('Phase 04 内の新規証拠ディレクトリを指定する');
}
const output = path.resolve(root, relativeOutput);
if (!output.startsWith(`${phaseRoot}${path.sep}`)) {
  throw new Error('Phase 04 の外には証拠を書き込めない');
}
if (fs.existsSync(output)) throw new Error(`証拠の上書きを拒否: ${output}`);
fs.mkdirSync(output, { recursive: true });

const excluded = new Set(['.git', '.venv', '.planning', 'build', 'dist', '__pycache__', '.pytest_cache']);
const inputs = [];
function visit(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (excluded.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) visit(full);
    else if (entry.isFile() && (entry.name.endsWith('.py') || ['AGENTS.md', 'pyproject.toml', '.ruff.toml'].includes(entry.name))) {
      inputs.push(path.relative(root, full).replaceAll('\\', '/'));
    }
  }
}
visit(root);
inputs.sort();
function snapshot() {
  return Object.fromEntries(inputs.map(file => [file, crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex')]));
}
const before = snapshot();
fs.writeFileSync(path.join(output, 'inputs-before.json'), JSON.stringify(before, null, 2));
const args = ['-m', 'pytest', '-q', '--basetemp', path.join(output, 'basetemp'), '--junitxml', path.join(output, 'junit.xml')];
const stdout = fs.openSync(path.join(output, 'stdout.txt'), 'wx');
const stderr = fs.openSync(path.join(output, 'stderr.txt'), 'wx');
const started = new Date().toISOString();
const child = spawn(path.join(root, '.venv', 'Scripts', 'python.exe'), args, { cwd: root, stdio: ['ignore', stdout, stderr], windowsHide: true });
child.on('error', finish);
child.on('exit', (code, signal) => finish(null, code, signal));
let finished = false;
function finish(error, code, signal) {
  if (finished) return;
  finished = true;
  fs.closeSync(stdout);
  fs.closeSync(stderr);
  const after = snapshot();
  fs.writeFileSync(path.join(output, 'inputs-after.json'), JSON.stringify(after, null, 2));
  const changed = inputs.filter(file => before[file] !== after[file]);
  const result = { started, ended: new Date().toISOString(), argv: [path.join('.venv', 'Scripts', 'python.exe'), ...args], exit_code: code, signal, error: error && String(error), input_count: inputs.length, changed_inputs: changed };
  fs.writeFileSync(path.join(output, 'run.json'), JSON.stringify(result, null, 2));
  process.stdout.write(JSON.stringify(result) + '\n');
  process.exitCode = error ? 1 : code ?? 1;
}
