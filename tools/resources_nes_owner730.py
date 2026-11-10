"""Charge730 one bulk service plus shared span costs on the same727 boundary."""
import argparse,json
from pathlib import Path
from analyze_nes_rows713 import resources
from nes_schedule492 import funcs
from nes_raw506 import sha

def run(a):
 previous=json.loads((a.probe.parent/'nes-pair727/resources01.json').read_text())
 names=tuple(previous['normal']['whole_functions'])+('span','span_cost227')
 rows={}
 for label,path in [('base_normal',a.probe.parent/'nes-pair727/normal01/src'),('base_long',a.probe.parent/'nes-pair727/arm01/src'),('A_normal',a.probe/'normal01/src'),('A_long',a.probe/'arm01/src'),('normal',a.probe/'normal02/src'),('long',a.probe/'arm02/src')]:
  r=resources(path);f=funcs(path/'obj-nes-100/sd2snes.elf');cost={}
  for n in names:
   matches=[x for x in f if x[0]==n and (n!='status' or x[2]==278)]
   assert len(matches)<=1,(n,matches)
   cost[n]=matches[0][2] if matches else 0
  r.update(whole_functions=cost,whole_boundary_B=sum(cost.values()),source_hashes={n:sha(path/n) for n in ('nes_native_sink165.c','nes_plan_service200.c')})
  rows[label]=r
 cap=rows['base_normal']['whole_boundary_B']+4
 for k,b in [('normal','base_normal'),('long','base_long')]:
  assert rows[k]['Flash_B']<=212992 and rows[k]['whole_boundary_B']<=cap
  assert rows[k]['sections']==rows[b]['sections'] and rows[k]['structs']==rows[b]['structs']
 r=dict(stage=730,Flash_cap_B=212992,expanded_boundary_cap_B=cap,note='727 whole boundary plus existing span188B and cost82B; same old4B margin, no free reclamation.',builds=rows)
 a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:{n:v[n] for n in ('Flash_B','whole_boundary_B')} for k,v in rows.items()}))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
