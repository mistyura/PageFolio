// W05c(script/module): 終了確認で「いいえ」→編集・排他の維持。
// test_startup_windows.py --uat の native-quit run を、利用者回答の原文と機械観測で照合して台帳へ記録する。
// 回答がドライバ経由でない場合は、原文・出所・採用承認を回答ファイル(06-05-evidence/*.json)に置き、
// run 内の観測記録の原文と完全一致することを確かめる。照合が1つでも合わなければ何も書かない。
// 使い方: node 06-05-record-w05c-python.cjs W05c_quit-no_at_<entry>-<UTC>.json [--dry-run]
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const phase = __dirname, root = path.resolve(phase, '../../..');
const name = process.argv[2], dryRun = process.argv.includes('--dry-run');
const assert = (ok, why) => { if (!ok) throw Error(why); };
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const mtime = p => fs.statSync(p).mtimeMs;

assert(/^W05c_quit-no_at_(script|module)-\d{8}T\d{6}Z\.json$/.test(name || ''), 'unexpected answer filename');
const relative = '06-05-evidence/' + name, raw = fs.readFileSync(path.join(phase, relative)), s = JSON.parse(raw);
assert(s.case === 'W05c' && s.condition === 'quit-no' && s.row === `W05c/quit-no@${s.entry}`, 'row mismatch');
assert(name.includes(`_at_${s.entry}-`), 'entry/filename mismatch');

// 回答: 原文が run 内の観測記録と完全一致し、採用承認がある
const answer = s.answer_original;
assert(typeof answer === 'string' && answer.trim().length > 0, 'answer missing');
const obsPath = path.join(root, s.observation_record), obsRaw = fs.readFileSync(obsPath);
assert(hash(obsRaw) === s.observation_record_sha256, 'observation record changed');
assert(obsRaw.toString('utf8').includes(`回答原文: 「${answer}」`), 'answer not found verbatim in observation record');
assert(s.adoption && s.adoption.approved_by && s.adoption.approved_at && s.adoption.decision, 'adoption approval missing');
const normalized = answer.normalize('NFKC');
if (s.entry === 'module') {
  assert(answer.includes('いいえを押し'), 'answer does not state No was pressed');
  assert(normalized.includes('1・2ページが横向き') && normalized.includes('3ページが縦向き'), 'answer does not describe the kept edit');
}

// run: 隔離 native-quit owner(手動)。二次起動2回(確認中・回答後)
const run = path.resolve(root, s.run);
assert(run.startsWith(path.join(root, '.planning', 'tmp') + path.sep), 'unexpected run root');
assert(obsPath.startsWith(run + path.sep), 'observation record outside run');
const manifest = readJson(path.join(run, 'manifest.json')), inspection = readJson(path.join(run, 'inspection.json'));
const isV3 = s.schema === 'w05c-v3';
assert(isV3 ? manifest.w05c_schema === s.schema && s.entry === 'script' : !manifest.w05c_schema && !s.schema, 'unknown/mixed collection schema');
const afterLabel = isV3 ? 'after_no' : 'after_answer';
assert(manifest.case === 'native-quit' && manifest.role === 'uat-owner-native-quit', 'not a native-quit run');
assert(manifest.expected_owner && manifest.expected_owner.manual === true, 'not a manual run (automatic No is not acceptance)');
const owner = path.join(run, 'uat-owner-native-quit');
assert(path.resolve(manifest.fixture) === owner, 'fixture mismatch');
for (const marker of ['ready', 'focus-ready', 'quit-cancelled']) assert(fs.existsSync(path.join(owner, marker)), 'owner marker missing: ' + marker);
assert(!fs.existsSync(path.join(owner, 'manual-deadline')), 'manual safety deadline fired');
assert(inspection.originals_unchanged === true, 'originals changed');
const primary = inspection['result.json'];
assert(primary.result === 'primary' && primary.constructed === 1 && primary.restored === 2 && primary.status_preserved, 'primary did not keep ownership through both peers');
const focus = inspection['focus-result.json'];
assert(focus.state_preserved === true && focus.document_pages === 3 && JSON.stringify(focus.page_rotations) === '[90,90,0]', 'edited state not kept');

