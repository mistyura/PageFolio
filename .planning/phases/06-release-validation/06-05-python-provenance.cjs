// 区分A(Python再採取)の正式記録recorder共通module。
// 目的: 旧harness採取を書込前に拒否し、harnessがstart時に保存したformal_provenanceを現行treeと照合し、
//       消失したfinal_dirではなく照合済みの復元配布のrelease-report.jsonから凍結入力を読み、台帳の新有効行を一意に選ぶ。
// 依存: Node標準moduleのみ。rootとphaseは呼出側の__dirnameから渡す(このmoduleは自分の位置から実台帳を推測しない)。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');

const PROVENANCE_MISSING = 'formal_provenance欠落（旧harness採取のため再採取が必要）';
const SUPERSESSION = '06-05-evidence/PYTHON-INPUT-SUPERSESSION-20261106.json';
const SUMMARY_RE = /本受入は必須108行(?:not-run|中\d+行pass・\d+行not-run)・W11対象外2行not-run。/g;

const fail = why => { throw Error(why); };
const check = (ok, why) => { if (!ok) fail(why); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const isObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);

// 配布tree/入力treeの列挙。symlinkと特殊ファイルは拒否する(w12bのwalkと同じ規則)。
function walk(base, suffix = null) {
  const files = [], dirs = [];
  const visit = rel => {
    const directory = rel ? path.join(base, rel) : base;
    for (const item of fs.readdirSync(directory, {withFileTypes: true})) {
      check(!item.isSymbolicLink(), '入力treeにsymlink');
      const key = rel ? `${rel}/${item.name}` : item.name;
      if (item.isDirectory()) { dirs.push(key); visit(key); }
      else if (item.isFile() && (!suffix || item.name.endsWith(suffix))) files.push(key);
      else if (!item.isFile()) fail('入力treeに特殊ファイル');
    }
  };
  visit('');
  return {files: files.sort(), dirs: dirs.sort()};
}

// w12bのtreeHashと同じ規則: dirsとfilesをsortし、filesは相対path→sha256、hashはJSON.stringify({dirs,files})のsha256。
function treeHash(dir) {
  const tree = walk(dir);
  const files = Object.fromEntries(tree.files.map(k => [k, sha(fs.readFileSync(path.join(dir, k)))]));
  return {files, hash: sha(Buffer.from(JSON.stringify({dirs: tree.dirs, files})))};
}

// 消失したfinal_dirではなく、照合付きでrestored_final_dirのrelease-report.jsonを読む。
function resolveFinalReport({phase, build}) {
  const final = build?.final_release;
  check(isObject(final), 'final_releaseがない');
  const restored = final.loss_incident?.restored_final_dir;
  const candidates = [
    restored ? {dir: path.resolve(restored), source: 'restored_final_dir'} : null,
    final.final_dir ? {dir: path.resolve(final.final_dir), source: 'final_dir'} : null,
  ].filter(Boolean);
  const chosen = candidates.find(c => fs.existsSync(c.dir));
  check(chosen, '最終配布treeが存在しない(restored_final_dir/final_dir)');
  const {dir, source} = chosen;
  check(!fs.lstatSync(dir).isSymbolicLink(), '最終配布rootがsymlink');
  const tree = treeHash(dir);
  check(tree.hash === final.tree_sha256, '最終配布tree hash不一致');
  check(tree.files['PageFolio.exe'] === final.exe_sha256, '最終配布PageFolio.exe hash不一致');
  const reportFile = path.join(dir, 'release-report.json');
  check(fs.existsSync(reportFile), 'release-report.jsonがない');
  const report = JSON.parse(fs.readFileSync(reportFile, 'utf8'));
  const rebuild = (final.runs || []).filter(r => r.order === 'rebuild');
  check(rebuild.length === 1 && rebuild[0].run_id && report.run_id === rebuild[0].run_id,
    'release-report.jsonのrun_idがrebuild runと不一致');
  const embedded = final.loss_incident?.restoration_verification?.embedded_report_run_id;
  if (final.loss_incident) check(embedded === report.run_id, 'release-report.jsonのrun_idが復元検証記録と不一致');
  check(isObject(report.input_manifest), 'release-reportにinput_manifestがない');
  return {finalDir: dir, report, source};
}

