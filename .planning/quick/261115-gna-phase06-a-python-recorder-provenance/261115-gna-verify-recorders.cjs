// 区分A Python recorder の隔離検証。実台帳・06-UAT.md・06-05-evidence は書き換えない。
// 使い方: node 261115-gna-verify-recorders.cjs <e2e-w01|real-report|legacy-reject [w01|w02|w03|w04|w05b|all]|static [w01|all]>
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync, execFileSync} = require('node:child_process');

const realRoot = path.resolve(__dirname, '../../..');
const realPhase = path.join(realRoot, '.planning/phases/06-release-validation');
const PHASE_REL = '.planning/phases/06-release-validation';
const fail = why => { throw Error(why); };
const check = (ok, why) => { if (!ok) fail(why); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = p => fs.readFileSync(p);
const MISSING = 'formal_provenance欠落';
const BASE_COMMIT = 'aceed78';

const RECORDERS = {
  w01: '06-05-record-w01-python.cjs',
  w02: '06-05-record-w02-settings.cjs',
  w03: '06-05-record-w03-python.cjs',
  w04: '06-05-record-w04.cjs',
  w05b: '06-05-record-w05b.cjs',
};
const PROVENANCE = '06-05-python-provenance.cjs';

// ---- 共通: ディレクトリ全体のsnapshot ----
function snap(dir) {
  const out = {};
  const visit = rel => {
    for (const item of fs.readdirSync(path.join(dir, rel), {withFileTypes: true})) {
      const key = rel ? `${rel}/${item.name}` : item.name;
      if (item.isDirectory()) visit(key);
      else out[key] = sha(read(path.join(dir, key)));
    }
  };
  visit('');
  return out;
}
function diff(a, b) {
  const changed = [];
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) if (a[k] !== b[k]) changed.push(k);
  return changed.sort();
}
function listNames(dir) {
  const out = [];
  const visit = rel => {
    for (const item of fs.readdirSync(path.join(dir, rel), {withFileTypes: true})) {
      const key = rel ? `${rel}/${item.name}` : item.name;
      out.push(key);
      if (item.isDirectory()) visit(key);
    }
  };
  visit('');
  return out.sort();
}