const ownerId = { pid: manifest.expected_owner.pid, created: manifest.expected_owner.process_created };
assert(Object.keys(s.peers).sort().join(',') === afterLabel + ',during_confirm', 'exactly two peers required');
const peers = {};
for (const [label, dir] of Object.entries(s.peers)) {
  assert(/^peer-[0-9a-f]{32}$/.test(dir), 'unexpected peer dir: ' + dir);
  const full = path.join(run, dir), result = readJson(path.join(full, 'result.json')), expected = readJson(path.join(full, 'expected-owner.json'));
  assert(result.constructed === 0 && result.status_preserved === true, `${label}: peer became primary`);
  assert(expected.pid === ownerId.pid && expected.process_created === ownerId.created, `${label}: peer saw a different owner`);
  const moduleEntry = fs.readFileSync(path.join(full, 'stderr.log'), 'utf8').includes("'pagefolio.__main__' found in sys.modules");
  assert(moduleEntry === (s.entry === 'module'), `${label}: peer entry is not ${s.entry}`);
  peers[label] = { dir, full, result, at: mtime(path.join(full, 'result.json')) };
}
// 時系列: 準備完了 → 確認中の二次起動 → いいえ(quit-cancelled) → 回答後の二次起動にownerが応答して
// 状態を記録(focus-result。二次起動ごとに上書き) → 回答後の二次起動が完了
const at = {
  focus_ready: mtime(path.join(owner, 'focus-ready')),
  peer_during_confirm: peers.during_confirm.at,
  quit_cancelled: mtime(path.join(owner, 'quit-cancelled')),
  focus_result: mtime(path.join(owner, 'focus-result.json')),
  ['peer_' + afterLabel]: peers[afterLabel].at,
};
const order = Object.values(at);
assert(order.every((v, n) => n === 0 || order[n - 1] <= v), 'event order mismatch: ' + JSON.stringify(at));
const iso = Object.fromEntries(Object.entries(at).map(([k, v]) => [k, new Date(v).toISOString()]));

