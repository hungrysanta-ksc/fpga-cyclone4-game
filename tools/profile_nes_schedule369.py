# SPDX-License-Identifier: MIT
"""Exact recorded-SPI replay and exclusive M4 row profiles; no new timing."""
import sys,json,shutil,bisect,collections,argparse,os
from pathlib import Path
import replay_nes_source368 as replay
from nes_delta231 import BASE,sha
from probe_nes_arm264 import ELFFile
from nes_bg295 import unbatch as unbatch295
from nes_bg293 import unbatch
parser=argparse.ArgumentParser();parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
REFERENCE=a.reference.resolve();replay.REFERENCE=REFERENCE
D=a.out.resolve();D.mkdir(parents=True,exist_ok=False)
for f in REFERENCE.iterdir():
 if f.is_file() and not f.name.startswith(('arm-req','arm-rsp')):shutil.copyfile(f,D/f.name)
instances=[]
class Profile(replay.baseline.ARM367):
 def __init__(self,*args):
  super().__init__(*args);self.rows=[];self.profiling=False;instances.append(self)
  with args[0].open('rb') as f:
   e=ELFFile(f);self.funcs=sorted((s['st_value']&~1,s['st_size'],s.name) for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC' and s['st_size'])
  self.starts=[x[0] for x in self.funcs]
 def hook(self,uc,address,size,user):
  if self.profiling:
   i=bisect.bisect_right(self.starts,address)-1
   n=self.funcs[i][2] if i>=0 and address<self.funcs[i][0]+self.funcs[i][1] else 'return_or_stub'
   self.counts[n]+=1
  super().hook(uc,address,size,user)
 def call(self,name,args):
  serial=int.from_bytes(self.uc.mem_read(self.symbols['receiver280']+4,4),'little')
  if name!='next_step286' or serial!=5:return super().call(name,args)
  i=len(self.rows);p=D/f'row369-{i}.bin';p.write_bytes(bytes(self.uc.mem_read(0x20000000,0x40000)))
  self.counts=collections.Counter();before=self.instructions;self.profiling=True
  try:result=super().call(name,args)
  finally:self.profiling=False
  assert sum(self.counts.values())==self.instructions-before
  self.rows.append(dict(index=i,result=result,instructions=self.instructions-before,exclusive=dict(self.counts),snapshot=p.name,sha256=sha(p)))
  return result
s=(REFERENCE/'executed-worker367.py').read_text();_,ns=replay.baseline.worker_source()
ns.update(ARM=Profile,Live=replay.Replay,os=os,unbatch295=unbatch295,unbatch=unbatch)
exec(compile(s,'schedule369-recorded-worker','exec'),ns);ns['worker'](D,910,False,True)
result=dict(passed=True,new_timing=False,source_ELF=sha(D/'output.elf'),transactions=instances[-1].endpoint.seq,rows=instances[-1].rows)
(D/'profile369.json').write_text(json.dumps(result,indent=2)+'\n')
print('PROFILE369',json.dumps(dict(transactions=result['transactions'],first=result['rows'][0],total=sum(x['instructions'] for x in result['rows']))))
