// W12aの9行のみ。採取runと利用者の二段階回答を照合して単一行へ記録する。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const phase = __dirname;
const root = path.resolve(phase, '../../..');
const check = (ok, why) => { if (!ok) throw Error(why); };
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const raw = p => fs.readFileSync(p);
const json = p => JSON.parse(raw(p).toString('utf8'));
const stamp = value => { const n = Date.parse(value); check(Number.isFinite(n), '時刻不正'); return n; };
const entries = ['script', 'module', 'relocated'];
const consent = new Set(['採用', '採用。', '採用してよい', '採用してよい。']);
const dry = process.argv.includes('--dry-run');
check(process.argv.length === (dry ? 4 : 3), 'usage: answer.json [--dry-run]');
const name = process.argv[2];
check(/^W12a_(script|module|relocated)-(script|module|relocated)_at_(script|module|relocated)-\d{8}T\d{6}Z\.json$/.test(name || ''), '回答名不正');
const evidence = path.join(phase, '06-05-evidence');
const safe = (base, relative) => {
  check(typeof relative === 'string' && relative && !path.isAbsolute(relative) && !relative.includes('\\'), '相対path不正');
  const full = path.resolve(base, relative);
  check(full.startsWith(base + path.sep) && fs.realpathSync.native(full).startsWith(fs.realpathSync.native(base) + path.sep) &&
    !fs.lstatSync(full).isSymbolicLink(), 'run外pathまたはlink');
  return full;
};
const answerPath = safe(evidence, name);
const answerRaw = raw(answerPath);
const a = JSON.parse(answerRaw.toString('utf8'));
const primary = a.primary, secondary = a.secondary;
check(a.schema === 'w12a-answer-v1' && entries.includes(primary) && entries.includes(secondary) &&
  a.row === `W12a/${primary}-${secondary}@${primary}` &&
  name.startsWith(`W12a_${primary}-${secondary}_at_${primary}-`), '対象行/入口不一致');
const run = path.resolve(root, a.run || '');
const tmp = path.join(root, '.planning/tmp');
check(run.startsWith(tmp + path.sep) && /^pagefolio-uat-[0-9a-f]{32}$/.test(path.basename(run)) &&
  fs.realpathSync.native(run).startsWith(fs.realpathSync.native(tmp) + path.sep) &&
  !fs.lstatSync(run).isSymbolicLink(), 'run外または任意path');
const files = ['manifest.json', 'w12a-driver.json', 'w12a-after-peer.json', 'inspection.json',
  'provenance-before-stop.json', `entry-owner-${primary}/ready`,
  `entry-owner-${primary}/result.json`, `entry-owner-${primary}/resource-audit.json`];
const manifestRaw = raw(safe(run, 'manifest.json'));
const m = JSON.parse(manifestRaw.toString('utf8'));
check(m.w12a_schema === 'w12a-v1' && m.w12a_primary === primary &&
  m.w12a_peer_entry === secondary && m.role === `entry-owner-${primary}` &&
  m.run === run && m.namespace !== 'fixed-production' &&
  path.resolve(m.fixture) === path.join(run, `entry-owner-${primary}`) &&
  a.manifest_sha256 === sha(manifestRaw), '一次run/manifest不一致');
const owner = m.expected_owner;
check(owner?.manual === true && Number.isInteger(owner.pid) && owner.pid > 0 &&
  Number.isFinite(owner.process_created) && owner.process_created > 0, '一次identity不正');
const exact = (bytes, prefix='') => {
  const match = bytes.toString('utf8').match(new RegExp(prefix + '[\\s\\S]*?"process_created"\\s*:\\s*(\\d+)'));
  check(match, 'FILETIME欠落'); return match[1];
};
const ownerFiletime = exact(manifestRaw, '"expected_owner"');
const ready = json(safe(run, `entry-owner-${primary}/ready`));
check(a.owner_process_created === ownerFiletime &&
  ready.pid === owner.pid &&
  exact(raw(safe(run, `entry-owner-${primary}/ready`))) === ownerFiletime,
  '一次FILETIME不一致');
const driver = json(safe(run, 'w12a-driver.json'));
check(driver.schema === 'w12a-driver-v1' && driver.run === run &&
  driver.primary === primary && driver.secondary === secondary &&
  driver.events.map(e => e.step).join(',') === 'start,peer,foreground,inspect,stop' &&
  driver.events[0].role === m.role && driver.events[0].owner.pid === owner.pid &&
  driver.events[1].result.constructed === 0 && driver.events[4].originals_unchanged === true,
  'driver途中失敗/一回性不成立');