// ---- e2e-w01: temp repo に fixture を組み、実物のrecorderとmoduleを複製して動かす ----
function buildFixture() {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'pf-gna-'));
  const repo = path.join(base, 'repo'), home = path.join(base, 'home'), restored = path.join(base, 'restored');
  const phase = path.join(repo, PHASE_REL);
  const w = (rel, text, root = repo) => {
    const full = path.join(root, rel);
    fs.mkdirSync(path.dirname(full), {recursive: true});
    fs.writeFileSync(full, text);
    return full;
  };
  // Python入力と plugins
  const py = {
    'pagefolio.py': '# entry\n',
    'pagefolio/__main__.py': 'print(1)\n',
    'tests/test_startup_windows.py': '# harness fixture\n',
    [`${PHASE_REL}/06-05-w12a-driver.py`]: '# driver fixture\n',
  };
  for (const [k, v] of Object.entries(py)) w(k, v);
  w('plugins/page_info.py', '# plugin\n');
  w('pagefolio/__pycache__/ignored.py', '# ignored\n');
  // recorder と共通module は実物を複製する
  for (const f of [RECORDERS.w01, PROVENANCE]) fs.copyFileSync(path.join(realPhase, f), path.join(phase, f));
  // Phase04 report と偽CLI(USERPROFILE差し替え)
  const report = Buffer.from('---\nstatus: passed\ncovered_digest: "v4:sha256:fixture"\n---\n# fixture\n');
  w('.planning/phases/04-startup-control/04-VERIFICATION.md', report);
  w('.codex/gsd-core/bin/status.txt', 'passed\n', home);
  w('.codex/gsd-core/bin/gsd-tools.cjs',
    "const fs=require('node:fs');if(!process.argv.includes('verification.status'))process.exit(2);" +
    "console.log(JSON.stringify({status:fs.readFileSync(__dirname+'/status.txt','utf8').trim()}));\n", home);
  // 復元配布(PageFolio.exe と release-report.json)
  const exe = Buffer.from('fixture exe');
  const frozen = {'pagefolio.py': sha(Buffer.from(py['pagefolio.py'])), 'pagefolio/__main__.py': sha(Buffer.from(py['pagefolio/__main__.py']))};
  w('PageFolio.exe', exe, restored);
  w('release-report.json', JSON.stringify({run_id: 'rebuild-run-1', input_manifest: frozen}), restored);
  const {treeHash} = require(path.join(realPhase, PROVENANCE));
  const tree = treeHash(restored);
  const build = {
    generation: 5, version: 'v1.10.2',
    final_release: {
      final_dir: path.join(base, 'gone-final'), exe_sha256: sha(exe), tree_sha256: tree.hash, input_manifest_sha256: 'f'.repeat(64),
      runs: [{order: 'initial', run_id: 'initial-run-1'}, {order: 'rebuild', run_id: 'rebuild-run-1'}],
      loss_incident: {restored_final_dir: restored, restoration_verification: {embedded_report_run_id: 'rebuild-run-1'}},
    },
  };
  w(`${PHASE_REL}/06-BUILD-EVIDENCE.json`, JSON.stringify(build, null, 2) + '\n');
  // 台帳・SUPERSESSION・UAT
  const SUP = '06-05-evidence/PYTHON-INPUT-SUPERSESSION-20261106.json';
  const generation = 'python-input-0b788cdf0b1c';
  w(`${PHASE_REL}/${SUP}`, JSON.stringify({superseded_by: generation, rows: [{card: 'W01/normal@script'}, {card: 'W01/zoomed@script'}]}));
  const mk = (card, entry, condition, index) => ({
    subrow: `${condition}@${entry}`, card, entry, condition, evidence_kind: 'python-real', generation: 5, release_requirement: 'required',
    status: 'not-run', observations: {}, answer: '', raw_inputs: [], run_id: '', environment: {},
    python_input_generation: generation, supersedes: {path: SUP, row_index: index},
  });
  const ledger = {cases: [
    {id: 'W01', subrows: [
      mk('W01/normal@script', 'script', 'normal', 0), mk('W01/zoomed@script', 'script', 'zoomed', 1),
      {card: 'W01/normal@production-exe', entry: 'production-exe', evidence_kind: 'production-exe', generation: 5, release_requirement: 'required', status: 'pass'},
    ]},
    {id: 'W02', subrows: [{card: 'W02/settings@production-exe', entry: 'production-exe', generation: 5, release_requirement: 'required', status: 'pass'}]},
  ]};
  w(`${PHASE_REL}/06-MANUAL-EVIDENCE.json`, JSON.stringify(ledger, null, 2) + '\n');
  const uat = ['# UAT', '', '本受入は必須108行中23行pass・85行not-run・W11対象外2行not-run。以下は履歴。', '',
    '### W01/normal@script', '', '- **状態**: not-run / 再採取待ち', '- **旧入力の受入**: 別保存', '',
    '### W01/zoomed@script', '', '- **状態**: not-run / 再採取待ち', ''].join('\r\n') + '\nLF-only tail line\n';
  w(`${PHASE_REL}/06-UAT.md`, uat);
  // run dir と manifest
  const run = path.join(repo, '.planning/tmp/pagefolio-uat-test0001');
  const formal = {
    source_inputs: Object.fromEntries(Object.entries(py).map(([k, v]) => [k, sha(Buffer.from(v))]).sort(([a], [b]) => a < b ? -1 : 1)),
    original_plugins: {'page_info.py': sha(Buffer.from('# plugin\n'))},
    phase04: {status: 'passed', covered_digest: 'v4:sha256:fixture', report_sha256: sha(report)},
  };
  const manifest = {
    run, namespace: 'ns', case: 'W01', role: 'uat-owner-normal', fixture: path.join(run, 'uat-owner-normal'),
    environment: {os: 'Windows', is_admin: false, session_id: 1}, originals_before: {'pagefolio_settings.json': null, 'ocr_custom_prompt.md': null},
    formal_provenance: formal, source_commit: 'c'.repeat(40),
  };
  w(`${path.relative(repo, run)}/manifest.json`, JSON.stringify(manifest));
  w(`${path.relative(repo, run)}/provenance-before-stop.json`, JSON.stringify({matched: true}));
  w(`${path.relative(repo, run)}/uat-owner-normal/result.json`, JSON.stringify({result: 'primary'}));
  w(`${path.relative(repo, run)}/uat-owner-normal/focus-result.json`, JSON.stringify({result: 'completed'}));
  // session
  const session = {
    row: 'W01/normal@script', case: 'W01', condition: 'normal', entry: 'script', run, target_exe_sha256: sha(exe),
    outcome: 'answered', procedure_verdict: 'clean', procedure_assessment: {rerun_required: false},
    harness_peer: {returncode: 0, json: {result: {result: 'completed', constructed: 0, status_preserved: true}}},
    harness_inspect: {returncode: 0, json: {manifest, originals_unchanged: true,
      'focus-result.json': {result: 'completed', state_preserved: true, target_correct: true, focus_correct: true, placement: 'normal'}}},
    harness_stop: {returncode: 0},
    cleanup: {alive_after: [], terminated_owned: [], left_after_harness_stop: []},
    steps: [{step: 'prepared', windows: [{hwnd: 10, iconic: true}]},
      {step: 'after-peer', windows: [{hwnd: 10, iconic: false, zoomed: false}], foreground: {hwnd: 10}}],
    raw_inputs: [{key: 'state_after', text: '通常'}],
    answers: {state_after: '通常', geometry: 'はい', single: '1つ', status: '見える'},
    composed_answer: '通常 / はい / 1つ / 見える', finished_at: '2026-11-15T00:00:00Z',
  };
  const sessionName = 'W01_normal_at_script-20261115T000000Z.json';
  w(`${PHASE_REL}/06-05-evidence/${sessionName}`, JSON.stringify(session));
  return {base, repo, home, restored, phase, run, sessionName, session, manifest, formal, py, ledger, uat, SUP, generation, exe, report};
}