// tests/test_startup_windows.py の _formal_source_inputs と同じ列挙(__pycache__除外・symlink拒否)。
function enumeratePython(root) {
  const found = [];
  for (const rel of ['pagefolio.py', '.planning/phases/06-release-validation/06-05-w12a-driver.py']) {
    const full = path.join(root, rel);
    if (!fs.existsSync(full)) continue;
    check(!fs.lstatSync(full).isSymbolicLink() && fs.lstatSync(full).isFile(), 'Python入力が通常ファイルでない');
    found.push(rel);
  }
  for (const directory of ['pagefolio', 'tests']) {
    const visit = rel => {
      for (const item of fs.readdirSync(path.join(root, rel), {withFileTypes: true})) {
        if (item.name === '__pycache__') continue;
        const key = `${rel}/${item.name}`;
        check(!item.isSymbolicLink(), 'Python入力にsymlink');
        if (item.isDirectory()) visit(key);
        else if (item.isFile() && item.name.endsWith('.py')) found.push(key);
      }
    };
    visit(directory);
  }
  return found.sort();
}

// _formal_original_plugins と同じ: plugins配下の全ファイル。
function enumeratePlugins(root) {
  const pluginRoot = path.join(root, 'plugins');
  if (!fs.existsSync(pluginRoot)) return {};
  const out = {};
  for (const key of walk(pluginRoot).files) out[key] = sha(fs.readFileSync(path.join(pluginRoot, key)));
  return out;
}

function sameKeysAndHashes(saved, current) {
  const a = Object.keys(saved).sort(), b = Object.keys(current).sort();
  return a.join('\n') === b.join('\n') && a.every(k => saved[k] === current[k]);
}

// harnessがstart時に保存したformal_provenanceを、記録時の現行treeと照合する。最初の不一致でthrowする。
function checkFormalProvenance({root, run, manifest}) {
  // (1) 旧harness採取はrun dirに触れる前に拒否する。
  const fp = manifest?.formal_provenance;
  if (!isObject(fp) || !isObject(fp.source_inputs) || !isObject(fp.original_plugins) || !isObject(fp.phase04)) {
    fail(PROVENANCE_MISSING);
  }
  // (2) run dirのmanifest・停止前照合記録との一致。
  const tmp = path.join(path.resolve(root), '.planning', 'tmp');
  const runDir = path.resolve(run || '');
  check(runDir.startsWith(tmp + path.sep), 'run dirが.planning/tmp外');
  check(fs.existsSync(path.join(runDir, 'manifest.json')), 'run/manifest.jsonがない');
  const runManifest = JSON.parse(fs.readFileSync(path.join(runDir, 'manifest.json'), 'utf8'));
  check(JSON.stringify(runManifest.formal_provenance) === JSON.stringify(fp), 'run/manifest.jsonのformal_provenanceがsessionと不一致');
  const stopFile = path.join(runDir, 'provenance-before-stop.json');
  check(fs.existsSync(stopFile) && JSON.parse(fs.readFileSync(stopFile, 'utf8')).matched === true,
    'provenance-before-stop.jsonがmatched:trueでない');
  // (3) 現行Python入力との集合・hash一致。
  const currentKeys = enumeratePython(root);
  const current = Object.fromEntries(currentKeys.map(k => [k, sha(fs.readFileSync(path.join(root, k)))]));
  check(sameKeysAndHashes(fp.source_inputs, current), '現行Python source_inputs不一致');
  const harness = fp.source_inputs['tests/test_startup_windows.py'];
  check(typeof harness === 'string' && harness.length === 64, 'source_inputsにharnessがない');
  // (4) 元plugins。
  check(sameKeysAndHashes(fp.original_plugins, enumeratePlugins(root)), '元plugins不一致');
  // (5) Phase04親検証。
  const p4 = fp.phase04;
  const reportRaw = fs.readFileSync(path.join(root, '.planning/phases/04-startup-control/04-VERIFICATION.md'));
  const digest = reportRaw.toString('utf8').match(/^covered_digest: "([^"]+)"\r?$/m)?.[1];
  check(p4.status === 'passed' && sha(reportRaw) === p4.report_sha256 && digest === p4.covered_digest,
    '親Phase04 report/hash/digest不一致');
  const gsd = path.join(process.env.USERPROFILE || '', '.codex/gsd-core/bin/gsd-tools.cjs');
  check(fs.existsSync(gsd), '親fresh CLIなし');
  const gate = JSON.parse(execFileSync(process.execPath, [gsd, 'query', 'verification.status',
    path.join(root, '.planning/phases/04-startup-control'), '--raw'], {cwd: root, encoding: 'utf8', timeout: 15000}));
  check(gate.status === 'passed', '親Phase04 freshでない');
  const keys = Object.keys(fp.source_inputs).sort();
  return {
    formal: fp,
    observed: {
      label: 'python-input-' + harness.slice(0, 12),
      harness_sha256: harness,
      source_inputs_sha256: sha(Buffer.from(JSON.stringify(keys.map(k => [k, fp.source_inputs[k]])))),
      source_input_count: keys.length,
      plugin_count: Object.keys(fp.original_plugins).length,
    },
    provenance_before_stop: true,
  };
}

