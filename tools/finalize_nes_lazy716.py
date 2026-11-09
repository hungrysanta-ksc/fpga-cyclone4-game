"""Publish716 A/B evidence without turning local planner savings into FPS."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha

def run(a):
 variants={}
 for variant in ('a','b'):
  path=a.probe/f'schedule-{variant}01.json';r=json.loads(path.read_text());phases={}
  for phase,v in r['phases'].items():
   b,c=v['base'],v['candidate'];details={}
   for g in map(str,range(951,958)):
    details[g]={}
    for label,row in [('base',b),('candidate',c)]:
     d=row['details'][g];keys=('relative_ms','early_DMA','BG_ROM_reads','last_BG_call_vs_previous_window_ms','last_BG_E9_vs_previous_window_ms','BG_producer_terms_ms')
     details[g][label]={k:d[k] for k in keys}
    details[g]['slots']=v['slots'][g]
    details[g]['planner']={n:p[g] for n,p in v['planner'].items()}
   phases[phase]=dict(timing_gate=v['timing_gate'],same_map_OBJ_plans_pixels=v['same_map_OBJ_plans_pixels'],protected=c['protected'],delta=v['delta'],
    baseline_dense_ms=b['dense_ms'],dense_ms=c['dense_ms'],last_ACK=c['last_ACK'],baseline_last_ACK=b['last_ACK'],
    after951_VBlank=c['after951_VBlank'],after951_mean_ms=c['after951_mean_ms'],intervals=c['intervals'],
    cold905_reveal_delta_ms=v['cold905_reveal_delta_ms'],changed_intervals=v['changed_intervals'],
    SPI_delta_B=v['SPI_delta_B'],ARM_instruction_delta=v['ARM_instruction_delta'],
    observed_stack_low=c['stack_low'],baseline_stack_low=b['stack_low'],extra_observed_stack_B=v['extra_observed_stack_B'],
    deadline911=c['deadline911'],reveal951=c['details']['951']['marks']['reveal'],details=details,pins=c['pins'])
  suffix='' if variant=='a' else '-b';temp_suffix='' if variant=='a' else 'b'
  guards={}
  for name,p in [('slots',a.probe/f'guards-{variant}02.json'),
                 ('runtime',a.probe/f'runtime{suffix}01.json'),('menu',a.probe/f'menu{suffix}01.json'),
                 ('STOP',a.temp/f'nes-lazy716-stop{temp_suffix}01/result.json'),('exit',a.temp/f'nes-lazy716-exit{temp_suffix}01/result.json')]:
   guards[name]=dict(SHA256=sha(p),result=json.loads(p.read_text()))
  variants[variant]=dict(selected=r['selected'],resource_gate=r['resource_gate'],resources=r['resources'],phases=phases,guards=guards,scope=r['limitations'],source_files=r['source_files'],schedule_SHA256=sha(path))
 out=dict(stage=716,selected='707D + original694/704 ARM + original69465816',variants=variants,
  performance_candidate_selected=any(v['selected'] for v in variants.values()),new_static_RAM_B=0,new_SPI_opcode=False,
  extra_internal_call_argument_B=4,new_FIT_STA=False,new_installer=False,board_evidence='analysis/bg707-verification.json',
  next_budget=dict(selected_normal_Flash_free_B=8,map_dispatch_boundary_cap_B=1116,proven_product_saving_B=0,
   extra_static_RAM_cap_B=4,FPGA_growth_LE=0,SNES_ROM_growth_B=0,
   decision='Keep selected original image. Preserve unselected B kernel: measured planner saving about1ms and four non-dense VBlank reductions in both phases. First trace951 reveal regression and954 last tile preparation/credit gap, then bound repeated validated tag/key search cost against remaining2.35ms ROM-window deficit. B needs16B normal Flash reduction and protected246-line recovery; do not claim those alone improve dense18VB. No new cache/prepass, unchecked hit, fixed phase wait, or lost independent checks.'),
  source_tools={p.name:sha(p) for p in Path('tools').glob('*lazy716*.py')})
 assert not out['performance_candidate_selected']
 a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n');print('716 A/B completed; selected baseline retained')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
