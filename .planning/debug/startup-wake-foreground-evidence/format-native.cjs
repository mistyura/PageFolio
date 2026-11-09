// 必須の全体check/formatを完走し、既存資料への整形だけは採取前bytesへ戻す。
const fs=require('fs'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const root=path.resolve(__dirname,'../../..'),ruff=path.join(root,'.venv/Scripts/ruff.exe');
const attempt=process.argv[2];
if(!/^[a-z0-9-]+$/.test(attempt||'')) throw Error('attempt required');
const dir=path.join(__dirname,attempt); fs.mkdirSync(dir);
const execute=args=>cp.spawnSync(ruff,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:60000});
const lint=execute(['check','.']);
fs.writeFileSync(path.join(dir,'ruff-check-native.txt'),lint.stdout+lint.stderr);
const check=execute(['format','--check','.']);
fs.writeFileSync(path.join(dir,'ruff-format-before.txt'),check.stdout+check.stderr);
const files=[...new Set([...(check.stdout+check.stderr).matchAll(/-->\s+(.+?):\d+:\d+/g)].map(m=>m[1]))];
if(check.status!==0 && files.length===0) throw Error('formatterの変更対象を取得できないため中止');
const originals=files.map(p=>[p,fs.readFileSync(path.join(root,p))]);
const formatted=execute(['format','.']);
fs.writeFileSync(path.join(dir,'ruff-format-native.txt'),formatted.stdout+formatted.stderr);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const restored=[];
for(const [p,b] of originals){fs.writeFileSync(path.join(root,p),b);restored.push({path:p,sha256:hash(b),matches:hash(fs.readFileSync(path.join(root,p)))===hash(b)});}
const report={lint_exit:lint.status,format_exit:formatted.status,restored,scope_note:'全体formatの完走後、今回対象外の既存ファイルはコマンド直前bytesへ戻した。'};
fs.writeFileSync(path.join(dir,'ruff-native.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({lint_exit:lint.status,format_exit:formatted.status,restored:restored.length}));
process.exitCode=lint.status===0&&formatted.status===0?0:1;
