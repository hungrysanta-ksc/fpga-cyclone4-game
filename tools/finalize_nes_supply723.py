"""Compact723 evidence with shared CRC/control same-boundary accounting."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_output615 import ms

def run(a):
 r=json.loads((a.probe/'schedule02.json').read_text());r['guards']={}
 for name,path in [('row_CRC',a.probe/'guards03.json'),('normal_row_CRC',a.probe/'normal-guards02.json'),
  ('CRC16',a.probe/'crc02.json'),('DMA_gate',a.probe/'gate02.json'),('admission',a.probe/'deadline02.json'),
  ('normal_menu',a.probe/'normal-menu02.json'),('bulk_policy',a.probe/'tail02.json'),('plan',a.probe/'ownership02.json'),
  ('credit',a.probe/'credit02.json'),('runtime',a.probe/'runtime02.json'),('menu',a.probe/'menu02.json'),
  ('STOP',a.temp/'nes-supply723-stop-c01/result.json'),('inherited_slots',a.probe.parent/'nes-supply720/lazy01.json'),
  ('inherited_same_65816_exit',a.temp/'nes-idle718-exit01/result.json')]:
  r['guards'][name]=dict(SHA256=sha(path),result=json.loads(path.read_text()))
  g=r['guards'][name]['result']
  if 'passed' in g:assert g['passed'],name
  if 'firmware' in g:
   expected=r['resources']['normal' if name.startswith('normal_') else 'long']['firmware']
   if not name.startswith('inherited_'):assert g['firmware']==expected,name
  if name=='bulk_policy':assert g['variants']['candidate']['firmware']==r['resources']['long']['firmware']
 for phase in r['phases'].values():
  for label in ('original','previous','candidate'):
   phase[label]['details']={g:{k:v for k,v in d.items() if k in ('previous_reveal','interval','early_DMA','relative_ms','BG_ROM_reads','map_packet_B','marks','next_budget721')} for g,d in phase[label]['details'].items()}
  phase['input_borrow']={g:dict(calls=len(xs),duration_ms=sum(x['duration_ms'] for x in xs),checked_blocks=sum(x['checked_blocks'] for x in xs),DMA_notices=sum(len(x['DMA_notices']) for x in xs)) for g,xs in phase['input_borrow'].items()}
 r['same_boundary_ledger']=json.loads((a.probe/'resources02.json').read_text())
 r['same_boundary_cap_B']=2432
 r['same_boundary_note']='Add unchanged prior resident_plan148/finish18/status308/CRC842 to both sides of7221916B cap:2432B. The shared CRC8 is counted once; no new table. Whole image Flash remains the stricter separate gate.'
 r['whole_boundary_gate']=r['same_boundary_ledger']['723C']['whole_B']<=2432
 r['selected']=r['selected'] and r['whole_boundary_gate']
 extra=r['replaced_functions_B']['long']
 assert extra==r['replaced_functions_B']['previous']
 r['next_boundary']=dict(existing_functions_B=extra,current_B=2430+sum(extra.values()),
  same_boundary_cap_B=2432+sum(extra.values()),normal_Flash_free_B=0,long_Flash_free_B=44,
  new_static_RAM_budget_B=0,proven_reclaim_B=0,
  scope='Review map credit/DMA wait and ready bulk ownership together with wait634, packet_wire and seal. Count unchanged functions on both sides; no budget is free reclaimed code.',
  time_goal='Keep C BG prior-window success, continuous map DMA and seven input blocks; remove actual bulk ready-to-submit hold and late ordinary tail, not a frame-dependent delay constant.')
 r['board']='707D/65816/SDC unchanged; existing whole Lite FIT/STA only. No new physical menu/FPS/IO signoff.'
 r['complete_CPU_frames']=212
 b=json.loads((a.probe/'schedule-b03.json').read_text())
 r['B_comparison']=dict(SHA256=sha(a.probe/'schedule-b03.json'),selected=b['selected'],phases={})
 for ph,v in r['phases'].items():
  prior=b['phases'][ph];x,y=prior['candidate'],v['candidate']
  r['B_comparison']['phases'][ph]={k:prior[k] for k in ('delta_722','wire_delta_722','wire_total_delta_722','absolute_boundary_delta_722_ms','boundary_audit')}
  r['B_comparison']['phases'][ph]['C_minus_B']=dict(after951_mean_ms=y['after951_mean_ms']-x['after951_mean_ms'],dense_ms=y['dense_ms']-x['dense_ms'],last_ACK_ms=ms(y['last_ACK']-x['last_ACK']))
 r['failed_fixture']='guards01: cold map_stale was nonzero in a no-payload callback fixture; bulk-only endpoint correctly rejected map E1. guards02 explicitly supplies an empty changed-map mask, target unchanged.'
 r['tools']={p.name:sha(p) for p in Path('tools').glob('*723*.py')}
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print('723 selected',r['selected'])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