let v2 = null;
let v3 = null;
if (s.entry === 'script' && !isV3) {
  const { validate } = require('./06-05-w05c-evidence.cjs');
  const logRaw = fs.readFileSync(path.join(owner, 'w05c-events.jsonl'));
  const lines = logRaw.toString('utf8').trimEnd().split('\n');
  const events = lines.map(line => JSON.parse(line));
  const checked = readJson(path.join(run, 'w05c-check-before_stop.json'));
  const firstCheck = readJson(path.join(run, 'w05c-check-before_peer.json'));
  assert(checked.ok === true && firstCheck.ok === true, 'pre-collection checks missing/failed');
  for (const check of [firstCheck, checked]) {
    const answerRecord = Object.fromEntries(Object.entries(s).filter(([key]) => key !== 'peers'));
    assert(check.run_id === path.basename(run) && JSON.stringify(check.answer_record) === JSON.stringify(answerRecord) &&
      path.resolve(check.answer_path) === path.resolve(phase, relative), 'check/answer binding mismatch');
  }
  const snapshot = checked.snapshot, final = readJson(path.join(owner, 'w05c-observer-final.json'));
  const identity = {
    run_id: path.basename(run), pid: ownerId.pid, process_created: ownerId.created,
    entry: s.entry, manual: manifest.expected_owner.manual,
    diagnostic_only: manifest.diagnostic_only, peers: s.peers,
  };
  assert(hash(Buffer.from(lines.slice(0, firstCheck.snapshot.events).join('\n') + '\n')) === firstCheck.snapshot.log_sha256, 'before-peer log changed');
  validate(events.slice(0, firstCheck.snapshot.events), firstCheck.snapshot, null, s, identity, 'before_peer');
  assert(hash(logRaw) === final.sha256, 'final event log changed');
  assert(hash(Buffer.from(lines.slice(0, snapshot.events).join('\n') + '\n')) === snapshot.log_sha256, 'pre-collection log changed');
  assert(hash(fs.readFileSync(path.join(owner, 'quit-cancelled'))) === snapshot.marker_sha256, 'marker changed');
  assert(hash(fs.readFileSync(path.join(owner, 'w05c-pre-collection.json'))) ===
    hash(fs.readFileSync(path.join(run, 'w05c-collection-before', 'w05c-pre-collection.json'))), 'pre-stop snapshot not preserved');
  const beforeOwner = readJson(path.join(run, 'w05c-collection-before', 'owner.json'));
  const afterOwner = readJson(path.join(run, 'w05c-collection-after', 'owner.json'));
  assert(beforeOwner.already_exited === false && afterOwner.exited === true &&
    [beforeOwner, afterOwner].every(o => o.pid === ownerId.pid && o.process_created === ownerId.created), 'owner exit not verified');
  assert(Date.parse(beforeOwner.utc) > Date.parse(events[snapshot.events - 1].utc), 'collection started before snapshot');
  v2 = validate(events, snapshot, final, s, identity);
  for (const stage of ['before', 'after']) {
    const dir = path.join(run, 'w05c-collection-' + stage), copies = readJson(path.join(dir, 'copies.json'));
    assert(copies.run_id === path.basename(run), 'collection run mismatch');
    for (const [name, expected] of Object.entries(copies.files)) {
      assert(path.basename(name) === name && hash(fs.readFileSync(path.join(dir, name))) === expected, 'collection copy changed: ' + name);
    }
  }
}
if (isV3) {
  const { machine, adoption } = require('./06-05-w05c-v3.cjs');
  assert(!fs.existsSync(path.join(run, 'w05c-v3-failed.json')), 'failed v3 collection');
  const collectionPath = path.join(run, 'w05c-v3-collection.json');
  const collection = readJson(collectionPath);
  assert(hash(fs.readFileSync(collectionPath)) === s.collection_sha256, 'sealed collection changed');
  assert(collection.status === 'machine_collected_pending_answer', 'collection incomplete');
  for (const [name, expected] of Object.entries(collection.files)) {
    const full = path.resolve(run, name);
    assert(full.startsWith(run + path.sep) && hash(fs.readFileSync(full)) === expected, 'sealed file changed: ' + name);
  }
  const first = readJson(path.join(run, 'w05c-v3-before_peer.json'));
  const checked = readJson(path.join(run, 'w05c-v3-before_stop.json'));
  const final = readJson(path.join(owner, 'w05c-observer-final.json'));
  const logRaw = fs.readFileSync(path.join(owner, 'w05c-events.jsonl'));
  const lines = logRaw.toString('utf8').trimEnd().split('\n'), events = lines.map(JSON.parse);
  const plan = manifest.w05c_plan;
  assert(plan.schema === 'w05c-v3' && plan.plan_sha256 === collection.plan_sha256, 'manifest/collection plan mismatch');
  assert(typeof plan.original_json === 'string' && hash(Buffer.from(plan.original_json)) === plan.plan_sha256, 'original plan changed');
  const originalPlan = JSON.parse(plan.original_json);
  assert(JSON.stringify(Object.fromEntries(Object.entries(plan).filter(([k]) => !['original_json', 'plan_sha256'].includes(k)))) ===
    JSON.stringify(originalPlan), 'plan fields changed');
  assert(JSON.stringify(readJson(path.join(owner, 'w05c-plan.json'))) === JSON.stringify(plan), 'owner plan changed');
  assert(originalPlan.source_inputs && Object.keys(originalPlan.source_inputs).length > 0, 'source inputs missing');
  for (const [name, expected] of Object.entries(originalPlan.source_inputs)) {
    const full = path.resolve(root, name);
    assert(full.startsWith(root + path.sep) && hash(fs.readFileSync(full)) === expected, 'collection input drift: ' + name);
  }
  const identity = {
    run_id: path.basename(run), pid: ownerId.pid, process_created: ownerId.created,
    entry: s.entry, manual: manifest.expected_owner.manual, diagnostic_only: manifest.diagnostic_only,
    peers: s.peers, schema: s.schema, plan_sha256: plan.plan_sha256,
    observation_seconds: plan.observation_seconds, collection_sha256: s.collection_sha256,
  };
  assert(JSON.stringify(collection.identity.peers) === JSON.stringify(s.peers), 'collection peer mismatch');
  const requiredSealed = ['manifest.json', 'inspection.json', 'w05c-v3-before_peer.json', 'w05c-v3-before_stop.json',
    'uat-owner-native-quit/w05c-events.jsonl', 'uat-owner-native-quit/w05c-observer-final.json',
    'uat-owner-native-quit/quit-cancelled', 'uat-owner-native-quit/w05c-plan.json',
    'w05c-v3-peer-started', 'w05c-v3-commands.jsonl', 'w05c-collection-before/owner.json', 'w05c-collection-after/owner.json'];
  const sealedNames = Object.keys(collection.files).map(n => n.replaceAll('\\', '/'));
  assert(requiredSealed.every(n => sealedNames.includes(n)), 'required file not sealed');
  for (const [check, stage] of [[first, 'before_peer'], [checked, 'before_stop']]) {
    assert(check.ok === true && check.schema === s.schema && check.run_id === identity.run_id, 'machine check missing/failed');
    const prefix = Buffer.from(lines.slice(0, check.snapshot.events).join('\n') + '\n');
    assert(hash(prefix) === check.snapshot.log_sha256, 'machine prefix changed');
    machine(events.slice(0, check.snapshot.events), check.snapshot, null, identity, stage);
  }
  assert(hash(logRaw) === final.sha256, 'final log changed');
  assert(hash(fs.readFileSync(path.join(owner, 'quit-cancelled'))) === checked.snapshot.marker_sha256, 'marker changed');
  assert(hash(fs.readFileSync(path.join(owner, 'w05c-pre-collection.json'))) ===
    hash(fs.readFileSync(path.join(run, 'w05c-collection-before', 'w05c-pre-collection.json'))), 'snapshot not preserved');
  const before = readJson(path.join(run, 'w05c-collection-before/owner.json'));
  const after = readJson(path.join(run, 'w05c-collection-after/owner.json'));
  assert(before.already_exited === false && after.exited === true &&
    [before, after].every(o => o.pid === ownerId.pid && o.process_created === ownerId.created), 'owner exit not verified');
  assert(Date.parse(before.utc) > Date.parse(events[checked.snapshot.events - 1].utc), 'collection before snapshot');
  assert(Date.parse(after.utc) <= Date.parse(collection.completed_at), 'sealed before exit');
  for (const stage of ['before', 'after']) {
    const dir = path.join(run, 'w05c-collection-' + stage), copies = readJson(path.join(dir, 'copies.json'));
    assert(copies.run_id === path.basename(run), 'collection run mismatch');
    for (const [name, expected] of Object.entries(copies.files)) {
      assert(path.basename(name) === name && hash(fs.readFileSync(path.join(dir, name))) === expected, 'collection copy changed: ' + name);
    }
  }
  v3 = adoption(events, checked.snapshot, final, s, identity, collection);
}

