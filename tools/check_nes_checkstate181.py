# SPDX-License-Identifier: MIT
"""Check same-edge CHECK state evidence and routed whole-board constraints."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from check_nes_boundary165 import measurements
from nes_checkstate181 import transform

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','fit','route','test','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();d=a.route
 load=lambda p:json.loads(p.read_bytes())
 rows=lambda p:list(csv.DictReader(p.open(),delimiter='\t'))
 m=load(d/'preparation.json');assert m==load(a.fit/'preparation.json')
 assert m['changed']==['nes_rom_spi.sv'] and len(m['sources'])==69
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.fit/n)==h,n
  assert sha(a.baseline/n)==m['baseline_checkstate_sources'][n],n
  if n!='nes_rom_spi.sv':assert sha(a.baseline/n)==h,n
 assert (d/'nes_rom_spi.sv').read_text()==transform((a.baseline/'nes_rom_spi.sv').read_text())
 original=load(d/'original-fit-manifest.json')
 for n,h in original.items():assert sha(a.fit/n)==h,n
 t=load(a.test/'result.json');assert t['passed'] and t['same_edge'] and t['edges']==1056768
 assert t['source_sha256']==m['sources']['nes_rom_spi.sv']
 assert t['reference_sha256']==sha(a.baseline/'nes_rom_spi.sv')
 for n,h in t['sources'].items():assert sha(a.test/n)==h,n
 for n,h in t['public_sources'].items():assert sha(ROOT/n)==h,n
 assert m['checkstate_generator_sha256']==sha(ROOT/'tools/nes_checkstate181.py')
 for n in ['map','fit']:assert int((a.fit/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0
 for n in ['timing','check-cdc181','io','oamread181-paths','check-reply181','critical']:
  assert int((d/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0,n
 f=(a.fit/'output_files/board.fit.rpt').read_text(encoding='latin1')
 count=lambda s:int(re.search(r'; '+re.escape(s)+r'\s*; ([\d,]+) /',f)[1].replace(',',''))
 worst=lambda xs:min(xs,key=lambda x:float(x['slack']))
 timing={}
 for view in ['nominal','implementation']:
  xs=rows(d/(view+'-clocks181.tsv'));assert len({x['corner'] for x in xs})==3
  setup=[x for x in xs if x['kind']=='setup']
  timing[view]=dict(rows=len(xs),worst_setup=worst(setup),worst_hold=worst([x for x in xs if x['kind']=='hold']),
   worst_related=worst([x for x in setup if x['from_clock']!=x['to_clock']]),
   scope='Same-clock / related PLL; asynchronous NES/PLL and reset remain separate.')
 ox=rows(d/'oamread181-paths.tsv');assert len({x['corner'] for x in ox})==3
 og={g:{k:worst([x for x in ox if x['group']==g and x['kind']==k]) for k in ['setup','hold']} for g in ['to_ram','from_ram','all_oam']}
 cdc=load(d/'cdc-routed01.json');reply=load(d/'reply-routed01.json')
 assert cdc['passed'] and cdc['routed_approval'] and reply['physical_pass']
 io=measurements(d)
 eligible=all(float(timing['nominal'][k]['slack'])>=0 for k in ['worst_setup','worst_hold']) and all(float(x['slack'])>=0 for z in og.values() for x in z.values()) and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 result=dict(evidence_verified=True,fit=dict(passed=True,le=count('Total logic elements'),labs=count('Total LABs:  partially or completely used'),m9k=count('M9Ks')),
  sources=m['sources'],functional=t,timing=timing,oam_timing=og,oam_timing_rows=len(ox),cdc=cdc,reply=reply,conditional_io=io,
  original_fit_files_preserved=len(original),nominal_candidate_eligible=eligible,
  full_design_timing_approval=False,adopted=False,new_package=False,physical=False,fps60=False,checker_sha256=sha(Path(__file__)))
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(fit=result['fit'],nominal=timing['nominal']['worst_setup'],strict=timing['implementation']['worst_setup']['slack'],
  hold=timing['nominal']['worst_hold']['slack'],related=timing['nominal']['worst_related']['slack'],eligible=eligible,
  oam_paths=len(ox),conditional_io=io['conditional_data_bounds_pass'],native_reset=io['native_payload_reset_pass'])))
if __name__=='__main__':main()
