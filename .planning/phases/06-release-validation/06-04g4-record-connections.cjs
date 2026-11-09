const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const code=String.raw`import importlib.util,json,pathlib,shutil
p=pathlib.Path('.planning/phases/06-release-validation')
spec=importlib.util.spec_from_file_location('assembly',p/'06-04-drivers/assemble_protection.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
e=json.loads(a.EVIDENCE.read_text('utf-8'))
assert e['generation']==4 and not e['connection']
base=pathlib.Path('C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g4_07447e7e5cfc42988b80fb84c58293ae/runs')
report=[]
for kind,rid in [('ocr-single','6dd0b4d0997b4b8eb0ccb665ab067123'),('w05b-modal','1125b7a0cfad4a4ab00a08b522e5aab1')]:
    source=base/('release-uat-'+rid)/'evidence'/('session-'+kind+'.json')
    session=json.loads(source.read_text('utf-8'))
    assert not session.get('error') and not session.get('peer_error') and not session.get('selftest')
    assert session['binary_sha256']==e['build_ref']['exe_sha256'] and session['tree_sha256']==e['build_ref']['tree_sha256']
    assert not session['owner_after'] and session['verify_after']['ok'] and not session['verify_after']['distribution_changed']
    assert all(s['result']=='already-exited' for s in session['stop'])
    assert session['completed_seen'] and not session['server_summary']['expired']
    assert session['server_summary']['posts']==1 and not session['foreground_trace_errors']
    entry=a.build_connection(session,kind)
    if kind=='w05b-modal':
        for key in ['modal_shown','peer_returned_to_modal','answered_no','same_request_completed']: assert entry[key],key
        before=entry['derivation']['modal_before_peer']; after=entry['derivation']['modal_after_peer']
        hwnd=session['foreground_after_peer']['hwnd']
        assert hwnd in {w['hwnd'] for w in before}&{w['hwnd'] for w in after}
        trace=session['foreground_trace']
        assert trace[0]['hwnd']!=hwnd and any(s['hwnd']==hwnd for s in trace)
        assert session['peer_return_user_answer']=='自動で同じ確認画面に戻った'
        entry['automatic_return_confirmed_by_user']=True
        entry['same_modal_hwnd']=hwnd
    entry['foreground_trace']=session['foreground_trace']
    entry['foreground_trace_errors']=session['foreground_trace_errors']
    entry['cleanup_note']='利用者がOCR画面とメイン画面を閉じ、終了確認はいで通常終了。driver回収時はprimary/peerともalready-exited。強制終了なし。'
    if kind=='ocr-single': entry['cleanup_user_answer']='PageFolio を終了した'
    dest=p/('06-04g4-session-'+kind+'.json')
    if dest.exists(): raise RuntimeError('connection raw already preserved')
    shutil.copyfile(source,dest)
    entry['preserved_session_file']=dest.name
    e['connection'].append(entry)
    report.append({'kind':kind,'run_id':rid,'posts':session['server_summary']['posts'],'stop':session['stop'],'modal_hwnd':entry.get('same_modal_hwnd')})
e['status']='complete'; e.pop('connection_pending')
e['purpose_note']='世代4のbuild/保護/外部障害条件/接続準備を実測。接続準備は110行の本受入passとは別。release_allowed=false。'
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
print(json.dumps(report,ensure_ascii=False))
`;
const r=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-c',code],{cwd:root,encoding:'utf8',windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');process.exitCode=r.status??1;
