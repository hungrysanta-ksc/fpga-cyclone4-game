"""Joint BG production/ROM-window and contiguous map-DMA budget, no free stalls."""
import argparse,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_bg674 import tile_image,preparation
from analyze_nes_rows713 import resources,map_image
from analyze_nes_seal686 import receive_batch
from test_nes_service509_schedule import Calendar

def report(folder,reference,calendar):
 j=read(folder/'joint.json');assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
 t=trace(folder,reference);ev=read(folder/'events.json');cpu=csv_groups(folder/'window.csv');obj=read(folder/'obj-phases.json')
 detail={};windows=[]
 for grant,response in calendar.pairs:
  if not windows or grant-windows[-1][-1][0]>10000:windows.append([])
  windows[-1].append((grant,response))
 for g in range(951,958):
  d=t['details'][g];prev=d['previous_reveal'];e=[x for x in ev if x['generation']==g]
  has_bg=any(x['event']=='call673' and x['name']=='nes_plan200_emit' and bytes.fromhex(x['plan'])[6]==0 for x in e)
  p=preparation(folder,g) if has_bg else dict(BG=[],nonoverlapping_terms_ms={})
  bg=[x for x in obj[str(g)]['cache611'] if x[0]==0 and x[5]=='ROM']
  last=max((x[4] for x in bg),default=prev);cycle=int(last//calendar.period)
  nearby=[[(cy*calendar.period+lo,cy*calendar.period+hi) for lo,hi in w] for cy in (cycle-1,cycle,cycle+1) for w in windows]
  current=next((w for w in nearby if w[0][0]<=last<=w[-1][1]),None) if bg else None
  previous=max((w for w in nearby if w[-1][1]<current[0][0]),key=lambda w:w[-1][1]) if current else None
  runs=[]
  for cmd in d['packets']:
   if cmd['section']!=2:continue
   idx=d['packets'].index(cmd)
   if runs and idx==runs[-1]['last_index']+1 and cmd['offset']==runs[-1]['offset']+runs[-1]['bytes']:
    runs[-1].update(bytes=runs[-1]['bytes']+cmd['expanded_B'],last_index=idx,last_load=cmd['load'])
   else:runs.append(dict(offset=cmd['offset'],bytes=cmd['expanded_B'],last_index=idx,first_load=cmd['load'],last_load=cmd['load']))
  fences=[r for r in e if r['event']=='return714' and r['name']=='offer527']
  quiet=[r for r in e if r['event']=='return714' and r['name']=='quiet528']
  maps=[r for r in d['packets'] if r['section']==2]
  detail[g]=dict(previous_reveal=prev,interval=t['intervals'][g],early_DMA=t['early_DMA_B'][g],
   relative_ms=dict(first_BG_call=ms(p['BG'][0]['call']-prev) if has_bg else None,last_BG_call=ms(p['last_BG_call']-prev) if has_bg else None,
    last_BG_return=ms(p['BG'][-1]['returned']-prev) if has_bg else None,last_BG_E9=ms(p['BG'][-1]['E9_accept']-prev) if has_bg else None,
    first_BG_ROM=ms(bg[0][3]-prev) if bg else None,last_BG_ROM=ms(last-prev) if bg else None,
    first_map_load=ms(maps[0]['load']-prev),last_map_load=ms(maps[-1]['load']-prev),
    last_tile_ACK=ms(d['last_tile_ACK']-prev),SEAL_load=ms(d['marks']['load']['clock']-prev)),
   BG_producer_terms_ms=p['nonoverlapping_terms_ms'],BG_ROM_reads=len(bg),BG_plans=p['BG'],
   previous_ROM_window_close=previous[-1][1] if previous else None,current_ROM_window_close=current[-1][1] if current else None,
   last_BG_call_vs_previous_window_ms=ms(p['last_BG_call']-previous[-1][1]) if previous else None,
   last_BG_E9_vs_previous_window_ms=ms(p['BG'][-1]['E9_accept']-previous[-1][1]) if previous else None,
   ROM_start_margin_current_ms=ms(current[-1][1]-bg[0][3]) if current else None,
   fences=fences,quiet_calls=len(quiet),quiet_inclusive_ms=sum(ms(r['clock']-r['start']) for r in quiet),
   map_runs=runs,map_packet_B=sum(r['expanded_B'] for r in maps),
   DMA_events=[r for r in cpu[g] if r['event']=='ppu_dma'],marks=d['marks'],packets=d['packets'])
 s911=[r for r in cpu[911] if r['op']==3];pre=receive_batch(folder)
 protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
  public951=t['details'][951]['marks']['reveal']['line']<=246,interval952=t['intervals'][952]['VBlank']==3,
  wait957=t['intervals'][957]['final_waits']==0,seven_blocks=pre['checked_blocks_before_ACK']==7)
 return dict(dense_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],protected=protected,
  after951_VBlank=sum(t['intervals'][g]['VBlank'] for g in range(952,958)),
  after951_mean_ms=sum(t['intervals'][g]['ms'] for g in range(952,958))/6,
  intervals={g:t['intervals'][g] for g in range(951,958)},details=detail,
  wire_B=j['wire_B'],ARM_instructions=j['ARM_instructions'],stack_low=j['observed_stack_low'],
  deadline911={n:one(s911,n) for n in ('load','upload165_entry')},receive956=pre,
  pins={n:sha(folder/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv')})

def run(a):
 res={n:resources(p) for n,p in dict(base=a.base,long=a.arm,normal_base=a.normal_base,normal=a.normal).items()}
 for old,new in (('base','long'),('normal_base','normal')):
  b,c=res[old],res[new];assert c['Flash_B']<=212992 and c['boundary_B']<=1116
  assert b['sections']==c['sections'] and b['structs']==c['structs']
 phases={};calendar=Calendar(a.temp/'nes-service509-rom03')
 for phase in (1,2):
  bpath=a.temp/f'nes-bg707-step{phase}';cpath=a.temp/f'nes-fence714-a{phase}';reference=a.temp/f'nes-front638-both{phase}h'
  b=read(bpath/'joint.json');c=read(cpath/'joint.json')
  assert b['parameters']==c['parameters'] and b['client_SHA256']==c['client_SHA256'] and c['firmware_SHA256']==res['long']['firmware']
  assert map_image(bpath)==map_image(cpath) and tile_image(bpath)==tile_image(cpath)
  def plans(path):return [(e['generation'],e['plan']) for e in read(path/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(bpath)==plans(cpath)
  rows={n:report(p,reference,calendar) for n,p in [('base',bpath),('candidate',cpath)]};b,c=rows.values()
  delta=dict(dense_ms=c['dense_ms']-b['dense_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),
   after951_VBlank=c['after951_VBlank']-b['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-b['after951_mean_ms'])
  gate=all(c['protected'].values()) and all(v<0 for v in delta.values())
  phases[phase]=dict(**rows,delta=delta,gate=gate,same_map_OBJ_plans_pixels=True)
 result=dict(stage=714,scope=__doc__,resources=res,phases=phases,selected=all(p['gate'] for p in phases.values()),
  new_RTL=False,new_65816=False,new_FIT_STA=False,physical_FPS=False,
  limitations=['Actual linked M4/65816 with modeled CPI2, shared SPI driver means and IRQ; periodic measured boot ROM windows, not live gameplay NES/PSRAM RTL.',
   'BG ROM deadline uses BG-only requests and actual plan-bank acceptance; map run adjacency is not itself permission to start DMA.',
   'ROM-window slack, ARM callback and SPI time overlap; no additive/free saving or shifted-input comparison.',
   'STOP/exit/menu and fault guards have their stated endpoint/CPU scope; no new physical menu trial.'],
  board='707D unchanged; analysis/bg707-verification.json',
  source_files={n:sha(a.arm/n) for n in ('nes_planner211.c','nes_native_runtime165.c','nes_native_sink165.c','nes_native_sink165.h')})
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(selected=result['selected'],resources=res,phases={p:dict(delta=r['delta'],protected=r['candidate']['protected'],intervals=r['candidate']['intervals']) for p,r in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','normal_base','normal','temp','out'):p.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
 run(p.parse_args())
