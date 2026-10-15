# SPDX-License-Identifier: MIT
"""Separate OAM functional/resource evidence from whole-board approval."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import sha
from check_nes_boundary165 import measurements

def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','test','core','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.prepared;assert not a.out.exists()
 load=lambda p:json.loads(p.read_bytes())
 rows=lambda p:list(csv.DictReader(p.open(),delimiter='\t'))
 m=load(d/'preparation.json');t=load(a.test/'result.json');c=load(a.core/'result.json')
 assert m['storage']=='owned' and m['changed']==['rtl/ppu.sv'] and len(m['sources'])==69
 for n,h in m['sources'].items():assert sha(d/n)==h,n
 assert t['passed'] and c['passed'] and t['source_sha256']==c['source_sha256']==m['sources']['rtl/ppu.sv']
 assert c['results']['baseline']==c['results']['candidate'] and c['independent_bytes']==4096
 assert t['results']['wrong-positive-read']=='expected mismatch'
 for n in ['map','fit','timing','cdc-verify','reply-verify','io','oamread181-paths']:
  assert int((d/(n+'.exitcode')).read_text(encoding='utf-8-sig'))==0,n
 f=(d/'output_files/board.fit.rpt').read_text(encoding='latin1')
 count=lambda s:int(re.search(r'; '+re.escape(s)+r'\s*; ([\d,]+) /',f)[1].replace(',',''))
 timing={}
 for view in ['nominal','implementation']:
  xs=rows(d/(view+'-clocks181.tsv'))
  assert len({x['corner'] for x in xs})==3
  worst=lambda v:min(v,key=lambda x:float(x['slack']))
  setup=[x for x in xs if x['kind']=='setup']
  timing[view]=dict(rows=len(xs),worst_setup=worst(setup),worst_hold=worst([x for x in xs if x['kind']=='hold']),
   worst_related_pll=worst([x for x in setup if x['from_clock']!=x['to_clock']]),
   scope='Same-clock and related PLL pairs only. NES/PLL CDC and reset checks are separate; NOT all design paths.')
 ox=rows(d/'oamread181-paths.tsv');og={}
 assert len({x['corner'] for x in ox})==3
 for group in ['to_ram','from_ram','all_oam']:
  og[group]={}
  for kind in ['setup','hold']:
   z=[x for x in ox if x['group']==group and x['kind']==kind];assert z
   assert all(float(x['slack'])>=0 for x in z)
   og[group][kind]=min(z,key=lambda x:float(x['slack']))
 assert any(x['kind']=='setup' and abs(float(x['relationship'])-22.727)<.002 for x in ox)
 cdc=load(d/'cdc-routed01.json');reply=load(d/'reply-routed01.json')
 assert cdc['routed_approval'] and cdc['passed'] and reply['physical_pass']
 io=measurements(d)
 result=dict(evidence_verified=True,selected=['map03','test04','core01'],sources=m['sources'],
  fit=dict(passed=True,le=count('Total logic elements'),labs=count('Total LABs:  partially or completely used'),m9k=count('M9Ks')),
  functional=t,core_dma=c,timing=timing,oam_timing=og,oam_timing_rows=len(ox),cdc=cdc,reply=reply,conditional_io=io,
  rendering_core_test=False,ram_primitive_simulation=False,full_design_timing_approval=False,
  future_savestate_physical_resource_approval=False,adopted=False,new_package=False,physical=False,fps60=False,
  sources_note='Generic extra/read/savestate semantics tested under half-cycle stable-input contract; unused ports prune in current board.',
  checker_sha256=sha(Path(__file__)))
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(fit=result['fit'],oam_paths=len(ox),io_pass=io['conditional_data_bounds_pass'],
  native_reset_pass=io['native_payload_reset_pass'],psram=io['psram_conditional_margin_ns'],snes=io['snes_read_envelope_ns'],spi=io['spi_reply_envelope_ns'],
  nominal=timing['nominal']['worst_setup']['slack'],strict=timing['implementation']['worst_setup']['slack'],adopted=False)))
if __name__=='__main__':main()
