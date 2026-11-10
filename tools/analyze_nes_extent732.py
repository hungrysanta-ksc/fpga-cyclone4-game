"""732 resource gate and two-phase inherited DMA/next-BG contract.

No new complete timeline was run: every normal build exceeds Flash.
The timelines below are pinned727/731 observations, not732 predictions.
"""
import argparse,json
from pathlib import Path
from analyze_nes_accept726 import audit,read,sha,ms

def run(a):
 resources=read(a.probe/'resources01.json')
 assert all(not resources['builds'][k]['budget_pass'] for k in ('A','B','C','D'))
 assert resources['builds']['B']['Flash_B']==213020
 prior=read(a.probe.parent/'nes-overlap731/analysis02.json');phases={}
 for ph in (1,2):
  folder=a.temp/f'nes-pair727-a{ph}';j=read(folder/'joint.json')
  assert j['passed'] and j['commits']==53
  p=prior['phases'][str(ph)];b=p['rows']['base'];c=p['rows']['candidate'];d=audit(folder)
  assert b['pins']['joint.json']==sha(folder/'joint.json')
  frames={}
  for g in (952,956,957):
   row=d['frames'][g];maps=row['maps'];last=maps[-1]
   frames[g]=dict(last_map={k:last[k] for k in ('offset','bytes','load_line','ACK_line','load_frame','ACK_frame','relative_ms')},
    early_DMA=row['prefix_map_DMA'],expected_total=b['details'][str(g)]['early_DMA'],
    all_map_packet_ranges=[(x['offset'],x['bytes']) for x in maps])
   if g in (952,957):
    assert sum(x['bytes'] for x in maps if 2048<=x['offset']<3584)==1536
    assert any(x['offset']==2048 and x['bytes']==1536 for x in row['prefix_map_DMA'])
   else:assert sum(x['bytes'] for x in row['prefix_map_DMA'])==1024
  bg=b['details']['953'];close=bg['current_ROM_window_close'];last_e9=bg['previous_reveal']+bg['relative_ms']['last_BG_E9']/ms(1)
  phases[ph]=dict(frames=frames,baseline_BG953=dict(reads=bg['BG_ROM_reads'],window_close=close,last_E9=last_e9,E9_to_window_close_ms=ms(close-last_e9)),
   rejected731=dict(last_ACK_delta_ms=p['delta']['last_ACK_ms'],protected=c['protected'],causal=read(a.probe.parent/'nes-overlap731/causal01.json')[str(ph)]),
   new732_timing=None,baseline_pins=b['pins'])
 guards={}
 for name in ('guards01','cursor01','gate03','deadline01','ownership03','credit03','runtime04','menu04','admission01'):
  path=a.probe/(name+'.json');g=read(path);assert g.get('passed',True)
  guards[name]=dict(SHA256=sha(path),passed=True,cases={k:len(v) for k,v in g.items() if isinstance(v,list)},menu_cases=len(g['rows'])+g['marker_cases'] if name=='menu04' else None)
 result=dict(stage=732,scope=__doc__,selected=False,budget_pass=False,timing_pass=None,new_complete_CPU_frames=0,inherited_complete_CPU_frames=212,
  resources=resources,guards=guards,phases=phases,new_RTL=False,new_65816=False,new_FIT_STA=False,new_installer=False,physical_FPS=False,
  next='Keep727/selected707. Remove at least28B of whole normal Flash and24B of the charged function boundary before a new two-phase replay. Do not claim a whole-DMA completion from E0 bit8. Preserve contiguous2048..3583 map extents, original bounded wait, checked OBJ ownership and next BG supply together.',
  tools={p.name:sha(p) for p in Path('tools').glob('*732.py')})
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(stage=732,budget_pass=False,timing_pass=None,Flash_excess_B=28,scope='Inherited two-phase budget; no new complete timeline',BG_margins_ms={p:d['baseline_BG953']['E9_to_window_close_ms'] for p,d in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
