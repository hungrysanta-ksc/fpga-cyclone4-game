# SPDX-License-Identifier: MIT
"""Count self cells once, including the new read owner, on the whole image."""
import argparse,json,re
from pathlib import Path
from nes_delta231 import sha

def measure(d):
 r=json.loads((d/'result.json').read_text());assert r['passed']and not r['undriven']and not r['FIT']and not r['STA']
 whole={k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',',''))for k,label in dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits').items()}
 cells={};decode=[]
 for line in(d/'output_files/board.map.rpt').read_text().splitlines():
  c=[x.strip()for x in line.split(';')]
  if len(c)>4 and re.fullmatch(r'\|[^|]+\|',c[1])and re.fullmatch(r'\d+ \(\d+\)',c[2]):
   cells[c[1].strip('|')]=int(re.search(r'\((\d+)\)',c[2])[1])
   if c[1]=='|altsyncram:program398_rtl_0|':decode.append(int(c[2].split()[0]))
 assert len(decode)==1
 keys={'host_and_core':['nes_output260:flow','nes_byte398:control','nes_read_owner400:read_owner'],
       'NES_source_plan_hint':['nes_transport257:transport','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_walk396:execution','nes_hint361:hint'],
       'SPI':['nes_spi270:spi_front270'],'queue':['nes_queue260:queue'],'tile':['nes_tile_link394:tile_link']}
 pool={k:sum(cells[n]for n in names)for k,names in keys.items()};pool['program_decode']=decode[0]
 retained=sum(cells[n]for n in('nes_core257:encoder','nes_validator278:validator'))
 control=sum(pool.values());outside=whole['comb']-control-retained
 assert control+retained+outside==whole['comb']
 return dict(whole=whole,pool=pool,control=control,cap=1172,over_1172=control-1172,retained=retained,outside=outside,raw_device_over=whole['comb']-15408,reserved155_over=whole['comb']-15253,MAP_LE_over=whole['LE']-15408,comb_budget_alone_does_not_prove_LE_fit=True,FIT=False,STA=False,source_sha256=sha(d/'output_files/board.map.rpt'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--map',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=measure(a.map);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
