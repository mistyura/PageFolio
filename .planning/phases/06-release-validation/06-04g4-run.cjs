const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const stage = process.argv[2];
if (!['launch','update','faults'].includes(stage)) throw Error('invalid stage');
const root=path.resolve(__dirname,'../../..');
const t2='C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g4_07447e7e5cfc42988b80fb84c58293ae';
const py=path.join(root,'.venv/Scripts/python.exe');
const code = `import sys,json,pathlib
root=pathlib.Path(sys.argv[1]); t2=pathlib.Path(sys.argv[2]); stage=sys.argv[3]
driver=root/'.planning/phases/06-release-validation/06-04-drivers/t2_driver.py'
sys.argv=[str(driver),str(t2),stage]
scope={'__name__':'g4_driver','__file__':str(driver)}
exec(compile(driver.read_bytes(),str(driver),'exec'),scope)
if stage in scope['load'](): raise RuntimeError('stage already recorded')
original=scope['hold_session']
def guarded(*args,**kwargs):
    record=original(*args,**kwargs)
    dest=t2/('g4-attempt-'+record['run_id']+'.json')
    with dest.open('x',encoding='utf-8') as f: json.dump(record,f,ensure_ascii=False,indent=2)
    errors=[]
    if any(p['result']!='closed' for p in record['stop']): errors.append('abnormal stop')
    if record['stop_diagnostics']: errors.append('stop diagnostics present')
    if record['owner_after']: errors.append('owner remains')
    if not record['source_unchanged']: errors.append('source changed')
    if record['hash_before_effective']!=record['hash_stable_effective']: errors.append('protected files changed while running')
    if errors: raise RuntimeError('FIRST FAILURE '+record['run_id']+': '+','.join(errors))
    return record
scope['hold_session']=guarded
scope['stage_'+stage]()
`;
const prefix=path.join(__dirname,'06-04g4-'+stage);
const out=fs.openSync(prefix+'.stdout.txt','wx');
const err=fs.openSync(prefix+'.stderr.txt','wx');
const started=new Date().toISOString();
const child=spawn(py,['-c',code,root,t2,stage],{cwd:root,windowsHide:true,stdio:['ignore',out,err],env:{...process.env,PYTHONIOENCODING:'utf-8'}});
child.on('close',code=>{
  fs.closeSync(out);fs.closeSync(err);
  fs.writeFileSync(prefix+'.json',JSON.stringify({stage,code,started,finished:new Date().toISOString(),t2},null,2),{flag:'wx'});
  console.log(JSON.stringify({stage,code,t2}));
  console.log(fs.readFileSync(prefix+'.stdout.txt','utf8').slice(-2000));
  console.log(fs.readFileSync(prefix+'.stderr.txt','utf8').slice(-1800));
  process.exitCode=code;
});
