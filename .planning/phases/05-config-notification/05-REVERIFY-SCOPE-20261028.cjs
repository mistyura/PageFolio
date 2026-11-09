// Phase 05 限定再検証。試験を実行せず、完了済み全件の正本と現行入力を読む。
const fs = require('node:fs');
const crypto = require('node:crypto');
const root = '.planning/phases/06-release-validation/06-08-evidence/native-docs-20261028/';
const baseline = '.planning/debug/ocr-off-summary-evidence/native-20261028/result.json';
const result = JSON.parse(fs.readFileSync(root + 'result.json', 'utf8'));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const checks = {};
for (const key of ['before', 'after']) {
  checks[key] = {count: Object.keys(result[key]).length, mismatches: []};
  for (const [path, expected] of Object.entries(result[key])) {
    if (!fs.existsSync(path) || hash(path) !== expected) checks[key].mismatches.push(path);
  }
}
const old = JSON.parse(fs.readFileSync(baseline, 'utf8'));
const baselineChanges = Object.entries(old.after).filter(([p, h]) => !fs.existsSync(p) || hash(p) !== h).map(([p]) => p);
const runtimeChanges = baselineChanges.filter(p => p === 'pagefolio.py' || p.startsWith('pagefolio/') || ['pyproject.toml', 'requirements.txt'].includes(p));
const xml = fs.readFileSync(root + 'junit.xml', 'utf8');
const stdout = fs.readFileSync(root + 'stdout.txt', 'utf8');
const attrs = s => Object.fromEntries([...s.matchAll(/(\w+)="([^"]*)"/g)].map(m => [m[1], m[2]]));
const suite = attrs(xml.match(/<testsuite\s([^>]+)>/)[1]);
const files = {};
const cases = [];
for (const m of xml.matchAll(/<testcase\s([^>]*?)(?:\/>|>([\s\S]*?)<\/testcase>)/g)) {
  const a = attrs(m[1]); const file = a.classname.split('.')[1] + '.py';
  files[file] = (files[file] || 0) + 1;
  if (/test_config_notification|test_settings_keyguard|test_ocr_dialog_provider_refresh|test_release_contract/.test(file)) {
    cases.push({name: a.classname + '::' + a.name, status: /<(failure|error|skipped)\b/.test(m[2] || '') ? 'nonpass' : 'pass'});
  }
}
const evidence = {
  verified_at: new Date().toISOString(),
  method: '独立読み取り照合。変更後単一全件を再利用し、pytest・GUI・buildを再実行しない。',
  source: root, argv: result.argv, started: result.started, finished: result.finished,
  exit_code: result.code, run_changed: result.changed, checks,
  baseline, baseline_changes: baselineChanges, product_or_dependency_changes: runtimeChanges,
  junit: suite, stdout_summary: stdout.trim().split(/\r?\n/).at(-1), files, cases,
  source_hashes: Object.fromEntries(['result.json', 'junit.xml', 'stdout.txt', 'stderr.txt', 'environment.txt', 'checks.json', 'before.json'].map(f => [root + f, hash(root + f)])),
};
console.log(JSON.stringify(evidence, null, 2));
if (result.code !== 0 || result.changed.length || checks.before.mismatches.length || checks.after.mismatches.length || runtimeChanges.length || suite.failures !== '0' || suite.errors !== '0' || suite.skipped !== '0') process.exitCode = 1;
