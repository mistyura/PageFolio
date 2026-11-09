// W11承認差分の読取専用再検証。製品/試験/証拠を書き換えない。
const fs = require('node:fs');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const dir = '.planning/phases/04-startup-control';
const src = '.planning/phases/06-release-validation/06-07-evidence/native-files-20261028';
const cli = 'C:/Users/shdwf/.codex/gsd-core/bin/gsd-tools.cjs';
const read = p => fs.readFileSync(p, 'utf8');
const load = p => JSON.parse(read(p));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const run = args => {
  const r = cp.spawnSync(process.execPath, [cli, ...args], {encoding:'utf8',timeout:10000});
  let data; try { data=JSON.parse(r.stdout); } catch { data=r.stdout; }
  return {args,exit:r.status,data,stderr:r.stderr};
};
const compare = map => {
  const rows=Object.entries(map).map(([file,expected])=>({file,expected,actual:fs.existsSync(file)?hash(file):null}));
  return {total:rows.length,matched:rows.filter(r=>r.expected===r.actual).length,differences:rows.filter(r=>r.expected!==r.actual)};
};
const prior=load(`${dir}/04-INDEPENDENT-REVERIFY-20261028-CORRECTED.json`);
const full=load(`${src}/result.json`);
const before=load(`${src}/before.json`);
const xml=read(`${src}/junit.xml`);
const tests=[...xml.matchAll(/<testcase\b([^>]*?)(?:\/>|>[\s\S]*?<\/testcase>)/g)].map(m=>({name:m[1].match(/(?:^|\s)name="([^"]*)"/)?.[1],classname:m[1].match(/classname="([^"]*)"/)?.[1],failed:/<(failure|error|skipped)\b/.test(m[0])}));
const previousNames=prior.full.named_testcases.map(t=>[t.classname,t.name].join('::'));
const currentNames=new Set(tests.filter(t=>!t.failed).map(t=>[t.classname,t.name].join('::')));
const scopePath='.planning/phases/06-release-validation/06-RELEASE-SCOPE.json';
const scope=load(scopePath);
const approval=read(scope.approval_path);
const carry=read('.planning/phases/06-release-validation/06-UAT-CARRYOVER.md');
const cases=load('.planning/phases/06-release-validation/06-MANUAL-EVIDENCE.json');
const subrows=cases.cases.flatMap(c=>c.subrows);
const deferred=subrows.filter(r=>r.release_requirement==='deferred');
const gates=Object.fromEntries(['04-VALIDATION.md','04-SECURITY.md','04-UI-REVIEW.md','04-REVIEW.md','04-REVIEW-DISPOSITION.md'].map(f=>[`${dir}/${f}`,hash(`${dir}/${f}`)]));
const oldGates=Object.fromEntries(prior.gate_report_hashes.filter(r=>!r.file.endsWith('VERIFICATION.md')).map(r=>[r.file,r.actual]));
const product=compare(Object.fromEntries(prior.inputs.map(r=>[r.file,r.sha256])));
const checks={
  original_21_truth_inputs_unchanged:product.differences.length===0,
  previous_gate_reports_unchanged:compare(oldGates).differences.length===0,
  full_exit_zero:full.code===0,
  full_inputs_unchanged:JSON.stringify(full.before)===JSON.stringify(full.after)&&full.changed.length===0,
  before_file_matches_record:JSON.stringify(before)===JSON.stringify(full.before),
  full_junit_2231_passed:tests.length===2231&&tests.every(t=>!t.failed),
  previous_named_cases_present:previousNames.every(n=>currentNames.has(n)),
  scope_approval_hash_matches:hash(scope.approval_path)===scope.approval_sha256,
  scope_exact:scope.approved===true&&scope.scope_id==='single-login-session'&&scope.approval_id==='W11-B-20261028'&&scope.case_count===31&&scope.total_subrows===110&&scope.required_subrows===108&&scope.deferred_subrows===2&&JSON.stringify([...scope.deferred_cards].sort())===JSON.stringify(['W11/other-session@production-exe','W11/other-session@script']),
  carryover_preserves_limits:carry.includes('108行')&&carry.includes('not-run / deferred')&&carry.includes('15609ms')&&carry.includes('15140ms')&&carry.includes('flagged-unverified')&&carry.includes('unclassified/unresolved'),
  approval_not_release:approval.includes('出荷承認や実機試験の合格回答ではない'),
  manual_rows_exact:cases.cases.length===31&&subrows.length===110&&subrows.filter(r=>r.release_requirement==='required').length===108&&deferred.length===2&&deferred.every(r=>scope.deferred_cards.includes(r.card)&&r.status==='not-run'&&r.approval_id===scope.approval_id),
};
const evidenceFiles=['result.json','before.json','junit.xml','stdout.txt','checks.json'].map(f=>`${src}/${f}`);
const result={captured:new Date().toISOString(),scope:'Phase04承認範囲の限定再検証。W11 2行以外の免除なし。',prior_verified:'2026-10-28T05:02:09Z',product,gate_report_comparison:compare(oldGates),gate_report_hashes:gates,full:{started:full.started,finished:full.finished,argv:full.argv,code:full.code,input_count:Object.keys(before).length,current_inputs:compare(before),junit_suite:xml.match(/<testsuite\s[^>]+>/)?.[0],test_count:tests.length,previous_named_count:previousNames.length,missing_named:previousNames.filter(n=>!currentNames.has(n)),summary:read(`${src}/stdout.txt`).trim().split(/\r?\n/).at(-1)},scope_contract:scope,manual_evidence_keys:Object.keys(cases),evidence_hashes:Object.fromEntries([...evidenceFiles,scopePath,scope.approval_path,'.planning/phases/06-release-validation/06-UAT-CARRYOVER.md'].map(f=>[f,hash(f)])),checks,decision_coverage:run(['query','check.decision-coverage-verify',dir,`${dir}/04-CONTEXT.md`]),roadmap:run(['query','roadmap.get-phase','04','--raw']),tests_reexecuted:false,gui_started:false,build_started:false,product_modified:false};
console.log(JSON.stringify(result,null,2));
if(Object.values(checks).some(v=>!v)||result.decision_coverage.exit!==0)process.exitCode=1;
