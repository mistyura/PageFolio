const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const code=String.raw`import importlib.util,json,pathlib,shutil
p=pathlib.Path('.planning/phases/06-release-validation')
spec=importlib.util.spec_from_file_location('assembly',p/'06-04-drivers/assemble_protection.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
raw=pathlib.Path('C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g4_07447e7e5cfc42988b80fb84c58293ae/t2-result.json')
dest=p/'06-04g4-t2-result.json'
if dest.exists(): raise RuntimeError('generation already assembled')
t=json.loads(raw.read_text('utf-8')); b=json.loads((p/'06-BUILD-EVIDENCE.json').read_text('utf-8'))
old=json.loads(a.EVIDENCE.read_text('utf-8')); final=b['final_release']
if old['generation']!=3 or b['generation']!=4: raise RuntimeError('generation mismatch')
for rec in t['fault_sessions'].values():
    assert rec['binary_sha256']==final['exe_sha256'] and rec['tree_sha256']==final['tree_sha256']
    assert rec['source_unchanged'] and not rec['owner_after']
prev=old.pop('previous_generations',[])
prev.append({'generation':3,'status':'superseded','superseded_reason':'CR-03修正後のv1.10.2へ更新。旧W05b不成立を保持','evidence':old})
ev={'generation':4,'previous_generations':prev,'version':b['version'],
    'status':'partial-pending-human-check','release_allowed':False,
    'purpose_note':'外部保護・障害条件の実測。接続実証と人手110行は未実施。X04強制終了は正常終了/passではない。',
    'build_ref':{'final_run_id':next(r['run_id'] for r in final['runs'] if r['order']=='rebuild'),'exe_sha256':final['exe_sha256'],'tree_sha256':final['tree_sha256']},
    'raw_observation_log':dest.name,'protection_stop':a.build_protection_stop(t),
    'launch':a.build_launch(t),'update':a.build_update(t),'faults':a.build_faults(t),
    'connection':[],'connection_pending':['ocr-single','w05b-modal'],
    'guard_stop_note':t['g4_fault_resume_note']}
assert all(f['established'] for f in ev['faults'].values())
shutil.copyfile(raw,dest)
a.S.write_json(a.EVIDENCE,ev)
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
a.build_run_refs=refs
labels=a.patch_prep(ev)
text=a.PREP.read_text('utf-8')
text=text.replace('status: preparation-blocked-w05b-automatic-return-unverified','status: preparation-pending-generation4-connection',1)
marker='## 現行状態（06-04 世代3・2026-10-28）'
current='''## 現行状態（06-04 世代4・2026-10-28）

CR-03修正後のv1.10.2。全件2083 passed、Phase04/05 fresh passed、新入力で初回/再build各1回成功、build-only exit0。
最終EXE '''+final['exe_sha256']+'''。保護3名・起動時保持3条件・更新衝突/非衝突・X01〜X05外部条件の記録は 06-04g4-t2-result.json。
X04 write/replaceは初回WM_CLOSE後12秒で終了せず、所有handleで回収した。追加guardがこれを一律失敗扱いして停止した原記録も保持。D19の画面維持仕様を確認し、未実施replace/X05のみ続行した。通知・次の終了操作の人手合否は未判定。
実EXEのocr-single/W05b接続はこれから実施。sourceの「isolated OCR」確認画面が自動復帰したとの回答は診断証拠で、実EXEや本受入のpassには転記しない。110行not-run、Phase06未完了、出荷未承認。
以下の世代3停止は履歴。現在の再開は利用者の「出荷停止状態を解消して」に基づく。

## 過去の状態（06-04 世代3・2026-10-28）'''
if marker not in text: raise RuntimeError('missing generation3 heading')
a.PREP.write_text(text.replace(marker,current,1),encoding='utf-8',newline='\n')
print(json.dumps({'generation':4,'faults_established':list(ev['faults']),'run_refs':len(labels),'connection_pending':ev['connection_pending']},ensure_ascii=False))
`;
const r=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-c',code],{cwd:root,encoding:'utf8',windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
process.stdout.write(r.stdout||''); process.stderr.write(r.stderr||'');process.exitCode=r.status??1;
