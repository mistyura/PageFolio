// v3: 機械採取と後着する直接回答を別々に検査する。書込み・GUI操作なし。
const { validateMachine } = require('./06-05-w05c-evidence.cjs');
const assert = (ok, why) => { if (!ok) throw Error('W05c v3: ' + why); };
const stamp = s => { const n = Date.parse(s); assert(Number.isFinite(n), 'invalid UTC'); return n; };
function machine(events, snapshot, final, identity, stage = 'final') {
  assert(identity.schema === 'w05c-v3' && identity.plan_sha256, 'schema/plan missing');
  assert(events.every(e => e.schema === identity.schema && e.plan_sha256 === identity.plan_sha256), 'schema/plan mismatch');
  assert(!events.some(e => e.event === 'peer_after_answer'), 'v2 event mixed into v3');
  const result = validateMachine(events, snapshot, final, identity, stage, 'after_no');
  for (const name of ['ask_enter', 'ask_return', 'marker_created'])
    assert(events.filter(e => e.event === name).length === 1, 'multiple original confirmations/markers');
  const initialState = events.find(e => e.event === 'quit_enter').state;
  for (const name of ['ask_return', 'quit_return', 'marker_created']) {
    const state = events.find(e => e.event === name).state;
    assert(state.undo === initialState.undo && state.redo === initialState.redo, 'undo/redo changed');
  }
  assert(snapshot.state.undo === initialState.undo && snapshot.state.redo === initialState.redo, 'snapshot undo/redo changed');
  const registered = events.filter(e => e.event === 'watchdog_registered');
  assert(registered.length === 1, 'watchdog registration missing/duplicate');
  const w = registered[0];
  assert(w.delay_ms === 120000 && Number.isFinite(w.registered_monotonic) &&
    w.due_monotonic === w.registered_monotonic + 120, 'original watchdog deadline');
  assert(w.registered_monotonic <= events[0].monotonic && w.seq < result.marker_seq, 'watchdog registration order');
  assert(events.every(e => e.monotonic < w.due_monotonic), 'deadline reached');
  assert(snapshot.schema === identity.schema && snapshot.plan_sha256 === identity.plan_sha256, 'snapshot schema/plan');
  if (stage === 'final') {
    assert(final.schema === identity.schema && final.plan_sha256 === identity.plan_sha256, 'final schema/plan');
    const marker = events.find(e => e.event === 'marker_created');
    const pre = events.find(e => e.seq === result.pre_collection_seq);
    assert(Number.isFinite(identity.observation_seconds) && identity.observation_seconds >= 10 &&
      pre.monotonic - marker.monotonic >= identity.observation_seconds, 'observation window shortened');
    const stop = events.find(e => e.event === 'stop_enter');
    assert(stop.monotonic > pre.monotonic, 'stop before final snapshot');
  }
  return { ...result, schema: identity.schema, plan_sha256: identity.plan_sha256, due_monotonic: w.due_monotonic };
}
function adoption(events, snapshot, final, answer, identity, collection) {
  const result = machine(events, snapshot, final, identity);
  assert(collection.schema === identity.schema && collection.status === 'machine_collected_pending_answer' &&
    collection.run_id === identity.run_id && collection.plan_sha256 === identity.plan_sha256, 'collection not complete');
  for (const key of ['schema', 'run_id', 'pid', 'process_created', 'entry', 'manual', 'plan_sha256', 'observation_seconds', 'peers'])
    assert(collection.identity && JSON.stringify(collection.identity[key]) === JSON.stringify(identity[key]), 'collection identity: ' + key);
  assert(answer && answer.schema === identity.schema && answer.answer_run_id === identity.run_id &&
    answer.collection_sha256 === identity.collection_sha256 && identity.collection_sha256, 'answer binding');
  assert(typeof answer.answer_original === 'string' && answer.answer_original.trim() && answer.answer_source, 'answer provenance');
  const at = stamp(answer.answer_captured_at), closed = stamp(events.at(-1).utc);
  // 早着/後着とも実際の受信時刻を保つ。封印後の採用と回答受信を区別する。
  assert(at >= stamp(events.find(e => e.event === 'marker_created').utc), 'answer predates No/marker');
  const semantics = answer.answer_semantics;
  assert(semantics && semantics.approved_by && stamp(semantics.approved_at) >= at, 'semantic approval missing/early');
  for (const key of ['answered_no', 'confirm_closed', 'three_pages', 'rotations_kept', 'single_window', 'observed_before_collection']) {
    const m = semantics[key];
    assert(m && m.confirmed === true && typeof m.quote === 'string' && m.quote.length &&
      answer.answer_original.includes(m.quote), 'answer mapping: ' + key);
  }
  assert(answer.adoption && answer.adoption.approved_by && answer.adoption.decision === '採用' &&
    stamp(answer.adoption.approved_at) >= Math.max(stamp(semantics.approved_at), closed,
      stamp(collection.completed_at)), 'adoption missing/early');
  return result;
}
module.exports = { machine, adoption };
if (require.main === module) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', value => input += value);
  process.stdin.on('end', () => {
    try {
      const p = JSON.parse(input);
      const result = p.mode === 'adoption'
        ? adoption(p.events, p.snapshot, p.final, p.answer, p.identity, p.collection)
        : machine(p.events, p.snapshot, p.final, p.identity, p.stage);
      console.log(JSON.stringify(result));
    } catch (error) { console.error(error.message); process.exitCode = 1; }
  });
}
