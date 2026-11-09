// 今回の全体formatterによる、開始時cleanだったtrackedファイルだけを復元する。
const fs=require('fs'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const root=path.resolve(__dirname,'../../..');
const run=args=>{
  const r=cp.spawnSync('git',args,{cwd:root});
  if(r.status!==0) throw Error(r.stderr.toString());
  return r.stdout;
};
const initial=fs.readFileSync(path.join(__dirname,'baseline/git-status.txt'),'utf8').split(/\r?\n/);
const dirty=new Set(initial.filter(l=>/^ M /.test(l)).map(l=>l.slice(3)));
const changes=run(['diff','--name-only','-z']).toString().split('\0').filter(Boolean);
const targets=changes.filter(p=>!dirty.has(p));
if(targets.some(p=>p==='AGENTS.md'||p==='pyproject.toml'||p.startsWith('tests/')||p.startsWith('pagefolio/'))) throw Error('unexpected target');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const report=[];
for(const p of targets){
  const full=path.join(root,p), formatted=fs.readFileSync(full), original=run(['show','HEAD:'+p]);
  report.push({path:p,formatted_sha256:hash(formatted),restored_sha256:hash(original)});
  fs.writeFileSync(full,original);
}
fs.writeFileSync(path.join(__dirname,'formatter-restoration.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({restored_clean_tracked:report.length,remaining_tracked_changes:run(['diff','--name-only','-z']).toString().split('\0').filter(Boolean)}));
