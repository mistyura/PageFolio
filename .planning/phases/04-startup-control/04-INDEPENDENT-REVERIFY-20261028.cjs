// Phase04独立再検証。製品/試験/既存証拠は読取りのみ。
const fs = require('node:fs');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const dir = '.planning/phases/04-startup-control';
const src = '.planning/debug/quality-gate-unblock-20261028';
const cli = 'C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs';
const read = p => fs.readFileSync(p, 'utf8');
const load = p => JSON.parse(read(p));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const run = args => {
  const r = cp.spawnSync(process.execPath, [cli, 'query', ...args], {encoding:'utf8', timeout:10000});
  let data; try { data = JSON.parse(r.stdout); } catch { data = r.stdout; }
  return { args, exit:r.status, data, stderr:r.stderr, error:r.error?.message };
};
const full = load(`${src}/full.json`);
const gates = load(`${dir}/04-GATES-CURRENT-20261028.json`);
const final = load(`${dir}/04-GATES-CURRENT-FINAL-20261028.json`);
const current = Object.entries(full.after).map(([file, expected]) => ({file, expected, actual:hash(file)}));
const xml = read(`${src}/full.xml`);
const testcase = [...xml.matchAll(/<testcase\b([^>]+)>/g)].map(m => ({
  classname:m[1].match(/classname="([^"]*)"/)?.[1],
  name:m[1].match(/(?:^|\s)name="([^"]*)"/)?.[1],
  time:m[1].match(/time="([^"]*)"/)?.[1]
}));
const inputs = ['pagefolio.py', 'pagefolio/__init__.py', 'pagefolio/__main__.py', 'pagefolio/app.py', 'pagefolio/lang.py',
  'pagefolio/startup_control.py', 'pagefolio/startup_focus.py', 'pagefolio/startup_notice.py', 'pagefolio/startup_win32.py',
  'pagefolio/startup_wake.py', 'tests/test_gsd_dod.py', 'tests/test_startup_control.py', 'tests/test_startup_focus.py',
  'tests/test_startup_notice.py', 'tests/test_startup_windows.py', 'tests/test_startup_wake.py', 'tests/startup_wake_child.py',
  'tests/startup_foreground_audit.py', 'tests/test_startup_foreground_audit.py'];
const markers = [];
for (const file of inputs) read(file).split(/\r?\n/).forEach((line, i) => {
  if (/TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|placeholder|except\s*:|#\s*type:\s*ignore|@pytest\.mark\.skip|@unittest\.skip/.test(line))
    markers.push({file,line:i+1,text:line});
});
const plans = fs.readdirSync(dir).filter(p => /-PLAN\.md$/.test(p));
const checks = plans.map(p => ({plan:p,
  artifacts:run(['verify.artifacts',`${dir}/${p}`]),
  links:run(['verify.key-links',`${dir}/${p}`])}));
const evidence = Object.entries(gates.evidence).map(([file,expected]) => ({file,expected,actual:hash(file)}));
const env = cp.spawnSync('.venv/Scripts/python.exe', ['-c', 'import sys,platform,json,importlib.metadata as m;print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={n:m.version(n) for n in ["pytest","ruff","PyMuPDF","Pillow","tkinterdnd2"]})))'], {encoding:'utf8',timeout:10000});
const environment = JSON.parse(env.stdout);
const result = {
  captured:new Date().toISOString(), scope:'Phase04独立再検証。既存pass21truthを現行コードと生結果へ再結合。全件再実行なし。',
  prior_report:{sha256:hash(`${dir}/04-VERIFICATION.md`),verified:'2026-10-28T01:12:08Z',status:'passed',score:'21/21'},
  full:{record:full.records,before_after_equal:JSON.stringify(full.before)===JSON.stringify(full.after),changed:full.changed,
    total:current.length,matched:current.filter(x=>x.expected===x.actual).length,
    differences:current.filter(x=>x.expected!==x.actual), python_total:current.filter(x=>x.file.endsWith('.py')).length,
    python_differences:current.filter(x=>x.file.endsWith('.py')&&x.expected!==x.actual),
    suite:xml.match(/<testsuite\s[^>]+>/)?.[0],summary:read(`${src}/full-0.stdout.txt`).split(/\r?\n/).slice(-3),
    named_testcases:testcase.filter(x=>/startup|gsd_dod/.test(x.classname))},
  gate_evidence:evidence, gate_evidence_unchanged:evidence.every(x=>x.actual===x.expected),
  gate_final_sha256:hash(`${dir}/04-GATES-CURRENT-FINAL-20261028.json`),
  gate_report_hashes:Object.entries(final.reports).map(([file,expected])=>({file,expected,actual:hash(file)})),
  environment, environment_matches:Object.keys(environment).every(k=>JSON.stringify(environment[k])===JSON.stringify(gates.environment[k])) && hash('.venv/Scripts/python.exe')===gates.environment.python_sha256,
  runtime_sha256:hash('.venv/Scripts/python.exe'), inputs:inputs.map(file=>({file,sha256:hash(file)})),markers,checks,
  decision_coverage:run(['check.decision-coverage-verify',dir,`${dir}/04-CONTEXT.md`]),
  roadmap:run(['roadmap.get-phase','4','--raw']),milestone:run(['roadmap.analyze','--raw']),
  probe_declarations:plans.flatMap(p=>read(`${dir}/${p}`).split(/\r?\n/).filter(l=>/probe-[^\s]+\.sh/.test(l))),
  tests_reexecuted:false, servers_started:false, product_modified:false,
};
const out = `${dir}/04-INDEPENDENT-REVERIFY-20261028${process.argv.includes('--corrected')?'-CORRECTED':process.argv.includes('--final')?'-FINAL':''}.json`;
fs.writeFileSync(out, JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output:out,sha256:hash(out),matched:result.full.matched,total:result.full.total,
  python_total:result.full.python_total,python_differences:result.full.python_differences,
  differences:result.full.differences.map(x=>x.file),suite:result.full.suite,evidence_unchanged:result.gate_evidence_unchanged,
  environment_matches:result.environment_matches,checks:checks.map(c=>({plan:c.plan,artifacts:c.artifacts.data,links:c.links.data})),
  decision:result.decision_coverage,markers},null,2));
if (result.full.python_differences.length || !result.gate_evidence_unchanged || !result.environment_matches || checks.some(c=>c.artifacts.exit!==0)) process.exitCode=1;
