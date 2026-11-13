"""728 shared map-DMA/OBJ handoff: actual M4/65816 with modeled SPI/IRQ/ROM calendar.

Match727 payloads, plans, pixels and start phases. This is not physical FPS,
full NES/PSRAM RTL coexecution or a new board/menu hardware test.
"""
import argparse,bisect,json,math
from pathlib import Path
from analyze_nes_accept726 import audit,read,sha,ms,csv_groups,report,map_image,tile_image,Calendar

def run(a):
 res=read(a.probe/'resources01.json')
 assert all(res[k]['Flash_B']<=212992 and res[k]['whole_boundary_B']<=4700 for k in ('normal','long'))
 cal=Calendar(a.temp/'nes-service509-rom03')
 windows=[t for i,t in enumerate(cal.starts) if (t-cal.starts[i-1])%cal.period>cal.period//16]
 assert len(windows)==8
 def window(t):
  cyc,off=divmod(math.ceil(t),cal.period);return cyc*8+bisect.bisect_right(windows,off)-1
 phases={}
 for ph in (1,2):
  old,new=[a.temp/f'{prefix}{ph}' for prefix in ('nes-pair727-a','nes-dma728-'+a.variant)]
  oj,nj=[read(p/'joint.json') for p in (old,new)]
  assert nj['passed'] and nj['commits']==53 and nj['parameters']==oj['parameters']
  assert nj['client_SHA256']==(sha(a.probe/'client02/sink165.sfc') if a.variant=='c' else oj['client_SHA256'])
  assert nj['firmware_SHA256']==res['long']['firmware'] and oj['firmware_SHA256']==res['base_long']['firmware']
  assert map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
  def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
  assert plans(old)==plans(new)
  pixels={p.name:sha(p) for p in new.glob('frame-*.rgb')}
  assert len(pixels)==53 and all(sha(old/n)==v for n,v in pixels.items())
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
  audits={k:audit(p) for k,p in [('base',old),('candidate',new)]}
  c['protected']['map384_DMA952']=any(d['offset']==1024 and d['bytes']>=384 for d in audits['candidate']['frames'][952]['prefix_map_DMA'])
  c['protected']['map953_restored']=c['details'][953]['early_DMA']['map']>=832
  delta=dict(dense_ms=c['dense_ms']-b['dense_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),after951_VBlank=c['after951_VBlank']-b['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-b['after951_mean_ms'])
  # Deliberately optimistic upper bound from observed clocks/scanlines in
  # the preceding frame, allowing through the end of line246. Use the max
  #1364 clocks per line; horizontal offset/short lines make it earlier.
  # Excludes independent checks and remaining DMA; this is NOT a WCET.
  deadlines={}
  for g,d in c['details'].items():
   rv=d['marks']['reveal']
   anchors=[r for r in cpu[g] if r['frame']==rv['frame']-1 and r['line']<=246]
   assert anchors
   upper=min(r['clock']+(247-r['line'])*1364 for r in anchors)
   deadlines[g]=dict(previous246_latest_upper_clock=upper,
    SEAL_min_lateness_ms=ms(d['marks']['load']['clock']-upper),
    tile_ACK_min_lateness_ms=ms(d['previous_reveal']+d['relative_ms']['last_tile_ACK']/ms(1)-upper))
  for row in (b,c):
   for d in row['details'].values():d.pop('BG_plans',None);d.pop('fences',None)
  # Sub-VBlank time and VBlank-count improvements are reported separately.
  requested_timing_pass=all(c['protected'].values()) and delta['after951_mean_ms']<0 and delta['last_ACK_ms']<0 and delta['after951_VBlank']<=0
  # Keep the pre-existing951-955 adoption check visible; do not relabel its
  # slight regression as a requested952-957 failure or silently drop it.
  timing_pass=requested_timing_pass and delta['dense_ms']<0
  phases[ph]=dict(base=b,candidate=c,delta=delta,protected=all(c['protected'].values()),BG_windows=bg,audit=audits,pixels=pixels,same_work=True,requested_timing_pass=requested_timing_pass,timing_pass=timing_pass,VBlank_reduced=delta['after951_VBlank']<0,earlier246_optimistic_budget=deadlines)
 guards={}
 for n in ('admission01','normal-admission01','gate02','deadline02','ownership02','credit02','runtime02','handoff01','normal-handoff01','menu02','normal-menu02'):
  p=a.probe/(n+'.json');d=read(p);assert d.get('passed',True);guards[n]=dict(SHA256=sha(p),result=d)
 r=dict(stage=728,variant=a.variant,scope=__doc__,selected=False,requested_timing_pass=all(p['requested_timing_pass'] for p in phases.values()),timing_pass=all(p['timing_pass'] for p in phases.values()),complete_CPU_frames=106,resources=res,phases=phases,guards=guards,notice_is_partial_progress_not_all_map_done=a.variant!='c',new_RTL=False,new_65816=a.variant=='c',new_FIT_STA=False,physical_FPS=False,new_installer=False,board='707D RTL/SDC unchanged; original ROM forB, changed ROM forC needs separate board gate')
 if a.variant=='c':
  r['client']=read(a.probe/'client02/build.json')
  r['native_guards']={n:read(a.temp/f'nes-dma728-{n}01/result.json') for n in ('boot','cpu','exit')}
  assert all(x['passed'] for x in r['native_guards'].values())
 a.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(timing_pass=r['timing_pass'],phases={p:dict(delta=d['delta'],protected=d['candidate']['protected']) for p,d in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--variant',choices=('a','c'),default='a')
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