// 台帳の新有効行だけを一意に選ぶ。python_input_generationは現行harness hashと比較せず、書き換えない。
function selectEffectiveRow({phase, ledger, caseId, card, entry}) {
  const cases = (ledger.cases || []).filter(c => c.id === caseId);
  check(cases.length === 1, `台帳のcaseが一意でない: ${caseId}`);
  const rows = (cases[0].subrows || []).filter(r => r.card === card);
  check(rows.length === 1, `台帳のcardが一意でない: ${card}`);
  const row = rows[0];
  check(row.status === 'not-run' && row.generation === 5 && row.release_requirement === 'required' &&
    row.evidence_kind === 'python-real' && row.entry === entry, '行が採取待ちの新有効行でない(判定済み/世代/種別/入口)');
  const supersessionFile = path.join(phase, SUPERSESSION);
  check(fs.existsSync(supersessionFile), 'PYTHON-INPUT-SUPERSESSIONがない');
  const supersession = JSON.parse(fs.readFileSync(supersessionFile, 'utf8'));
  check(isObject(row.supersedes) && row.supersedes.path === SUPERSESSION &&
    Number.isInteger(row.supersedes.row_index) &&
    supersession.rows?.[row.supersedes.row_index]?.card === card, 'supersedesリンクが同じcardを指さない');
  check(typeof supersession.superseded_by === 'string' && row.python_input_generation === supersession.superseded_by,
    'python_input_generationがSUPERSESSIONのsuperseded_byと不一致');
  return row;
}

// 06-UAT.mdのcardを見出しで一意に特定する(CRLF/LF両対応)。
function locateUatCard(uat, card) {
  const heading = '### ' + card;
  let count = 0, start = -1, headingEnd = -1, eol = '\n';
  for (let at = uat.indexOf(heading); at >= 0; at = uat.indexOf(heading, at + 1)) {
    const prev = at === 0 || uat[at - 1] === '\n';
    const after = uat.slice(at + heading.length, at + heading.length + 2);
    const crlf = after === '\r\n', lf = after[0] === '\n';
    if (prev && (crlf || lf)) { count++; start = at; headingEnd = at + heading.length; eol = crlf ? '\r\n' : '\n'; }
  }
  check(count === 1, `UAT cardが一意でない: ${card} (${count}件)`);
  const next = uat.indexOf('\n### ', headingEnd);
  const stop = next < 0 ? uat.length : next;
  const text = uat.slice(start, stop);
  check(text.includes('- **状態**: not-run'), 'UAT cardが既に判定済み');
  return {start, stop, card: text, eol};
}

// 集計行は丁度1回一致することを確認してから置換する。
function updateUatSummary(uat, passed) {
  check((uat.match(SUMMARY_RE) || []).length === 1, 'UAT集計行が丁度1件でない');
  return uat.replace(SUMMARY_RE, () => `本受入は必須108行中${passed}行pass・${108 - passed}行not-run・W11対象外2行not-run。`);
}

// card内の状態行を既存の改行を保ったままpassへ置換し、回答原文行を足し、集計行を更新した新しい全文を返す。
function applyUatPass({uat, card, passed, status, answer}) {
  const located = locateUatCard(uat, card);
  const safeAnswer = String(answer ?? '').replaceAll('\r', '\\r').replaceAll('\n', '\\n');
  const updated = located.card.replace(/- \*\*状態\*\*: not-run[^\r\n]*/,
    () => `- **状態**: ${status}${located.eol}- **回答原文**: ${safeAnswer}`);
  check(updated !== located.card, 'UAT状態行を置換できなかった');
  return updateUatSummary(uat.slice(0, located.start) + updated + uat.slice(located.stop), passed);
}

// run dirの停止前照合記録と回収記録(存在すれば)をraw copy対象として読む。
function provenanceRaw(run) {
  const out = [];
  for (const file of ['provenance-before-stop.json', 'inspection.json']) {
    const source = path.join(run, file);
    if (fs.existsSync(source)) out.push({file, source, bytes: fs.readFileSync(source)});
  }
  return out;
}

// 台帳行のobservation_basisに足す6欄。python_input_generationとsupersedesはここでは触らない。
function provenanceBasis({prov, finalSource, recorderFile}) {
  return {
    formal_provenance: prov.formal,
    observed_python_input: prov.observed,
    provenance_before_stop: prov.provenance_before_stop,
    final_report_source: finalSource,
    recorder_sha256: sha(fs.readFileSync(recorderFile)),
    provenance_module_sha256: sha(fs.readFileSync(__filename)),
  };
}

module.exports = {
  PROVENANCE_MISSING, SUPERSESSION, resolveFinalReport, checkFormalProvenance, selectEffectiveRow,
  locateUatCard, updateUatSummary, applyUatPass, provenanceRaw, provenanceBasis, treeHash, walk, sha,
};
