# SPDX-License-Identifier: MIT
"""Whole402 costs and non-overlapping hierarchy closures, including rejected host."""
import argparse,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def measure(d):
 text=(d/'output_files/board.map.rpt').read_text();summary=(d/'output_files/board.map.summary').read_text();rows=[]
 for line in text.splitlines():
  c=[x.strip()for x in line.split(';')]
  if len(c)>11 and re.fullmatch(r'\d+ \(\d+\)',c[2]):
   co=list(map(int,re.findall(r'\d+',c[2])));ff=list(map(int,re.findall(r'\d+',c[3])));rows.append(dict(node=c[1],path=c[10],comb=co[1],FF=ff[1],inclusive_comb=co[0],inclusive_FF=ff[0],RAM_bits=int(c[4])))
 def metric(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary)[1].replace(',',''))
 whole=dict(LE=metric('Total logic elements'),comb=metric('Total combinational functions'),FF=metric('Dedicated logic registers'),RAM_bits=metric('Total memory bits'))
 assert sum(r['comb']for r in rows)==whole['comb']and sum(r['FF']for r in rows)==whole['FF']
 def closure(name):
  candidates=[r for r in rows if r['node']=='|'+name+'|'];assert len(candidates)==1,name;p=candidates[0]['path']
  return{r['path']for r in rows if r['path']==p or r['path'].startswith(p+'|')}
 def total(paths):
  a=[r for r in rows if r['path']in paths];return dict(comb=sum(r['comb']for r in a),FF=sum(r['FF']for r in a),nodes=a)
 controls=set()
 for name in('nes_output260:flow','nes_transport257:transport','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_spi270:spi_front270','nes_hint361:hint'):controls|=closure(name)
 controls-=closure('nes_stage396:aperture')
 stage=total(closure('nes_stage396:aperture'));capture=total(closure('nes_native_capture365:native_frame'));cache=total(closure('nes_chr_cache192:cache_path.cache'))
 R2={k:sum(v[k]for v in(stage,capture,cache))for k in('comb','FF')}
 return dict(whole=whole,control=total(controls),capture=capture,cache=cache,stage=stage,R2=R2,R2_cap401=dict(comb=1400,FF=992),R2_over401={k:R2[k]-v for k,v in dict(comb=1400,FF=992).items()},flow=total(closure('nes_output260:flow')),goals=dict(LE_short=whole['LE']-15408,comb_with155reserve_short=whole['comb']-15253,control_over1172=total(controls)['comb']-1172),pins=dict(report=sha(d/'output_files/board.map.rpt'),summary=sha(d/'output_files/board.map.summary')))

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'analysis/joint402-cost.json');a=p.parse_args()
 def evidence(run):
  archived=BASE/'probes/nes-joint402'/run
  return archived if(archived/'archive402.json').exists()else Path('C:/Users/mohallo/AppData/Local/Temp')/('nes-joint402-'+run)
 r={n:measure(d)for n,d in(('baseline400',BASE/'probes/nes-joint400/map01'),('joint402',evidence('map04')),('RAM_only402',evidence('map05')),('funded402',evidence('map07')))}
 r['scope']='Actual whole Lite MAP; both402 variants still fail capacity. New source/plan/SPI body deletion is incomplete.'
 terms=dict(program_padding=-2048*18,previous=33*15,rank=8*61,shared_cache_delta=144*18-128*8)
 assert sum(terms.values())==r['funded402']['whole']['RAM_bits']-r['baseline400']['whole']['RAM_bits']
 r['RAM_funding402']=dict(logical_bit_delta_terms=terms,total_bit_delta=sum(terms.values()),nominal_program_blocks_freed=4,nominal_capture_blocks_added=3,cache_uses_existing_one_block=True,Fitter_proven=False)
 a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps({n:{k:v[k]for k in('whole','goals')}for n,v in r.items()if isinstance(v,dict)and'whole'in v},indent=2))
if __name__=='__main__':main()
