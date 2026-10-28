const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const relative='.planning/phases/06-release-validation/06-08-evidence/native-ready-20261028/';
const read=name=>fs.readFileSync(path.join(root,relative,name),'utf8');
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const result=JSON.parse(read('result.json')),checks=JSON.parse(read('checks.json'));
if(result.code!==0||result.changed.length||checks.some(c=>c.exit!==0))throw Error('quality did not pass');
for(const [file,hash] of Object.entries(result.after))if(sha(fs.readFileSync(path.join(root,file)))!==hash)throw Error('input drift: '+file);
const stdout=read('stdout.txt'),match=stdout.match(/(\d+) passed, (\d+) warnings in ([\d.]+)s/);
if(!match||Number(match[1])!==2232)throw Error('unexpected full-suite summary');
const file=path.join(__dirname,'06-BUILD-EVIDENCE.json'),build=JSON.parse(fs.readFileSync(file,'utf8'));
if(build.generation!==5||build.quality_before_build)throw Error('unexpected or already finalized generation');
build.quality_before_build=build.quality;
build.quality={...build.quality,scope_note:'世代5の台帳・接続準備確定後の単一全件。build前品質はquality_before_buildに保持。',pytest:{...build.quality.pytest,result:match[0],exit:0,passed:Number(match[1]),log:relative+'stdout.txt',log_sha256:sha(stdout),evidence:relative+'result.json',input_count:Object.keys(result.after).length}};
fs.writeFileSync(file,JSON.stringify(build,null,2)+'\n');
const audits=[];
for(const mode of ['build-only','preparation-only','allow-pending']){
 const argv=['tests/release_uat_support.py','audit','--phase-dir','.planning/phases/06-release-validation','--'+mode];
 const r=cp.spawnSync(path.join(root,'.venv/Scripts/python.exe'),argv,{cwd:root,encoding:'utf8',windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
 const parsed=JSON.parse(r.stdout);audits.push({argv,exit:r.status,result:parsed,stderr:r.stderr});
 fs.writeFileSync(path.join(__dirname,'06-08-evidence/final-audits.json'),JSON.stringify(audits,null,2)+'\n');
 if(r.status!==0||!parsed.ok)throw Error('audit failed: '+mode);
}
console.log(JSON.stringify({quality:match[0],inputs:Object.keys(result.after).length,audits:audits.map(a=>({mode:a.result.mode,exit:a.exit})),release_allowed:false}));