// 凍結入力: 現行buildの入力manifestと一致し、試行後に変更されていない
const build = readJson(path.join(phase, '06-BUILD-EVIDENCE.json'));
const finalDir = (build.final_release.loss_incident || {}).restored_final_dir || build.final_release.final_dir;
const report = readJson(path.join(finalDir, 'release-report.json'));
assert(build.generation === 5 && report.run_id === build.final_release.runs.find(r => r.order === 'rebuild').run_id, 'generation mismatch');
const trialStart = mtime(path.join(run, 'manifest.json'));
for (const [file, expected] of Object.entries(report.input_manifest)) {
  const full = path.join(root, file);
  assert(hash(fs.readFileSync(full)) === expected, 'frozen input drift: ' + file);
  assert(mtime(full) <= trialStart, 'frozen input modified after trial: ' + file);
}

// 台帳とカード: 未判定の世代5必須行だけを更新する
const ledgerPath = path.join(phase, '06-MANUAL-EVIDENCE.json'), ledger = readJson(ledgerPath);
const row = ledger.cases.find(c => c.id === 'W05c').subrows.find(r => r.card === s.row);
assert(row && row.status === 'not-run' && row.generation === 5 && row.release_requirement === 'required', 'row already judged or wrong generation');
const uatPath = path.join(phase, '06-UAT.md'), uat = fs.readFileSync(uatPath, 'utf8'), marker = '### ' + s.row + '\n', start = uat.indexOf(marker);
assert(start >= 0, 'card missing');
const end = uat.indexOf('\n### ', start + marker.length), stop = end < 0 ? uat.length : end, card = uat.slice(start, stop);
assert(card.includes('- **状態**: not-run'), 'UAT row already judged');

