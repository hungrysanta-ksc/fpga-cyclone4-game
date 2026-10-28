# SPDX-License-Identifier: MIT
"""403 replacement scope/budget and fixed-supply deadlines, not new RTL gains."""
import argparse,collections,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from cost_nes_joint402 import measure

def budget():
 d=BASE/'probes/nes-joint402/map07';m=measure(d);rows=[]
 for line in(d/'output_files/board.map.rpt').read_text().splitlines():
  c=[x.strip()for x in line.split(';')]
  if len(c)>11 and re.fullmatch(r'\d+ \(\d+\)',c[2]):
   rows.append(dict(node=c[1],path=c[10],comb=int(re.findall(r'\d+',c[2])[1]),FF=int(re.findall(r'\d+',c[3])[1])))
 assert sum(x['comb']for x in rows)==16508 and sum(x['FF']for x in rows)==7917
 def closure(name):
  a=[x for x in rows if x['node']=='|'+name+'|'];assert len(a)==1,name;p=a[0]['path'];return{x['path']for x in rows if x['path']==p or x['path'].startswith(p+'|')}
 def total(s):return{k:sum(x[k]for x in rows if x['path']in s)for k in('comb','FF')}
 host=closure('nes_output260:flow');stage=closure('nes_stage396:aperture');capture=closure('nes_native_capture365:native_frame');raster=closure('nes_native_raster181:raster')
 lease={x['path']for x in rows if x['node']=='|nes_native_capture365:native_frame|'}
 keep=closure('nes_read_owner400:read_owner')|closure('nes_tile_link394:tile_link')|closure('nes_hint361:hint')
 ctl=host|closure('nes_transport257:transport')|closure('nes_plan_batch206:transport')|closure('nes_plan_spi200:endpoint')|closure('nes_spi270:spi_front270')|closure('nes_hint361:hint')
 named=ctl-stage-keep;assert not named&keep
 common=dict(host_record=dict(comb=256,FF=160),SPI_snapshot=dict(comb=224,FF=96),NES_source_plan=dict(comb=192,FF=128),queue_credit=dict(comb=130,FF=96))
 stages=dict(staging=dict(comb=192,FF=128));narrow=dict(common,**stages,lease=dict(comb=144,FF=128),raster=dict(comb=400,FF=38))
 expanded=dict(common,**stages,NES_capture_raster_lease_fetch=dict(comb=1100,FF=512))
 whole=m['whole'];pairs=whole['comb']+whole['FF']-whole['LE'];scopes={}
 for name,pool,palette,caps in(('control_only',named,0,common),('control_staging_raster_lease',named|stage|raster|lease,384,narrow),('plus_compact_fetch_patch_frame',named|stage|capture,384,expanded)):
  old=total(pool);reclaim=dict(comb=old['comb'],FF=old['FF']-palette);new={k:sum(v[k]for v in caps.values())for k in('comb','FF')}
  projected={k:whole[k]-reclaim[k]+new[k]for k in('comb','FF')};needed_pairs=max(0,sum(projected.values())-15408)
  scopes[name]=dict(old_cells=old,retained_palette_FF=palette,replacement_boundary=reclaim,new_design_caps=caps,new_caps_total=new,caps_are_measured=False,comb_FF_if_caps_realized=projected,paired_LEs_needed_if_caps_realized=needed_pairs,change_vs_current_paired_LEs=needed_pairs-pairs,whole_LE_prediction=None,whole_fit_proven=False,maximum_removed_C_plus_FF=sum(reclaim.values()),row_paths=sorted(pool),conditional_only=True)
 return dict(whole=whole,current_paired_LEs=pairs,kept_read_hint_tile=total(keep),new_control_comb_cap_for1172=1172-total(keep)['comb'],scopes=scopes,cache402_preserved=m['cache'],independent_checker_retained=True,FIT=False,STA=False)

