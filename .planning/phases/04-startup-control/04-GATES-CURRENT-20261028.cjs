// 依存元ゲートの読取監査。製品や既存証拠を書き換えない。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const root = process.cwd();
const dir = '.planning/phases/04-startup-control';
const source = '.planning/debug/quality-gate-unblock-20261028';
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const read = file => fs.readFileSync(file, 'utf8');
const load = file => JSON.parse(read(file));
const compare = map => {
  const rows = Object.entries(map).map(([file, expected]) => {
    const actual = fs.existsSync(file) ? hash(file) : null;
    return { file, expected, actual, matches: expected === actual };
  });
  return { total: rows.length, matched: rows.filter(r => r.matches).length,
    differences: rows.filter(r => !r.matches),
    python: { total: rows.filter(r => r.file.endsWith('.py')).length,
      differences: rows.filter(r => r.file.endsWith('.py') && !r.matches) } };
};
if (process.argv.includes('--final')) {
  const cli = 'C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs';
  const audits = [];
  for (const [file, heading, rows] of [
    ['04-VALIDATION.md', 'Validation Audit', { 'Gaps found': 0, Resolved: 0, Escalated: 0 }],
    ['04-SECURITY.md', 'Security Audit', { 'Threats found': 22, Closed: 22, Open: 0 }],
  ]) {
    const run = cp.spawnSync(process.execPath, [cli, 'query', 'verification.append-audit',
      `${dir}/${file}`, '--heading', heading, '--rows', JSON.stringify(rows)], { encoding: 'utf8' });
    audits.push({ file, status: run.status, stdout: run.stdout, stderr: run.stderr });
    if (run.status !== 0) throw new Error(JSON.stringify(audits));
  }
  const environmentRun = cp.spawnSync(path.join(root, '.venv/Scripts/python.exe'), ['-c',
    'import sys,platform,json,importlib.metadata as m;print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={n:m.version(n) for n in ["pytest","ruff","PyMuPDF","Pillow","tkinterdnd2"]})))'],
    { encoding: 'utf8' });
  if (environmentRun.status !== 0) throw new Error(environmentRun.stderr);
  const currentEnvironment = JSON.parse(environmentRun.stdout);
  const previous = load(`${dir}/04-GATES-CURRENT-20261028.json`);
  const evidenceUnchanged = Object.entries(previous.evidence).every(([file, value]) => hash(file) === value);
  const fullComparison = compare(load(`${source}/full.json`).after);
  const oldComparison = compare(load('.planning/debug/startup-wake-foreground-evidence/full-native-after-state/inputs-before.json'));
  const final = { captured: new Date().toISOString(), audits, environment: currentEnvironment,
    environment_matches_recorded: Object.keys(currentEnvironment).every(k =>
      JSON.stringify(currentEnvironment[k]) === JSON.stringify(previous.environment[k])),
    evidence_unchanged: evidenceUnchanged, current_full_comparison: fullComparison,
    old_118_comparison: oldComparison,
    reports: Object.fromEntries(Object.keys(previous.before_reports).map(file => [file, hash(file)])),
    verification_untouched: hash(`${dir}/04-VERIFICATION.md`) === previous.before_reports[`${dir}/04-VERIFICATION.md`],
  };
  const out = `${dir}/04-GATES-CURRENT-FINAL-20261028.json`;
  fs.writeFileSync(out, JSON.stringify(final, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ output: out, sha256: hash(out), ...final }, null, 2));
  process.exit(final.environment_matches_recorded && evidenceUnchanged && final.verification_untouched
    && fullComparison.python.differences.length === 0 ? 0 : 1);
}
const snapshots = {};
for (const name of ['full', 'native-final', 'documents', 'connection', 'nine']) {
  const file = `${source}/${name}.json`;
  const j = load(file);
  snapshots[name] = { file, sha256: hash(file), passed: j.passed,
    records: j.records, changed_during_run: j.changed,
    current_comparison: compare(j.after || j.before) };
}
const artifacts = fs.readdirSync(dir).filter(f => /-(PLAN|SUMMARY)\.md$/.test(f)).map(f => {
  const file = `${dir}/${f}`;
  const text = read(file);
  return { file, sha256: hash(file),
    requirements: [...new Set(text.match(/V110-(?:START|FOCUS)-\d+/g) || [])],
    tasks: [...text.matchAll(/<task\b([^>]*)>([\s\S]*?)<\/task>/g)].map(m => ({
      attributes: m[1].trim(), name: m[2].match(/<name>([\s\S]*?)<\/name>/)?.[1],
      files: m[2].match(/<files>([\s\S]*?)<\/files>/)?.[1],
      verification: m[2].match(/<verify>([\s\S]*?)<\/verify>/)?.[1] })),
    threats: [...new Set(text.match(/T-04-(?:\d+|SC)/g) || [])],
    threat_models: [...text.matchAll(/<threat_model>([\s\S]*?)<\/threat_model>/g)].map(m => m[1]),
    threat_flags: text.match(/## Threat Flags[\s\S]*?(?=\n## |$)/)?.[0] || null };
});
const evidenceFiles = ['full.json', 'full.xml', 'full-0.stdout.txt', 'full-0.stderr.txt',
  'native-final.json', 'native-final-0.stdout.txt', 'native-final-1.stdout.txt',
  'native-final-2.stdout.txt', 'native-final-3.stdout.txt', 'environment.json',
  'final-summary.json', 'documents.json', 'documents-0.stdout.txt',
  'connection.json', 'connection.xml', 'nine.json', 'nine.xml'];
const evidence = Object.fromEntries(evidenceFiles.map(f => [`${source}/${f}`, hash(`${source}/${f}`)]));
const xml = read(`${source}/full.xml`);
const suite = xml.match(/<testsuite\s[^>]+>/)?.[0];
const namedTests = [...xml.matchAll(/<testcase\b([^>]+)>/g)]
  .map(m => m[1]).filter(s => /startup|gsd_dod|lang_parity|font_hardcode/.test(s));
const reports = ['04-VALIDATION.md', '04-SECURITY.md', '04-UI-REVIEW.md',
  '04-REVIEW.md', '04-REVIEW-DISPOSITION.md', '04-VERIFICATION.md'];
const beforeReports = Object.fromEntries(reports.map(f => [`${dir}/${f}`, hash(`${dir}/${f}`)]));
const environment = load(`${source}/environment.json`);
const result = {
  captured: new Date().toISOString(), root, node: process.version, platform: process.platform,
  snapshots, evidence, full_suite: suite,
  named_test_count: namedTests.length, named_tests: namedTests,
  full_summary: read(`${source}/full-0.stdout.txt`).split(/\r?\n/).filter(l => /passed|warnings summary|PytestWarning|DeprecationWarning/.test(l)).slice(-12),
  environment, artifacts, before_reports: beforeReports,
  unchanged_runtime_files: ['.venv/pyvenv.cfg', '.venv/Scripts/python.exe', '.venv/Scripts/ruff.exe']
    .map(file => ({ file, sha256: fs.existsSync(file) ? hash(file) : null })),
  current_review_inputs: ['pagefolio/__main__.py', 'pagefolio/startup_win32.py',
    'pagefolio/startup_control.py', 'pagefolio/startup_focus.py', 'pagefolio/startup_notice.py',
    'pagefolio/startup_wake.py', 'tests/test_startup_windows.py', 'tests/startup_foreground_audit.py',
    'tests/test_startup_foreground_audit.py', 'tests/test_startup_wake.py', 'tests/startup_wake_child.py']
    .map(file => ({ file, sha256: hash(file) })),
  git_diff_check: cp.spawnSync('git', ['-c', 'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol',
    'diff', '--check', '--', 'tests/test_startup_windows.py', 'tests/startup_foreground_audit.py',
    'tests/test_startup_foreground_audit.py', 'pagefolio/startup_win32.py', 'pagefolio/__main__.py'], { encoding: 'utf8' })
};
const out = path.join(root, dir, '04-GATES-CURRENT-20261028.json');
if (fs.existsSync(out)) throw new Error('今回証拠を上書きしない: ' + out);
fs.writeFileSync(out, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
console.log(JSON.stringify({ evidence: path.relative(root, out), sha256: hash(out), full_suite: suite,
  snapshots: Object.fromEntries(Object.entries(snapshots).map(([k, v]) => [k,
    { sha256: v.sha256, passed: v.passed, changed: v.changed_during_run, comparison: v.current_comparison }])),
  artifacts: artifacts.map(a => ({ file: a.file, tasks: a.tasks.length, requirements: a.requirements, threats: a.threats.length })),
  diff_check: { status: result.git_diff_check.status, stderr: result.git_diff_check.stderr },
  environment }, null, 2));