const dest = path.join(phase, '06-05-evidence', name.replace('.json', '-raw'));
assert(!fs.existsSync(dest), 'raw already preserved');
const pending = [];
const take = (label, dir, files) => { for (const file of files) { const source = path.join(dir, file); assert(fs.existsSync(source), 'raw missing: ' + file); pending.push({ source, target: path.join(dest, label + '-' + file), bytes: fs.readFileSync(source) }); } };
take('run', run, ['manifest.json', 'inspection.json', path.basename(obsPath)]);
take('primary', owner, ['result.json', 'focus-result.json', 'resource-audit.json', 'initializing.json', 'ready', 'focus-ready', 'quit-cancelled', 'stderr.log', 'stdout.log', 'traceback.log']);
for (const [label, p] of Object.entries(peers)) take('peer-' + label, p.full, ['result.json', 'expected-owner.json', 'resource-audit.json', 'stderr.log', 'stdout.log', 'traceback.log']);
if (v2) {
  take('v2', owner, ['w05c-events.jsonl', 'w05c-observer-final.json', 'w05c-pre-collection.json', 'w05c-pre-collection-stack.log']);
  take('checks', run, ['w05c-check-before_peer.json', 'w05c-check-before_stop.json']);
  for (const stage of ['before', 'after']) {
    const dir = path.join(run, 'w05c-collection-' + stage);
    take('collection-' + stage, dir, fs.readdirSync(dir));
  }
}
if (v3) {
  take('v3', owner, ['w05c-plan.json', 'w05c-events.jsonl', 'w05c-observer-final.json', 'w05c-pre-collection.json', 'w05c-pre-collection-stack.log']);
  take('checks', run, ['w05c-v3-before_peer.json', 'w05c-v3-before_stop.json', 'w05c-v3-collection.json', 'w05c-v3-peer-started', 'w05c-v3-commands.jsonl']);
  for (const stage of ['before', 'after']) {
    const dir = path.join(run, 'w05c-collection-' + stage);
    take('collection-' + stage, dir, fs.readdirSync(dir));
  }
}

const passed = ledger.cases.flatMap(c => c.subrows).filter(r => r.release_requirement === 'required' && r.status === 'pass').length + 1;
const composed = `W05c quit-no ${s.entry}：${answer}`;
const preparationNote = isV3
  ? '隔離native-quit owner(手動)。未保存の3ページで確認中とNo後に二次起動し、回収前snapshotを採取した。回答の意味承認と機械証拠を封印後に照合。'
  : '隔離native-quit owner(手動)。3ページPDFを回転・複製・削除した未保存状態で終了確認を表示し、確認中と回答後に二次起動。自動Noなし。利用者が「いいえ」を押した。';
const noBasis = isV3
  ? `利用者回答の承認済み引用「${s.answer_semantics.answered_no.quote}」と、native No→False→元quit戻り→quit-cancelledが一致`
  : '利用者回答「いいえを押し」と、_quit()が窓を残して戻った時だけ作るquit-cancelledマーカー';