function runRecorder(fx, flags = []) {
  const recorder = path.join(fx.phase, RECORDERS.w01);
  const r = spawnSync(process.execPath, [recorder, fx.sessionName, ...flags], {
    cwd: fx.repo, encoding: 'utf8', env: {...process.env, USERPROFILE: fx.home}, timeout: 60000,
  });
  return {code: r.status, stdout: r.stdout || '', stderr: r.stderr || ''};
}

const editJson = (file, fn) => { const v = JSON.parse(read(file).toString('utf8')); fn(v); fs.writeFileSync(file, JSON.stringify(v, null, 2) + '\n'); };
const editBoth = (fx, fn) => {
  // session内のmanifestとrun/manifest.jsonを同じ変更で更新する
  const sessionFile = path.join(fx.phase, '06-05-evidence', fx.sessionName);
  editJson(sessionFile, s => fn(s.harness_inspect.json.manifest));
  editJson(path.join(fx.run, 'manifest.json'), fn);
};

// 改変13件: 名前, 改変, (任意)stderrに含まれるべき文字列
const MUTATIONS = [
  ['formal_provenance削除', fx => editBoth(fx, m => { delete m.formal_provenance; }), MISSING],
  ['harness(tests/test_startup_windows.py)内容変更', fx => fs.appendFileSync(path.join(fx.repo, 'tests/test_startup_windows.py'), '# changed\n')],
  ['tests/new_input.py追加', fx => fs.writeFileSync(path.join(fx.repo, 'tests/new_input.py'), '# new\n')],
  ['plugins変更', fx => fs.appendFileSync(path.join(fx.repo, 'plugins/page_info.py'), '# changed\n')],
  ['偽CLIがstaleを返す', fx => fs.writeFileSync(path.join(fx.home, '.codex/gsd-core/bin/status.txt'), 'stale\n')],
  ['04-VERIFICATION.mdのcovered_digest変更', fx => {
    const f = path.join(fx.repo, '.planning/phases/04-startup-control/04-VERIFICATION.md');
    fs.writeFileSync(f, read(f).toString('utf8').replace('fixture"', 'changed"'));
  }],
  ['provenance-before-stop matched:false', fx => fs.writeFileSync(path.join(fx.run, 'provenance-before-stop.json'), JSON.stringify({matched: false, error: 'x'}))],
  ['run/manifest.jsonのformal_provenance改変', fx => editJson(path.join(fx.run, 'manifest.json'), m => { m.formal_provenance.phase04.covered_digest = 'other'; })],
  ['同cardの重複行', fx => editJson(path.join(fx.phase, '06-MANUAL-EVIDENCE.json'), l => { l.cases[0].subrows.push({...l.cases[0].subrows[0]}); })],
  ['python_input_generation改変', fx => editJson(path.join(fx.phase, '06-MANUAL-EVIDENCE.json'), l => { l.cases[0].subrows[0].python_input_generation = 'python-input-000000000000'; })],
  ['supersedes.path改変', fx => editJson(path.join(fx.phase, '06-MANUAL-EVIDENCE.json'), l => { l.cases[0].subrows[0].supersedes.path = '06-05-evidence/other.json'; })],
  ['restored_final_dir削除(final_dirも無い)', fx => fs.rmSync(fx.restored, {recursive: true, force: true})],
  ['restoredのrelease-report.json改変(tree不一致)', fx => fs.appendFileSync(path.join(fx.restored, 'release-report.json'), ' ')],
];

