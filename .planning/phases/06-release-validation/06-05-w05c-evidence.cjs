// W05c v2 の純粋な証拠検査。ファイルや正式台帳を変更しない。
const assert = (ok, why) => { if (!ok) throw Error('W05c v2: ' + why); };
const stateOK = s => s && s.root_alive === true && s.pages === 3 &&
  JSON.stringify(s.rotations) === '[90,90,0]' && s.undo > 0 && s.redo === 0;
function validateMachine(events, snapshot, final, identity, stage = 'final', afterLabel = 'after_answer') {
  assert(['after_answer', 'after_no'].includes(afterLabel), 'unknown peer label');
  const afterEvent = 'peer_' + afterLabel;
  assert(['final', 'before_peer', 'before_stop'].includes(stage), 'unknown stage');
  assert(identity.entry === 'script', 'new candidate must be script');
  assert(identity.manual === true && !identity.diagnostic_only, 'manual acceptance only');
  assert(events.length > 0, 'empty log');
  let previous = -Infinity, previousUTC = -Infinity;
  for (const [i, e] of events.entries()) {
    assert(e.seq === i + 1, 'missing/duplicate sequence');
    assert(e.run_id === identity.run_id && e.pid === identity.pid &&
      e.process_created === identity.process_created, 'owner/run mismatch');
    const utc = Date.parse(e.utc);
    assert(Number.isFinite(e.monotonic) && e.monotonic >= previous &&
      Number.isFinite(utc) && utc >= previousUTC, 'clock order');
    previous = e.monotonic; previousUTC = utc;
    assert(!['acquisition_error', 'tk_error', 'ask_error', 'quit_error',
      'watchdog_enter', 'root_destroy_error', 'cleanup_error'].includes(e.event), 'recording/runtime error: ' + e.event);
  }
  const first = name => { const e = name === 'pre_collection' ? events.find(e => e.event === name && e.request_id === snapshot.request_id) : events.find(e => e.event === name); assert(e, 'missing ' + name); return e; };
  let names = ['observer_started', 'quit_enter', 'ask_enter', 'native_shown',
    'peer_during_confirm', 'native_no', 'ask_return', 'quit_return', 'marker_created',
    afterEvent, 'pre_collection', 'stop_enter', 'cleanup_enter', 'observer_closed'];
  if (stage !== 'final') names = names.filter(n => !['stop_enter', 'cleanup_enter', 'observer_closed'].includes(n));
  if (stage === 'before_peer') names = names.filter(n => n !== afterEvent);
  const ordered = names.map(first);
  assert(ordered.every((e, i) => i === 0 || ordered[i - 1].seq < e.seq), 'required event order');
  const shown = first('native_shown'), no = first('native_no');
  assert(Number.isSafeInteger(shown.hwnd) && shown.hwnd > 0, 'native HWND missing');
  for (const name of ['peer_during_confirm', 'native_no', 'ask_return', 'quit_return', 'marker_created', afterEvent, 'pre_collection']) {
    if (stage === 'before_peer' && name === afterEvent) continue;
    assert(first(name).hwnd === shown.hwnd, 'native HWND mismatch: ' + name);
  }
  assert(events.filter(e => e.event === 'native_shown').length === 1 &&
    events.filter(e => e.event === 'native_no').length === 1, 'multiple confirmations/No');
  assert(first('ask_return').result === false, 'askyesno did not return False');
  for (const name of ['quit_enter', 'ask_return', 'quit_return', 'marker_created']) {
    assert(stateOK(first(name).state), 'edited state mismatch: ' + name);
  }
  const marker = first('marker_created'), pre = first('pre_collection');
  for (const e of events) {
    if (['stop_enter', 'cleanup_enter', 'watchdog_enter', 'root_destroy_enter'].includes(e.event))
      assert(e.seq > pre.seq, 'collection began before snapshot/marker');
  }
  assert(pre.elapsed >= 0 && pre.elapsed < 120 &&
    pre.monotonic - first('observer_started').monotonic < 120, 'deadline');
  assert(snapshot.request_id === pre.request_id && snapshot.marker === true &&
    snapshot.stop === false && snapshot.stop_all === false && stateOK(snapshot.state), 'pre-collection snapshot');
  assert(snapshot.events === pre.seq && snapshot.errors.length === 0 &&
    snapshot.log_sha256 && snapshot.marker_sha256, 'snapshot log incomplete');
  for (const obj of [snapshot, ...(final ? [final] : [])]) {
    assert(obj.run_id === identity.run_id && obj.pid === identity.pid &&
      obj.process_created === identity.process_created, 'snapshot/final identity');
  }
  if (stage === 'final') {
    assert(final && final.events === events.length && final.written === events.length &&
    final.pending === 0 && final.errors.length === 0 && final.sha256, 'unflushed/failed final log');
  assert(events.at(-1).event === 'observer_closed', 'log after close');
  }
  for (const name of ['peer_during_confirm', afterEvent]) {
    if (stage === 'before_peer' && name === afterEvent) continue;
    const p = first(name).peer;
    assert(p && p.constructed === 0 && p.status_preserved === true &&
      p.pid === identity.pid && p.process_created === identity.process_created &&
      p.dir === identity.peers[name.replace('peer_', '')], 'peer identity/state: ' + name);
  }
  assert(no.seq < marker.seq && snapshot.state.pages === 3, 'marker before No');
  return { hwnd: shown.hwnd, marker_seq: marker.seq, pre_collection_seq: pre.seq, events: events.length };
}
function validate(events, snapshot, final, answer, identity, stage = 'final') {
  const checked = validateMachine(events, snapshot, final, identity, stage);
  const first = name => events.find(e => e.event === name && (name !== 'pre_collection' || e.request_id === snapshot.request_id));
  const marker = first('marker_created');
  assert(typeof answer.answer_original === 'string' && answer.answer_original.length > 0 &&
    answer.answer_run_id === identity.run_id && answer.answer_source, 'answer provenance/run');
  const at = Date.parse(answer.answer_captured_at);
  const answerLimit = Date.parse(first(stage === 'before_peer' ? 'pre_collection' : 'peer_after_answer').utc);
  assert(Number.isFinite(at) && at >= Date.parse(marker.utc) && at < answerLimit, 'answer time');
  const semantics = answer.answer_semantics;
  assert(semantics && semantics.approved_by && Number.isFinite(Date.parse(semantics.approved_at)) &&
    Date.parse(semantics.approved_at) >= at && Date.parse(semantics.approved_at) < answerLimit, 'human semantic approval missing/late');
  for (const key of ['answered_no', 'confirm_closed', 'three_pages', 'rotations_kept', 'single_window']) {
    const mapping = semantics[key];
    assert(mapping && mapping.confirmed === true && typeof mapping.quote === 'string' &&
      mapping.quote.length > 0 && answer.answer_original.includes(mapping.quote), 'answer mapping: ' + key);
  }
  return checked;
}
module.exports = { validate, validateMachine };
if (require.main === module) {
  let input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => input += chunk);
  process.stdin.on('end', () => {
    try { const p = JSON.parse(input); console.log(JSON.stringify(validate(p.events, p.snapshot, p.final, p.answer, p.identity, p.stage))); }
    catch (error) { console.error(error.message); process.exitCode = 1; }
  });
}