def schedule():
 d=BASE/'probes/nes-joint402/live04';e=list(csv.reader((d/'joint-events.csv').read_text().splitlines()));audit=json.loads((ROOT/'analysis/joint402-verification.json').read_text());arm=json.loads((d/'arm-result.json').read_text());out=[]
 for f in(914,915):
  a=[x for x in e if len(x)>1 and x[1]==str(f)];single=lambda n:next(x for x in a if x[0]==n)
  end=lambda n:int(single(n)[-1])/1e9
  wires=[x for x in a if x[0]=='arm267'];last_wire={str(k):max(int(x[4])/1e9 for x in wires if int(x[2])==k)for k in(0xe1,0xe9)if any(int(x[2])==k for x in wires)}
  tile=[int(x[-1])/1e9 for x in a if x[0]=='tile_last334'];stored=[x for x in a if x[0]=='stored394'];g=next(v for v in audit['variants']['funded_RAM']['local_display_windows']if v['frame']==f)
  barrier=max(max(tile),*last_wire.values());view=end('view_end401')-end('view_start401');supply_deficit=max(0,barrier-g['latest_gate_ms'])
  stats=next(x for x in arm['frames']if x['frame']==f)
  out.append(dict(frame=f,start_ms=int(single('start319')[2])/1e9,materialized_ms=end('materialized366'),input_done_ms=end('input_done337'),first_plan_ms=min(int(x[-1])/1e9 for x in a if x[0]=='plan293'),last_tile_ms=max(tile),last_ARM_wire_end=last_wire,unavoidable_supply_barrier_if_realized_schedule_frozen_ms=barrier,supply_advance_needed_even_zero_executor_ms=supply_deficit,first_stored_ms=int(stored[0][-1])/1e9,last_stored_ms=int(stored[-1][-1])/1e9,jobs=len(stored),actual_DMA_read_bytes=sum(int(x[3])for x in stored),view_ms=view,gate=g,ARM={k:stats[k]for k in('instructions','SPI_bytes','source_instructions367','packets','prefetch_completions400')},ROM_plan_stats=single('rom267')[2:],not_a_global_impossibility=True,feedback_can_move_producer_schedule=True))
  gate_event=single('display_gate401');target=f-891;cut,tail=map(int,gate_event[3:5]);latest=(target*357368+min((cut+1)*1364-1,357368-tail))*46561/1e9
  out[-1]['ideal_unskipped_sequence']=dict(target_VBlank=target,latest_gate_ms=latest,advance_of_current_gate_ms=g['gate_ms']-latest,advance_of_current_supply_ms=max(0,barrier-latest),includes_prior_missed_VBlank_wait=True,not_an_independent_new_work_cost=True)
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'analysis/scope403-budget.json');a=p.parse_args();r=budget();r.update(scope=__doc__,baseline402_schedule=schedule(),new_RTL=False,new_whole_MAP=False,new_ARM=False,new_time_gain_ms=None)
 r['RAM_plan']=dict(host_control_existing_region=[800,1023],host_layout=[dict(name=n,first=s,last=t)for n,s,t in(('active17B_DMA_header_and_work',800,831),('old_display_context',832,863),('next_input_context',864,895),('progress_and_staging',896,927),('unchanged_hint_tags',928,941),('SPI_snapshot_A',942,973),('SPI_snapshot_B',974,1005),('reserve',1006,1023))],NES_row_tail_words=[224,255],NES_row_width=56,new_tail_bits=32*56,old_program_removed_bits=2048*18,new_microcontrol_capacity_bits=256*32,new_bits_if_plan_realized=347991-2048*18+32*56+256*32,nominal_row_SDP_blocks=2,nominal_row_TDP_blocks=4,nominal_old_program_blocks=4,nominal_new_microcontrol_blocks=1,Fitter_proven=False,not_a_permanent_program_cap=True)
 r['pins']={str(q.relative_to(BASE)).replace('\\','/'):sha(q)for q in(ROOT/'analysis/joint402-verification.json',ROOT/'analysis/joint402-cost.json',BASE/'probes/nes-joint402/map07/output_files/board.map.rpt',BASE/'probes/nes-joint402/map07/result.json',BASE/'probes/nes-joint402/live04/joint-events.csv',BASE/'probes/nes-joint402/live04/arm-result.json')}
 a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps(dict(kept=r['kept_read_hint_tile'],control_cap=r['new_control_comb_cap_for1172'],scopes={n:{k:v[k]for k in('replacement_boundary','new_caps_total','comb_FF_if_caps_realized','paired_LEs_needed_if_caps_realized','change_vs_current_paired_LEs')}for n,v in r['scopes'].items()},schedule=r['baseline402_schedule']),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
