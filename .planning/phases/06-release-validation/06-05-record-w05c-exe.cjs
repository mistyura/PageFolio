// W05c/quit-no@production-exe: 外部観測と利用者直接回答を照合して、対象1行だけ採用する。
// node 06-05-record-w05c-exe.cjs W05c_quit-no_at_production-exe-YYYYMMDDTHHMMSSZ.json --dry-run
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const phase = __dirname;
const root = path.resolve(phase, '../../..');
const name = process.argv[2];
const dryRun = process.argv.includes('--dry-run');
const assert = (condition, message) => { if (!condition) throw Error(message); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = file => fs.readFileSync(file);
const json = file => JSON.parse(read(file).toString('utf8'));
const inside = (base, child) => child.startsWith(base + path.sep);
const iso = value => { const time = Date.parse(value); assert(Number.isFinite(time), 'invalid timestamp'); return time; };
const fileWithin = (base, relative) => {
  assert(typeof relative === 'string' && !path.isAbsolute(relative) && !relative.includes('\\'), 'invalid relative path');
  const full = path.resolve(base, relative);
  assert(inside(base, full) && inside(fs.realpathSync.native(base), fs.realpathSync.native(full)) &&
    !fs.lstatSync(full).isSymbolicLink(), 'path outside owner run');
  return full;
};

assert(process.argv.length === (dryRun ? 4 : 3), 'usage: answer.json [--dry-run]');
assert(/^W05c_quit-no_at_production-exe-\d{8}T\d{6}Z\.json$/.test(name || ''), 'unexpected answer filename');
const answerPath = path.join(phase, '06-05-evidence', name);
assert(inside(fs.realpathSync.native(phase), fs.realpathSync.native(answerPath)) &&
  !fs.lstatSync(answerPath).isSymbolicLink(), 'answer symlink/outside phase');
const answerRaw = read(answerPath);
const s = JSON.parse(answerRaw.toString('utf8'));
assert(s.schema === 'w05c-exe-v1' && s.case === 'W05c' && s.row === 'W05c/quit-no@production-exe' &&
  s.entry === 'production-exe' && s.condition === 'quit-no', 'wrong evidence schema/row');
assert(s.collection_status === 'machine_collected_pending_answer' && !s.diagnostic_only && !s.failed, 'collection not eligible');

const run = path.resolve(root, s.run || '');
assert(inside(path.join(root, '.planning', 'tmp'), run) && /^release-uat-[0-9a-f]{32}$/.test(path.basename(run)), 'unexpected run root');
assert(inside(fs.realpathSync.native(path.join(root, '.planning', 'tmp')), fs.realpathSync.native(run)) &&
  !fs.lstatSync(run).isSymbolicLink(), 'run symlink/outside tmp');
const manifestPath = fileWithin(run, 'manifest.json');
const manifestRaw = read(manifestPath);
const m = JSON.parse(manifestRaw.toString('utf8'));
assert(sha(manifestRaw) === s.manifest_sha256 && m.run_id === path.basename(run).slice('release-uat-'.length) &&
  m.run === run && m.case === 'W05c' && m.entry === 'production-exe' &&
  m.evidence_kind === 'production-exe' && m.role === 'final-release-candidate' && m.status === 'stopped' &&
  m.schema_version === 1 && m.generation === 1, 'run manifest mismatch');
assert(path.resolve(m.copy) === path.join(run, 'dist'), 'copy outside run');
assert(m.fixtures?.['edit-three-page']?.pages === 3 &&
  path.resolve(m.fixtures['edit-three-page'].path) === path.join(run, 'fixtures', 'edit-three-page.pdf'),
  'three-page edit fixture missing');
const fixturePath = fileWithin(run, 'fixtures/edit-three-page.pdf');
assert(s.fixture_sha256 === sha(read(fixturePath)), 'edit fixture changed');
assert(m.processes.length === 2 && m.processes[0].role === 'primary' && m.processes[1].role === 'peer', 'expected one owner and one peer');
const [owner, peer] = m.processes;
assert(Object.keys(m.overlay || {}).join(',') === 'pagefolio_settings.json' &&
  m.overlay['pagefolio_settings.json'] === null &&
  m.overlay_log?.some(x => x.name === 'pagefolio_settings.json' && x.sha256 === null &&
    iso(x.at) < iso(owner.started_at)), 'settings overlay not declared before start');
const processRaw = manifestRaw.toString('utf8').split('"processes"')[1]?.split('"observations"')[0] || '';
const creationTokens = [...processRaw.matchAll(/"created"\s*:\s*(\d+)/g)].map(match => match[1]);
assert(creationTokens.length >= 2 && s.owner_created === creationTokens[0] &&
  s.peer_created === creationTokens[1], 'exact process creation timestamps mismatch');
assert(Number.isInteger(owner.pid) && owner.pid > 0 && Number.isFinite(owner.created) && owner.created > 0 &&
  Number.isInteger(peer.pid) && peer.pid > 0 && Number.isFinite(peer.created) && peer.created > 0 &&
  owner.pid !== peer.pid && peer.peer_source?.run_id === m.run_id && peer.peer_source?.role === m.role &&
  peer.peer_source?.exe_sha256 === m.source.exe_sha256, 'process/peer identity mismatch');
assert(owner.exit === s.stop_outcome && ['closed', 'terminated'].includes(s.stop_outcome) &&
  peer.exit === 'already-exited', 'stop outcome or peer exit mismatch');

const build = json(path.join(phase, '06-BUILD-EVIDENCE.json'));
const protection = json(path.join(phase, '06-PROTECTION-EVIDENCE.json'));
const binary = build.final_release;
assert(build.generation === 5 && build.version === 'v1.10.2' &&
  protection.generation === 5 && protection.build_ref?.exe_sha256 === binary.exe_sha256 &&
  protection.build_ref?.tree_sha256 === binary.tree_sha256 &&
  protection.build_ref?.final_run_id === m.source.report_run_id &&
  m.source.version === build.version && m.source.exe_sha256 === binary.exe_sha256 &&
  m.source.tree_sha256 === binary.tree_sha256 &&
  build.final_release.runs.some(r => r.run_id === m.source.report_run_id) &&
  s.binary_sha256 === binary.exe_sha256 && s.tree_sha256 === binary.tree_sha256 &&
  s.input_manifest_sha256 === binary.input_manifest_sha256, 'frozen generation/binary/tree mismatch');
assert(sha(read(path.join(run, 'dist', 'PageFolio.exe'))) === binary.exe_sha256, 'run executable changed');

const stages = ['before_confirm', 'during_confirm', 'after_no', 'after_peer'];
assert(Object.keys(s.inspections || {}).sort().join(',') === stages.slice().sort().join(','), 'inspection stages missing');
const inspections = {};
let previous = -Infinity;
for (const stage of stages) {
  const seal = s.inspections[stage];
  assert(Number.isInteger(seal.index) && seal.index >= 1 && seal.index <= m.observations.length &&
    /^[0-9a-f]{64}$/.test(seal.sha256), 'inspection seal invalid');
  const file = fileWithin(run, `evidence/inspect-${String(seal.index).padStart(3, '0')}.json`);
  const bytes = read(file);
  assert(sha(bytes) === seal.sha256, 'inspection changed: ' + stage);
  const obs = JSON.parse(bytes.toString('utf8'));
  const rawText = bytes.toString('utf8');
  const primaryCreated = rawText.match(/"role"\s*:\s*"primary"[\s\S]*?"created"\s*:\s*(\d+)/)?.[1];
  const peerCreated = rawText.match(/"role"\s*:\s*"peer"[\s\S]*?"created"\s*:\s*(\d+)/)?.[1];
  assert(primaryCreated === s.owner_created &&
    (stage === 'before_confirm' || peerCreated === s.peer_created), 'inspection creation token mismatch');
  assert(JSON.stringify(obs) === JSON.stringify(m.observations[seal.index - 1]), 'manifest/inspection mismatch');
  const at = iso(obs.at);
  assert(at > previous, 'inspection order reversed');
  previous = at;
  const primary = obs.processes.find(p => p.role === 'primary');
  assert(primary && primary.pid === owner.pid && primary.created === owner.created &&
    primary.identity === 'same' && primary.alive === true, 'owner lost before collection: ' + stage);
  assert(obs.copy?.ok === true && (obs.copy.overlay_changed || []).every(n => n === 'pagefolio_settings.json') &&
    (obs.copy.locked_unverified || []).length === 0 && obs.source_unchanged !== false &&
    Array.isArray(obs.owner_probe) && obs.owner_probe.length > 0, 'copy/owner probe invalid: ' + stage);
  inspections[stage] = obs;
}
assert(inspections.before_confirm.processes.length === 1 &&
  inspections.during_confirm.processes.length === 2 &&
  inspections.after_no.processes.length === 2 &&
  inspections.after_peer.processes.length === 2, 'peer observation count mismatch');
const duringPeer = inspections.during_confirm.processes.find(p => p.role === 'peer');
const afterPeer = inspections.after_peer.processes.find(p => p.role === 'peer');
const dialogVisible = obs => obs.processes.find(p => p.role === 'primary').windows.some(w => w.visible && w.class === '#32770');
assert(dialogVisible(inspections.during_confirm) && !dialogVisible(inspections.after_no) &&
  !dialogVisible(inspections.after_peer), 'quit confirmation did not visibly disappear before collection');
assert(duringPeer?.pid === peer.pid && duringPeer.created === peer.created &&
  afterPeer?.pid === peer.pid && afterPeer.created === peer.created &&
  afterPeer.alive === false && afterPeer.identity === 'gone' &&
  !duringPeer.windows.some(w => w.visible) && !afterPeer.windows.some(w => w.visible),
  'peer created another visible window or did not exit under same owner');
assert(inspections.after_no.foreground?.owned_by === 'primary' &&
  inspections.after_no.foreground.pid === owner.pid,
  'foreground immediately after No was not primary');
assert(s.peer_constructed === 0 && s.peer_constructed_basis === 'external-no-new-primary-window-and-same-owner',
  'peer construction conclusion lacks external basis');
assert(s.confirm_disappeared_before_collection === true &&
  s.confirm_disappeared_basis === 'direct-user-observation', 'confirmation disappearance not observed');

const answer = s.direct_answer;
assert(answer?.source === 'user-direct' && typeof answer.text === 'string' && answer.text.trim() &&
  typeof answer.question === 'string' && answer.question.trim() &&
  typeof answer.source_ref === 'string' && answer.source_ref.trim(), 'direct answer missing');
const answerAt = iso(answer.captured_at);
assert(answerAt > iso(inspections.after_no.at) && answerAt < iso(inspections.after_peer.at), 'answer outside pre-collection observation window');
for (const field of ['quit_confirm_shown', 'answered_no', 'edit_state_kept', 'owner_kept', 'foreground_after']) {
  assert(answer[field] === true, 'human observation missing: ' + field);
}
assert(answer.confirm_disappeared === true && answer.observed_before_collection === true &&
  answer.text.includes('いいえ'), 'human answer lacks No/pre-collection observation');
assert(s.stop_observed_at && iso(s.stop_observed_at) > iso(inspections.after_peer.at) &&
  iso(s.stop_observed_at) >= iso(m.snapshots.at(-1)?.at) &&
  iso(s.stop_observed_at) >= fs.statSync(manifestPath).mtimeMs, 'stop chronology mismatch');
assert(m.snapshots[0]?.label === 'before-start' && m.snapshots.at(-2)?.label === 'before-stop' &&
  m.snapshots.at(-1)?.label === 'after-stop' &&
  iso(m.snapshots.at(-2).at) > iso(inspections.after_peer.at), 'source snapshots missing/out of order');
const adoption = s.adoption;
const adoptionAt = iso(adoption?.approved_at);
const collectionCompleteAt = Math.max(iso(inspections.after_peer.at), iso(m.snapshots.at(-2).at),
  iso(m.snapshots.at(-1).at), fs.statSync(manifestPath).mtimeMs, iso(s.stop_observed_at));
const adoptionWords = new Set(['採用', '採用。', '採用してよい', '採用してよい。']);
assert(adoption?.decision === '採用' && adoption.approved_by === '利用者' &&
  adoption.source === 'user-direct' && typeof adoption.source_ref === 'string' &&
  adoption.source_ref.trim() && adoption.source_ref !== answer.source_ref &&
  typeof adoption.text === 'string' && adoptionWords.has(adoption.text.trim()) &&
  adoptionAt > collectionCompleteAt && adoption.answer_sha256 === sha(Buffer.from(answer.text)),
  'explicit post-collection adoption missing or not bound to answer');
const original = m.snapshots[0].originals;
assert(original && Object.keys(original).length >= 4 &&
  m.snapshots.every(snapshot => snapshot.originals && JSON.stringify(snapshot.originals) === JSON.stringify(original) &&
    snapshot.source_unchanged === true && snapshot.copy?.ok === true &&
    (snapshot.copy.overlay_changed || []).every(n => n === 'pagefolio_settings.json') &&
    (snapshot.copy.locked_unverified || []).length === 0), 'original settings/prompts/plugins or source changed');
assert(s.originals_sha256 === sha(Buffer.from(JSON.stringify(original))), 'original protection seal mismatch');

// 全検証後にだけ台帳を読む。dry-run/拒否は原本も台帳も変更しない。
const ledgerPath = path.join(phase, '06-MANUAL-EVIDENCE.json');
const uatPath = path.join(phase, '06-UAT.md');
const ledger = json(ledgerPath);
const row = ledger.cases.find(c => c.id === 'W05c')?.subrows.find(r => r.card === s.row);
assert(row?.status === 'not-run' && row.generation === 5 && row.expected_binary_sha256 === binary.exe_sha256 &&
  row.release_requirement === 'required' &&
  [...row.required_observations].sort().join(',') ===
    ['quit_confirm_shown', 'answered_no', 'edit_state_kept', 'owner_kept', 'stop_outcome', 'foreground_after'].sort().join(','),
  'target row already judged or wrong generation');
const uat = read(uatPath).toString('utf8');
const marker = `### ${s.row}`;
const start = uat.indexOf(marker);
assert(start >= 0 && (start === 0 || uat[start - 1] === '\n') &&
  ['\n', '\r'].includes(uat[start + marker.length]), 'card missing');
const next = uat.indexOf('\n### ', start + marker.length);
const end = next < 0 ? uat.length : next;
const card = uat.slice(start, end);
assert(card.includes('- **状態**: not-run'), 'card already judged');
const targetDir = path.join(phase, '06-05-evidence', name.replace(/\.json$/, '-raw'));
assert(!fs.existsSync(targetDir), 'raw already preserved');
const copyNames = ['manifest.json', 'fixtures/edit-three-page.pdf',
  ...Object.values(s.inspections).map(x => `evidence/inspect-${String(x.index).padStart(3, '0')}.json`)];
const copies = copyNames.map(n => ({ name: n, bytes: read(fileWithin(run, n)) }));
const relative = `06-05-evidence/${name}`;
const result = { row: s.row, status: 'pass', run_id: m.run_id, binary_sha256: binary.exe_sha256, dry_run: dryRun };
if (dryRun) { console.log(JSON.stringify(result)); process.exit(0); }
fs.mkdirSync(targetDir);
const copied = copies.map(({ name, bytes }) => {
  const target = path.join(targetDir, name.replaceAll('/', '-'));
  fs.writeFileSync(target, bytes, { flag: 'wx' });
  return { source: name, target: path.relative(phase, target).replaceAll('\\', '/'), sha256: sha(bytes) };
});
fs.writeFileSync(path.join(targetDir, 'copies.json'), JSON.stringify(copied, null, 2) + '\n', { flag: 'wx' });
row.status = 'pass';
row.preparation = { status: 'prepared', run_id: m.run_id, note: '固定世代5の未改変EXE隔離copy。終了確認中の二次起動、No後、回収前の外部観測を保存。' };
row.observations = Object.fromEntries(row.required_observations.map(key => [key, {
  value: key === 'stop_outcome' ? s.stop_outcome : true,
  basis: key === 'stop_outcome' ? 'manifestの同一owner終了経過' : '利用者直接回答と同一runの回収前外部観測',
}]));
row.answer = `W05c quit-no production-exe：${answer.text}`;
row.raw_inputs = [
  { at: answer.captured_at, key: 'answer', text: answer.text, role: 'chat-answer' },
  { at: adoption.approved_at, key: 'adoption', text: adoption.text, role: 'chat-answer' },
];
row.answer_provenance = `${answer.source_ref}。回収後の別回答 ${adoption.source_ref} で${adoption.approved_at}に利用者が明示承認。`;
row.run_id = m.run_id;
row.observed_at = answer.captured_at;
row.environment = m.environment;
row.binary_sha256 = binary.exe_sha256;
row.input_manifest_sha256 = binary.input_manifest_sha256;
row.observation_basis = { answer_file: relative, answer_file_sha256: sha(answerRaw),
  raw_copy_manifest: path.relative(phase, path.join(targetDir, 'copies.json')).replaceAll('\\', '/'),
  owner: { pid: owner.pid, created: owner.created }, peer: { pid: peer.pid, created: peer.created },
  inspections: s.inspections, originals_sha256: s.originals_sha256, stop_outcome: s.stop_outcome,
  confirm_disappeared_before_collection: true, peer_constructed: 0 };
const passed = ledger.cases.flatMap(c => c.subrows).filter(r => r.release_requirement === 'required' && r.status === 'pass').length;
const answerForCard = answer.text.replaceAll('\r', '\\r').replaceAll('\n', '\\n');
const newCard = card.replace(/- \*\*状態\*\*: not-run[^\n]*/, `- **状態**: pass / 利用者直接回答と外部観測を照合。根拠: ${relative}\n- **回答原文**: ${answerForCard}`);
let newUat = uat.slice(0, start) + newCard + uat.slice(end);
newUat = newUat.replace(/本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/,
  `本受入は必須108行中${passed}行pass・${108 - passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath, JSON.stringify(ledger, null, 2) + '\n');
fs.writeFileSync(uatPath, newUat);
console.log(JSON.stringify(result));
