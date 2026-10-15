# SPDX-License-Identifier: MIT
"""Verify wide OAM RAM evidence; do not equate fit or model tests with hardware."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from check_nes_boundary165 import measurements

def main():
 p=argparse.ArgumentParser()
 for n in ['fit','route','primitive','render','reference','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();d=a.route
 load=lambda p:json.loads(p.read_bytes());rows=lambda p:list(csv.DictReader(p.open(),delimiter='\t'))
 m=load(d/'preparation.json');assert m==load(a.fit/'preparation.json')
 assert m['oamports_mode']=='primitive' and m['changed']==['rtl/ppu.sv'] and len(m['sources'])==69
 for n,h in m['sources'].items():assert sha(d/n)==sha(a.fit/n)==h,n
 t=load(a.primitive/'result.json');r=load(a.render/'result.json');ref=load(a.reference/'result.json')
 assert t['passed'] and t['primitive_model'] and r['passed'] and ref['passed']
 assert r['baseline_reused_sha256']==sha(a.reference/'result.json')
 assert r['source_sha256']==t['source_sha256']==m['sources']['rtl/ppu.sv']
 assert r['results']['baseline']==r['results']['candidate']==ref['results']['baseline']
 assert r['results']['candidate']['counts']==[920545,180740,153,512,513]
 for n,h in r['results']['candidate']['files'].items():assert sha(a.render/'candidate'/n)==h
 assert t['altera_mf_sha256']==r['altera_mf_sha256']==sha(a.render/'candidate/altera_mf.v')
 assert t['wrapper_sha256']==sha(ROOT/'tools/test_nes_oamports181.py') and r['runner_sha256']==sha(ROOT/'tools/test_nes_oamrender181.py')
 assert m['oamports_generator_sha256']==sha(ROOT/'tools/nes_oamports181.py')
 for n in ['map','fit']:assert int((a.fit/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0
 for n in ['timing','check-cdc181','io','oamread181-paths','check-reply181']:
  assert int((d/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0,n
 f=(a.fit/'output_files/board.fit.rpt').read_text(encoding='latin1')
 count=lambda s:int(re.search(r'; '+re.escape(s)+r'\s*; ([\d,]+) /',f)[1].replace(',',''))
 timing={}
 for view in ['nominal','implementation']:
  xs=rows(d/(view+'-clocks181.tsv'));assert len({x['corner'] for x in xs})==3
  worst=lambda v:min(v,key=lambda x:float(x['slack']))
  setup=[x for x in xs if x['kind']=='setup']
  timing[view]=dict(rows=len(xs),worst_setup=worst(setup),worst_hold=worst([x for x in xs if x['kind']=='hold']),
   worst_related=worst([x for x in setup if x['from_clock']!=x['to_clock']]),
   scope='Same-clock / related PLL only; async NES/PLL reset/CDC kept separate.')
 ox=rows(d/'oamread181-paths.tsv');og={}
 for group in ['to_ram','from_ram','all_oam']:
  og[group]={}
  for kind in ['setup','hold']:
   z=[x for x in ox if x['group']==group and x['kind']==kind];assert z
   og[group][kind]=min(z,key=lambda x:float(x['slack']))
 assert len({x['corner'] for x in ox})==3
 cdc=load(d/'cdc-routed01.json');reply=load(d/'reply-routed01.json')
 assert cdc['passed'] and cdc['routed_approval'] and reply['physical_pass']
 io=measurements(d)
 # Count known/unknown pixels without hiding reference imperfections.
 pixels=[l.split() for l in (a.render/'candidate/ppu.tsv').read_text().splitlines()]
 colors={x[3] for x in pixels};unknown=sum('x' in x[3].lower() for x in pixels)
 result=dict(evidence_verified=True,fit=dict(passed=True,le=count('Total logic elements'),labs=count('Total LABs:  partially or completely used'),m9k=count('M9Ks')),
  sources=m['sources'],functional=t,rendering=r,reference_result_sha256=sha(a.reference/'result.json'),
  pixels=dict(samples=len(pixels),scanlines=len({x[1] for x in pixels}),known_colors=len(colors-{'xx'}),unknown_colors=unknown,
   note='Eight unknown color samples also exist in exact baseline; this is equality, not all-pixel correctness proof.'),
  timing=timing,oam_timing=og,oam_timing_rows=len(ox),cdc=cdc,reply=reply,conditional_io=io,
  primitive_behavioral_model=True,postfit_timing_simulation=False,full_design_timing_approval=False,
  adopted=False,new_package=False,physical=False,fps60=False,checker_sha256=sha(Path(__file__)))
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(fit=result['fit'],nominal=timing['nominal']['worst_setup']['slack'],strict=timing['implementation']['worst_setup']['slack'],
  hold=timing['nominal']['worst_hold']['slack'],oam_paths=len(ox),conditional_io=io['conditional_data_bounds_pass'],native_reset=io['native_payload_reset_pass'])))
if __name__=='__main__':main()
