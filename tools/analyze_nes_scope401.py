# SPDX-License-Identifier: MIT
"""401 deletion boundary from whole400 Quartus Lite hierarchy.

Frozen-packing arithmetic is a necessary scope check, not a replacement MAP
or a proof that resynthesis/repacking cannot change the result.
"""
import argparse,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def ledger(d):
 rows=[]
 for line in(d/'output_files/board.map.rpt').read_text().splitlines():
  c=[x.strip()for x in line.split(';')]
  if len(c)>11 and re.fullmatch(r'\d+ \(\d+\)',c[2]):
   co=list(map(int,re.findall(r'\d+',c[2])));ff=list(map(int,re.findall(r'\d+',c[3])))
   rows.append(dict(node=c[1],path=c[10],comb=co[1],FF=ff[1],inclusive_comb=co[0],inclusive_FF=ff[0],inclusive_RAM=int(c[4])))
 assert sum(r['comb']for r in rows)==17376 and sum(r['FF']for r in rows)==8903
 def node(name):
  a=[r for r in rows if r['node']=='|'+name+'|'];assert len(a)==1,name;return a[0]
 def closure(name):
  p=node(name)['path'];return {r['path']for r in rows if r['path']==p or r['path'].startswith(p+'|')}
 def total(paths):
  chosen=[r for r in rows if r['path']in paths];return dict(comb=sum(r['comb']for r in chosen),FF=sum(r['FF']for r in chosen),nodes=chosen)
 host=closure('nes_output260:flow');source=closure('nes_transport257:transport');plan=closure('nes_plan_batch206:transport');endpoint=closure('nes_plan_spi200:endpoint');spi=closure('nes_spi270:spi_front270');hint=closure('nes_hint361:hint')
 stage=closure('nes_stage396:aperture');keep=closure('nes_read_owner400:read_owner')|closure('nes_tile_link394:tile_link')|hint
 control=host|source|plan|endpoint|spi|hint
 named=control-stage-keep
 capture=closure('nes_native_capture365:native_frame');cache=closure('nes_chr_cache192:cache_path.cache')
 scopes={};previous=set()
 for key,pool in(('named_control_IO_source_plan_SPI',named),('plus_staging',named|stage),('plus_capture_storage_and_CHR_metadata',named|stage|capture|cache)):
  assert not pool&keep
  t=total(pool);maximum=t['comb']+t['FF'];floor=22114-maximum
  scopes[key]=dict(**t,maximum_deleted_LUT_plus_FF=maximum,frozen_packing_remaining_LE_at_least=floor,optimistic_raw_LE_allowance_for_replacement=15408-floor,optimistic_comb_allowance_with155reserve=15253-(17376-t['comb']),not_actual_new_MAP=True,not_global_impossibility=True)
  assert previous<=pool;previous=pool
 ctrl=total(control-stage);kept=total(keep)
 caps=dict(host_record_executor=dict(comb=256,FF=160),SPI_frame_snapshot=dict(comb=224,FF=96),NES_source_plan=dict(comb=192,FF=128),queue_credit=dict(comb=131,FF=96),staging=dict(comb=200,FF=160),capture_raster=dict(comb=900,FF=704),CHR_metadata=dict(comb=300,FF=128))
 assert sum(caps[n]['comb']for n in list(caps)[:4])==803
 target={k:sum(v[k]for v in caps.values())for k in('comb','FF')}
 return dict(scope=__doc__,whole=dict(LE=22114,comb=17376,FF=8903,RAM_bits=382304),baseline400_self_control=dict(comb=3465,FF=1669,cap=1172,over=2293),control_closure=ctrl,kept_read_hint_mailbox=kept,remaining_control_cap=1172-kept['comb'],closure_control_over_1172=ctrl['comb']-1172,scopes=scopes,replacement_design_caps=dict(blocks=caps,total=target,maximum_new_C_plus_FF=target['comb']+target['FF'],measured=False,area_prediction=False,whole_acceptance=dict(LE_max=15408,comb_max=15253,control_closure_max=1172),conditional_optimistic_LE_allowance_only=4023),RAM_candidate=dict(deleted_program_bits=73728,new_bytes=dict(host_record=256,SPI_snapshot_two64B=128,NES_two_port_context=256,capture_previous_rank=256,CHR_metadata=128,independent_expected=512),logical_bits_if_replaced=382304-73728+(256+128+256+256+128+512)*8,nominal_512x18_ROM_blocks=8,logical_RAM_regions=6,nominal_M9K_budget=8,capture_previous_rank_M9K_budget=3,palette_FF_retained=384,physical_fit_proven=False),independent_encoder_checker_retained=total({node('nes_core257:encoder')['path'],node('nes_validator278:validator')['path']}),new_RTL=False,new_MAP=False,FIT=False,STA=False,pins={'whole_map':sha(d/'output_files/board.map.rpt'),'whole_result':sha(d/'result.json')})

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'analysis/scope401-budget.json');a=p.parse_args();r=ledger(BASE/'probes/nes-joint400/map01');a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps({k:r[k]for k in('remaining_control_cap','closure_control_over_1172','RAM_candidate')}));print(json.dumps({k:{n:v[n]for n in('comb','FF','frozen_packing_remaining_LE_at_least','optimistic_raw_LE_allowance_for_replacement')}for k,v in r['scopes'].items()}))
if __name__=='__main__':main()
