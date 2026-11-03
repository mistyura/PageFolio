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
assert(typeof answer === 'string' && answer.trim() === answer && answer.length > 0, 'answer missing');
const obsPath = path.join(root, s.observation_record), obsRaw = fs.readFileSync(obsPath);
assert(hash(obsRaw) === s.observation_record_sha256, 'observation record changed');
assert(obsRaw.toString('utf8').includes(`回答原文: 「${answer}」`), 'answer not found verbatim in observation record');
assert(s.adoption && s.adoption.approved_by && s.adoption.approved_at && s.adoption.decision, 'adoption approval missing');
assert(answer.includes('いいえを押し'), 'answer does not state No was pressed');
const normalized = answer.normalize('NFKC');
assert(normalized.includes('1・2ページが横向き') && normalized.includes('3ページが縦向き'), 'answer does not describe the kept edit');

// run: 隔離 native-quit owner(手動)。二次起動2回(確認中・回答後)
const run = path.resolve(root, s.run);
assert(run.startsWith(path.join(root, '.planning', 'tmp') + path.sep), 'unexpected run root');
assert(obsPath.startsWith(run + path.sep), 'observation record outside run');
const manifest = readJson(path.join(run, 'manifest.json')), inspection = readJson(path.join(run, 'inspection.json'));
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
  peer_after_answer: peers.after_answer.at,
};
const order = Object.values(at);
assert(order.every((v, n) => n === 0 || order[n - 1] <= v), 'event order mismatch: ' + JSON.stringify(at));
const iso = Object.fromEntries(Object.entries(at).map(([k, v]) => [k, new Date(v).toISOString()]));

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

const passed = ledger.cases.flatMap(c => c.subrows).filter(r => r.release_requirement === 'required' && r.status === 'pass').length + 1;
const composed = `W05c quit-no ${s.entry}：${answer}`;
if (dryRun) {
  console.log(JSON.stringify({ dry_run: true, row: s.row, checks: 'all passed', at: iso, required_pass_after: passed, copies: pending.length }));
  process.exit(0);
}

fs.mkdirSync(dest);
const copies = [];
for (const p of pending) { fs.writeFileSync(p.target, p.bytes, { flag: 'wx' }); copies.push({ source: p.source, target: path.relative(phase, p.target).replaceAll('\\', '/'), sha256: hash(p.bytes) }); }
fs.writeFileSync(path.join(dest, 'copies.json'), JSON.stringify(copies, null, 2) + '\n');

row.status = 'pass';
row.preparation = { status: 'prepared', run_id: path.basename(run), note: '隔離native-quit owner(手動)。3ページPDFを回転・複製・削除した未保存状態で終了確認を表示し、確認中と回答後に二次起動。自動Noなし。利用者が「いいえ」を押した。' };
row.observations = {
  quit_confirm_shown: { value: true, basis: '_quit()が終了確認で待機した区間(focus-ready→quit-cancelled)に確認中の二次起動が入り、利用者が「いいえ」を押した回答と一致' },
  answered_no: { value: true, basis: '利用者回答「いいえを押し」と、_quit()が窓を残して戻った時だけ作るquit-cancelledマーカー' },
  edit_state_kept: { value: true, basis: '利用者回答(1・2ページ横・3ページ縦)と、回答後の二次起動後のfocus-result(3ページ・[90,90,0]・state_preserved)が一致' },
  owner_kept: { value: true, basis: '二次起動2回ともconstructed=0で同一owner(PID・生成時刻)を参照し、ownerはconstructed=1・restored=2で一次のまま終了' },
};
row.observation_basis = {
  answer_file: relative, answer_file_sha256: hash(raw), timeline: iso, focus_result: focus, primary_result: primary,
  peers: Object.fromEntries(Object.entries(peers).map(([k, p]) => [k, { dir: p.dir, result: p.result }])),
  raw_copy_manifest: path.relative(phase, path.join(dest, 'copies.json')).replaceAll('\\', '/'),
  frozen_input_files: Object.keys(report.input_manifest).length, frozen_inputs_unmodified_since_trial: true,
};
row.answer = composed;
row.raw_inputs = [{ at: iso.quit_cancelled, key: 'answer', text: answer, role: 'chat-answer' }];
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
