"""Independent Mapper4 integrated RTL/Mesen evidence audit. SPDX-License-Identifier: MIT."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
from verify_nes_rtl_fetch import oracle,pixel_coordinate,RGB
ROM_SHA='8b380949760320c993fd35a2a48af29a6afe2516f353d048f65f49fa1dd38ba9'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def numbers(p):return [tuple(map(int,s.split())) for s in p.read_text().splitlines()]
def pixel_check(actual,chrdata,table):
 expected=oracle(chrdata,table)
 return len(actual)==len(expected) and actual==expected

def fetch_check(records,chrdata,table,mesen):
 errors=Counter();used=0
 slots=Counter((line,dot) for line in range(-1,240) for k in range(34) for dot in ((k*8+5,k*8+7) if k<32 else (325+8*(k-32),327+8*(k-32))))
 if Counter((r[0],r[1]) for r in records)!=slots:errors['slots']+=1
 for line,dot,tick,virtual,physical,value in records:
  if not 0<=virtual<4096 or physical!=0x200000+table+virtual:errors['mapping']+=1
  if not 0<=physical-0x200000<len(chrdata) or value!=chrdata[physical-0x200000]:errors['value']+=1
  coord=pixel_coordinate(line,dot)
  if coord is None:continue
  y,x=coord;expected=(((y//8)*32+x)&255)*16+y%8+(8 if dot%8==7 else 0)
  if virtual!=expected:errors['coordinate_address']+=1
  if mesen.get((line,dot))!=(virtual,physical-0x200000,value):errors['mesen_fetch']+=1
  used+=1
 if used!=15360:errors['used_count']+=1
 return dict(errors=dict(errors),pixel_referenced_reads=used)

def verify(out,ref,romdir):
 errors=Counter();rom=(romdir/'mmc3.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 manifest=json.loads((out/'manifest.json').read_text());capture=json.loads((ref/'capture.json').read_text());assert manifest['sha256']==capture['rom_sha256']==ROM_SHA and capture['exit_code']==0
 prg=bytes(int(s,16) for s in (out/'prg.hex').read_text().split());chrdata=bytes(int(s,16) for s in (out/'chr.hex').read_text().split());assert rom[16:]==prg+chrdata
 log=(out/'simulation.log').read_text();build=json.loads((out/'build.json').read_text());m=re.search(r'^# RESULT (.+)$',log,re.M);assert m
 metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
 if not build.get('diagnostic_passed') or re.search(r'\*\* (?:Fatal|Error):',log) or 'PASS NES DIAGNOSTIC' not in log:errors['rtl_pass']+=1
 for k in ('pixel_errors','fetch_errors','cpu_period_errors','unknown_bus','prg_errors'):
  if metrics.get(k)!=0:errors[k]+=1
 if tuple(metrics.get(k) for k in ('frames','pixels','fetches','table_changes'))!=(4,245760,65552,3) or metrics.get('irq_count',0)<4:errors['metrics']+=1
 mt=numbers(ref/'frames.tsv');rt=numbers(out/'frames.tsv');trace=numbers(out/'fetch.tsv')
 reads={};mw=[];mr=[];mp=[]
 for row in (ref/'trace.tsv').read_text().splitlines():
  v=row.split();kind=v[0];f,line,dot,master,cpu,address,value,physical,memtype=map(int,v[1:])
  if kind=='read':reads.setdefault(f,{})[(line,dot)]=(address,physical,value)
  elif kind=='write':mw.append((f,line,dot,master,address,value))
  elif kind=='ram':mr.append((f,line,dot,master,address,value))
  elif kind=='prg':mp.append((f,line,dot,master,address,value,physical))
 if [r[0] for r in mt]!=[6,7,8,9]:errors['mesen_frames']+=1
 mesen_frames=[]
 for f,group,counter,marker,irqs,prgerr,expected,signature,fixed in mt:
  if (group,marker,irqs,prgerr,expected,signature,fixed)!=((counter&1)*8,160+(counter&1),counter,0,160+(counter&1),90,163):errors['mesen_cpu_state']+=1
  table=group*1024;rgb=(ref/f'frame-{f:03}.rgb').read_bytes();expected_rgb=b''.join(RGB[v] for v in oracle(chrdata,table))
  if rgb!=expected_rgb:errors['mesen_oracle_pixels']+=1
  acks=[v for v in mw if v[0]==f and v[4]==0xe000]
  if len(acks)!=1 or acks[0][1]!=62:errors['mesen_irq_ack']+=1
  handler=[v for v in mr if v[0]==f and v[4]==3]
  if [v[5] for v in handler]!=[counter-1,counter] or any(v[1]!=62 for v in handler):errors['mesen_irq_handler']+=1
  banks=[v for v in mp if v[0]==f]
  if len(banks)!=1 or banks[0][5:]!=(160+(counter&1),(counter&1)*8192):errors['mesen_prg_bank']+=1
  mesen_frames.append(dict(frame=f,table=table,counter=counter,rgb_sha256=sha(ref/f'frame-{f:03}.rgb'),irq_ack=acks[0][1:3] if acks else None))
 if any(b[2]!=a[2]+1 for a,b in zip(mt,mt[1:])):errors['mesen_counter_progress']+=1
 controls=[tuple(map(int,s.split()[1:])) for s in (out/'control.tsv').read_text().splitlines()]
 edges=[];a12=[]
 for s in (out/'edges.tsv').read_text().splitlines():
  v=s.split()
  if v[0]=='A12':a12.append(tuple(map(int,v[1:])))
  if v[0]=='IRQ' and int(v[1])>2148:edges.append(tuple(map(int,v[1:]))) # after 100us reset settling
 frames=[];neg={}
 if [r[0] for r in rt]!=[1,2,3,4]:errors['rtl_frames']+=1
 for i,(f,table,counter,start,marker,irqs,prgerr,fixed) in enumerate(rt):
  end=rt[i+1][3] if i+1<len(rt) else start+357368
  if (table,marker,irqs,prgerr,fixed)!=((counter&1)*8192,160+(counter&1),counter-1,0,163):errors['rtl_cpu_state']+=1
  values=bytes(int(s,16) for s in (out/f'frame-{f:3}.hex').read_text().split())
  if not pixel_check(values,chrdata,table):errors['rtl_oracle_pixels']+=1
  candidates=[m for m in mesen_frames if m['table']==table];ref_frame=next((m for m in candidates if m['counter']==counter),candidates[0])
  rgb=b''.join(RGB.get(v,b'\xff\x00\xff') for v in values)
  if hashlib.sha256(rgb).hexdigest()!=ref_frame['rgb_sha256']:errors['mesen_pixels']+=1
  records=[(line if line!=511 else -1,cycle-1,tick,virtual,physical,value) for frame,line,cycle,tick,virtual,physical,value,t in trace if frame==f]
  checked=fetch_check(records,chrdata,table,reads[ref_frame['frame']]);errors.update(checked['errors'])
  irq=[v for v in edges if start<=v[0]<end];acks=[v for v in controls if start<=v[0]<end and v[3]==0xe000];handler=[v for v in controls if start<=v[0]<end and v[3]==3]
  a12_rises=[v for v in a12 if start<=v[0]<end and v[3]==1]
  expected_a12=Counter((line,dot) for line in [-1,*range(240)] for dot in range(261,318,8))
  observed_a12=Counter(((-1 if v[1]==511 else v[1]),v[2]) for v in a12_rises if v[1]==511 or v[1]<240)
  if observed_a12!=expected_a12:errors['ppu_a12_cadence']+=1
  if len(irq)==2 and not any(v[0]+1==irq[0][0] and v[1:3]==irq[0][1:3] for v in a12_rises):errors['irq_a12_link']+=1
  if len(irq)!=2 or [v[3] for v in irq]!=[1,0] or irq[0][1:3]!=(62,261):errors['rtl_irq_edges']+=1
  if len(acks)!=1 or acks[0][1]!=62 or len(handler)!=2 or [v[4] for v in handler]!=[counter-1,counter] or any(v[1]!=62 for v in handler):errors['rtl_irq_handler']+=1
  if len(irq)==2 and len(acks)==1 and irq[1][0]!=acks[0][0]+1:errors['rtl_irq_ack_timing']+=1
  frames.append(dict(frame=f,table=table,counter=counter,pixels=len(values),rgb_sha256=hashlib.sha256(rgb).hexdigest(),mesen_frame=ref_frame['frame'],bg_latches=len(records),**checked,irq_edges=irq,irq_ack=acks,handler_ram_writes=handler,visible_and_prerender_a12_rises=sum(observed_a12.values())))
  if not neg:
   changed=bytearray(values);changed[0]^=1
   neg['pixel_corruption_rejected']=not pixel_check(bytes(changed),chrdata,table);neg['wrong_bank_rejected']=not pixel_check(values,chrdata,8192-table);neg['truncated_frame_rejected']=not pixel_check(values[:-1],chrdata,table)
   damaged=records.copy();idx=next(j for j,r in enumerate(damaged) if pixel_coordinate(r[0],r[1]) is not None);v=list(damaged[idx]);v[4]^=8192;damaged[idx]=tuple(v)
   neg['physical_bank_corruption_rejected']=bool(fetch_check(damaged,chrdata,table,reads[ref_frame['frame']])['errors'])
   neg['missing_fetch_rejected']=bool(fetch_check(records[:-1],chrdata,table,reads[ref_frame['frame']])['errors'])
 if any(b[2]!=a[2]+1 or b[3]-a[3] not in (357364,357368) for a,b in zip(rt,rt[1:])):errors['rtl_frame_progress']+=1
 return dict(candidate='NES-P2-MMC3-INTEGRATED-009',passed=not errors and all(neg.values()),errors=dict(errors),metrics=metrics,frames=frames,mesen_frames=mesen_frames,negative_tests=neg,rom_sha256=ROM_SHA,verifier_sha256=sha(Path(__file__)),scope='Four original Mapper4 BG frames under ideal memory; PRG R6 readback, CHR banks, NMI frame service, real PPU-driven A12 and CPU IRQ handler/ack. Compare full RGB, pixel-used fetches and scanline/handler semantics, not exact CPU interrupt latency or A12 electrical timing. No SMB3, full mapper/revision/scroll/sprite conformance, memory stalls, NES-to-SNES integration, fit/STA or hardware claim.')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('run','reference','rom'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();result=verify(a.run,a.reference,a.rom);(a.run/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
