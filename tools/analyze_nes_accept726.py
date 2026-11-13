"""726 actual ARM/65816 acceptance timing, same723 work and ROM calendar.

SPI intervals include the existing driver/IRQ model. Residual caller time
includes preparation, checks and callbacks; it is not pure measured MCU time.
No sum of overlapping BG production, SPI and SNES intervals is a speedup.
"""
import argparse,bisect,json,math
from collections import Counter
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,packets
from analyze_nes_fence714 import report
from analyze_nes_rows713 import resources,map_image
from analyze_nes_bg674 import tile_image
from test_nes_service509_schedule import Calendar

def audit(folder):
 ev=read(folder/'events.json');cpu=csv_groups(folder/'window.csv');commands=packets(folder);result={}
 for g in range(951,958):
  rows=cpu[g];events=[e for e in ev if e['generation']==g]
  prev=next(r['clock'] for r in cpu[g-1] if r['event']=='reveal' and r['op']==3)
  frozen=next(e for e in events if e['event']=='bg_map_frozen')
  # Frozen is observed at the first OAM memset, AFTER the BG-complete offer.
  # Use its matching last callback entry, not post-offer time, for readiness.
  done=max((e for e in events if e['event']=='bg684_enter' and e['clock']<=frozen['clock']),key=lambda e:e['clock'])
  assert done['map_sha']==frozen['sha256']
  completed=next(e for e in events if e['event']=='bg684_return' and e['begin']['clock']==done['clock'])
  assert completed['map_sha']==done['map_sha'] and completed['passed']==1
  loads=[r for r in rows if r['event']=='load'];acks=[r for r in rows if r['event']=='ack'];mapped=[]
  assert len(loads)==len(acks)==len(commands[g])
  for (h,bulk,push),lo,ack in zip(commands[g],loads,acks):
   if h[1]!=2:continue
   offset=int.from_bytes(h[10:12],'little');length=int.from_bytes(h[14:16],'little') or int.from_bytes(h[12:14],'little')
   call,=[e for e in events if e['event']=='call673' and e['name']=='packet_wire' and e['section']==2 and e['offset']==offset]
   wire,=[e for e in events if e['event']=='SPI' and e['opcode']=='0xe1' and abs(e['clock']-push)<=1]
   ret,=[e for e in events if e['event']=='return673' and e['call']==call['call']]
   assert call['clock']<=wire['start']<=push<=lo['clock']<=ack['clock'] and push<=ret['clock']
   enq,=[e for e in events if e['event']=='map_enqueue' and e['offset']==offset]
   assert call['clock']<=enq['clock']<=wire['start']
   io=Counter();credit=0
   for e in events:
    if e['event']=='SPI':
     io[e['opcode']]+=max(0,min(wire['start'],e['clock'])-max(call['clock'],e['start']))
     if e['opcode']=='0xe0':credit+=max(0,min(wire['start'],e['clock'])-max(enq['clock'],e['start']))
   before=wire['start']-call['clock'];assert sum(io.values())<=before+1e-5
   terms=dict(pre_E1_credit_E0_ms=ms(credit),pre_E1_receipt_E0_ms=ms(io['0xe0']-credit),pre_E1_E8_producer_ms=ms(io['0xe8']),
    pre_E1_other_SPI_ms=ms(sum(v for k,v in io.items() if k not in ('0xe0','0xe8'))),
    pre_E1_other_ARM_callbacks_ms=ms(before-sum(io.values())),E1_wire_driver_ms=ms(push-wire['start']),
    queue_to_65816_load_ms=ms(lo['clock']-push),consume_to_packet_ACK_ms=ms(ack['clock']-lo['clock']))
   assert abs(sum(terms.values())-ms(ack['clock']-call['clock']))<1e-7
   mapped.append(dict(offset=offset,bytes=length,sequence=int.from_bytes(h[2:4],'little'),
    prior_BG_complete=done['clock']<=call['clock'],
    BG_complete_to_call_ms=ms(call['clock']-done['clock']) if done['clock']<=call['clock'] else None,
    call=call['clock'],wire_start=wire['start'],push=push,load=lo['clock'],ACK=ack['clock'],
    relative_ms={k:ms(t-prev) for k,t in [('call',call['clock']),('push',push),('load',lo['clock']),('ACK',ack['clock'])]},
    load_line=lo['line'],ACK_line=ack['line'],load_frame=lo['frame'],ACK_frame=ack['frame'],
    outstanding_at_call=call['sent']-call['retired'],terms=terms))
  first=next(m for m in mapped if m['prior_BG_complete'])
  preparation=next(e['clock'] for e in events if e['event']=='prepare_enter')
  end=next(e['clock'] for e in events if e['event']=='end_enter')
  output=next(e['clock'] for e in events if e['event']=='output_enter531')
  stages=[('BG_offer',done['clock'],completed['clock']),('remaining_planner',completed['clock'],preparation),('resident_prepare',preparation,end),('END_service',end,output),('seal_preflight',output,first['call'])]
  split={k:ms(max(0,min(hi,first['call'])-max(lo,done['clock']))) for k,lo,hi in stages}
  assert abs(sum(split.values())-first['BG_complete_to_call_ms'])<1e-7
  map_dma=[]
  for i,r in enumerate(rows):
   if r['event']=='idle524' and r['value']>=65536:
    dma=next(x for x in rows[i+1:] if x['event']=='ppu_dma')
    map_dma.append(dict(offset=r['value']-65536,bytes=dma['value'],clock=dma['clock'],line=dma['line'],frame=dma['frame']))
  result[g]=dict(previous_reveal=prev,BG_complete=done['clock'],BG_last_write=done['last_map_write'],prefix_map_DMA=map_dma,
   BG_offer_return=completed['clock'],BG_complete_ms=ms(done['clock']-prev),offer_final=done['final'],
   BG_offer_ms=ms(completed['clock']-done['clock']),
   offer_maps=[m for m in mapped if done['clock']<=m['call']<completed['clock']],maps=mapped,BG_to_first_map_call_ms=split,
   total_call_to_ACK_terms_ms={k:sum(m['terms'][k] for m in mapped) for k in mapped[0]['terms']})
 return dict(frames=result,pins={n:sha(folder/n) for n in ('events.json','window.csv','packets.jsonl')},
  note='Per-packet call-to-ACK partitions are exact but overlap each other. Sum is a workload diagnostic, not elapsed frame time. BG callback readiness excludes its own offer wait.')

