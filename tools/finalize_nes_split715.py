"""Summarize715 measured rejection and safe selected baseline for handoff."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_output615 import ms

def run(a):
 r=json.loads((a.probe/'schedule02.json').read_text());phases={}
 for phase,v in r['phases'].items():
  b,c=v['base'],v['candidate'];details={}
  for g in map(str,range(951,958)):
   details[g]={}
   for label,row in [('base',b),('candidate',c)]:
    d=row['details'][g]
    keys=('relative_ms','early_DMA','BG_ROM_reads','last_BG_call_vs_previous_window_ms','last_BG_E9_vs_previous_window_ms','BG_producer_terms_ms')
    details[g][label]={k:d[k] for k in keys}
   s=v['split'][g];details[g]['split']={k:s[k] for k in ('clock','groups','unique_rows','scratch_written','map_after_BG_inclusive_ms','BG_flush_ms','callbacks_ms','map_loop_residual_including_IRQ_ms')}
   plans=c['details'][g]['BG_plans']
   if plans:details[g]['split']['last_BG_return_to_fence_ms']=ms(s['clock']-plans[-1]['returned'])
  phases[phase]=dict(timing_gate=v['timing_gate'],same_map_OBJ_plans_pixels=v['same_map_OBJ_plans_pixels'],protected=c['protected'],delta=v['delta'],
   baseline_dense_ms=b['dense_ms'],dense_ms=c['dense_ms'],last_ACK=c['last_ACK'],baseline_last_ACK=b['last_ACK'],
   after951_VBlank=c['after951_VBlank'],after951_mean_ms=c['after951_mean_ms'],intervals=c['intervals'],
   cold905_reveal_delta_ms=v['cold905_reveal_delta_ms'],changed_intervals=v['changed_intervals'],
   SPI_delta_B=v['SPI_delta_B'],ARM_instruction_delta=v['ARM_instruction_delta'],
   observed_stack_low=c['stack_low'],baseline_stack_low=b['stack_low'],extra_observed_stack_B=v['extra_observed_stack_B'],
   deadline911=c['deadline911'],details=details,pins=c['pins'])
 guards={}
 for key,p in [('phases',a.probe/'guards02.json'),('runtime',a.probe/'runtime01.json'),('menu',a.probe/'menu01.json'),
               ('STOP',a.temp/'nes-split715-stop01/result.json'),('exit',a.temp/'nes-split715-exit01/result.json')]:
  guards[key]=dict(SHA256=sha(p),result=json.loads(p.read_text()))
 out=dict(stage=715,selected='707D + original694/704 ARM + original69465816',performance_candidate_selected=r['selected'],
  resource_gate=r['resource_gate'],resources=r['resources'],phases=phases,guards=guards,source_files=r['source_files'],
  scope=r['limitations'],full_schedule_SHA256=sha(a.probe/'schedule02.json'),
  borrowed_scratch_B=2144,new_static_RAM_B=0,new_FIT_STA=False,new_installer=False,board_evidence='analysis/bg707-verification.json',
  next_budget=dict(replacement_cap_B=1116,candidate_boundary_B=1120,selected_normal_Flash_free_B=8,candidate_normal_Flash_free_B=-4,
   new_RAM_cap_B=4,proven_product_saving_B=0,FPGA_growth_LE=0,SNES_ROM_growth_B=0,
   decision='Reject whole-frame BG-first materialization. Keep original row publication/packet order. Profile and replace redundant normal-BG plan construction on exact same-frame slot hits before considering another schedule; preserve full tag/shape/epoch/STOP validation. No extra prepass/buffer/flush or reuse of rejected714 Flash savings.'),
  source_tools={p.name:sha(p) for p in Path('tools').glob('*split715*.py')})
 out['source_tools']['trace_nes_map527.py']=sha(Path('tools/trace_nes_map527.py'))
 assert not out['performance_candidate_selected']
 a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n');print('715 complete: independent safety passed; timing and resource gates rejected; original retained')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
