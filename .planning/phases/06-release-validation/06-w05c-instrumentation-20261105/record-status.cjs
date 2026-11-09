// 品質証拠を照合し、人手確認待ちの再開点を記録する。製品・台帳は変更しない。
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '../../../..');
const phase = path.join(root, '.planning/phases/06-release-validation');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const resultPath = path.join(phase, '06-05-evidence/w05c-instrumentation-native-20261105/result.json');
const result = read(resultPath);
if (result.code !== 0 || result.changed.length) throw Error('quality evidence failed');
const drift = Object.keys(result.after).filter(file => hash(fs.readFileSync(path.join(root, file))) !== result.after[file]);
if (drift.length) throw Error('current inputs drifted: ' + drift.join(', '));
const ledger = read(path.join(phase, '06-MANUAL-EVIDENCE.json'));
const rows = ledger.cases.flatMap(c => c.subrows);
const counts = { required_pass: rows.filter(r => r.release_requirement === 'required' && r.status === 'pass').length,
  required_not_run: rows.filter(r => r.release_requirement === 'required' && r.status === 'not-run').length,
  deferred_not_run: rows.filter(r => r.release_requirement === 'deferred' && r.status === 'not-run').length };
if (JSON.stringify(Object.values(counts)) !== '[28,80,2]') throw Error('ledger unexpectedly changed');
const now = new Date().toISOString();
const next = '利用者の操作可能時間の回答待ち。開始直前に入力/親鮮度/owner/lockを再照合し、新規W05c/scriptを1回だけ確認する。before_peer→回答後peer→before_stop→inspect→stop→正式helper dry-run→書込→行監査。';
const hpath = path.join(root, '.planning/HANDOFF.json'), h = read(hpath);
h.timestamp = now;
h.status = 'waiting_for_human_action';
Object.assign(h.w05c_retry_policy, { implementation_status: 'validated', machine_gates_passed: true,
  ready_for_retry: false, awaiting: 'operator_availability', next_action: next,
  implementation_report: '.planning/phases/06-release-validation/06-W05C-INSTRUMENTATION.md' });
h.next_action = next;
h.context_notes = 'W05c v2計測/回収前検査/helperと39件の正負/実Windows対照を実装。native全件2293成功、167一意入力前後/現行一致。Phase04/05を必須ゲートで再検証し公式passed/fresh。正式script候補0回、製品/版/配布物/台帳不変・再build/commit/pushなし。元No不成立と過去事故は未解除。';
Object.assign(h.validation, counts, {full_suite: 'native全件2293 passed / 2 warnings / 1191.69秒、failure/error/skip各0、167一意入力前後/現行一致。', release_allowed: false});
Object.assign(h.current_session_validation, { phase4: 'fresh passed / 21/21', phase5: 'fresh passed / 23/23',
  full_evidence: '.planning/phases/06-release-validation/06-05-evidence/w05c-instrumentation-native-20261105',
  w05c_script: 'v2 implementation validated; formal candidate not started; awaiting operator availability',
  owner_running: false, quality_unique_inputs: Object.keys(result.after).length });
Object.assign(h.current_stop, { next_command: '$gsd-execute-phase 6', next_action: next, ready_for_retry: false, machine_gates_passed: true });
if (h.completed_tasks?.[1]) h.completed_tasks[1].progress = h.context_notes;
if (h.remaining_tasks?.[0]) h.remaining_tasks[0].name = 'W05c/script直接操作待ち、専用EXE手順/helper・残受入は未実施';
if (h.blockers?.[0]) Object.assign(h.blockers[0], {description:'W05c v2は検証済み。利用者の操作可能時間と直接No回答待ち。元runの主因は未解決。',type:'human_action',workaround:next});
fs.writeFileSync(hpath, JSON.stringify(h, null, 2) + '\n');
const statePath = path.join(root, '.planning/STATE.md');
let state = fs.readFileSync(statePath, 'utf8');
for (const [key, value] of Object.entries({status:'waiting_for_human_action',stopped_at:'W05c v2実装と全件品質・親鮮度回復完了。利用者の操作可能時間の回答待ち。',last_updated:now,last_activity:'W05c v2検証済み、正式script候補0回・人手開始待ち',last_activity_desc:'2293件成功/167入力不変、Phase04/05 fresh passed。06-05未完了・06-06未開始。'})) {
  state = state.replace(new RegExp('^' + key + ':.*$', 'm'), key + ': ' + value);
}
state = state.replace('## 2026-11-05 最新の再開方針',
  '## 2026-11-05 現行再開点（計測実装後）\n\n' + h.context_notes + '\n\n' + next + ' ready_for_retry=false、正式台帳28pass/80not-run・対象外2、出荷不可。詳細は `phases/06-release-validation/06-W05C-INSTRUMENTATION.md`。下記は方針設計時の履歴。\n\n## 2026-11-05 方針設計時の再開方針');
state = state.replace(/^Status: Blocked.*$/m, 'Status: Waiting for human action — W05c/script one candidate');
state = state.replace(/^Last activity: W05c.*$/m, 'Last activity: W05c v2検証完了・2293 passed・Phase04/05 fresh。利用者の操作可能時間待ち。');
fs.writeFileSync(statePath, state);
const files = ['tests/w05c_evidence.py','tests/test_w05c_evidence.py','tests/test_startup_windows.py','.gitignore',
  ...['06-05-record-w05c-python.cjs','06-05-w05c-evidence.cjs','06-07-quality.cjs'].map(n=>'.planning/phases/06-release-validation/'+n)];
const proof = {at:now, status:'awaiting_operator_availability', ready_for_retry:false, machine_gates_passed:true,
  formal_script_attempts:0, phase_complete:false, release_allowed:false, ...counts,
  full_result:path.relative(root,resultPath).replaceAll('\\','/'), full_result_sha256:hash(fs.readFileSync(resultPath)),
  unique_quality_inputs:Object.keys(result.after).length, current_input_drift:drift,
  files:Object.fromEntries(files.map(f=>[f,hash(fs.readFileSync(path.join(root,f)))])),
  note:'過去のNo不成立/153fixture原bytes不明/開始前Ruff一過性警告/配布元・tracer消失等の未解除事項は保持。開始直前にowner/lock・入力・親鮮度と利用者の準備を再確認する。'};
fs.writeFileSync(path.join(__dirname,'closeout.json'), JSON.stringify(proof,null,2)+'\n');
console.log(JSON.stringify({at:now,...counts,unique_inputs:proof.unique_quality_inputs,ready_for_retry:false}));
