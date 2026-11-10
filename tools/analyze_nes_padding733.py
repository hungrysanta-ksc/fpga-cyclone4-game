"""733 zero-padding storage removal and732B complete map extents versus727."""
import argparse,json
from pathlib import Path
from collections import defaultdict,Counter
from analyze_nes_accept726 import read,sha,ms,report,Calendar,map_image,tile_image,csv_groups,audit

def tail(path,d):
 ev=[e for e in read(path/'events.json') if e['generation']==953]
 obj=read(path/'obj-phases.json')['953'];last=[p for p in d['packets'] if p['op']==7 and p['section']==1][-1]
 replies=[]
 for e in ev:
  if e['event']!='SPI' or e['opcode']!='0xe8':continue
  b=bytes.fromhex(e['reply'])
  if b[6]==1 and b[7]==1 and int.from_bytes(b[8:10],'little')==last['expanded_B'] and int.from_bytes(b[10:12],'little')==last['offset']:replies.append(e)
 ready=min(e['clock'] for e in replies)
 assert obj['last_obj_rom_response']<=ready<=last['start']<=last['push']<=last['load']<=last['ack']
 stages=dict(ROM_to_descriptor_ms=ms(ready-obj['last_obj_rom_response']),descriptor_to_SPI_ms=ms(last['start']-ready),SPI_ms=ms(last['push']-last['start']),queue_to_load_ms=ms(last['load']-last['push']),consume_ms=ms(last['ack']-last['load']))
 assert abs(sum(stages.values())-ms(last['ack']-obj['last_obj_rom_response']))<1e-8
 lo,hi=last['ack'],d['marks']['load']['clock'];spi=defaultdict(float)
 for e in ev:
  if e['event']=='SPI':spi[e['opcode']]+=max(0,min(hi,e['clock'])-max(lo,e['start']))
 busy=sum(spi.values());assert busy<=hi-lo+1e-5
 access=[r for r in obj['cache611'] if r[0]==1]
 gaps=sorted([dict(clocks=y[2]-x[4],previous_response=x[4],next_demand=y[2],kind=y[5]) for x,y in zip(access,access[1:])],key=lambda r:r['clocks'],reverse=True)[:3]
 first=next(p for p in d['packets'] if p['op']==7 and p['section']==1)
 boundary=next(r for r in obj['boundaries561'] if r['kind']==1 and r['prior_slot']==first['offset'])
 maps=[p for p in d['packets'] if p['op']==2 and p['section']==2]
 ownership=dict(first_OBJ_offset=first['offset'],first_OBJ_bytes=first['expanded_B'],first_OBJ_ready=boundary['ready'],
  first_OBJ_start=first['start'],first_OBJ_load=first['load'],first_OBJ_ACK=first['ack'],
  first_ready_to_SPI_ms=ms(first['start']-boundary['ready']),
  last_map_ACK_to_first_OBJ_start_ms=ms(first['start']-max(p['ack'] for p in maps)),
  maximum_producer_demand_gap_ms=ms(gaps[0]['clocks']),
  maximum_gap_next_demand_vs_first_packet_ACK_ms=ms(first['ack']-gaps[0]['next_demand']),
  repeated_through_calls_before_first_OBJ=sum(e['event']=='call673' and e['name']=='nes_window184_through' and max(p['push'] for p in maps)<=e['clock']<first['start'] for e in ev if e['event']=='call673'),
  note='Maximum OBJ demand gap need not be the first bank stall in this candidate. Do not infer bank-release latency from its distance to first packet ACK. Actual consumer token writes return modeled banks; no new whole FPGA/PSRAM co-simulation.')
 return dict(ownership=ownership,OBJ=last,OBJ_stages=stages,OBJ_producer={k:v for k,v in obj.items() if k not in ('cache611','banks557','boundaries561')},OBJ_access_classes=dict(Counter(r[5] for r in access)),largest_OBJ_demand_gaps=gaps,
  last_ROM_to_ACK_ms=sum(stages.values()),post_OBJ_to_SEAL_ms=ms(hi-lo),post_OBJ_SPI_ms={k:ms(v) for k,v in spi.items() if v},
  post_OBJ_residual_ARM_callbacks_wait_ms=ms(hi-lo-busy),tail_packets=[p for p in d['packets'] if p['push']>=lo],
  note='Historical obj_rom/ROM_to_descriptor fields include OBJ_capture, not just external PSRAM. SPI partition is elapsed non-overlap; residual is not pure measured MCU computation. Per-packet consumer/queue times overlap and must not be summed.')

