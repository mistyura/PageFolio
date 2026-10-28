const path=require('node:path'), {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..'), t2=process.argv[2];
if(!t2)throw Error('T2 root required');
const code=String.raw`import importlib.util,json,pathlib,shutil,sys
p=pathlib.Path('.planning/phases/06-release-validation')
spec=importlib.util.spec_from_file_location('assembly',p/'06-04-drivers/assemble_protection.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
raw=pathlib.Path(sys.argv[1])
if raw.is_dir(): raw=raw/'t2-result.json'
dest=p/'06-08-t2-result.json'
if dest.exists(): raise RuntimeError('generation already assembled')
t=json.loads(raw.read_text('utf-8')); b=json.loads((p/'06-BUILD-EVIDENCE.json').read_text('utf-8'))
old=json.loads(a.EVIDENCE.read_text('utf-8')); final=b['final_release']
if old['generation']!=4 or b['generation']!=5: raise RuntimeError('generation mismatch')
for rec in list(t['fault_sessions'].values())+t['launch']['cases']:
    assert rec['binary_sha256']==final['exe_sha256'] and rec['tree_sha256']==final['tree_sha256']
    assert rec['source_unchanged'] and not rec['owner_after']
prev=old.pop('previous_generations',[])
prev.append({'generation':4,'status':'superseded','superseded_reason':'保証範囲の配布文書更新後の新世代。旧観測を保持','evidence':old})
ev={'generation':5,'previous_generations':prev,'version':b['version'],
    'status':'partial-pending-human-check','release_allowed':False,
    'purpose_note':'外部保護・障害条件の準備実測。X04の強制回収は正常終了/passではない。必須108行の本受入とW11未確認2行を区別する。',
    'build_ref':{'final_run_id':next(r['run_id'] for r in final['runs'] if r['order']=='rebuild'),'exe_sha256':final['exe_sha256'],'tree_sha256':final['tree_sha256']},
    'raw_observation_log':dest.name,'protection_stop':a.build_protection_stop(t),
    'launch':a.build_launch(t),'update':a.build_update(t),'faults':a.build_faults(t),
    'connection':[],'connection_pending':['ocr-single','w05b-modal']}
assert all(f['established'] for f in ev['faults'].values())
shutil.copyfile(raw,dest);a.S.write_json(a.EVIDENCE,ev)
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
a.build_run_refs=refs;labels=a.patch_prep(ev)
text=a.PREP.read_text('utf-8')
import re
text=re.sub(r'^status: .+$','status: preparation-pending-generation5-connection',text,count=1,flags=re.M)
marker='## 現行状態（06-04 世代4・2026-10-28）'
current='''## 現行状態（06-08 世代5・2026-10-28）

単一ログインセッション保証の文書を同梱したv1.10.2。文書反映後の単一全件2232 passed、実初回/再build各1回成功。
最終EXE '''+final['exe_sha256']+'''。保護3名・起動時保持3条件・更新衝突/非衝突・X01〜X05外部条件は06-08-t2-result.json。
X04の初回保存失敗後の画面保持と強制回収は観測のまま保持し、人手合否にしない。
実EXEのocr-single/W05b接続は未実施。必須108行not-run、W11対象外2行not-run、Phase06未完了・出荷未承認。
以下の世代4は履歴。

## 過去の状態（06-04 世代4・2026-10-28）'''
if marker not in text: raise RuntimeError('missing generation4 heading')
a.PREP.write_text(text.replace(marker,current,1),encoding='utf-8',newline='\n')
print(json.dumps({'generation':5,'faults_established':list(ev['faults']),'run_refs':len(labels),'connection_pending':ev['connection_pending']},ensure_ascii=False))
`;
const r=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-c',code,t2],{cwd:root,encoding:'utf8',windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');process.exitCode=r.status??1;
