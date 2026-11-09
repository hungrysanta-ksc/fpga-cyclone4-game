"""Isolated linked ARM tag/hash search cost, not joint SPI/IRQ timing."""
import argparse,json,re,struct
from pathlib import Path
from check_nes_game478 import Machine,sha
from nes_raw506 import encode
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R2

def run(a):
 palette=struct.pack('<64H',*map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(',')))
 m=Machine(a.arm,palette);stats={};pending={};returns=set();last_BG={}
 def returned(u,pc,size,user):
  key=(pc,u.reg_read(UC_ARM_REG_SP))
  if key not in pending:return
  name,start=pending.pop(key);r=stats.setdefault(name,dict(calls=0,instructions=0));r['calls']+=1;r['instructions']+=m.instructions-start
 def entered(name):
  def hook(u,pc,size,user):
   n=name+('_BG' if u.reg_read(UC_ARM_REG_R2)==1 else '_OBJ') if name=='tile' else name
   ret=u.reg_read(UC_ARM_REG_LR)&~1;key=(ret,u.reg_read(UC_ARM_REG_SP));assert key not in pending
   pending[key]=(n,m.instructions)
   if ret not in returns:returns.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
  return hook
 for n in ('tile','find221'):
  pc=m.syms[n];m.u.hook_add(UC_HOOK_CODE,entered(n),begin=pc,end=pc)
 def written(u,pc,size,user):
  nonlocal last_BG
  q=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2),40))
  if q[6]==0:last_BG=json.loads(json.dumps(stats))
 m.u.hook_add(UC_HOOK_CODE,written,begin=m.writer,end=m.writer)
 rows=[]
 for serial,g in enumerate(range(905,a.end+1),1):
  geometry=(a.data/f'frame{g}.geometry').read_bytes();raw=(a.data/f'frame{g}.raw').read_bytes();packets,_,_=encode(geometry,raw,g)
  stats={};last_BG={};r=m.frame(packets,geometry,raw,g,serial);assert not pending
  rows.append(dict(generation=g,ntiles=r['tiles'],planner_instructions=r['planner_instructions'],search=stats,search_before_last_BG=last_BG,
   source_SHA256=sha(a.data/f'frame{g}.geometry'),plan_SHA256=__import__('hashlib').sha256(json.dumps(r['plans']).encode()).hexdigest()))
  print(g,stats,flush=True)
 a.out.write_text(json.dumps(dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows,
  scope=__doc__+' Unit128KiB workspace, immediate plan callback, no SPI/ROM/IRQ waits. Entire search time is an optimistic deletion ceiling, not a safe implementation saving.'),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','data','out'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--end',type=int,default=957);run(p.parse_args())
