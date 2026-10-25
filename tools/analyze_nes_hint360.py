# SPDX-License-Identifier: MIT
"""Audit actual M4 small hints, bounded cache timing and whole Lite cost."""
import argparse,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);d=ap.parse_args().root.resolve();pins={}
 def pin(p):
  p=p.resolve();pins[str(p)]=sha(p);return p
 def read(p):return pin(p).read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 def check(result):
  assert result['passed']
  for p,h in result.get('pins',{}).items():assert sha(pin(Path(p)))==h,p
 old=js(ROOT/'analysis/prefetch359-verification.json');assert old['analysis_passed']
 for p,h in old['pins'].items():assert sha(pin(Path(p)))==h,p
 obs=js(d/'window01/result.json');assert obs['passed']
 ref=BASE/'probes/nes-prefetch359/window02'
 assert read(d/'window01/joint-events.csv')==read(ref/'joint-events.csv')
 assert load_image(pin(d/'window01/output.elf'))==load_image(pin(ref/'output.elf'))
 for n,h in obs['rtl_hashes'].items():assert sha(pin(d/'window01'/n))==h==sha(pin(ref/n))
 arms={};caches={}
 for name,batch,expected in [('arm02',2,4295),('arm03',5,3631)]:
  r=js(d/name/'result.json');check(r);assert len(r['rows'])==3 and len(r['guards'])==4
  assert all(x['source_decode_delta']==0 for x in r['rows'])
  assert not r['rows'][0]['packets'] and not r['rows'][1]['packets']
  w=r['rows'][2];tags=[t for p in w['packets'] for t in p['tags']]
  assert tags==[6525,6424,6426,6425,6427]
  instructions=w['reset_instructions']+sum(x['instructions'] for x in w['calls']);assert instructions==expected
  arms[name]=dict(batch=batch,instructions=instructions,CPI1_ms=instructions/84000,SPI_bytes=sum(p['bytes'] for p in w['packets']),packets=len(w['packets']),size=r['size'],stack=r['stack_observed'],guards=r['guards'])
 for name in ('cache02','cache03'):
  r=js(d/name/'result.json');check(r);assert len(r['rows'])==3 and not r['integrated_EA']
  assert r['IRQ']['instructions']==66 and r['exception_entry_exit_cycle_allocation']==24
  assert all(x['ROM_bytes']==80 for x in r['rows'])
  assert read(d/name/'nes_chr_cache192.sv')==read(d/'map01/nes_chr_cache192.sv')
  for p in (d/name).glob('*.log'):read(p)
  caches[name]=r
 m=js(d/'map01/result.json');assert m['passed']
 for n,h in m['actual_inputs'].items():assert sha(pin(d/'map01'/n))==h
 s=read(d/'map01/output_files/board.map.summary');read(d/'map01/output_files/board.map.rpt')
 whole={k:int(re.search(p+r'\s*:\s*([0-9,]+)',s)[1].replace(',','')) for k,p in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
 assert whole==dict(LE=22234,comb=17364,FF=9005,RAM_bits=308832)
 target=15253;retained=10910+151;source_host_cap=target-retained-1245-650-458
 assert source_host_cap==1839 and whole['comb']-target==2111
 for p in ROOT.glob('tools/*360.py'):pin(p)
 result=dict(stage=360,analysis_passed=True,selected_RTL=338,selected_ARM=355,candidate_selected=False,ARM=arms,cache=caches,whole=whole,
  delta_vs359_host={k:whole[k]-old['host_whole'][k] for k in whole},comb_deficit=whole['comb']-15408,
  selected_gap_ms=old['selected_gap_ms'],selected_comb_deficit=1866,baseline_runs=old['runs'],observer_events_exact=True,
  budget=dict(target_comb=target,source_host_current=3805,source_host_cap=source_host_cap,source_host_required_deletion=1966,queue_SPI_current=795,queue_SPI_cap=650,checker_aperture=1245,plan=458,retained_plus_cache=retained,total_required_deletion=2111,estimated_achievement=False),
  continuous_window_upper_ms=1.727706540,grouped_CPI2_margin_ms=1.727706540-caches['cache03']['rows'][2]['fill_ns']/1e6,
  integrated_EA=False,new_source_host_replacement=False,FIT=False,STA=False,physical=False,
  scope='Actual M4 prior-history hint producer on 905..907; TB SPI feeds actual cache/arbiter/READ16. IRQ body measured, entry/exit allocated. EA admission/CRC/CDC/lease and shared-SPI whole-frame feedback absent. Whole MAP is normal-consumer cache capacity, not full hint integration. Previous independent host/ACK/VBlank evidence reused; no new complete VBlank or hardware WCET proof.',pins=pins)
 (ROOT/'analysis/hint360-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(pins=len(pins),whole=whole,ARM=arms,budget=result['budget']),indent=2))
if __name__=='__main__':main()