check(driver.events.every(e=>e.at_utc) &&
  driver.events.every((e,i)=>i===0 || stamp(driver.events[i-1].at_utc)<=stamp(e.at_utc)) &&
  stamp(driver.events[4].at_utc)<=stamp(driver.finished_at), 'driver時系列不正');
check(raw(safe(run, 'w12a-peer-started')).toString('utf8') === secondary, 'peer一回性marker不一致');
const fg = json(safe(run, 'w12a-after-peer.json'));
check(fg.entry === secondary && fg.owner_verified === true &&
  Number.isInteger(fg.hwnd) && fg.hwnd > 0 && fg.pid === owner.pid &&
  fg.peer_fixture.startsWith(run + path.sep), '実foreground/同ownerが不足');
check(stamp(driver.events[0].at_utc)<stamp(fg.at_utc) &&
  stamp(fg.at_utc)<=stamp(driver.events[1].at_utc), '前景採取時点不正');
const peerRel = path.relative(run, fg.peer_fixture).replaceAll('\\', '/');
check(/^peer-[0-9a-f]{32}$/.test(peerRel), 'peer fixture不正');
files.push(`${peerRel}/result.json`, `${peerRel}/resource-audit.json`,
  `${peerRel}/expected-owner.json`, `${peerRel}/stdout.log`, `${peerRel}/stderr.log`,
  'w12a-peer-started');
const peerResult = json(safe(run, `${peerRel}/result.json`));
const peerExpectedRaw = raw(safe(run, `${peerRel}/expected-owner.json`));
const peerExpected = JSON.parse(peerExpectedRaw.toString('utf8'));
const peerAuditRaw = raw(safe(run, `${peerRel}/resource-audit.json`));
const peerAudit = JSON.parse(peerAuditRaw.toString('utf8'));
check(peerResult.constructed === 0 && ['completed','foreground_denied'].includes(peerResult.result) &&
  peerExpected.pid === owner.pid && exact(peerExpectedRaw) === ownerFiletime &&
  Number.isInteger(peerAudit.pid) && peerAudit.pid !== owner.pid &&
  peerAudit.verified_owner?.pid === owner.pid &&
  exact(peerAuditRaw, '"verified_owner"') === ownerFiletime &&
  peerAudit.owner_result === 'existing' &&
  peerAudit.allow_foreground?.pid === owner.pid &&
  typeof peerAudit.allow_foreground.allowed === 'boolean' &&
  Number.isInteger(peerAudit.allow_foreground.os_error), '二次API/owner不一致');
const ownerResult = json(safe(run, `entry-owner-${primary}/result.json`));
check(ownerResult.constructed === 1 && ownerResult.restored === 1 &&
  ownerResult.status_preserved === true && ownerResult.result === 'primary', '一次復帰/終了不一致');
const inspected = json(safe(run, 'inspection.json'));
check(JSON.stringify(inspected.manifest) === JSON.stringify(m) && inspected.originals_unchanged === true &&
  JSON.stringify(inspected['result.json']) === JSON.stringify(ownerResult), '回収inspection不一致');
check(json(safe(run, 'provenance-before-stop.json')).matched === true, '回収前入力不一致');
check(['pagefolio_settings.json','ocr_custom_prompt.md','ocr_summary_prompt.md'].every(n =>
  m.originals_before?.[n] === (fs.existsSync(path.join(root,n)) ? sha(raw(path.join(root,n))) : null)),
  '元設定/2prompt不一致');
const inputs = m.formal_provenance?.source_inputs;
const enumeratePython = () => {
  const found = ['pagefolio.py', '.planning/phases/06-release-validation/06-05-w12a-driver.py'];
  for (const directory of ['pagefolio', 'tests']) {
    const visit = relative => {
      for (const item of fs.readdirSync(safe(root, relative), {withFileTypes:true})) {
        if (item.name === '__pycache__') continue;
        const key = `${relative}/${item.name}`;
        check(!item.isSymbolicLink(), 'Python入力にsymlink');
        if (item.isDirectory()) visit(key);
        else if (item.isFile() && item.name.endsWith('.py')) found.push(key);
      }
    };
    visit(directory);
  }
  return found.sort();
};
const currentInputs = enumeratePython();
check(inputs && currentInputs.join('\n') === Object.keys(inputs).sort().join('\n') &&
  currentInputs.every(k => sha(raw(safe(root, k))) === inputs[k]), '現行Python source_inputs不一致');
