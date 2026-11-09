"""Same payload/CPU pixels; charge real713 ARM, SPI, credit and ROM schedule."""
import argparse,json,hashlib
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one,packets
from analyze_nes_bg674 import tile_image,preparation
from analyze_nes_seal686 import receive_batch
from nes_schedule492 import funcs
from check_nes_game478 import ELFFile

NAMES=('map527','nes_sink527_early','nes_plan527_map_credit','offer527','quiet528','drive554','nes_plan200_progress')
def resources(src):
 f=funcs(src/'obj-nes-100/sd2snes.elf');sizes={n:next((r[2] for r in f if r[0]==n),0) for n in NAMES}
 with (src/'obj-nes-100/sd2snes.elf').open('rb') as handle:
  e=ELFFile(handle);sections={s.name:s['sh_size'] for s in e.iter_sections() if s.name in ('.bss','.data','.ahbram')}
  structs={}
  for cu in e.get_dwarf_info().iter_CUs():
   for d in cu.iter_DIEs():
    if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name') or not d.attributes.get('DW_AT_byte_size'):continue
    n=d.attributes['DW_AT_name'].value.decode()
    if n in ('nes_native_sink165','nes_native_runtime165','nes_resident211'):structs[n]=d.attributes['DW_AT_byte_size'].value
 return dict(functions=sizes,boundary_B=sum(sizes.values()),Flash_B=(src/'obj-nes-100/firmware.stm').stat().st_size,
  sections=sections,structs=structs,firmware=sha(src/'obj-nes-100/firmware.stm'))

def map_image(folder):
 result={}
 for g,cmds in packets(folder).items():
  cells={}
  for h,_,t in cmds:
   if h[1]!=2:continue
   assert h[0] in (2,4)
   off=int.from_bytes(h[10:12],'little');n=int.from_bytes(h[14:16],'little') or int.from_bytes(h[12:14],'little')
   raw=h[16:] if h[0]==2 else h[16:]*(n//2)
   assert len(raw)==n
   for i,b in enumerate(raw):assert off+i not in cells;cells[off+i]=b
  result[g]=dict(bytes=len(cells),SHA256=hashlib.sha256(json.dumps(sorted(cells.items())).encode()).hexdigest())
 return result

def run(a):
 phases={};res={n:resources(p) for n,p in dict(base=a.base,long=a.arm,normal_base=a.normal_base,normal=a.normal).items()}
 for old,new in (('base','long'),('normal_base','normal')):
  b,c=res[old],res[new];assert b['boundary_B']==1108 and c['boundary_B']<=1116
  assert c['Flash_B']<=212992 and c['sections']['.bss']-b['sections']['.bss']<=4
  assert c['sections']['.data']==b['sections']['.data'] and c['sections']['.ahbram']==b['sections']['.ahbram']
 for phase in (1,2):
  paths=dict(base=a.temp/f'nes-bg707-step{phase}',candidate=a.temp/f'nes-rows713-{a.variant}{phase}');rows={}
  if not (paths['candidate']/'joint.json').exists():
   p=paths['candidate'];error=p/'map-error.txt';assert error.is_file(),('not completed',p)
   cpu=csv_groups(p/'window.csv');last=max(g for g,rs in cpu.items() if any(r['event']=='ack' and r['op']==3 for r in rs))
   phases[phase]=dict(timing_gate=False,functional_pass=False,last_completed_generation=last,
    failure=error.read_text(encoding='utf8'),pins={n:sha(p/n) for n in ('map-error.txt','window.csv','capture.lua','mesen.log')},
    dense_and_last_ACK='not reached; no success extrapolation')
   continue
  for name,p in paths.items():
   j=read(p/'joint.json');assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
   c=trace(p,a.temp/f'nes-front638-both{phase}h');cpu=csv_groups(p/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
   b=read(paths['base']/'joint.json');assert j['parameters']==b['parameters'] and j['client_SHA256']==b['client_SHA256']
   assert map_image(p)==map_image(paths['base']) and tile_image(p)==tile_image(paths['base'])
   def plans(path):return [(e['generation'],e['plan']) for e in read(path/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
   assert plans(p)==plans(paths['base'])
   pre=receive_batch(p)
   protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
    public951=c['details'][951]['marks']['reveal']['line']<=246,interval952=c['intervals'][952]['VBlank']==3,
    wait957=c['intervals'][957]['final_waits']==0,seven_blocks=pre['checked_blocks_before_ACK']==7)
   if name=='candidate':assert j['firmware_SHA256']==res['long']['firmware']
   rows[name]=dict(dense_mean_ms=c['checked']['dense_mean_ms'],last_ACK=c['checked']['last_ACK'],protected=protected,
    after951_VBlank=sum(c['intervals'][g]['VBlank'] for g in range(952,958)),after951_mean_ms=sum(c['intervals'][g]['ms'] for g in range(952,958))/6,
    intervals=c['intervals'],early_DMA_B=c['early_DMA_B'],receive956=pre,
    details={g:c['details'][g] for g in range(951,958)},BG={g:preparation(p,g)['BG'] for g in (952,954,955,957)},
    wire=j['wire_B'],ARM_instructions=j['ARM_instructions'],stack_low=j['observed_stack_low'],
    pins={n:sha(p/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv')})
  b,c=rows['base'],rows['candidate'];delta=dict(dense_ms=c['dense_mean_ms']-b['dense_mean_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),
   after951_VBlank=c['after951_VBlank']-b['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-b['after951_mean_ms'])
  gate=all(c['protected'].values()) and delta['dense_ms']<0 and delta['last_ACK_ms']<0 and delta['after951_VBlank']<0
  phases[phase]=dict(**rows,delta=delta,timing_gate=gate,payload_pixels_equal=True)
 suffix='b01' if a.variant=='b' else '01'
 r=dict(stage=713,variant=a.variant,scope=__doc__,resources=res,phases=phases,selected=all(v['timing_gate'] for v in phases.values()),
  FPGA='707D unchanged; analysis/bg707-verification.json',SNES='original694 unchanged',new_FIT_STA=False,physical_FPS=False,
  proof_scope='Actual linked ARM/65816 and immutable published-row assertions. CPI2/84MHz, SPI/driver/IRQ and repeated ROM-window model; not simultaneous full NES/PSRAM RTL or physical gameplay.',
  source_changes={p.name:sha(p) for p in (a.arm.parent.parent/('patchb01' if a.variant=='b' else 'patch01')).iterdir() if p.is_file()},
  guards=read(a.probe/('guardsb01.json' if a.variant=='b' else 'guards03.json')),runtime=read(a.probe/f'runtime{suffix}.json'),menu=read(a.probe/f'menu{suffix}.json'),
  exit=read(a.temp/f'nes-rows713-exit{suffix}/result.json'),STOP=read(a.temp/f'nes-rows713-stop{suffix}/result.json'),
  first_BG_gate=read(a.probe/'firstb01.json') if a.variant=='b' else None,
  base_recovery={n:read(a.probe/f'base01-{n}/result.json') for n in ('none','program','done','busy','token')},
  base_recovery_scope='Executed on A ARM; same unchanged cleanup source on B, with B menu release gates separately executed.')
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(selected=r['selected'],resources=res,phases={p:(dict(delta=v['delta'],protected=v['candidate']['protected'],intervals={g:v['candidate']['intervals'][g]['VBlank'] for g in range(951,958)}) if 'candidate' in v else v) for p,v in phases.items()})))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','normal_base','normal','probe','temp','out'):p.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
 p.add_argument('--variant',choices=('a','b'),default='a')
 run(p.parse_args())
