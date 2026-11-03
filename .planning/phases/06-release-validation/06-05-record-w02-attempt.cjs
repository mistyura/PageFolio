// 操作未実施の回答と原本を保存する。判定は not-run のままにする。
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const phase=__dirname,root=path.resolve(phase,'../../..');
const name=process.argv[2]||'W02_settings_at_script-20261028T110310Z.json';
if(!['W02_settings_at_script-20261028T110310Z.json','W02_thumb_at_script-20261028T112320Z.json','W03_pdf-3page_at_script-20261028T123333Z.json','W03_pdf-3page_at_module-20261028T124840Z.json','W05a_nested-settings_at_module-20261028T150224Z.json','W05a_nested-settings_at_module-20261028T150612Z.json','W05a_nested-settings_at_module-20261028T150929Z.json','W05a_nested-settings_at_module-20261028T151354Z.json'].includes(name))throw Error('unexpected session');
const relative='06-05-evidence/'+name;
const raw=fs.readFileSync(path.join(phase,relative)),s=JSON.parse(raw);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const missingPdf=s.row==='W02/thumb@script'&&s.answers.kept==='PDFなし';
const w03Preparation=s.row==='W03/pdf-3page@module'&&s.outcome==='procedure-contaminated'&&s.procedure_assessment.pagefolio_presses_before_peer_done.length===2&&s.procedure_assessment.pagefolio_presses_before_peer_done.every(e=>e.phase==='awaiting-enter');
const w03=w03Preparation||(s.row==='W03/pdf-3page@script'&&s.answers.redo_1==='4 横'&&s.answers.undo_2==='画面が消えた');
const nestedWrongField=name==='W05a_nested-settings_at_module-20261028T150612Z.json'&&s.procedure_verdict==='clean'&&s.answers.input==='入らない（カーソル位置が入力欄にない。Tab押せない）'&&s.harness_inspect.json['manual-nested-input.json']?.text==='ux input';
const nestedSwitch=name==='W05a_nested-settings_at_module-20261028T151354Z.json'&&s.procedure_assessment.pagefolio_keys_before_peer_done.length===11&&s.procedure_assessment.pagefolio_keys_before_peer_done.every(e=>[9,88].includes(e.vk)&&e.phase==='awaiting-enter');
const nestedEarlyX=(nestedSwitch||(name==='W05a_nested-settings_at_module-20261028T150929Z.json'&&s.procedure_assessment.pagefolio_keys_before_peer_done.length===1&&s.procedure_assessment.pagefolio_keys_before_peer_done.every(e=>e.vk===88&&e.phase==='awaiting-enter')))&&s.harness_peer.json.result.result==='connection_failed';
const nested=s.row==='W05a/nested-settings@module'&&(nestedWrongField||nestedEarlyX||(s.procedure_verdict==='keys-suspect'&&s.procedure_assessment.rerun_required&&s.procedure_assessment.pagefolio_keys_before_peer_done.length===2&&s.procedure_assessment.pagefolio_keys_before_peer_done.every(e=>e.vk===9&&e.phase==='peer')));
if((!nested&&!w03&&!missingPdf&&(s.row!=='W02/settings@script'||s.answers.input!=='押していない'||s.answers.kept!=='分からない'))||s.selftest||s.error||s.cleanup.alive_after.length)throw Error('unexpected attempt');
const ledgerPath=path.join(phase,'06-MANUAL-EVIDENCE.json'),ledger=JSON.parse(fs.readFileSync(ledgerPath));
const row=ledger.cases.find(c=>c.id===s.case).subrows.find(r=>r.card===s.row);
if(ledger.generation!==5||row.status!=='not-run'||row.attempts?.some(a=>a.session_file===relative))throw Error('unexpected ledger or duplicate');
const run=path.resolve(s.run);
if(!run.startsWith(path.join(root,'.planning','tmp')+path.sep))throw Error('unexpected run root');
const dest=path.join(phase,relative.replace('.json','-raw'));
if(fs.existsSync(dest))throw Error('raw already preserved');
const pending=[];
for(const [label,dir,names] of [['run',run,['manifest.json']],['primary',path.join(run,'uat-owner-'+(nested?'nested':w03?'pdf':s.condition)),['result.json','focus-result.json','resource-audit.json','ready','stderr.log','stdout.log','traceback.log',...(w03?['manual-pdf-ready.json']:[]),...(nested?['manual-nested-closed.json','manual-nested-input.json']:[])]]]){
 for(const name of names){const source=path.join(dir,name);if(!fs.existsSync(source))continue;pending.push({source,target:path.join(dest,label+'-'+name),bytes:fs.readFileSync(source)});}
}
if((!nestedEarlyX&&!pending.some(p=>p.source.endsWith('focus-result.json')))||!pending.some(p=>p.source.endsWith('result.json')))throw Error('missing originals');
fs.mkdirSync(dest);const copies=[];
for(const p of pending){fs.writeFileSync(p.target,p.bytes,{flag:'wx'});copies.push({source:p.source,target:path.relative(phase,p.target).replaceAll('\\','/'),sha256:hash(p.bytes)});}
fs.writeFileSync(path.join(dest,'copies.json'),JSON.stringify(copies,null,2)+'\n');
const reason=w03?'4手確認を完遂せず一次が約120秒の試験期限で終了（elapsed122829ms）。Redo1も4ページとの回答であり、時間切れだけでは説明せずdebug/w03-manual-sequence.mdで入力経路を調査中。未完了attemptをpassにせず原回答を保持。':missingPdf?'自動復帰・F5往復は成功したが、PDFなしとの直接回答。harnessがCanvasの入力先だけ用意しPDFを作っていなかった準備不足。空選択のstate_preservedを選択保持passへ転用しない。':'自動復帰の回答と機械観測は一致したが、実キー入力は押していない・保持は分からないとの回答。操作時刻が分からなかったため未実施であり、passにも製品failにも変更しない。';
const followup=w03Preparation?null:w03?{answer:'Ctrl+Yを押したが4ページのままだった',source:'request_user_input_async/call_5ce671a4dab8436a956db14c49d63423'}:!missingPdf?{answer:'x を押すタイミングが分からなかった',source:'request_user_input_async/call_62bffc89159448918cea271749f480f1'}:null;
row.attempts??=[];row.attempts.push({status:'not-run',reason:w03Preparation?'準備中の2クリックをW01/W02入力先保持用の規則が拒否し、利用者の4手操作前にdriver停止。peer自体はcompleted/63ms、正常回収。W03は準備中のクリックと復帰中の無操作を分ける必要があり、driverを修正して再確認する。':reason,session_file:relative,session_sha256:hash(raw),run_id:path.basename(run),observed_at:s.finished_at,answer:s.composed_answer,raw_inputs:s.raw_inputs,procedure_assessment:s.procedure_assessment,cleanup:s.cleanup,raw_copy_manifest:path.relative(phase,path.join(dest,'copies.json')).replaceAll('\\','/'),...(followup?{followup}:{})});
if(nested){const attempt=row.attempts.at(-1);attempt.reason='自動復帰中にTabを2回検出し、利用者もTabを押したと回答。入力先の自動保持を判定できないためnot-runを維持し、操作を限定して再確認する。製品failとは扱わない。';attempt.followup={answer:'Tabを押した',source:'request_user_input_async/call_bc2199e7d6524a2194f04bf8a8ea123b'};}
if(nestedWrongField){const attempt=row.attempts.at(-1);attempt.reason='機械記録では外側検証欄へx入力されux inputになったが、人は通常のフォントサイズ等を見ていたと補足。対象欄の保持・入力を人が確認していないためnot-runを維持し、場所を先に示して再確認する。';attempt.followup={answer:'フォントサイズなど通常の設定欄を見ていた',source:'request_user_input_async/call_c0fc2c1b1a304bcfa08cdc471f734ded'};}
if(nestedEarlyX){const attempt=row.attempts.at(-1);attempt.reason='二次起動前(awaiting-enter)にx入力を記録。選択範囲が消え、検証snapshotが selection isn\'t in widget .!settingsdialog.!entry で例外となりpeerはconnection_failed/10141ms。準備が崩れた実行を受入へ転用せず、対象欄と音を合図にした操作順へ案内を修正する。';delete attempt.followup;}
if(nestedSwitch){const attempt=row.attempts.at(-1);attempt.reason='二次起動前の設定画面でTab10回/x1回を検出。選択範囲消失で検証snapshotが例外となりpeerはconnection_failed/10125ms。利用者はPowerShellへ切り替えたつもりでも設定画面だったと補足。開始前の画面切替を確認する手順へ変更し、not-runのまま原回答を保持。';attempt.followup={answer:'PowerShellへ切り替えたつもりでも設定画面のままだった',source:'request_user_input_async/call_4f02b09ba1384154be0eaa83df155776'};}
fs.writeFileSync(ledgerPath,JSON.stringify(ledger,null,2)+'\n');
console.log(JSON.stringify({row:row.card,status:row.status,attempts:row.attempts.length,copied:copies.length}));
