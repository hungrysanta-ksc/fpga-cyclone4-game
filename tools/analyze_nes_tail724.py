"""724 ready-bulk handoff and early tail preparation same-work actual linked ARM/65816 replay, relative-ACK estimate audit.

CPI2/84MHz, modeled shared SPI/IRQ and periodic measured ROM windows.
The admission estimate is not a hardware beam clock or a WCET guarantee.
"""
import argparse,json,bisect,math
from pathlib import Path
from analyze_nes_fence714 import report
from analyze_nes_output615 import read,sha,ms,csv_groups
from analyze_nes_rows713 import resources,map_image
from analyze_nes_bg674 import tile_image
from test_nes_service509_schedule import Calendar
from nes_schedule492 import funcs
from audit_nes_supply720 import audit

from analyze_nes_supply723 import boundary_audit

def run(a):
 build='02';tag='b'
 prior=read(a.probe.parent/'nes-supply723/schedule02.json');phases={}
 sources=dict(base=a.probe.parent/'nes-longrun694/arm01/src',normal_base=a.probe.parent/'nes-trial704/arm704-02/src',
  previous=a.probe.parent/'nes-supply723/arm03/src',long=a.probe/f'arm{build}/src',normal=a.probe/f'normal{build}/src')
 res={n:resources(p) for n,p in sources.items()}
 for old,new in (('base','long'),('normal_base','normal')):
  for name in ('.data','.ahbram'):assert res[old]['sections'][name]==res[new]['sections'][name]
  assert res[new]['sections']['.bss']-res[old]['sections']['.bss']==4
  for name,number in res[old]['structs'].items():assert res[new]['structs'][name]-number==(0 if name=='nes_resident211' else 4)
 for old,new in ((a.probe.parent/'nes-supply723/arm03/src',sources['long']),
                 (a.probe.parent/'nes-supply723/normal03/src',sources['normal'])):
  changed=sorted(p.name for pat in ('nes*.c','nes*.h') for p in old.glob(pat) if sha(p)!=sha(new/p.name))
  assert changed==['nes_native_sink165.c'],changed
  for n in ('nes_native_runtime165.c','nes_plan_service200.c','nes_sink_window184.c','nes_native_sink165.h','nes_planner211.c','nes_resident211.c','nes_resident211.h','crc.S','crc.h'):assert sha(old/n)==sha(new/n)
 costs={k:{n:size for n,_,size,*rest in funcs(p/'obj-nes-100/sd2snes.elf') if n in ('wait634','packet_wire','nes_sink212_seal')} for k,p in sources.items()}
 cal=Calendar(a.temp/'nes-service509-rom03')
 windows=[t for i,t in enumerate(cal.starts) if (t-cal.starts[i-1])%cal.period>cal.period//16]
 assert len(windows)==8
 def window(t):
  cycle,offset=divmod(math.ceil(t),cal.period);index=bisect.bisect_right(windows,offset)-1
  return cycle*8+index
 for ph in (1,2):
  old=a.temp/f'nes-supply723-c{ph}';new=a.temp/f'nes-tail724-{tag}{ph}'
  oj,nj=[read(p/'joint.json') for p in (old,new)]
  assert oj['passed'] and nj['passed'] and nj['commits']==53
  assert nj['max_bulk_banks']<=2
  assert nj['parameters']['ROM_phase']==0
  assert nj['firmware_SHA256']==res['long']['firmware'] and nj['client_SHA256']==oj['client_SHA256'] and nj['parameters']==oj['parameters']
  assert map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
  def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(old)==plans(new)
  pixel_pins={p.name:sha(p) for p in new.glob('frame-*.rgb')}
  assert len(pixel_pins)==53 and pixel_pins=={p.name:sha(p) for p in old.glob('frame-*.rgb')}
  c=report(new,a.temp/f'nes-front638-both{ph}h',cal)
  obj=read(new/'obj-phases.json')
  for g in (953,956):
   d=c['details'][g];o=obj[str(g)];prev=d['previous_reveal'];cache=o['cache611']
   # At most the END of line246 in the prior period, ignoring current
   # horizontal position. Optimistic: zero parsing/DMA after SEAL.
   latest=d['interval']['ms']-ms(357368)+ms((247-d['marks']['reveal']['line'])*1364)
   d['next_budget721']=dict(optimistic_SEAL_advance_at_least_ms=d['relative_ms']['SEAL_load']-latest,
    OBJ_first_plan_accept_ms=ms(min(q['accepted_clock'] for q in o['obj_plans'])-prev),
    OBJ_last_plan_accept_ms=ms(max(q['accepted_clock'] for q in o['obj_plans'])-prev),
    OBJ_first_read_request_ms=ms(o['first_obj_rom_request']-prev),OBJ_last_read_response_ms=ms(o['last_obj_rom_response']-prev),
    OBJ_read_source_counts={name:sum(v[0]==1 and v[5]==name for v in cache) for name in sorted({v[5] for v in cache if v[0]==1})},
    note='Historical obj_rom fields include OBJ_capture cache; not all reads are external PSRAM competition.')
  b=prior['phases'][str(ph)]['original'];v=prior['phases'][str(ph)]['candidate']
  deadline={};intervals={}
  for label,folder,row in (('original',a.temp/f'nes-bg707-step{ph}',b),('previous',old,v),('candidate',new,c)):
   groups=csv_groups(folder/'window.csv')
   prev=next(x for x in groups[910] if x['event']=='reveal' and x['op']==3)
   marks={x['event']:x for x in groups[911] if x['op']==3 and x['event'] in ('load','upload165_entry','reveal')}
   deadline[label]=dict(previous=prev,marks=marks,VBlank=marks['reveal']['frame']-prev['frame'],relative_ms={n:ms(x['clock']-prev['clock']) for n,x in marks.items()})
   reveals={g:next(x for x in groups[g] if x['event']=='reveal' and x['op']==3) for g in range(905,958)}
   intervals[label]={g:dict(VBlank=reveals[g]['frame']-reveals[g-1]['frame'],ms=ms(reveals[g]['clock']-reveals[g-1]['clock'])) for g in range(906,958)}
  c['protected']['deadline911']=c['protected']['deadline911'] and deadline['candidate']['VBlank']<=2
  c['protected']['public951']=c['protected']['public951'] and c['intervals'][951]['VBlank']<=b['intervals']['951']['VBlank']
  c['protected']['716B_gains']=all(intervals['candidate'][g]['VBlank']<=intervals['previous'][g]['VBlank'] for g in (908,934,940,943))
  c['protected']['map_DMA_719']=all(c['details'][g]['early_DMA']['map']>=v['details'][str(g)]['early_DMA']['map'] for g in (952,956,957))
  bgwindows={}
  for label,row in [('previous',v['details']['953']),('candidate',c['details'][953])]:
   last=row['previous_reveal']+row['relative_ms']['last_BG_ROM']/ms(1)
   first=row['previous_reveal']+row['relative_ms']['first_BG_ROM']/ms(1)
   bgwindows[label]=dict(previous_display_window=window(row['previous_reveal']),first_BG_window=window(first),last_BG_window=window(last),service_window_span=window(last)-window(first))
  # The display can cross a ROM-window boundary without gaining a frame.
  # Compare actual first-to-last BG service windows, not display-window IDs.
  c['protected']['BG953_window723']=bgwindows['candidate']['service_window_span']<=bgwindows['previous']['service_window_span']
  def delta(x):return dict(dense_ms=c['dense_ms']-x['dense_ms'],last_ACK_ms=ms(c['last_ACK']-x['last_ACK']),after951_VBlank=c['after951_VBlank']-x['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-x['after951_mean_ms'])
  events=read(new/'events.json');progress=read(new/'progress680-events.json');borrow={}
  for g in (908,911,934,940,943,*range(951,958)):
   waits=[e for e in events if e['event']=='input682_return' and e['generation']==g and e['begin']['reason']==4]
   for e in waits:
    e['duration_ms']=ms(e['clock']-e['begin']['clock'])
    e['checked_blocks']=(e['next_token']-e['begin']['next_token'])&65535 if e['input_generation']==e['begin']['input_generation'] else e['next_token']
    e['DMA_notices']=[p for p in progress if e['begin']['clock']<=p['clock']<=e['clock']]
   borrow[g]=waits
  d=delta(b);phases[ph]=dict(original=b,previous=v,candidate=c,delta_original=d,delta_723=delta(v),same_map_tile_plan_pixels=True,pixel_pins=pixel_pins,
   input_borrow=borrow,BG953_window_audit=bgwindows,deadline911_audit=deadline,all_intervals=intervals,timing_gate=all(c['protected'].values()) and all(z<0 for z in d.values()) and c['dense_ms']<v['dense_ms'] and c['last_ACK']<v['last_ACK'],
   observed_extra_stack_B=int(b['stack_low'],16)-int(c['stack_low'],16))
 assert res['long']['sections']['.bss']==res['previous']['sections']['.bss']
 resource_gate=all(res[k]['Flash_B']<=212992 for k in ('long','normal'))
 result=dict(stage=724,variant=a.variant,resources=res,replaced_functions_B=costs,resource_gate=resource_gate,phases=phases,
  selected=resource_gate and all(p['timing_gate'] for p in phases.values()),new_RTL=False,new_65816=False,new_FIT_STA=False,new_installer=False,physical_FPS=False,
  scope=__doc__,tools={p.name:sha(p) for p in Path('tools').glob('*724*.py')},source_changes={n:sha(sources['long']/n) for n in changed+['crc.h']})
 for ph,v in phases.items():
  b,c=v['previous'],v['candidate']
  v['wire_delta_723']={k:c['wire_B'].get(k,0)-b['wire_B'].get(k,0) for k in sorted(set(b['wire_B'])|set(c['wire_B']))}
  v['wire_total_delta_723']=sum(v['wire_delta_723'].values())
  v['supply_audit']={label:{g:{k:x for k,x in d.items() if k!='reads'} for g,d in audit(a.temp/f'{prefix}{ph}')['frames'].items()} for label,prefix in [('previous','nes-supply723-c'),('candidate',f'nes-tail724-{tag}')]}
  # Legacy720 calls header[12:14] "offset"; these bytes are payload length.
  # Actual target addresses/work equality come from map_image above.
  for frames in v['supply_audit'].values():
   for frame in frames.values():
    for name in ('tile','maps'):
     for packet in frame[name]:packet['wire_payload_B']=packet.pop('offset')
  v['same_static_RAM_723']=True
  v['boundary_audit']={label:boundary_audit(a.temp/f'{prefix}{ph}',cal) for label,prefix in [('previous','nes-supply723-c'),('candidate',f'nes-tail724-{tag}')]}
  ref720=read(Path('analysis/supply720-verification.json'))['phases'][str(ph)]['candidate']
  v['delta_720']=dict(after951_VBlank=c['after951_VBlank']-ref720['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-ref720['after951_mean_ms'],last_ACK_ms=ms(c['last_ACK']-ref720['last_ACK']))

  v['absolute_boundary_delta_723_ms']={}
  for g in (953,956,957):
   before,after=b['details'][str(g)],c['details'][g]
   shift=ms(after['previous_reveal']-before['previous_reveal'])
   d={k:after['relative_ms'][k]-before['relative_ms'][k]+shift for k in ('last_BG_call','last_BG_E9','last_BG_ROM','last_tile_ACK','SEAL_load')}
   d['previous_reveal_shift']=shift
   if g in (953,956):
    old,new=v['supply_audit']['previous'][g],v['supply_audit']['candidate'][g]
    d['OBJ_last_response']=new['OBJ_last_response_ms']-old['OBJ_last_response_ms']+shift
   v['absolute_boundary_delta_723_ms'][g]=d

 result['supply_audit_scope']='Same-work BG deadlines and OBJ capture/bulk ownership, non-additive spans.'
 result['supply_audit_limit']='Capture-backed OBJ intervals are not external ROM stalls. Request, queue and ARM spans overlap and must not be added.'
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(selected=result['selected'],resources={k:v['Flash_B'] for k,v in res.items()},phases={p:dict(delta=x['delta_original'],vs_723=x['delta_723'],protected=x['candidate']['protected'],public951=x['candidate']['details'][951]['marks']['reveal']['line']) for p,x in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--variant',choices=['B'],default='B')
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
