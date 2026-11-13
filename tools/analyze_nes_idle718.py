"""718 same-work actual linked ARM/65816 schedule versus707D and717.

CPI2, shared-SPI/IRQ driver and periodic measured ROM calendar; not live FPS.
"""
import argparse,json
from pathlib import Path
from analyze_nes_fence714 import report
from analyze_nes_output615 import read,sha,ms,csv_groups
from analyze_nes_rows713 import resources,map_image
from analyze_nes_bg674 import tile_image
from test_nes_service509_schedule import Calendar
from nes_schedule492 import funcs

def run(a):
 prior=read(a.probe.parent/'nes-tail717/schedule01.json');phases={}
 sources=dict(base=a.probe.parent/'nes-longrun694/arm01/src',normal_base=a.probe.parent/'nes-trial704/arm704-02/src',
  previous=a.probe.parent/'nes-tail717/arm01/src',long=a.probe/('arm02/src' if a.variant=='a' else 'arm-b01/src'),
  normal=a.probe/('normal01/src' if a.variant=='a' else 'normal-b01/src'))
 res={n:resources(p) for n,p in sources.items()}
 for old,new in (('base','long'),('normal_base','normal')):
  assert res[old]['sections']==res[new]['sections'] and res[old]['structs']==res[new]['structs']
 for old,new in ((a.probe.parent/'nes-tail717/arm01/src',sources['long']),
                 (a.probe.parent/'nes-tail717/normal01/src',sources['normal'])):
  changed=sorted(p.name for pat in ('nes*.c','nes*.h') for p in old.glob(pat) if sha(p)!=sha(new/p.name))
  assert changed==(['nes_native_runtime165.c','nes_native_sink165.c'] if a.variant=='a' else ['nes_native_sink165.c']),changed
  for n in ('nes_planner211.c','nes_resident211.c','nes_resident211.h','nes_plan_service200.c'):assert sha(old/n)==sha(new/n)
 costs={}
 for name,src in sources.items():
  costs[name]={n:size for n,_,size,*rest in funcs(src/'obj-nes-100/sd2snes.elf') if n in ('wait634','packet_wire','nes_sink212_seal','nes_cost474_pause')}
 cal=Calendar(a.temp/'nes-service509-rom03')
 for ph in (1,2):
  old=a.temp/f'nes-tail717-bounded{ph}';new=a.temp/f'nes-idle718-{a.variant}{ph}'
  oj,nj=[read(p/'joint.json') for p in (old,new)]
  assert oj['passed'] and nj['passed'] and nj['commits']==53
  assert nj['firmware_SHA256']==res['long']['firmware'] and nj['client_SHA256']==oj['client_SHA256'] and nj['parameters']==oj['parameters']
  assert map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
  def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(old)==plans(new)
  pixel_pins={p.name:sha(p) for p in new.glob('frame-*.rgb')}
  assert len(pixel_pins)==53 and pixel_pins=={p.name:sha(p) for p in old.glob('frame-*.rgb')}
  c=report(new,a.temp/f'nes-front638-both{ph}h',cal)
  b=prior['phases'][str(ph)]['original'];v=prior['phases'][str(ph)]['candidate']
  for folder,row in ((a.temp/f'nes-bg707-step{ph}',b),(old,v)):
   assert all(sha(folder/n)==h for n,h in row['pins'].items())
  deadline={}
  for label,folder,row in (('original',a.temp/f'nes-bg707-step{ph}',b),('previous',old,v),('candidate',new,c)):
   groups=csv_groups(folder/'window.csv')
   prev=next(x for x in groups[910] if x['event']=='reveal' and x['op']==3)
   marks={x['event']:x for x in groups[911] if x['op']==3 and x['event'] in ('load','upload165_entry','reveal')}
   deadline[label]=dict(previous=prev,marks=marks,VBlank=marks['reveal']['frame']-prev['frame'],
    relative_ms={n:ms(x['clock']-prev['clock']) for n,x in marks.items()})
  c['deadline911']['line_only_pass']=c['protected']['deadline911']
  c['protected']['deadline911']=c['protected']['deadline911'] and deadline['candidate']['VBlank']<=deadline['original']['VBlank']
  c['public951_line_only_pass']=c['protected']['public951']
  c['protected']['public951']=c['protected']['public951'] and c['intervals'][951]['VBlank']<=b['intervals']['951']['VBlank']
  def delta(x):return dict(dense_ms=c['dense_ms']-x['dense_ms'],last_ACK_ms=ms(c['last_ACK']-x['last_ACK']),
   after951_VBlank=c['after951_VBlank']-x['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-x['after951_mean_ms'])
  events=read(new/'events.json');progress=read(new/'progress680-events.json');borrow={}
  for g in range(951,958):
   waits=[e for e in events if e['event']=='input682_return' and e['generation']==g and e['begin']['reason']==4]
   for e in waits:
    e['duration_ms']=ms(e['clock']-e['begin']['clock'])
    e['checked_blocks']=(e['next_token']-e['begin']['next_token'])&65535 if e['input_generation']==e['begin']['input_generation'] else e['next_token']
    e['DMA_notices']=[p for p in progress if e['begin']['clock']<=p['clock']<=e['clock']]
   borrow[g]=waits
  d=delta(b);phases[ph]=dict(original=b,previous=v,candidate=c,delta_original=d,delta_717=delta(v),
   same_map_tile_plan_pixels=True,pixel_pins=pixel_pins,input_borrow=borrow,deadline911_audit=deadline,
   timing_gate=all(c['protected'].values()) and all(z<0 for z in d.values()),
   observed_extra_stack_B=int(b['stack_low'],16)-int(c['stack_low'],16))
 resource_gate=all(res[k]['Flash_B']<=212992 for k in ('long','normal'))
 result=dict(stage=718,variant=a.variant,resources=res,replaced_functions_B=costs,resource_gate=resource_gate,phases=phases,
  selected=resource_gate and all(p['timing_gate'] for p in phases.values()),
  new_RTL=False,new_65816=False,new_FIT_STA=False,new_installer=False,physical_FPS=False,
  scope=__doc__,tools={p.name:sha(p) for p in Path('tools').glob('*718*.py')},
  source_changes={n:sha(sources['long']/n) for n in changed})
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(selected=result['selected'],resources={k:v['Flash_B'] for k,v in res.items()},
  phases={p:dict(delta=x['delta_original'],vs_717=x['delta_717'],protected=x['candidate']['protected'],
   public951=x['candidate']['details'][951]['marks']['reveal']['line']) for p,x in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--variant',choices=('a','b'),default='a')
 run(p.parse_args())
