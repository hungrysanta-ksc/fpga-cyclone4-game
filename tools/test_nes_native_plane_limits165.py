# SPDX-License-Identifier: MIT
"""Changed 20-bit exception format: column0, capacity and canonical rejection."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_native_commands165 import Fetch
from nes_native_planes165 import pack,decode,MIXED
from nes_native_compact165 import equivalent
from test_nes_native_commands165 import fixture

def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 rtl='src/nes/diagnostic/nes_native_compact_planes165.sv';tb='tests/nes-functional/native_compact165_tb.sv'
 shutil.copy2(ROOT/rtl,a.out/Path(rtl).name)
 original=(ROOT/tb).read_text();assert original.count('nes_native_compact165 dut')==1
 (a.out/'tb.sv').write_text(original.replace('nes_native_compact165 dut','nes_native_compact_planes165 dut'))
 def run(exe,args,name):
  with (a.out/(name+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  s=(a.out/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:]
 run('vlib',['work'],'vlib');run('vlog',['-sv',Path(rtl).name,'tb.sv'],'vlog')
 base,_,_=fixture(0);results=[]
 for name,count,corrupt,ok in [('column0',1,None,True),('limit128',128,None,True),('overflow129',129,None,False),
                              ('unflagged',0,'unflagged',False),('OBJmixed',0,'obj',False),('reserved',0,'reserved',False)]:
  events=[];changed=False
  for word in base:
   f=Fetch.unpack(word);tick=f.row*1364+(f.rank*32 if f.obj else 280+f.x*32)+1
   if not f.obj and f.x==0 and f.row<count:word=pack(f,(f.fine+1)&7)
   if not changed and corrupt:
    if corrupt=='unflagged':word|=1<<53;changed=True
    elif corrupt=='reserved':word|=1<<63;changed=True
    elif f.obj:word|=MIXED|((f.fine+1)&7)<<53;changed=True
   events.append((tick,word))
  events.sort();previous=events[0][0]-1;lines=[]
  for tick,word in events:lines.append(f'{tick-previous} {word:016x}\n');previous=tick
  (a.out/(name+'.tsv')).write_text(''.join(lines))
  run('vsim',['-c','work.native_compact165_tb',f'+INPUT={name}.tsv',f'+OUTPUT={name}.dump',
   '-do','onerror {quit -code 1}; run -all; quit -f'],name)
  info,words=decode(a.out/(name+'.dump'));assert info['valid']==ok,(name,info)
  if ok:assert equivalent(words,[w for t,w in events]) and info['exceptions']==count
  elif name=='overflow129':assert info['error']&4
  else:assert info['error']&1
  info['name']=name;results.append(info)
 result=dict(passed=True,cases=results,public_sources={n:sha(ROOT/n) for n in [rtl,tb,'tools/nes_native_planes165.py',
  'tools/test_nes_native_plane_limits165.py','tools/test_nes_native_commands165.py']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
