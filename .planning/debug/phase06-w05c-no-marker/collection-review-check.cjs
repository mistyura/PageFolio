// 保存証拠と文書見直しの整合性を読むだけ。GUI・helper・台帳書込みは実行しない。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const phase = '.planning/phases/06-release-validation';
const raw = `${phase}/06-05-evidence/W05c_quit-no_at_script-20261105T072535Z-incomplete-raw`;
const quality = read(`${phase}/06-05-evidence/w05c-instrumentation-native-20261105/result.json`);
for (const [p, expected] of Object.entries(quality.after)) assert.equal(sha(p), expected, p);
const copies = read(`${raw}/copies.json`);
for (const item of copies) assert.equal(sha(path.join(raw, item.path)), item.sha256, item.path);
const answerCopy = read(`${raw}/answer-copy.json`);
assert.equal(sha(`${raw}/answer-original.json`), answerCopy.sha256);
assert.equal(sha(answerCopy.source), answerCopy.sha256);
const answer = read(`${raw}/answer-original.json`);
const events = fs.readFileSync(`${raw}/run/uat-owner-native-quit/w05c-events.jsonl`, 'utf8').trim().split(/\r?\n/).map(JSON.parse);
const event = name => events.find(e => e.event === name);
assert.equal(events.length, 18);
assert.equal(event('ask_return').result, false);
assert.equal(event('native_no').hwnd, event('marker_created').hwnd);
assert.equal(event('peer_after_answer'), undefined);
assert.equal(event('pre_collection'), undefined);
const noToMarkerMs = Number(((event('marker_created').monotonic - event('native_no').monotonic) * 1000).toFixed(6));
const markerToWatchdogSeconds = Number((event('watchdog_enter').monotonic - event('marker_created').monotonic).toFixed(6));
const answerAfterWatchdogSeconds = (Date.parse(answer.answer_captured_at) - Date.parse(event('watchdog_enter').utc)) / 1000;
assert.equal(markerToWatchdogSeconds, 97.672166);
assert(answerAfterWatchdogSeconds > 1958 && answerAfterWatchdogSeconds < 1959);
const ledger = read(`${phase}/06-MANUAL-EVIDENCE.json`);
const rows = ledger.cases.flatMap(c => c.subrows);
const required = rows.filter(r => r.release_requirement === 'required');
assert.equal(required.filter(r => r.status === 'pass').length, 28);
assert.equal(required.filter(r => r.status === 'not-run').length, 80);
assert.equal(rows.length - required.length, 2);
const handoff = read('.planning/HANDOFF.json');
assert.equal(handoff.w05c_retry_policy.ready_for_retry, false);
assert.equal(handoff.w05c_retry_policy.root_cause, 'unresolved');
assert.equal(handoff.w05c_retry_policy.collection_implementation_status, 'not_started');
assert.equal(handoff.current_stop.phase_complete, false);
assert.equal(handoff.validation.release_allowed, false);
assert.equal(handoff.remaining_tasks.find(t => t.id === '06-06').status, 'not_started');
const review = '06-W05C-COLLECTION-REVIEW.md';
for (const file of ['06-W05C-RETRY-POLICY.md', '06-W05C-INSTRUMENTATION.md',
  '06-W05C-CANDIDATE-STOP-20261105.md', '.continue-here.md', '06-05-CHECKPOINT.md']) {
  assert(fs.readFileSync(`${phase}/${file}`, 'utf8').includes(review), file);
}
assert(fs.readFileSync('.planning/debug/phase06-w05c-no-marker.md', 'utf8').includes(review));
assert(fs.existsSync(handoff.w05c_retry_policy.collection_review));
console.log(JSON.stringify({
  checked_utc: new Date().toISOString(), result: 'passed', scope: '保存証拠と設計文書の読取照合のみ',
  quality_inputs_unchanged: Object.keys(quality.after).length, raw_files_verified: copies.length,
  original_answer_hash_verified: true, events: events.length, no_to_marker_monotonic_ms: noToMarkerMs,
  marker_to_watchdog_seconds: markerToWatchdogSeconds, answer_after_watchdog_seconds: answerAfterWatchdogSeconds,
  required_pass: 28, required_not_run: 80, deferred_not_run: 2,
  design_links_verified: 7, ready_for_retry: false, release_allowed: false,
  implementation_status: 'not_started', root_cause: 'unresolved',
  additional_gui_trials: 0, new_product_tests: 0,
}, null, 2));
