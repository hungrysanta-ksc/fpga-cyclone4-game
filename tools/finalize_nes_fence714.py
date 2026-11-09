"""Publish measured714 gate and resource ledger without selecting a regression."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_output615 import csv_groups,one,ms

def run(a):
 r=json.loads((a.probe/'schedule02.json').read_text());phases={}
 for phase,v in r['phases'].items():
  b,c=v['base'],v['candidate'];details={}
  for g in map(str,range(951,958)):
   details[g]={}
   for label,row in [('base',b),('candidate',c)]:
    d=row['details'][g]
    keys=('relative_ms','early_DMA','BG_ROM_reads','last_BG_call_vs_previous_window_ms','last_BG_E9_vs_previous_window_ms','quiet_calls','quiet_inclusive_ms','BG_producer_terms_ms')
    details[g][label]={k:d[k] for k in keys}
    details[g][label]['map_runs']=[{k:x[k] for k in ('offset','bytes','first_load','last_load')} for x in d['map_runs']]
    if d['fences']:
     f=d['fences'][0]
     details[g][label]['fence_ms']=ms(f['clock']-f['start'])
     details[g][label]['last_BG_return_to_fence_ms']=ms(f['start']-d['BG_plans'][-1]['returned']) if d['BG_plans'] else None
  base=csv_groups(a.temp/f'nes-bg707-step{phase}/window.csv');new=csv_groups(a.temp/f'nes-fence714-a{phase}/window.csv')
  def reveal(rows,g):return one([x for x in rows[g] if x['op']==3],'reveal')
  changed=[]
  for g in range(906,958):
   old_v=reveal(base,g)['frame']-reveal(base,g-1)['frame'];new_v=reveal(new,g)['frame']-reveal(new,g-1)['frame']
   if old_v!=new_v:changed.append(dict(generation=g,base=old_v,candidate=new_v))
  phases[phase]=dict(gate=v['gate'],same_map_OBJ_plans_pixels=v['same_map_OBJ_plans_pixels'],protected=c['protected'],delta=v['delta'],
   baseline_dense_ms=b['dense_ms'],dense_ms=c['dense_ms'],last_ACK=c['last_ACK'],baseline_last_ACK=b['last_ACK'],
   after951_VBlank=c['after951_VBlank'],after951_mean_ms=c['after951_mean_ms'],intervals=c['intervals'],
   cold905_reveal_delta_ms=ms(reveal(new,905)['clock']-reveal(base,905)['clock']),all_changed_VBlank_intervals=changed,
   wire_delta_B={k:c['wire_B'][k]-x for k,x in b['wire_B'].items()},ARM_instruction_delta=c['ARM_instructions']-b['ARM_instructions'],
   observed_stack_low=c['stack_low'],baseline_stack_low=b['stack_low'],
   observed_extra_stack_B=int(b['stack_low'],16)-int(c['stack_low'],16),deadline911=c['deadline911'],
   details=details,pins=c['pins'])
 guards={}
 for key,p in [('fence',a.probe/'guards04.json'),('runtime',a.probe/'runtime01.json'),('menu',a.probe/'menu02.json'),
               ('STOP',a.temp/'nes-fence714-stop01/result.json'),('exit',a.temp/'nes-fence714-exit01/result.json')]:
  guards[key]=dict(SHA256=sha(p),result=json.loads(p.read_text()))
 out=dict(stage=714,selected='707D + original694/704 ARM + original694 65816',performance_candidate_selected=r['selected'],
  resources=r['resources'],phases=phases,guards=guards,source_files=r['source_files'],
  scope=r['limitations'],full_schedule_SHA256=sha(a.probe/'schedule02.json'),
  new_FIT_STA=False,new_installer=False,board_evidence='analysis/bg707-verification.json',
  next_budget=dict(replacement_cap_B=1116,actual_boundary_B=962,additional_boundary_cap_B=154,
   normal_whole_Flash_free_B=244,static_RAM_growth_B=0,observed_stack_growth_max_B=100,
   proven_product_saving_B=0,FPGA_growth_LE=0,SNES_ROM_growth_B=0,
   decision='Reject global all-BG fence. Required BG discovery/slot assignment must be separated from remaining map-row materialization; map transmission requires an actual dispatch point, not an idle-bus assumption. No new prepass/coroutine accepted without its full CPU/stack and independent row-ownership costs.'),
  source_tools={p.name:sha(p) for p in Path('tools').glob('*fence714*.py')})
 assert not out['performance_candidate_selected']
 a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n');print('714 complete: resource gain, no sustained timing gain, baseline retained')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