function e2eW01() {
  const summary = {positives: [], mutations: []};
  const fx = buildFixture();
  try {
    // p1: --dry-run は exit 0 で、temp repo の全bytesが前後で同一
    const before = snap(fx.repo);
    const dry = runRecorder(fx, ['--dry-run']);
    check(dry.code === 0, `p1 dry-run exit=${dry.code}: ${dry.stderr}`);
    const dryOut = JSON.parse(dry.stdout);
    check(dryOut.dry_run === true && dryOut.status === 'validated' && dryOut.final_report_source === 'restored_final_dir', 'p1 出力が不正');
    check(diff(before, snap(fx.repo)).length === 0, 'p1 dry-runで書込が発生');
    summary.positives.push('p1 dry-run');
    // p2: 本記録
    const real = runRecorder(fx);
    check(real.code === 0, `p2 本記録 exit=${real.code}: ${real.stderr}`);
    const after = snap(fx.repo);
    const changed = diff(before, after);
    const allowed = f => f === `${PHASE_REL}/06-MANUAL-EVIDENCE.json` || f === `${PHASE_REL}/06-UAT.md` ||
      f.startsWith(`${PHASE_REL}/06-05-evidence/W01_normal_at_script-20261115T000000Z-raw/`);
    check(changed.every(allowed), 'p2 許可外のファイルが変化: ' + changed.filter(f => !allowed(f)).join(','));
    check(changed.includes(`${PHASE_REL}/06-MANUAL-EVIDENCE.json`) && changed.includes(`${PHASE_REL}/06-UAT.md`), 'p2 台帳またはUATが未更新');
    const ledger = JSON.parse(read(path.join(fx.phase, '06-MANUAL-EVIDENCE.json')).toString('utf8'));
    const row = ledger.cases[0].subrows[0];
    check(row.status === 'pass', 'p2 行がpassでない');
    check(row.python_input_generation === fx.generation && JSON.stringify(row.supersedes) === JSON.stringify(fx.ledger.cases[0].subrows[0].supersedes), 'p2 python_input_generation/supersedesが変化');
    const basis = row.observation_basis;
    check(JSON.stringify(basis.formal_provenance.source_inputs) === JSON.stringify(fx.formal.source_inputs), 'p2 source_inputsがfixtureと不一致');
    check(basis.observed_python_input.label === 'python-input-' + fx.formal.source_inputs['tests/test_startup_windows.py'].slice(0, 12), 'p2 observed label不一致');
    check(typeof row.environment.elevated === 'boolean', 'p2 environment.elevatedがbooleanでない');
    check(basis.final_report_source === 'restored_final_dir' && basis.provenance_before_stop === true, 'p2 final_report_source/provenance_before_stop不正');
    check(basis.recorder_sha256 === sha(read(path.join(fx.phase, RECORDERS.w01))) && basis.provenance_module_sha256 === sha(read(path.join(fx.phase, PROVENANCE))), 'p2 recorder/module hash不一致');
    check(JSON.stringify(ledger.cases[0].subrows.slice(1)) === JSON.stringify(fx.ledger.cases[0].subrows.slice(1)) && JSON.stringify(ledger.cases[1]) === JSON.stringify(fx.ledger.cases[1]), 'p2 他の行が変化');
    const raw = fs.readdirSync(path.join(fx.phase, '06-05-evidence/W01_normal_at_script-20261115T000000Z-raw'));
    check(raw.includes('run-provenance-before-stop.json') && raw.includes('run-manifest.json') && raw.includes('copies.json'), 'p2 raw copy不足');
    // UAT: card以外のCRLF行が不変、集計行が更新
    const uatOld = fx.uat.split('\n'), uatNew = read(path.join(fx.phase, '06-UAT.md')).toString('utf8').split('\n');
    check(uatNew.length === uatOld.length + 1, 'p2 UAT行数が+1でない');
    const k = uatOld.findIndex(l => l.startsWith('- **状態**: not-run'));
    check(uatNew[k].startsWith('- **状態**: pass') && uatNew[k].endsWith('\r') && uatNew[k + 1].startsWith('- **回答原文**: 通常') && uatNew[k + 1].endsWith('\r'), 'p2 UAT状態行/回答行の改行不正');
    const restOld = uatOld.filter((_, i) => i !== k), restNew = uatNew.filter((_, i) => i !== k && i !== k + 1);
    const diffs = restOld.map((l, i) => [l, restNew[i]]).filter(([a, b]) => a !== b);
    check(diffs.length === 1 && diffs[0][0].startsWith('本受入は必須108行中23行pass') && diffs[0][1].startsWith('本受入は必須108行中3行pass・105行not-run・W11対象外2行not-run。') && diffs[0][1].endsWith('\r'), 'p2 UAT集計行以外の行が変化: ' + JSON.stringify(diffs));
    summary.positives.push('p2 本記録');
    // p3: 同じsessionの再実行は拒否され、何も変わらない
    const again = snap(fx.repo);
    const second = runRecorder(fx);
    check(second.code !== 0, 'p3 再実行が成功してしまった');
    check(diff(again, snap(fx.repo)).length === 0, 'p3 再実行で書込が発生');
    summary.positives.push('p3 再実行拒否');
  } finally { fs.rmSync(fx.base, {recursive: true, force: true}); }
  for (const [name, mutate, expectText] of MUTATIONS) {
    const m = buildFixture();
    try {
      mutate(m);
      const before = snap(m.repo);
      let reason = '';
      for (const flags of [['--dry-run'], []]) {
        const r = runRecorder(m, flags);
        check(r.code !== 0, `改変「${name}」が${flags.join('') || '本記録'}で拒否されなかった`);
        if (expectText) check(r.stderr.includes(expectText), `改変「${name}」のstderrに${expectText}が無い: ${r.stderr.slice(0, 300)}`);
        check(diff(before, snap(m.repo)).length === 0, `改変「${name}」で拒否後にtemp repoが変化`);
        reason = (r.stderr.match(/^Error: (.*)$/m) || [])[1] || r.stderr.slice(0, 120);
      }
      summary.mutations.push(`${name} => ${reason}`);
    } finally { fs.rmSync(m.base, {recursive: true, force: true}); }
  }
  check(summary.mutations.length === 13, '改変件数が13でない');
  return summary;
}

