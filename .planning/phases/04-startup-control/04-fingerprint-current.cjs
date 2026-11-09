const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const phase = '.planning/phases/04-startup-control';
const file = path.join(phase, '04-VERIFICATION.md');
let report = fs.readFileSync(file, 'utf8');
const currentLine = report.match(/^covered_files: (.+)$/m);
if (!currentLine) throw new Error('covered_files が見つからない');
const files = JSON.parse(currentLine[1]);
const additions = [
  '04-REVALIDATION-20261105.md',
  '04-reverify-current.cjs',
  '04-fingerprint-current.cjs',
  '04-reverify-20261105-full/run.json',
  '04-reverify-20261105-full/inputs-before.json',
  '04-reverify-20261105-full/inputs-after.json',
  '04-reverify-20261105-full/junit.xml',
  '04-reverify-20261105-full/stdout.txt',
  '04-reverify-20261105-full/stderr.txt',
  '04-reverify-20261105-full/ruff-check.txt',
  '04-reverify-20261105-full/ruff-format-check.txt',
  '04-reverify-20261105-full/ruff-check-excluding-evidence.txt',
  '04-reverify-20261105-full/ruff-format-check-excluding-evidence.txt',
].map(name => `${phase}/${name}`);
for (const entry of additions) if (!files.includes(entry)) files.push(entry);
const query = spawnSync('node', [
  'C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs',
  'query', 'verification.fingerprint', phase, ...files,
], { encoding: 'utf8', maxBuffer: 2 * 1024 * 1024 });
if (query.status !== 0) throw new Error(query.stderr || query.stdout);
const result = JSON.parse(query.stdout);
if (!result.covered_files || !result.covered_digest) throw new Error('fingerprint の戻り値が不完全');
report = report.replace(/^covered_files: .+$/m, `covered_files: ${JSON.stringify(result.covered_files)}`);
report = report.replace(/^covered_digest: .+$/m, `covered_digest: "${result.covered_digest}"`);
fs.writeFileSync(file, report, 'utf8');
process.stdout.write(JSON.stringify({ covered_files: result.covered_files.length, covered_digest: result.covered_digest }) + '\n');
