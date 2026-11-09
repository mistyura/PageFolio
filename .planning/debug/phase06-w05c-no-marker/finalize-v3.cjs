// v3実装後の記録同期と保存証拠の照合。GUI・正式受入の書込みは行わない。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const phase = '.planning/phases/06-release-validation';
const debug = '.planning/debug/phase06-w05c-no-marker';
const qualityDir = `${phase}/06-05-evidence/w05c-v3-final-native-20261105`;
const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const quality = read(`${qualityDir}/result.json`);
assert.equal(quality.code, 0);
assert.deepEqual(quality.changed, []);
assert.equal(Object.keys(quality.after).length, 170);
const delta = Object.keys(quality.after).filter(p => sha(p) !== quality.after[p]);
assert.deepEqual(delta, ['開発履歴.md'], '全件検証後は履歴の追記だけを許容');
assert(fs.readFileSync(`${qualityDir}/stdout.txt`, 'utf8').includes('2333 passed, 2 warnings'));
const raw = `${phase}/06-05-evidence/W05c_quit-no_at_script-20261105T072535Z-incomplete-raw`;
const copies = read(`${raw}/copies.json`);
for (const item of copies) assert.equal(sha(path.join(raw, item.path)), item.sha256);
const answer = read(`${raw}/answer-copy.json`);
assert.equal(sha(`${raw}/answer-original.json`), answer.sha256);
assert.equal(sha(answer.source), answer.sha256);
const rows = read(`${phase}/06-MANUAL-EVIDENCE.json`).cases.flatMap(c => c.subrows);
const required = rows.filter(r => r.release_requirement === 'required');
assert.equal(required.filter(r => r.status === 'pass').length, 28);
assert.equal(required.filter(r => r.status === 'not-run').length, 80);
assert.equal(rows.length - required.length, 2);
const next = '全体formatの既存検証tmpアクセス拒否を解消し、新規v3 Windows統合の範囲/許可・実測予算を確定する。再開前に06-03 resume_contractで親ゲート鮮度を照合。新規統合/正式試行/期限延長/正常診断反復/製品推測修正/commitは自動実行しない。';
const status = 'v3採取runner/契約を実装し、対象79件・最終全件2333件成功（170入力前後不変）。既存pytest自動GUIのみ利用者許可済み。新規v3 Windows統合は未検証、全体formatは既存tmpアクセス拒否で未通過。元主因未解決、ready_for_retry=false、台帳28pass/80not-run・対象外2、06-06未開始・出荷不可。';
const handoff = read('.planning/HANDOFF.json');
handoff.timestamp = new Date().toISOString();
Object.assign(handoff.w05c_retry_policy, {
  status: 'v3_implemented_integration_blocked',
  collection_implementation_status: 'implemented_native_integration_pending',
  ready_for_retry: false, next_action: next,
  machine_gates_passed: false,
  collection_implementation_report: `${phase}/06-W05C-COLLECTION-REVIEW.md`,
  existing_automated_gui_tests_authorized: true,
  new_v3_native_integration_authorized: false,
});
handoff.completed_tasks.find(t => t.id === 2).progress = status;
handoff.remaining_tasks.find(t => t.id === '06-05-02').name = 'v3実装/自動試験完了。format制限と新規Windows統合・親ゲートが残る。';
handoff.blockers[0].workaround = next;
handoff.human_actions_pending[0] = {
  action: 'format制限の解消と新規v3 Windows統合の具体的条件/許可を確定するまで追加のW05c操作を要求しない',
  context: status, blocking: true,
};
handoff.next_action = next;
handoff.context_notes = status;
handoff.validation.full_suite = '最終native全件2333 passed / 2 warnings / 1274.11秒、170入力前後不変。終了後は開発履歴.mdのみ追記し文書契約検証を別記録。全体format制限は未解消。';
Object.assign(handoff.current_session_validation, {
  full_evidence: qualityDir, quality_unique_inputs: 170,
  phase4: '過去fresh passed / 21/21。v3 harness変更後はresume_contractで再確認が必要',
  phase5: '過去fresh passed / 23/23。v3変更後はresume_contractで再確認が必要',
  new_v3_native_integration: 'not-run',
  v3_target_tests: '79 passed',
});
handoff.current_stop.next_action = next;
handoff.current_stop.machine_gates_passed = false;
handoff.current_stop.collection_report = `${phase}/06-W05C-COLLECTION-REVIEW.md`;
assert.equal(handoff.remaining_tasks.find(t => t.id === '06-06').status, 'not_started');
assert.equal(handoff.validation.release_allowed, false);
fs.writeFileSync('.planning/HANDOFF.json', JSON.stringify(handoff, null, 2) + '\n');
function replaceLine(file, contains, replacement) {
  const original = fs.readFileSync(file, 'utf8');
  const lines = original.split(/\r?\n/);
  const found = lines.map((line, i) => line.includes(contains) ? i : -1).filter(i => i >= 0);
  assert.equal(found.length, 1, file + ': ' + contains);
  lines[found[0]] = replacement;
  fs.writeFileSync(file, lines.join(original.includes('\r\n') ? '\r\n' : '\n'));
}
const linked = '`06-W05C-COLLECTION-REVIEW.md` を現行の実装/検証正本とする。' + status + next;
replaceLine(`${phase}/.continue-here.md`, '# 2026-11-05 W05c採取手順の見直し完了（最新）', '# 2026-11-05 W05c v3実装・自動検証完了（最新、再開不可）');
replaceLine(`${phase}/.continue-here.md`, '`06-W05C-COLLECTION-REVIEW.md` に期限内機械採取', linked);
replaceLine(`${phase}/06-05-CHECKPOINT.md`, '## 2026-11-05 採取手順の見直し完了（最新）', '## 2026-11-05 v3実装・自動検証完了（最新、再開不可）');
replaceLine(`${phase}/06-05-CHECKPOINT.md`, '設計正本 `06-W05C-COLLECTION-REVIEW.md`。', linked);
replaceLine(`${phase}/06-W05C-RETRY-POLICY.md`, '[06-W05C-COLLECTION-REVIEW.md](06-W05C-COLLECTION-REVIEW.md) に保存時系列', linked + ' frontmatterのimplementation_status: validatedは旧v2の履歴である。');
replaceLine(`${phase}/06-W05C-INSTRUMENTATION.md`, '現行v2は回答JSON取得と意味承認をbefore_peerより前に要求', linked + ' 下記v2操作順は保存履歴であり直接再実行しない。');
replaceLine(`${phase}/06-W05C-CANDIDATE-STOP-20261105.md`, '`$gsd-debug continue phase06-w05c-no-marker` で行った手順見直し', linked + ' 本報告の旧候補は未完了のまま保持する。');
const report = {
  checked_utc: new Date().toISOString(), result: 'passed_with_explicit_limits',
  full_suite: {passed: 2333, warnings: 2, seconds: 1274.11, code: 0, evidence: qualityDir},
  target: {passed: 79, evidence: `${debug}/v3-target-final.xml`},
  quality_inputs: 170, changes_during_full_suite: [],
  changes_after_full_suite: delta,
  post_suite_document_sha256: {'開発履歴.md': sha('開発履歴.md')},
  preserved_raw_files: copies.length, original_answer_hash_verified: true,
  required_pass: 28, required_not_run: 80, deferred_not_run: 2,
  python_explicit_files: 146, ast: 'passed',
  ruff_full_check: 'exit0 with access-denied warning',
  ruff_full_format: 'blocked by existing 05-closeout-20261028-tmp access denial',
  new_native_integration: 'not-run; not authorized',
  formal_trials_this_continuation: 0, ready_for_retry: false, release_allowed: false,
  root_cause: 'unresolved', commit: false,
};
fs.writeFileSync(`${debug}/collection-implementation-verification.json`, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({result: report.result, quality_inputs: 170, raw_files: copies.length, ledger: '28/80/2', ready_for_retry: false}));