// ---- real-report: 実repoの凍結入力を読取専用で照合 ----
function realReport() {
  const prov = require(path.join(realPhase, PROVENANCE));
  const build = JSON.parse(read(path.join(realPhase, '06-BUILD-EVIDENCE.json')).toString('utf8'));
  const {report, source, finalDir} = prov.resolveFinalReport({phase: realPhase, build});
  check(source === 'restored_final_dir', `sourceがrestored_final_dirでない: ${source}`);
  const files = Object.keys(report.input_manifest);
  check(files.length === 65, `input_manifestが65件でない: ${files.length}`);
  const drift = files.filter(f => sha(read(path.join(realRoot, f))) !== report.input_manifest[f]);
  check(drift.length === 0, 'drift: ' + drift.join(','));
  return {source, finalDir, run_id: report.run_id, input_manifest: files.length, drift: 0};
}

// ---- legacy-reject: 実repoの旧pass session 18件をdry-runで拒否できるか ----
function legacySessions() {
  const md = read(path.join(realPhase, '06-PYTHON-REUSE-AUDIT-20261106.md')).toString('utf8');
  const out = [];
  for (const m of md.matchAll(/^\| (W0[1-5][ab]?\/[^|\s]+@(?:script|module)) \| [^|]+ \| (W0[^|\s]+\.json) \|/gm)) {
    if (m[1].startsWith('W05c/')) continue;
    out.push({card: m[1], file: m[2]});
  }
  check(out.length === 18, `旧session表が18件でない: ${out.length}`);
  return out;
}
const recorderKey = file => file.startsWith('W01_') ? 'w01' : file.startsWith('W02_') || file.startsWith('W05a_') ? 'w02' :
  file.startsWith('W03_') ? 'w03' : file.startsWith('W04_') ? 'w04' : file.startsWith('W05b_') ? 'w05b' : fail('未知のsession: ' + file);

