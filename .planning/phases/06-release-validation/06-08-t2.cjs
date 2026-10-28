const fs=require('node:fs'), path=require('node:path'), {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const t2=process.argv[2], stage=process.argv[3];
if(!t2||!['protect','launch','update','faults'].includes(stage))throw Error('T2 root and stage required');
const build=JSON.parse(fs.readFileSync(path.join(__dirname,'06-BUILD-EVIDENCE.json')));
if(build.generation!==5)throw Error('generation5 required');
const code=String.raw`import sys,json,pathlib
root=pathlib.Path(sys.argv[1]); t2=pathlib.Path(sys.argv[2]); stage=sys.argv[3]
driver=root/'.planning/phases/06-release-validation/06-04-drivers/t2_driver.py'
sys.argv=[str(driver),str(t2),stage]
scope={'__name__':'generation5_driver','__file__':str(driver)}
exec(compile(driver.read_bytes(),str(driver),'exec'),scope)
keys={'protect':'protection_stop','launch':'launch','update':'update','faults':'fault_sessions'}
if keys[stage] in scope['load'](): raise RuntimeError('stage already recorded')
if scope['S'].probe_owner(): raise RuntimeError('existing production owner; no launch')
original=scope['hold_session']
def guarded(*args,**kwargs):
    record=original(*args,**kwargs)
    expected_retained=record['case'] in ('fault-x04-save-write','fault-x04-save-replace')
    record['cleanup_classification']='X04 first-save failure retention; forced cleanup is not human pass' if expected_retained else 'normal close required'
    dest=t2/('attempt-'+record['run_id']+'.json')
    with dest.open('x',encoding='utf-8') as f: json.dump(record,f,ensure_ascii=False,indent=2)
    errors=[]
    if not expected_retained and any(p['result']!='closed' for p in record['stop']): errors.append('abnormal stop')
    if not expected_retained and record['stop_diagnostics']: errors.append('stop diagnostics present')
    if record['owner_after']: errors.append('owner remains')
    if not record['source_unchanged']: errors.append('source changed')
    if record['hash_before_effective']!=record['hash_stable_effective']: errors.append('protected files changed while running')
    if errors: raise RuntimeError('FIRST FAILURE '+record['run_id']+': '+','.join(errors))
    return record
scope['hold_session']=guarded
scope['stage_'+stage]()
`;
const prefix=path.join(__dirname,'06-08-'+stage);
const out=fs.openSync(prefix+'.stdout.txt','wx'), err=fs.openSync(prefix+'.stderr.txt','wx');
const started=new Date().toISOString();
const child=spawn(path.join(root,'.venv/Scripts/python.exe'),['-c',code,root,t2,stage],{cwd:root,windowsHide:true,stdio:['ignore',out,err],env:{...process.env,PYTHONIOENCODING:'utf-8'}});
child.on('close',code=>{
 fs.closeSync(out);fs.closeSync(err);
 fs.writeFileSync(prefix+'.json',JSON.stringify({stage,code,started,finished:new Date().toISOString(),t2},null,2),{flag:'wx'});
 console.log(JSON.stringify({stage,code,t2}));
 console.log(fs.readFileSync(prefix+'.stdout.txt','utf8').slice(-1600));
 console.log(fs.readFileSync(prefix+'.stderr.txt','utf8').slice(-1600));
 process.exitCode=code;
});