def run(a):
 if a.baseline_only:
  r={ph:audit(a.temp/f'nes-supply723-c{ph}') for ph in (1,2)}
  a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS726 baseline acceptance audit');return
 res=read(a.probe/'resources01.json');cal=Calendar(a.temp/'nes-service509-rom03');phases={}
 windows=[t for i,t in enumerate(cal.starts) if (t-cal.starts[i-1])%cal.period>cal.period//16];assert len(windows)==8
 def window(t):
  cyc,off=divmod(math.ceil(t),cal.period);return cyc*8+bisect.bisect_right(windows,off)-1
 for ph in (1,2):
  old,new=[a.temp/f'{prefix}{ph}' for prefix in ('nes-supply723-c','nes-accept726-a')]
  oj,nj=[read(p/'joint.json') for p in (old,new)]
  assert nj['passed'] and nj['commits']==53 and nj['parameters']==oj['parameters'] and nj['client_SHA256']==oj['client_SHA256']
  assert nj['firmware_SHA256']==res['long']['firmware'] and oj['firmware_SHA256']==res['base_long']['firmware']
  assert map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
  def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(old)==plans(new)
  pixels={p.name:sha(p) for p in new.glob('frame-*.rgb')};assert len(pixels)==53 and all(sha(old/n)==v for n,v in pixels.items())
  b,c=[report(p,a.temp/f'nes-front638-both{ph}h',cal) for p in (old,new)]
  cpu,prior=[csv_groups(p/'window.csv') for p in (new,old)]
  def reveal(rows,g):return next(r for r in rows[g] if r['event']=='reveal' and r['op']==3)
  c['protected']['deadline911'] &= reveal(cpu,911)['frame']-reveal(cpu,910)['frame']<=2
  c['protected']['public951'] &= c['intervals'][951]['VBlank']<=b['intervals'][951]['VBlank']
  c['protected']['716B_gains']=all(reveal(cpu,g)['frame']-reveal(cpu,g-1)['frame']<=reveal(prior,g)['frame']-reveal(prior,g-1)['frame'] for g in (908,934,940,943))
  c['protected']['map_DMA_719']=all(c['details'][g]['early_DMA']['map']>=b['details'][g]['early_DMA']['map'] for g in (952,956,957))
  bg={}
  for label,row in [('base',b['details'][953]),('candidate',c['details'][953])]:
   first=row['previous_reveal']+row['relative_ms']['first_BG_ROM']/ms(1);last=row['previous_reveal']+row['relative_ms']['last_BG_ROM']/ms(1)
   bg[label]=dict(first=window(first),last=window(last),span=window(last)-window(first))
  c['protected']['BG953_window723']=bg['candidate']['span']<=bg['base']['span'] and bg['candidate']['last']<=bg['base']['last']
  delta=dict(dense_ms=c['dense_ms']-b['dense_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),after951_VBlank=c['after951_VBlank']-b['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-b['after951_mean_ms'])
  for r in (b,c):
   for d in r['details'].values():d.pop('BG_plans',None);d.pop('fences',None)
  phases[ph]=dict(base=b,candidate=c,delta=delta,protected=all(c['protected'].values()),BG_windows=bg,
   audit={k:audit(p) for k,p in [('base',old),('candidate',new)]},pixels=pixels,same_work=True,
   timing_pass=all(c['protected'].values()) and all(v<0 for v in delta.values()))
 guards={}
 for name in ('admission01','normal-admission01','gate02','deadline02','ownership02','credit02','runtime02','tail02','menu02','normal-menu02'):
  p=a.probe/(name+'.json');d=read(p);assert d.get('passed',True);guards[name]=dict(SHA256=sha(p),result=d)
 result=dict(stage=726,scope=__doc__,selected=False,timing_pass=all(r['timing_pass'] for r in phases.values()),
  complete_CPU_frames=106,resources=res,phases=phases,guards=guards,new_RTL=False,new_65816=False,new_FIT_STA=False,
  physical_FPS=False,new_installer=False,board='707D unchanged RTL/ROM/SDC; inherited full FIT/STA scope only',
  tools={p.name:sha(p) for p in Path('tools').glob('*726*.py')})
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(timing_pass=result['timing_pass'],phases={p:dict(delta=r['delta'],protected=r['candidate']['protected']) for p,r in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline-only',action='store_true')
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
