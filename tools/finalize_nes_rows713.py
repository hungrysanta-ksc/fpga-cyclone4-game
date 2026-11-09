"""Summarize both actual713 candidates without promoting partial/timing failures."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_output615 import ms

def run(a):
 variants={}
 for name in ('a','b'):
  p=a.probe/f'schedule-{name}.json';r=json.loads(p.read_text());rows={}
  for phase,v in r['phases'].items():
   if 'candidate' not in v:rows[phase]=v;continue
   b,c=v['base'],v['candidate'];details={}
   for g in ('951','952','954','955','957'):
    details[g]={}
    for k,s in (('base',b),('candidate',c)):
     d=s['details'][g];start=d['previous_reveal'];bg=s['BG'].get(g,[])
     details[g][k]=dict(early_DMA_B=s['early_DMA_B'][g],interval=s['intervals'][g],
      first_BG_after_previous_ms=ms(bg[0]['call']-start) if bg else None,
      last_BG_reply_after_previous_ms=ms(bg[-1]['last_ROM_response']-start) if bg else None,
      last_tile_after_previous_ms=ms(d['last_tile_ACK']-start),SEAL_after_previous_ms=ms(d['marks']['load']['clock']-start))
   rows[phase]=dict(timing_gate=v['timing_gate'],functional_pass=True,payload_pixels_equal=v['payload_pixels_equal'],
    protected=c['protected'],delta=v['delta'],dense_mean_ms=c['dense_mean_ms'],last_ACK=c['last_ACK'],
    after951_VBlank=c['after951_VBlank'],intervals951_957={g:c['intervals'][g] for g in map(str,range(951,958))},
    wire_delta_B={k:c['wire'][k]-b['wire'][k] for k in b['wire']},ARM_instruction_delta=c['ARM_instructions']-b['ARM_instructions'],
    stack_low=c['stack_low'],baseline_stack_low=b['stack_low'],details=details,pins=c['pins'])
  variants[name]=dict(resources=r['resources'],phases=rows,selected=r['selected'],source_changes=r['source_changes'],
    schedule_SHA256=sha(p),linked_guards=len(r['guards']['cases']),runtime_guards=len(r['runtime']['cases']),
    first_BG_gate_cases=len(r['first_BG_gate']['cases']) if r['first_BG_gate'] else 0,
    menu_cases=len(r['menu']['rows']),CPU_STOP_cases=len(r['STOP']),CPU_exit_cases=len(r['exit']['cases']),
    base_recovery_scope=r['base_recovery_scope'])
 diagnostic=a.temp/'nes-rows713-diag1';failure=(diagnostic/'map-error.txt').read_text(encoding='utf8')
 original=a.temp/'nes-rows713-b1'
 assert sha(diagnostic/'window.csv')==sha(original/'window.csv')
 assert sha(diagnostic/'packets.jsonl')==sha(original/'packets.jsonl')
 result=dict(stage=713,variants=variants,diagnostic=dict(message=failure,
  exact_packet_and_CPU_trace_reproduction=True,pins={n:sha(diagnostic/n) for n in ('capture.lua','map-error.txt','window.csv','packets.jsonl')}),
  selected='707D + original694/704 ARM + original694 65816',performance_candidate_selected=any(v['selected'] for v in variants.values()),
  inherited_FIT_STA='analysis/bg707-verification.json',new_RTL=False,new_65816=False,new_FIT_STA=False,new_installer=False,
  scope='Actual linked ARM/65816 with shared modeled SPI, driver, IRQ and repeated ROM windows. No physical FPS or full concurrent NES/PSRAM RTL. Failed beam oracle was not relaxed.',
  budgets=dict(replacement_max_B=1116,RAM_growth_max_B=4,FPGA_LE_growth=0,SNES_ROM_growth=0),
  source_tools={p.name:sha(p) for p in Path('tools').glob('*rows713*.py')})
 assert not result['performance_candidate_selected']
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print('713 A/B complete; baseline retained')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
