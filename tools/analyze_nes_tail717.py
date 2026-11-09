"""Paired716 observer control and717 actual two-phase tail schedule."""
import argparse,json
from pathlib import Path
from analyze_nes_fence714 import report
from analyze_nes_output615 import read,sha,ms
from analyze_nes_rows713 import resources,map_image
from analyze_nes_bg674 import tile_image
from test_nes_service509_schedule import Calendar

def run(a):
 prior=read(a.probe.parent/'nes-lazy716/schedule-b01.json');phases={}
 res={n:resources(p) for n,p in dict(base=a.probe.parent/'nes-longrun694/arm01/src',normal_base=a.probe.parent/'nes-trial704/arm704-02/src',B=a.probe.parent/'nes-lazy716/arm02/src',
   long=a.probe/'arm01/src',normal=a.probe/'normal01/src').items()}
 assert res['base']['sections']==res['long']['sections'] and res['base']['structs']==res['long']['structs']
 assert res['normal_base']['sections']==res['normal']['sections'] and res['normal_base']['structs']==res['normal']['structs']
 for parent,child in [('arm02','arm01'),('normal02','normal01')]:
  oldsrc=a.probe.parent/'nes-lazy716'/parent/'src';newsrc=a.probe/child/'src'
  changed=[p.name for pattern in ('nes*.c','nes*.h') for p in oldsrc.glob(pattern) if sha(p)!=sha(newsrc/p.name)]
  assert changed==['nes_plan_service200.c'],changed
 cal=Calendar(a.temp/'nes-service509-rom03')
 for ph in (1,2):
  old=a.temp/f'nes-lazy716-b{ph}';control=a.temp/f'nes-tail717-control{ph}';new=a.temp/f'nes-tail717-bounded{ph}'
  oj,cj,nj=[read(p/'joint.json') for p in (old,control,new)]
  assert oj['passed'] and cj['passed'] and nj['passed'] and nj['commits']==53
  for k in ('frames','ARM_instructions','wire_B','observed_stack_low','firmware_SHA256','client_SHA256'):
   assert oj[k]==cj[k],('observer changed',ph,k)
  equal_files=('window.csv','seal528.csv','tile532.csv','packets.jsonl')
  assert all(sha(old/n)==sha(control/n) for n in equal_files)
  assert nj['firmware_SHA256']==res['long']['firmware'] and nj['client_SHA256']==oj['client_SHA256'] and nj['parameters']==oj['parameters']
  assert map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
  def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(old)==plans(new)
  c=report(new,a.temp/f'nes-front638-both{ph}h',cal);b=prior['phases'][str(ph)]['base'];v=prior['phases'][str(ph)]['candidate']
  for folder,row in [(a.temp/f'nes-bg707-step{ph}',b),(old,v)]:
   assert all(sha(folder/n)==h for n,h in row['pins'].items())
  def delta(x):return dict(dense_ms=c['dense_ms']-x['dense_ms'],last_ACK_ms=ms(c['last_ACK']-x['last_ACK']),
   after951_VBlank=c['after951_VBlank']-x['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-x['after951_mean_ms'])
  d=delta(b);phases[ph]=dict(observer_control_exact=True,control_pins={n:sha(control/n) for n in equal_files},
   original=b,B=v,candidate=c,delta_original=d,delta_B=delta(v),same_map_tile_plan_pixels=True,
   timing_gate=all(c['protected'].values()) and all(z<0 for z in d.values()),
   SPI_delta_original={k:c['wire_B'][k]-n for k,n in b['wire_B'].items()},
   observed_extra_stack_B=int(b['stack_low'],16)-int(c['stack_low'],16))
 gate=all(res[k]['Flash_B']<=212992 for k in ('long','normal'))
 result=dict(stage=717,resources=res,resource_gate=gate,phases=phases,selected=gate and all(p['timing_gate'] for p in phases.values()),
  new_RTL=False,new_65816=False,new_FIT_STA=False,new_installer=False,physical_FPS=False,
  selected_image='707D + original694/704 ARM + original69465816',
  scope=__doc__+' Same linked M4/65816/CPI2/sharedSPI/IRQ/ROM calendar. No full live game CPU/PSRAM RTL or physical FPS.',
  tools={p.name:sha(p) for p in Path('tools').glob('*717*.py')},
  source_changes={'nes_plan_service200.c':sha(a.probe/'arm01/src/nes_plan_service200.c')})
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(selected=result['selected'],resources={k:v['Flash_B'] for k,v in res.items()},phases={p:dict(delta=x['delta_original'],vs_B=x['delta_B'],protected=x['candidate']['protected']) for p,x in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