const stateBasis = isV3
  ? '利用者回答の承認済みthree_pages/rotations_kept/observed_before_collectionと、No後の二次起動・回収前snapshot(3ページ・[90,90,0]・Undo/Redo維持)が一致'
  : '利用者回答(1・2ページ横・3ページ縦)と、回答後の二次起動後のfocus-result(3ページ・[90,90,0]・state_preserved)が一致';
if (dryRun) {
  console.log(JSON.stringify({ dry_run: true, row: s.row, checks: 'all passed', at: iso, required_pass_after: passed, copies: pending.length, preparation_note: preparationNote, answered_no_basis: noBasis, edit_state_basis: stateBasis }));
  process.exit(0);
}

fs.mkdirSync(dest);
const copies = [];
for (const p of pending) { fs.writeFileSync(p.target, p.bytes, { flag: 'wx' }); copies.push({ source: p.source, target: path.relative(phase, p.target).replaceAll('\\', '/'), sha256: hash(p.bytes) }); }
fs.writeFileSync(path.join(dest, 'copies.json'), JSON.stringify(copies, null, 2) + '\n');

row.status = 'pass';
row.preparation = { status: 'prepared', run_id: path.basename(run), note: preparationNote };
row.observations = {
  quit_confirm_shown: { value: true, basis: '_quit()が終了確認で待機した区間(focus-ready→quit-cancelled)に確認中の二次起動が入り、利用者が「いいえ」を押した回答と一致' },
  answered_no: { value: true, basis: noBasis },
  edit_state_kept: { value: true, basis: stateBasis },
  owner_kept: { value: true, basis: '二次起動2回ともconstructed=0で同一owner(PID・生成時刻)を参照し、ownerはconstructed=1・restored=2で一次のまま終了' },
};
row.observation_basis = {
  answer_file: relative, answer_file_sha256: hash(raw), timeline: iso, focus_result: focus, primary_result: primary,
  peers: Object.fromEntries(Object.entries(peers).map(([k, p]) => [k, { dir: p.dir, result: p.result }])),
  raw_copy_manifest: path.relative(phase, path.join(dest, 'copies.json')).replaceAll('\\', '/'),
  ...(v2 ? { event_evidence_v2: v2, answer_semantics: s.answer_semantics, answer_captured_at: s.answer_captured_at } : {}),
  ...(v3 ? { event_evidence_v3: v3, collection_sha256: s.collection_sha256, answer_semantics: s.answer_semantics, answer_captured_at: s.answer_captured_at } : {}),
  frozen_input_files: Object.keys(report.input_manifest).length, frozen_inputs_unmodified_since_trial: true,
};
row.answer = composed;
row.raw_inputs = [{ at: isV3 ? s.answer_captured_at : iso.quit_cancelled, key: 'answer', text: answer, role: 'chat-answer' }];
row.answer_provenance = s.answer_source + ' 採用は' + s.adoption.approved_at + 'に' + s.adoption.approved_by + 'が承認し、事後に正式記録した。';
row.run_id = path.basename(run);
row.observed_at = iso.quit_cancelled;
row.environment = { ...manifest.environment, elevated: manifest.environment.is_admin };
row.input_manifest_sha256 = build.final_release.input_manifest_sha256;
row.source_commit = manifest.source_commit;

const updated = card.replace(/- \*\*状態\*\*: not-run[^\n]*/, `- **状態**: pass / 利用者回答(チャット・事後採用)と機械観測が一致。根拠: ${relative}\n- **回答原文**: ${composed}`);
let finalUat = uat.slice(0, start) + updated + uat.slice(stop);
finalUat = finalUat.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/, `本受入は必須108行中${passed}行pass・${108 - passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath, JSON.stringify(ledger, null, 2) + '\n');
fs.writeFileSync(uatPath, finalUat);
console.log(JSON.stringify({ row: s.row, status: 'pass', required_pass: passed, required_not_run: 108 - passed, deferred: 2, copied: copies.length }));
