const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../../..');
const code = String.raw`import importlib.util,json,pathlib,shutil
p=pathlib.Path('.planning/phases/06-release-validation')
spec=importlib.util.spec_from_file_location('assembly',p/'06-04-drivers/assemble_protection.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
e=json.loads(a.EVIDENCE.read_text('utf-8'))
assert e['generation']==5 and not e['connection']
base=pathlib.Path('C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g5_3f96a37a7cef4ee1ab3a1c1b2f2c435f/runs')
report=[]; pending=[]
import sys
assert len(sys.argv)==2 and len(sys.argv[1])==32 and all(c in '0123456789abcdef' for c in sys.argv[1])
for kind,rid in [('ocr-single','18986e4dd7b341bd81d4a6d4b0da8afd'),('w05b-modal',sys.argv[1])]:
    source=base/('release-uat-'+rid)/'evidence'/('session-'+kind+'.json')
    session=json.loads(source.read_text('utf-8'))
    assert not session.get('error') and not session.get('peer_error') and not session.get('selftest')
    assert session['binary_sha256']==e['build_ref']['exe_sha256'] and session['tree_sha256']==e['build_ref']['tree_sha256']
    assert not session['owner_after'] and session['verify_after']['ok'] and not session['verify_after']['distribution_changed']
    assert session['stop'] and all(s['result']=='already-exited' for s in session['stop'])
    assert session['completed_seen'] and not session['server_summary']['expired']
    assert session['server_summary']['posts']==1 and not session['foreground_trace_errors']
    events=[v['event'] for v in session['server_summary']['events']]
    assert all(events.count(name)==1 for name in ['received','released','completed'])
    raw_answers=json.dumps(session['user_inputs'],ensure_ascii=False)
    assert '合成OCR結果' in raw_answers and 'PageFolio を終了した' in raw_answers
    entry=a.build_connection(session,kind)
    if kind=='w05b-modal':
        for key in ['modal_shown','peer_returned_to_modal','answered_no','same_request_completed']: assert entry[key],key
        before=entry['derivation']['modal_before_peer']; after=entry['derivation']['modal_after_peer']
        hwnd=session['foreground_after_peer']['hwnd']
        assert hwnd in {w['hwnd'] for w in before}&{w['hwnd'] for w in after}
        trace=session['foreground_trace']
        assert trace[0]['hwnd']!=hwnd and any(s['hwnd']==hwnd for s in trace)
        assert session['peer_return_user_answer']=='自動で同じ確認画面に戻り、そのまま10秒待った'
        entry['automatic_return_confirmed_by_user']=True
        entry['same_modal_hwnd']=hwnd
    entry['foreground_trace']=session['foreground_trace']
    entry['foreground_trace_errors']=session['foreground_trace_errors']
    entry['answer_provenance']='利用者のチャット回答を担当がdriver stdinへ代理入力。原文はuser_inputsに保持。'
    entry['cleanup_note']='利用者が結果確認後にOCR画面とメイン画面を閉じ、終了確認はいで通常終了。primary/peerともalready-exited、残存ownerなし。'
    dest=p/('06-08-session-'+kind+'.json')
    assert not dest.exists(), 'connection raw already preserved'
    entry['preserved_session_file']=dest.name
    pending.append((source,dest,entry))
    report.append({'kind':kind,'run_id':rid,'posts':session['server_summary']['posts'],'stop':session['stop'],'modal_hwnd':entry.get('same_modal_hwnd')})
for source,dest,entry in pending:
    shutil.copyfile(source,dest)
    e['connection'].append(entry)
e['status']='complete'; e.pop('connection_pending')
e.setdefault('failed_connection_attempts',[]).append({'run_id':'31d4388e2cbb4f80944a015b67bc3234','kind':'w05b-modal','status':'not-established','session_file':'06-08-w05b-interrupted-session.json','clarification_file':'06-08-W05B-OBSERVATION.md','reason':'同確認HWNDへの自動復帰を約2.4秒観測したが、観測終了前に利用者がChatGPTへ手動切替した。peer後snapshot不一致のため合格にせず、操作手順を明確化した別runで確認する。'})
e['purpose_note']='世代5のbuild/保護/外部障害条件/接続準備を実測。必須108行の本受入とは別。W11の2行は承認済み対象外のまま未確認。release_allowed=false。'
a.S.write_json(a.EVIDENCE,e)
original=a.build_run_refs
def refs(evidence):
    labels=original(evidence)
    def visit(node):
        if isinstance(node,dict):
            if isinstance(node.get('run_id'),str): labels.setdefault(node['run_id'],'過去世代を含む原記録（現行受入への昇格なし）')
            for value in node.values(): visit(value)
        elif isinstance(node,list):
            for value in node: visit(value)
    visit(evidence)
    return labels
a.build_run_refs=refs; a.patch_prep(e)
text=a.PREP.read_text('utf-8')
text=text.replace('status: preparation-pending-generation5-connection','status: preparation-established-generation5')
text=text.replace('実EXEのocr-single/W05b接続は未実施。必須108行not-run、W11対象外2行not-run、Phase06未完了・出荷未承認。','実EXEのocr-single/W05b接続2件を実測。W05bはChatGPTから同確認HWNDへ自動復帰し、いいえで処理維持、同1POST完了を利用者回答と50ms観測で照合。両runは利用者が通常終了し残存ownerなし。原記録は06-08-session-*.json。必須108行not-run、W11対象外2行not-run、Phase06未完了・出荷未承認。')
a.PREP.write_text(text,encoding='utf-8',newline='\n')
print(json.dumps(report,ensure_ascii=False))
`;
const r = spawnSync(path.join(root,'.venv/Scripts/python.exe'), ['-c', code, ...process.argv.slice(2)], {cwd:root,encoding:'utf8',windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
process.stdout.write(r.stdout||''); process.stderr.write(r.stderr||''); process.exitCode=r.status??1;