check(m.formal_provenance.w12a_helper_sha256 === sha(raw(__filename)), 'W12a helper来歴不一致');
const pluginRoot = path.join(root, 'plugins');
const pluginFiles = fs.existsSync(pluginRoot) ? fs.readdirSync(pluginRoot,{recursive:true,withFileTypes:true})
  .filter(x=>x.isFile()).map(x=>path.relative(pluginRoot,path.join(x.parentPath,x.name)).replaceAll('\\','/')) : [];
const plugins = m.formal_provenance.original_plugins;
check(plugins && pluginFiles.sort().join(',') === Object.keys(plugins).sort().join(',') &&
  pluginFiles.every(k=>sha(raw(safe(pluginRoot,k)))===plugins[k]), '元plugins不一致');
const p4 = m.formal_provenance.phase04;
const reportPath = path.join(root, '.planning/phases/04-startup-control/04-VERIFICATION.md');
const reportRaw = raw(reportPath);
const digest = reportRaw.toString('utf8').match(/^covered_digest: "([^"]+)"\r?$/m)?.[1];
check(p4.status === 'passed' && digest === p4.covered_digest &&
  sha(reportRaw) === p4.report_sha256, '親fresh report/hash不一致');
const node = process.execPath;
const gsd = path.join(process.env.USERPROFILE || '', '.codex/gsd-core/bin/gsd-tools.cjs');
check(fs.existsSync(gsd), '親fresh CLIなし');
const gate = JSON.parse(execFileSync(node, [gsd, 'query', 'verification.status',
  path.join(root, '.planning/phases/04-startup-control'), '--raw'], {cwd: root, encoding: 'utf8', timeout: 15000}));
check(gate.status === 'passed', '親freshでない');
const copyInputs = [];
if (primary === 'relocated' || secondary === 'relocated') {
  const fixtures = [primary === 'relocated' ? `entry-owner-${primary}` : null,
    secondary === 'relocated' ? peerRel : null].filter(Boolean);
  for (const fixture of fixtures) {
    const alternate = safe(run, `${fixture}/alternate/pagefolio.py`);
    check(sha(raw(alternate)) === inputs['pagefolio.py'], '別配置entry source不一致');
    const dir = path.join(run, fixture, 'alternate', 'pagefolio');
    for (const source of fs.readdirSync(dir, {recursive: true, withFileTypes: true})) {
      if (!source.isFile() || !source.name.endsWith('.py')) continue;
      const rel = path.relative(run, path.join(source.parentPath, source.name)).replaceAll('\\', '/');
      const original = rel.split('/alternate/')[1];
      check(inputs[original] === sha(raw(safe(run, rel))), '別配置copyhash不一致');
      copyInputs.push(rel);
    }
    copyInputs.push(`${fixture}/alternate/pagefolio.py`);
  }
}
files.push(...copyInputs);
const human = a.direct_answer;
check(human?.source === 'user-direct' && human.row === a.row &&
  typeof human.text === 'string' && human.text.includes(a.row) &&
  typeof human.source_ref === 'string' && human.source_ref.trim() &&
  human.observations?.one_primary_screen === 'はい' &&
  human.observations?.secondary_returns_to_primary === 'はい' &&
  human.observations?.state_kept === 'はい', '利用者直接回答不足');
const answerAt = stamp(human.captured_at);
check(answerAt > stamp(driver.finished_at), '直接回答が回収前');
const adoption = a.adoption;
check(adoption?.decision === '採用' && adoption.approved_by === '利用者' &&
  adoption.source === 'user-direct' && adoption.source_ref?.trim() &&
  adoption.source_ref !== human.source_ref &&
  consent.has(adoption.text?.trim()) &&
  adoption.answer_sha256 === sha(Buffer.from(human.text)) &&
  stamp(adoption.approved_at) > Math.max(answerAt, stamp(driver.finished_at),
    fs.statSync(safe(run, 'manifest.json')).mtimeMs,
    fs.statSync(safe(run, 'inspection.json')).mtimeMs), '回収後の明示採用不足');