def run(a):
 resources=read(a.probe/'resources02.json')
 cal=Calendar(a.temp/'nes-service509-rom03');phases={}
 for ph in (1,2):
  folders={'base':a.temp/f'nes-pair727-a{ph}'}
  if a.variant:folders['candidate']=a.temp/f'nes-padding733-{a.variant}{ph}'
  rows={k:report(p,a.temp/f'nes-front638-both{ph}h',cal) for k,p in folders.items()}
  for k,v in rows.items():
   v['tail953']=tail(folders[k],v['details'][953])
   ev=read(folders[k]/'events.json');measure={}
   for g in range(951,958):
    d=v['details'][g];pack=d['packets'];events=[e for e in ev if e['generation']==g]
    prepared=next(e['clock'] for e in events if e['event']=='output_enter531')
    ordinary=[p for p in pack if p['section'] in (3,4)]
    assert all(p['start']>=prepared for p in ordinary)
    tiles=[p for p in pack if p['op']==7 and p['section']==1]
    maps=[p for p in pack if p['section']==2]
    last_tile=max((p['ack'] for p in tiles),default=prepared)
    measure[g]=dict(prepared=prepared,first_ordinary=ordinary[0]['start'],last_ordinary_ACK=ordinary[-1]['ack'],
     last_OBJ_ACK=last_tile,ordinary_before_last_OBJ_ACK_B=sum(p['expanded_B'] for p in ordinary if p['start']<last_tile),
     map_packets_before_ordinary=sum(p['start']<ordinary[0]['start'] for p in maps),
     map_packets_after_ordinary=sum(p['start']>ordinary[-1]['start'] for p in maps),
     ordinary_start_relative_ms=ms(ordinary[0]['start']-d['previous_reveal']),
     last_ordinary_ACK_relative_ms=ms(ordinary[-1]['ack']-d['previous_reveal']))
   v['overlap731']=measure
  entry=dict(rows=rows)
  if a.variant:
   b,c=rows.values();bp,cp=folders.values();bj,cj=[read(p/'joint.json') for p in (bp,cp)]
   assert cj['firmware_SHA256']==resources['builds']['733_long']['firmware']
   assert cj['passed'] and cj['commits']==53 and cj['parameters']==bj['parameters'] and cj['client_SHA256']==bj['client_SHA256']
   assert map_image(bp)==map_image(cp) and tile_image(bp)==tile_image(cp)
   def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
   assert plans(bp)==plans(cp)
   pixels={p.name:sha(p) for p in cp.glob('frame-*.rgb')};assert len(pixels)==53 and all(sha(bp/n)==v for n,v in pixels.items())
   bc,cc=[csv_groups(p/'window.csv') for p in (bp,cp)]
   def rv(cpu,g):return next(r for r in cpu[g] if r['event']=='reveal' and r['op']==3)
   entry['cold905_reveal_delta_ms']=ms(rv(cc,905)['clock']-rv(bc,905)['clock'])
   protect=c['protected']
   protect['deadline911'] &= rv(cc,911)['frame']-rv(cc,910)['frame']<=2
   protect['prior_gains']=all(rv(cc,g)['frame']-rv(cc,g-1)['frame']<=rv(bc,g)['frame']-rv(bc,g-1)['frame'] for g in (908,934,940,943,951))
   protect['map384_and_following']=all(c['details'][g]['early_DMA']['map']>=b['details'][g]['early_DMA']['map'] for g in (952,956,957))
   actual=audit(cp)
   protect['map384_contiguous']=any(d['offset']==1024 and d['bytes']>=384 for d in actual['frames'][952]['prefix_map_DMA'])
   entry['prefix_map_DMA']={g:d['prefix_map_DMA'] for g,d in actual['frames'].items()}
   cpu=csv_groups(cp/'window.csv');d956=c['details'][956]
   lastmap=next(p for p in d956['packets'] if p['section']==2 and p['offset']==3264)
   cut=next(d for d in actual['frames'][956]['prefix_map_DMA'] if d['offset']==2368)
   ended=next(r for r in cpu[956] if r['event']=='ppu_last' and r['clock']>cut['clock'])
   head=next(r for r in cpu[956] if r['event']=='load' and r['clock']>ended['clock'])
   nextdma=next(r for r in cpu[956] if r['event']=='ppu_dma' and r['clock']>ended['clock'])
   entry['handoff956']=dict(last_map_packet=lastmap,last_map_ACK_before_128B_DMA_ms=ms(cut['clock']-lastmap['ack']),
    map128_DMA=cut,map128_end=ended,next_head=head,next_DMA=nextdma,
    new_packet_won_before_next_DMA=head['clock']<nextdma['clock'],
    note='Map is already accepted. Phase1 next OBJ load at240 and HDMA at250 consume the idle opportunity; phase2 map384 DMA at241 precedes OBJ load244. This is an observed queue/idle arbitration boundary, not a missing map byte or a STOP/priority bypass.')

   protect['map1536_contiguous']=all(any(d['offset']==2048 and d['bytes']==1536 for d in actual['frames'][g]['prefix_map_DMA']) for g in (952,957))
   protect['tile956_early']=c['details'][956]['early_DMA']['tile']>=b['details'][956]['early_DMA']['tile']
   protect['BG953_window']=c['details'][953]['current_ROM_window_close']<=b['details'][953]['current_ROM_window_close']
   entry['delta']=dict(mean952_957_ms=c['after951_mean_ms']-b['after951_mean_ms'],dense951_955_ms=c['dense_ms']-b['dense_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),VBlank=c['after951_VBlank']-b['after951_VBlank'])
   entry['timing_pass']=all(protect.values()) and all(entry['delta'][k]<0 for k in ('mean952_957_ms','dense951_955_ms','last_ACK_ms')) and entry['delta']['VBlank']<=0
   entry['same_work_pixels']=True;entry['pixels']=pixels
  for v in rows.values():
   for d in v['details'].values():d.pop('BG_plans',None);d.pop('fences',None)
  phases[ph]=entry
 guards={}
 for name in ('padding02','guards02','cursor02','normal-admission02','gate03','ownership03','credit03','runtime03','normal-runtime02','menu03','normal-menu03','deadline02'):
  p=a.probe/(name+'.json');g=read(p);assert g.get('passed',True)
  guards[name]=dict(SHA256=sha(p),passed=True,cases={k:len(v) for k,v in g.items() if isinstance(v,list)})
 r=dict(resources=resources,guards=guards,stage=733,scope=__doc__,variant=a.variant,phases=phases,physical_FPS=False,new_RTL=False,new_65816=False)
 r['new_complete_CPU_frames']=106
 r['timing_pass']=all(x['timing_pass'] for x in phases.values())
 r['selected']=r['timing_pass']
 r['new_FIT_STA']=False
 r['proof_scope']='Actual linked M4/65816; CPI2/84MHz, shared SPI/IRQ and repeated ROM calendar are models. No whole NES/PSRAM RTL co-simulation or physical FPS.'
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({p:dict(delta=d.get('delta'),tail={k:dict(stages=v['tail953']['OBJ_stages'],post_ms=v['tail953']['post_OBJ_to_SEAL_ms'],SPI=v['tail953']['post_OBJ_SPI_ms'],residual=v['tail953']['post_OBJ_residual_ARM_callbacks_wait_ms']) for k,v in d['rows'].items()}) for p,d in phases.items()}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--variant')
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
