"""716 actual deferred descriptor cost and two-phase continuous timing gate."""
import argparse,json
from pathlib import Path
from analyze_nes_fence714 import report
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_rows713 import resources,map_image
from analyze_nes_bg674 import tile_image
from test_nes_service509_schedule import Calendar
from nes_schedule492 import funcs

def run(a):
 src=dict(base=a.base,long=a.arm,normal_base=a.normal_base,normal=a.normal);res={n:resources(p) for n,p in src.items()}
 for old,new in (('base','long'),('normal_base','normal')):
  assert res[old]['sections']==res[new]['sections'] and res[old]['structs']==res[new]['structs']
  before={n:z for n,_,z in funcs(src[old]/'obj-nes-100/sd2snes.elf')};after={n:z for n,_,z in funcs(src[new]/'obj-nes-100/sd2snes.elf')}
  res[new]['changed_functions']={n:dict(before=before.get(n,0),after=after.get(n,0)) for n in before.keys()|after.keys() if before.get(n,0)!=after.get(n,0)}
  res[new]['Flash_free_B']=212992-res[new]['Flash_B']
 resource_gate=all(res[n]['Flash_free_B']>=0 for n in ('long','normal'))
 phases={};cal=Calendar(a.temp/'nes-service509-rom03')
 for phase in (1,2):
  paths=dict(base=a.temp/f'nes-bg707-step{phase}',candidate=a.temp/f'nes-lazy716-{a.variant}{phase}')
  b,c=[read(p/'joint.json') for p in paths.values()]
  assert b['parameters']==c['parameters'] and b['client_SHA256']==c['client_SHA256'] and c['firmware_SHA256']==res['long']['firmware']
  assert map_image(paths['base'])==map_image(paths['candidate']) and tile_image(paths['base'])==tile_image(paths['candidate'])
  events={n:read(p/'events.json') for n,p in paths.items()}
  def plans(ev):return [(e['generation'],e['plan']) for e in ev if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(events['base'])==plans(events['candidate'])
  rows={n:report(p,a.temp/f'nes-front638-both{phase}h',cal) for n,p in paths.items()};b,c=rows.values()
  slots={e['generation']:e['stats'] for e in events['candidate'] if e['event']=='slots716'};assert len(slots)==53
  planner={n:{e['generation']:dict(instructions=e['instructions'],inclusive_ms=ms(e['clock']-e['start'])) for e in es if e['event']=='return673' and e['name']=='nes_native_video211_plan'} for n,es in events.items()}
  cpu={n:csv_groups(p/'window.csv') for n,p in paths.items()}
  def reveal(n,g):return one([x for x in cpu[n][g] if x['op']==3],'reveal')
  changes=[]
  for g in range(906,958):
   old=reveal('base',g)['frame']-reveal('base',g-1)['frame'];new=reveal('candidate',g)['frame']-reveal('candidate',g-1)['frame']
   if old!=new:changes.append(dict(generation=g,base=old,candidate=new))
  delta=dict(dense_ms=c['dense_ms']-b['dense_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),after951_VBlank=c['after951_VBlank']-b['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-b['after951_mean_ms'])
  timing_gate=all(c['protected'].values()) and all(v<0 for v in delta.values())
  phases[phase]=dict(**rows,delta=delta,timing_gate=timing_gate,same_map_OBJ_plans_pixels=True,slots=slots,planner=planner,
   cold905_reveal_delta_ms=ms(reveal('candidate',905)['clock']-reveal('base',905)['clock']),changed_intervals=changes,
   SPI_delta_B={k:c['wire_B'][k]-v for k,v in b['wire_B'].items()},ARM_instruction_delta=c['ARM_instructions']-b['ARM_instructions'],
   extra_observed_stack_B=int(b['stack_low'],16)-int(c['stack_low'],16))
 result=dict(stage=716,variant=a.variant,scope=__doc__,resources=res,resource_gate=resource_gate,phases=phases,selected=resource_gate and all(p['timing_gate'] for p in phases.values()),
  new_RTL=False,new_65816=False,new_FIT_STA=False,physical_FPS=False,added_static_RAM_B=0,extra_internal_argument_B=4,
  limitations=['Linked M4/65816; CPI2 and shared SPI/IRQ models with periodic measured ROM windows, not live gameplay CPU/PSRAM RTL.',
   'Lazy ordinary rows are initialized before every observed read on all106 frames; exact hits do not read them. Exceptional shape/source validation unchanged.',
   'Planner time and instructions include nested callbacks/IRQ. Slot counters exclude caller construction; whole-path differences include its actual cost.',
   'No physical FPS or whole-board IO sign-off. 707D/69465816 unchanged, inherited FIT/STA.'],
  source_files={n:sha(a.arm/n) for n in ('nes_planner211.c','nes_resident211.c','nes_resident211.h')})
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(selected=result['selected'],resource_gate=resource_gate,phases={p:dict(delta=r['delta'],protected=r['candidate']['protected'],intervals=r['candidate']['intervals'],SPI_delta_B=r['SPI_delta_B'],extra_stack_B=r['extra_observed_stack_B']) for p,r in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','normal_base','normal','temp','out'):p.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
 p.add_argument('--variant',choices=('a','b'),default='a')
 run(p.parse_args())