const build = json(path.join(phase, '06-BUILD-EVIDENCE.json'));
check(build.generation === 5 && build.version === 'v1.10.2', '世代不一致');
const copies = [...new Set(files)].map(n => ({name: n, bytes: raw(safe(run, n))}));
const ledgerPath = path.join(phase, '06-MANUAL-EVIDENCE.json');
const uatPath = path.join(phase, '06-UAT.md');
const ledger = json(ledgerPath);
const row = ledger.cases.find(c => c.id === 'W12a')?.subrows.find(r => r.card === a.row);
check(row?.status === 'not-run' && row.generation === 5 && row.entry === primary &&
  row.condition === `${primary}-${secondary}` && row.evidence_kind === 'python-real' &&
  row.required_observations.join(',') ===
    'one_primary_screen,secondary_returns_to_primary,state_kept,api_return,actual_foreground',
  '対象行不一致/既採用');
const uat = raw(uatPath).toString('utf8');
const marker = `### ${a.row}`;
const start = uat.indexOf(marker);
check(start >= 0 && (start === 0 || uat[start-1] === '\n'), 'UAT card欠落');
const end0 = uat.indexOf('\n### ', start + marker.length);
const end = end0 < 0 ? uat.length : end0;
const card = uat.slice(start, end);
check(card.includes('- **状態**: not-run'), 'UAT card既採用');
check(/本受入は必須108行中\d+行pass・\d+行not-run・W11対象外2行not-run。/.test(uat),
  'UAT集計行不在');
const targetDir = path.join(evidence, name.replace(/\.json$/, '-raw'));
check(!fs.existsSync(targetDir), 'raw上書き禁止');
const ref = `06-05-evidence/${name}`;
const output = {row: a.row, status: 'pass', run: path.basename(run), dry_run: dry};
if (dry) { console.log(JSON.stringify(output)); process.exit(0); }
fs.mkdirSync(targetDir);
const copyManifest = copies.map(({name:n,bytes}) => {
  const dest = path.join(targetDir, n.replaceAll('/', '-'));
  fs.writeFileSync(dest, bytes, {flag:'wx'});
  return {source:n, sha256:sha(bytes), target:path.relative(phase,dest).replaceAll('\\','/')};
});
fs.writeFileSync(path.join(targetDir,'copies.json'), JSON.stringify(copyManifest,null,2)+'\n',{flag:'wx'});
row.status = 'pass';
row.preparation = {status:'prepared', run_id:path.basename(run), note:'隔離した実Python一次入口から一度だけ二次起動。'};
row.observations = {one_primary_screen:true, secondary_returns_to_primary:true,
  state_kept:true,
  api_return:{allowed:peerAudit.allow_foreground.allowed,os_error:peerAudit.allow_foreground.os_error,
    terminal_result:peerAudit.terminal_result},
  actual_foreground:{hwnd:fg.hwnd,pid:fg.pid,at:fg.at_utc}};
row.answer = human.text;
row.raw_inputs = [{key:'direct_answer',text:human.text,at:human.captured_at},
  {key:'adoption',text:adoption.text,at:adoption.approved_at}];
row.answer_provenance = `${human.source_ref}; 回収後別回答 ${adoption.source_ref}`;
row.run_id = path.basename(run); row.observed_at = human.captured_at;
row.environment = {...m.environment,elevated:m.environment.is_admin};
row.input_manifest_sha256 = build.final_release.input_manifest_sha256;
row.source_commit = m.source_commit;
row.observation_basis = {answer_file:ref,answer_sha256:sha(answerRaw),
  raw_copy_manifest:path.relative(phase,path.join(targetDir,'copies.json')).replaceAll('\\','/'),
  primary,secondary,owner:{pid:owner.pid,process_created:ownerFiletime},
  peer_fixture:peerRel,source_inputs:inputs,phase04:p4,
  w12a_helper_sha256:m.formal_provenance.w12a_helper_sha256};
const safeText = human.text.replaceAll('\r','\\r').replaceAll('\n','\\n');
const newCard = card.replace(/- \*\*状態\*\*: not-run[^\n]*/,
  `- **状態**: pass / 利用者直接回答・同一一次ownerと実foregroundを照合。根拠: ${ref}\n- **回答原文**: ${safeText}`);
let newUat = uat.slice(0,start)+newCard+uat.slice(end);
const passed = ledger.cases.flatMap(c=>c.subrows).filter(r=>r.release_requirement==='required'&&r.status==='pass').length;
newUat = newUat.replace(/本受入は必須108行中\d+行pass・\d+行not-run・W11対象外2行not-run。/,
  `本受入は必須108行中${passed}行pass・${108-passed}行not-run・W11対象外2行not-run。`);
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');
fs.writeFileSync(uatPath,newUat);
console.log(JSON.stringify(output));
