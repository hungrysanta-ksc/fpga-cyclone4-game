# SPDX-License-Identifier: MIT
"""Reconcile row CPU costs, live schedules and unchanged whole RTL cost."""
import argparse,ast,collections,json
from pathlib import Path
import analyze_nes_source368 as prior
from analyze_nes_receipt335 import load_image
from analyze_nes_hint367 import hierarchy
from check_nes_compact354 import objects
from nes_delta231 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
 p.add_argument('--last',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=BASE/'probes/nes-source369';d=a.run.resolve();old=BASE/'probes/nes-source368/joint07'
 read=prior.read;js=prior.js
 diagnostic='Fatal: capture coverage367' in read(d/'vsim.log')
 candidate=prior.measure(d,a.last,int(diagnostic));control=prior.measure(old,910,1)
 pairs=[]
 for x,y in zip(candidate['rows'][2:],control['rows'][2:]):
  same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  assert x['frame']==y['frame']
  if x['frame']<=909:assert same
  pairs.append(dict(frame=x['frame'],before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_start_ROM_phase=same))
 assert load_image(d/'output.elf')==load_image(root/'build01/output.elf')
 assert load_image(d/'pre369-output.elf')==load_image(old/'output.elf')
 assert objects(d/'output.elf')==objects(old/'output.elf')
 sources=js(d/'manifest367.json')['sources'];shared={}
 for n in sources:
  read(d/n);read(old/n);assert sha(d/n)==sha(old/n);shared[n]=sha(d/n)
 assert js(d/'manifest368.json')['shared_boundary']==js(old/'manifest368.json')['shared_boundary']
 from nes_source368 import FILES
 arm_inputs=set(FILES)|{'nes_input286.inc','nes_decode280.c'}
 for p in old.iterdir():
  if p.is_file() and (p.name in arm_inputs or p.suffix=='.h') and p.name!='nes_resident211.c':
   assert sha(p)==sha(d/p.name),(p.name,'unexpected ARM source change')
 expected=read(old/'nes_resident211.c')
 moved=' bool retain=ordinary(q);\n uint32_t key=q->kind==2?65534u:q->tag|(kind?(uint32_t)q->mask<<13:0);\n'
 assert expected.count(moved)==1
 expected=expected.replace(moved,'').replace(' if(exact_slot!=stop)return exact_slot;\n',' if(exact_slot!=stop)return exact_slot;\n'+moved)
 assert expected==read(d/'nes_resident211.c')
 checks=js(root/'check02.json');profile=js(root/'profile01/profile369.json')
 assert checks['passed'] and len(checks['direct_cases'])==320 and len(checks['rows'])==41
 assert checks['total_saved']==113020 and checks['global_objects']==96
 assert len(checks['STOP_cases'])==5
 assert sha(root/'build01/output.elf') in checks['pins'].values()
 assert sha(root/'profile01/output.elf')==sha(old/'output.elf')==profile['source_ELF']
 assert checks['pins'][str(ROOT/'tools/check_nes_schedule369.py')]==sha(ROOT/'tools/check_nes_schedule369.py')
 assert sha(root/'profile01/executed-worker367.py')==sha(old/'executed-worker367.py')
 executed=ast.parse(read(root/'run_profile.py'))
 reproducible=ast.parse(read(ROOT/'tools/profile_nes_schedule369.py'))
 assert ast.dump(next(x for x in executed.body if isinstance(x,ast.ClassDef)))==ast.dump(next(x for x in reproducible.body if isinstance(x,ast.ClassDef)))
 counts=collections.Counter()
 for x in profile['rows']:counts.update(x['exclusive'])
 assert sum(counts.values())==516431
 # These are disjoint top-level ARM.call intervals; do not sum nested
 # preparation/watch events with them or call them peripheral wait savings.
 calls=js(old/'calls337.json');start=control['rows'][4]['start_ps']/1000;intervals=[]
 for c in calls:
  if start<=c['start']['modeled_ns'] and c['end']['modeled_ns']<=start+control['rows'][4]['processing_ms']*1e6:
   intervals.append(dict(name=c['name'],start_ms=(c['start']['modeled_ns']-start)/1e6,duration_ms=(c['end']['modeled_ns']-c['start']['modeled_ns'])/1e6))
 size=dict(before=prior.size(d/'pre369-output.elf'),after=prior.size(d/'output.elf'))
 size['delta']={k:size['after'][k]-size['before'][k] for k in size['before']}
 assert size['delta']==dict(text=8,data=0,BSS=0)
 board=BASE/'probes/nes-source368/map01';whole=prior.whole(board);cost=hierarchy(board)
 assert whole['comb']==17698
 previous=js(ROOT/'analysis/source368-verification.json')
 assert previous['whole_MAP']['after']==whole
 assert js(d/'manifest368.json')['shared_boundary']==previous['shared_boundary']
 for n in ('nes_schedule369.py','probe_nes_schedule369.py','check_nes_schedule369.py','profile_nes_schedule369.py','analyze_nes_schedule369.py'):read(ROOT/'tools'/n)
 result=dict(stage=369,analysis_passed=True,continuous_capture_passed=candidate['continuous_capture_passed'],candidate=candidate,control=control,paired=pairs,
  measured_row_CPU=dict(instructions_before=516431,saved=113020,allocated_CPI1_saved_ms=113020/84000,exclusive=dict(counts),new_timing=False),
  baseline909_intervals=intervals,checks=checks,ARM_size=size,unchanged_functional_RTL=shared,
  whole_MAP=dict(values=whole,inherited_from368=True,new_MAP=False,delta=dict(LE=0,comb=0,FF=0,RAM_bits=0),hierarchy=cost),
  comb_deficit=2290,deletion_needed_with155reserve=2445,
  scope='Actual M4 row changes with live shared SPI/IRQ and input/output ROM stress. CPU CPI/exception adapters; ordinary65816 trace and DMA/final display bus model. Not full VBlank/firmware WCET/71/heavy7/multiple phases/physical60fps.',
  FIT=False,STA=False,physical=False,sustained60fps=False,pins=prior.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(paired=pairs,captures=candidate['captures'],ARM_size=size),indent=2))
if __name__=='__main__':main()
