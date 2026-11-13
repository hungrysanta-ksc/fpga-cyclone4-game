"""Whole linked733 cost, including the actual removed constant storage.

The prior code-only sub-budget is reported, not silently treated as passed.
Whole Flash and the expanded code+padding boundary charge both sides equally.
"""
import argparse,json
from pathlib import Path
from analyze_nes_rows713 import resources
from nes_schedule492 import funcs
from check_nes_game478 import ELFFile
from nes_raw506 import sha

def run(a):
 previous=json.loads((a.probe.parent/'nes-extent732/resources01.json').read_text())
 names=tuple(previous['builds']['B']['whole_functions'])
 rows={}
 for label,p in [('727_normal',a.probe.parent/'nes-pair727/normal01/src'),('727_long',a.probe.parent/'nes-pair727/arm01/src'),('732B_normal',a.probe.parent/'nes-extent732/normal02/src'),('733_normal',a.probe/'normal02/src'),('733_long',a.probe/'arm02/src')]:
  r=resources(p);f=funcs(p/'obj-nes-100/sd2snes.elf');cost={}
  for n in names:
   matches=[x for x in f if x[0]==n and (n!='status' or x[2]==278)]
   assert len(matches)<=1,(n,matches)
   cost[n]=matches[0][2] if matches else 0
  with (p/'obj-nes-100/sd2snes.elf').open('rb') as h:
   e=ELFFile(h);z=[s['st_size'] for s in e.get_section_by_name('.symtab').iter_symbols() if s.name.startswith('zero.')]
   assert len(z)==1,z
  r.update(whole_functions=cost,code_boundary_B=sum(cost.values()),padding_constant_B=z[0],source_SHA256=sha(p/'nes_native_sink165.c'))
  r['code_plus_padding_B']=r['code_boundary_B']+r['padding_constant_B'];rows[label]=r
 cap=rows['727_normal']['code_plus_padding_B']+4
 for kind in ('normal','long'):
  b,c=rows['727_'+kind],rows['733_'+kind]
  assert c['sections']==b['sections'] and c['structs']==b['structs']
  c['old_code_only_subgate']=c['code_boundary_B']<=4970
  c['whole_budget_pass']=c['Flash_B']<=212992 and c['code_plus_padding_B']<=cap
  assert c['whole_budget_pass']
 r=dict(stage=733,scope=__doc__,Flash_cap_B=212992,old_code_only_cap_B=4970,expanded_code_plus_padding_cap_B=cap,builds=rows,
  note='The added code is8B versus732B; constant storage falls238B. Code-only subgate still fails, but actual code+constant and entire linked image both shrink. No unallocated RAM or free code reclamation is assumed.')
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({k:{n:v[n] for n in ('Flash_B','code_boundary_B','padding_constant_B','code_plus_padding_B')} for k,v in rows.items()}))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
