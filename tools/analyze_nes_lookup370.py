# SPDX-License-Identifier: MIT
"""Reconcile group-local checks, longer live cadence and whole port budget."""
import argparse,json
from pathlib import Path
import analyze_nes_source368 as prior
from analyze_nes_receipt335 import load_image
from check_nes_compact354 import objects
from nes_delta231 import ROOT,BASE,sha,once
from nes_lookup370 import HELPER

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--last',type=int,required=True)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.run.resolve()
 root=BASE/'probes/nes-source370';old=BASE/'probes/nes-source369/joint01';read=prior.read;js=prior.js
 strict=root/'joint01';strict_log=read(strict/'vsim.log')
 assert 'Fatal: next capture deadline missed367 frame915 owned1 initialized1 release0 fault0' in strict_log
 assert 'CADENCE367 attempts=8 admitted=7 missed=1' in strict_log
 diagnostic='Fatal: capture coverage367' in read(d/'vsim.log')
 assert diagnostic and a.last==914
 candidate=prior.measure(d,a.last,int(diagnostic));control=prior.measure(old,911,0);pairs=[]
 failed_prefix=prior.events(strict);drained=prior.events(d)
 def prefix(e):
  at=next(i for i,x in enumerate(e) if x[:2]==['capture_attempt367','915'])
  return e[:at+1]
 assert prefix(failed_prefix)==prefix(drained),'Diagnostic changed the strict failure prefix'
 for x,y in zip(candidate['rows'][2:],control['rows'][2:]):
  assert x['frame']==y['frame'];same=(x['start_ps'],x['start_ROM_cycle'])==(y['start_ps'],y['start_ROM_cycle'])
  if x['frame']<=909:assert same
  pairs.append(dict(frame=x['frame'],before_ms=y['processing_ms'],after_ms=x['processing_ms'],delta_ms=x['processing_ms']-y['processing_ms'],same_start_ROM_phase=same))
 assert load_image(d/'output.elf')==load_image(root/'build02/output.elf')
 assert load_image(d/'pre370-output.elf')==load_image(old/'output.elf')
 assert objects(d/'output.elf')==objects(old/'output.elf')
 sources=js(d/'manifest367.json')['sources'];shared={}
 for n in sources:
  read(d/n);read(old/n);assert sha(d/n)==sha(old/n);shared[n]=sha(d/n)
 assert js(d/'manifest368.json')['shared_boundary']==js(old/'manifest368.json')['shared_boundary']
 from nes_source368 import FILES
 for f in old.iterdir():
  if f.is_file() and (f.name in set(FILES)|{'nes_input286.inc','nes_decode280.c'} or f.suffix=='.h') and f.name!='nes_planner211.c':
   assert sha(f)==sha(d/f.name),(f.name,'unexpected ARM change')
 expected=read(old/'nes_planner211.c')
 for before,after in [('static inline __attribute__((always_inline)) bool patched(',HELPER+'static inline __attribute__((always_inline)) bool patched('),
  ('  bool shaped286=false;','  uint16_t checked370[2]={65535,65535};\n  bool shaped286=false;'),
  ('if(!tile(s,cell&8191,1))','if(!bg_tile370(s,cell&8191,checked370))'),
  ('if(!tile(s,e>>19,1))','if(!bg_tile370(s,e>>19,checked370))')]:expected=once(expected,before,after)
 assert expected==read(d/'nes_planner211.c')
 check=js(root/'check02.json');guards=js(root/'guards03.json');profile=js(root/'profile01.json');ports=js(root/'ports02.json')
 assert all(x['passed'] for x in (check,guards,profile,ports)) and len(guards['rows'])==45
 assert len(check['rows'])==41 and len(check['direct_cases'])==320 and len(check['STOP_cases'])==5
 assert check['total_saved']==168273 and profile['total']['before']['instructions']-profile['total']['after']['instructions']==55253
 assert profile['total']['before']['BG']==792 and profile['total']['after']['BG']==189
 assert profile['total']['before']['OBJ']==profile['total']['after']['OBJ']==8
 for evidence in (check,guards,profile):assert sha(root/'build02/output.elf') in evidence['pins'].values()
 assert guards['pins'][str(ROOT/'tools/check_nes_lookup370.py')]==sha(ROOT/'tools/check_nes_lookup370.py')
 assert ports['deletion_credit_comb']==0 and ports['replacement_control_ceiling']==1003
 input_audit=js(root/'input03.json');assert input_audit['passed'] and input_audit['hint_replay_instructions']==8917
 assert input_audit['retrospective_BG']['missing_from_initial_hint']==[6136,6554,6555]
 size=dict(before=prior.size(d/'pre370-output.elf'),after=prior.size(d/'output.elf'))
 size['delta']={k:size['after'][k]-size['before'][k] for k in size['before']};assert size['delta']==dict(text=48,data=0,BSS=0)
 early=js(root/'check01.json');assert early['passed'] and early['total_saved']==120472
 whole=prior.whole(BASE/'probes/nes-source368/map01');previous=js(ROOT/'analysis/schedule369-verification.json')
 assert whole==previous['whole_MAP']['values']
 for n in ('nes_lookup370.py','probe_nes_lookup370.py','check_nes_lookup370.py','profile_nes_lookup370.py','audit_nes_ports370.py','analyze_nes_lookup370.py'):read(ROOT/'tools'/n)
 warm=candidate['rows'][2:];worst=max(warm,key=lambda x:x['processing_ms'])
 result=dict(stage=370,analysis_passed=True,continuous_capture_passed=candidate['continuous_capture_passed'],candidate=candidate,control=control,paired=pairs,
  strict_first_missed_capture=915,strict_and_diagnostic_prefix_exact=True,planned_905_to915_completed=False,
  bounded_warm_60Hz_budget_passed=all(x['processing_ms']<=1000/60 for x in warm),worst_warm_frame=worst['frame'],worst_warm_ms=worst['processing_ms'],warm_budget_margin_ms=1000/60-worst['processing_ms'],
  check=check,guards=guards,profile=profile,nonselected_early_exit=dict(new_timing=False,extra_saved_instructions=early['total_saved']-113020,selected=False),
  ARM_size=size,unchanged_functional_RTL=shared,whole_MAP=dict(values=whole,inherited_from368=True,new_MAP=False,delta=dict(LE=0,comb=0,FF=0,RAM_bits=0)),
  ports=ports,input_audit=input_audit,comb_deficit=2290,deletion_needed_with155reserve=2445,FIT=False,STA=False,physical=False,sustained60fps=False,
  scope='Actual M4/SPI/IRQ/2slot and input/output ROM stress at one fixed start phase. CPI/exception adapters;ordinary65816 trace and DMA/final display bus model. Not full firmware WCET/65816/VBlank/heavy7/71/multiple phases/FIT/STA/physical60fps.',pins=prior.PINS)
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(paired=pairs,worst_warm=worst,margin_ms=result['warm_budget_margin_ms'],captures=candidate['captures'],ARM_size=size),indent=2))
if __name__=='__main__':main()