function realFingerprint() {
  return {
    ledger: sha(read(path.join(realPhase, '06-MANUAL-EVIDENCE.json'))),
    uat: sha(read(path.join(realPhase, '06-UAT.md'))),
    evidence: listNames(path.join(realPhase, '06-05-evidence')).join('\n'),
  };
}

function legacyReject(which) {
  const keys = which === 'all' ? Object.keys(RECORDERS) : [which];
  check(keys.every(k => RECORDERS[k]), 'recorder指定が不正: ' + which);
  const targets = legacySessions().filter(t => keys.includes(recorderKey(t.file)));
  check(targets.length > 0, '対象sessionが無い');
  if (which === 'w01') check(targets.length === 4, 'W01は4件のはず');
  if (which === 'all') check(targets.length === 18, '全体は18件のはず');
  const before = realFingerprint();
  const results = [];
  for (const t of targets) {
    const r = spawnSync(process.execPath, [path.join(realPhase, RECORDERS[recorderKey(t.file)]), t.file, '--dry-run'], {cwd: realRoot, encoding: 'utf8', timeout: 60000});
    check(r.status !== 0, `旧session ${t.file} が拒否されなかった`);
    check((r.stderr || '').includes(MISSING), `旧session ${t.file} のstderrに${MISSING}が無い: ${(r.stderr || '').slice(0, 300)}`);
    results.push(t.file);
  }
  const after = realFingerprint();
  check(JSON.stringify(before) === JSON.stringify(after), '実台帳/UAT/evidence一覧が変化');
  return {rejected: results.length, sessions: results};
}

// ---- static ----
function staticCheck(which) {
  const keys = which === 'all' ? Object.keys(RECORDERS) : ['w01'];
  const problems = [];
  for (const key of keys) {
    const text = read(path.join(realPhase, RECORDERS[key])).toString('utf8');
    const code = text.split('\n').filter(l => !/^\s*\/\//.test(l)).join('\n');
    if (!text.includes("require('./06-05-python-provenance.cjs')")) problems.push(`${key}: moduleをrequireしていない`);
    if (code.includes('final_release.final_dir')) problems.push(`${key}: final_release.final_dirを直接参照`);
    if (!code.includes("'--dry-run'")) problems.push(`${key}: --dry-run未対応`);
  }
  if (which === 'all') {
    const w12c = read(path.join(realPhase, '06-05-record-w12c.cjs')).toString('utf8');
    if (!w12c.includes('elevated:manifest.environment.is_admin')) problems.push('w12c: elevated出力が無い');
  }
  // 変更禁止ファイルのhashがBASE_COMMITと一致
  const frozen = ['06-05-record-w05c-python.cjs', '06-05-record-w05c-exe.cjs', '06-05-record-w12a.cjs', '06-05-record-w12b.cjs', '06-05-w12a-driver.py'].map(f => `${PHASE_REL}/${f}`);
  for (const f of fs.readdirSync(path.join(realPhase, '06-05-drivers'))) if (f.endsWith('.py')) frozen.push(`${PHASE_REL}/06-05-drivers/${f}`);
  for (const f of frozen) {
    const base = execFileSync('git', ['show', `${BASE_COMMIT}:${f}`], {cwd: realRoot, maxBuffer: 1 << 26});
    if (sha(base) !== sha(read(path.join(realRoot, f)))) problems.push(`${f}: ${BASE_COMMIT}と不一致`);
  }
  check(problems.length === 0, problems.join(' / '));
  return {checked: keys, frozen_files: frozen.length};
}

function main() {
  const [mode, arg] = process.argv.slice(2);
  let result;
  if (mode === 'e2e-w01') result = e2eW01();
  else if (mode === 'real-report') result = realReport();
  else if (mode === 'legacy-reject') result = legacyReject(arg || 'all');
  else if (mode === 'static') result = staticCheck(arg === 'all' ? 'all' : 'w01');
  else fail('usage: e2e-w01 | real-report | legacy-reject [w01|w02|w03|w04|w05b|all] | static [w01|all]');
  console.log(JSON.stringify({mode, arg: arg || null, ok: true, ...result}));
}
try { main(); } catch (e) { console.error('FAIL: ' + e.message); process.exit(1); }
