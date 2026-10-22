# SPDX-License-Identifier: MIT
"""Execute the ARM semantic-program producer; no new FPGA/CPU/SPI schedule."""
from pathlib import Path
import argparse,collections,csv,json,math,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ARM,u16,u32,crc
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_R0,UC_ARM_REG_LR

REFERENCE=BASE/'probes/nes-joint270/test05'

class Producer(ARM):
 def __init__(self,elf):
  self.output=bytearray();super().__init__(elf,None)
 def hook(self,uc,address,size,user):
  self.instructions+=1;self.low_sp=min(self.low_sp,uc.reg_read(UC_ARM_REG_SP))
  if address==0x0800fff0:uc.emu_stop()
  elif address==(self.symbols['emit273']&~1):
   self.output.append(uc.reg_read(UC_ARM_REG_R0));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def packet(self,p,mode):
  self.uc.mem_write(0x20010000,bytes(p));self.output.clear();before=self.instructions
  ok=self.call('packet273',[0x20010000,len(p),mode])
  return ok,bytes(self.output),self.instructions-before

def build(d):
 shutil.copyfile(ROOT/'tools/nes_primitive273.c',d/'nes_primitive273.c')
 shutil.copyfile(Path(__file__),d/Path(__file__).name)
 (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global emit273\n.thumb_func\nemit273:\n bx lr\n')
 (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 for exe,args,name in [
  ('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map','nes_primitive273.c','stubs.s','-o','output.elf'],'build'),
  ('size',['output.elf'],'size'),('objdump',['-dr','output.elf'],'disassembly')]:
  r=subprocess.run([str(tool/f'arm-none-eabi-{exe}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  (d/f'{name}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')

def events(program,mode,packet=b''):
 out=[];a=0
 while a<len(program):
  if mode==0:
   assert a+3<=len(program);v=int.from_bytes(program[a:a+3],'little');a+=3
   assert v>>22==2;k=(v>>18)&15;v&=(1<<18)-1
   if k==1:assert v>>12==1;v&=4095
   elif k in (3,5,7):assert v<256
   elif k==4:assert v<64
   else:assert k==6 and v==1
   out.append((k,v));continue
  k=program[a];a+=1
  if k==1:
   assert a+3<=len(program);first=u16(program,a);n=program[a+2];a+=3
   assert 1<=n<=16 and first+n<=1312
   assert not any(first<x<first+n for x in (1024,1152))
   out.extend((1,x) for x in range(first,first+n))
  elif k in (3,5,7):
   assert a<len(program);n=program[a];a+=1
   assert 1<=n<=16 and a+n<=len(program)
   out.extend((k,x) for x in program[a:a+n]);a+=n
  elif mode==2 and k in (9,10,11,12):
   assert a<len(program);n=program[a];a+=1;assert n>0
   if k==12:out.extend([(3,0)]*n);continue
   assert a<len(program);off=program[a];a+=1;period=phase=0
   if k==9:
    assert a<len(program);pattern=program[a];a+=1;period=pattern&15;phase=pattern>>4
    assert period in (0,2,4) and (phase<period if period else phase==0)
   assert off>=16 and off+(period or n)<=len(packet)
   kind={9:5,10:3,11:7}[k]
   out.extend((kind,packet[off+((i+phase)%period if period else i)]) for i in range(n))
  else:
   assert k in (4,6) and a<len(program);v=program[a];a+=1
   assert v<64 if k==4 else v==1
   out.append((k,v))
 return out

def oracle(p,scroll,raw):
 """Derive covered granules and consumed bytes from expanded command data.
 No C parser state, continuations or compact encoder are used here."""
 op,kind=p[:2];start=u16(p,10);length=u16(p,14);data=p[16:]
 if op in (1,12,13,14):return []
 if op==7:
  unit=(16,32)[kind];base=(0,1024)[kind]
  return [(1,base+i) for i in range(start//unit,(start+length)//unit)]
 if op==15:return [(7,x) for x in data[:24]]+[(3,x) for x in data[24:]]
 if op in (10,11):
  if op==11:
   assert data[0]==3;expanded=bytearray();at=1
   while at<len(data):
    tag=data[at];at+=1;n=(tag&127)+1
    if tag&128:expanded.extend(bytes(n))
    else:expanded.extend(data[at:at+n]);at+=n
   data=bytes(expanded)
  return [(3,x) for x in data]
 if op==3:return [(4,3),(4,2),(6,1)]
 assert op in (2,4,5,8)
 data=data if op==2 else (data*(length//len(data)))
 if kind==4:return []
 if kind==3:return [(1,1152+i) for i in range(start//16,(start+len(data))//16)]
 assert kind==5
 writes=dict(enumerate(data,start));out=[]
 if 0 in writes:out.append((4,1))
 out.extend((5,writes[i]) for i in range(scroll) if i in writes)
 out.extend((1,1184+i) for i in range(128) if 1121+16*i in writes)
 if raw:
  for i in range(249):
   if 3169+i in writes:
    if i%16==0:out.append((4,(i//16)<<2))
    out.append((5,writes[3169+i]))
 return out

def packets(frame):
 q=REFERENCE/f'arm{frame}.json';r=json.loads(q.read_text())
 tx=[bytes.fromhex(t['tx']) for t in r['transfers'] if t['tx'].startswith('e1')]
 assert all(crc(t[:-2])==int.from_bytes(t[-2:],'big') for t in tx)
 return q,[t[1:-2] for t in tx]

def negative_cases(ps):
 """Mutate real packets after a valid prefix. Failed packet emits no bytes."""
 cases=[]
 def add(label,i,edit):
  p=bytearray(ps[i]);edit(p);cases.append((label,i,bytes(p)))
 index=lambda op:next(i for i,p in enumerate(ps) if p[0]==op)
 add('identity_serial',1,lambda p:p.__setitem__(4,p[4]^1))
 add('identity_generation',1,lambda p:p.__setitem__(8,p[8]^1))
 add('sequence',1,lambda p:p.__setitem__(2,p[2]^1))
 add('packet_length',1,lambda p:p.__setitem__(12,p[12]^1))
 add('prelude_type',0,lambda p:p.__setitem__(1,4))
 add('scroll_zero',0,lambda p:p.__setitem__(slice(30,32),b'\0\0'))
 add('raw_out_of_range',0,lambda p:p.__setitem__(36,8))
 add('begin_missing',1,lambda p:p.__setitem__(0,2))
 i=index(7)
 add('tile_alignment',i,lambda p:p.__setitem__(10,p[10]|1))
 add('tile_type',i,lambda p:p.__setitem__(1,2))
 i=index(14)
 add('batch_empty',i,lambda p:p.__setitem__(20,0))
 add('batch_odd_length',i,lambda p:p.__setitem__(23,p[23]|1))
 add('batch_range_overflow',i,lambda p:p.__setitem__(slice(21,23),b'\xfe\x0f'))
 add('batch_token_wrap',i,lambda p:p.__setitem__(slice(16,20),b'\xff'*4))
 i=index(15)
 add('requirements_type',i,lambda p:p.__setitem__(1,1))
 add('manifest_before_requirements',i,lambda p:p.__setitem__(0,10))
 i=next(i for i,p in enumerate(ps) if p[0] in (10,11))
 add('manifest_offset',i,lambda p:p.__setitem__(10,p[10]^1))
 add('finish_before_manifest',i,lambda p:p.__setitem__(slice(None),p[:16]))
 add('finish_nonempty',len(ps)-1,lambda p:p.__setitem__(14,1))
 cases.append(('duplicate_prelude',1,ps[0][:2]+ps[1][2:4]+ps[0][4:]))
 return cases

def directed(arm,ps):
 """Codec vectors only: synthetic H2 lengths are not certificates or frames."""
 results=[]
 for label,scroll,raw,op,out,data in [
  ('repeat2_1116_scroll_cross255',1116,0,4,1120,b'\x2a\x97'),
  ('repeat4_1116_scroll_cross255',1116,0,8,1120,b'\x2a\x97\x15\xe3'),
  ('repeat2_full_HDMA_odd_tail_phase',21,7,4,3418,b'\x2a\x97'),
 ]:
  prefix=bytearray(ps[0]);prefix[30:32]=scroll.to_bytes(2,'little');prefix[36]=raw
  p=bytearray(16)+data;p[:10]=ps[1][:10];p[0]=op;p[1]=5;p[2:4]=(2).to_bytes(2,'little')
  p[12:14]=len(data).to_bytes(2,'little');p[14:16]=out.to_bytes(2,'little')
  expect=oracle(p,scroll,raw)
  for mode in (0,1,2):
   arm.call('reset273',[u32(ps[0],4),u16(ps[0],8)])
   for q in (prefix,ps[1]):assert arm.packet(q,mode)[0]>0
   ok,program,_=arm.packet(p,mode);assert ok and events(program,mode,p)==expect,(label,mode)
  results.append(label)
 # RLE zeros/literals exercise maximum expansion and preflight rollback.
 req=bytearray(next(p for p in ps if p[0]==15));req[2:4]=(2).to_bytes(2,'little')
 for label,data,valid in [
  ('RLE_256_zero',b'\3\xff\xff',True),
  ('RLE_literal_truncated',b'\3\3\x11',False),
  ('RLE_expansion257',b'\3\xff\xff\x80',False),
  ('RLE_wrong_marker',b'\2\xff\xff',False),
 ]:
  p=bytearray(16)+data;p[:10]=ps[1][:10];p[0]=11;p[1]=2;p[2:4]=(3).to_bytes(2,'little')
  p[12:14]=len(data).to_bytes(2,'little')
  for mode in (0,1,2):
   arm.call('reset273',[u32(ps[0],4),u16(ps[0],8)])
   for q in (ps[0],ps[1],req):assert arm.packet(q,mode)[0]>0
   ok,program,_=arm.packet(p,mode)
   if valid:assert ok and events(program,mode,p)==oracle(p,21,7)
   else:assert ok==0 and not program
  results.append(label)
 return results

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
 a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);build(d)
 arm=Producer(d/'output.elf');rows=[];pin={};total_packets=total_events=0
 for frame in range(905,976):
  q,ps=packets(frame);pin[str(q)]=sha(q)
  scroll=u16(ps[0],30);raw=ps[0][36];expected=[oracle(p,scroll,raw) for p in ps]
  assert sum(k==7 for ev in expected for k,v in ev)==24
  assert sum(k==3 for ev in expected for k,v in ev)==422
  total_packets+=len(ps);total_events+=sum(map(len,expected))
  for mode in (0,1,2):
   assert arm.call('reset273',[u32(ps[0],4),u16(ps[0],8)])==1
   ins=program_bytes=proposed_wire=proposed_packets=0;result=[]
   original_wire=sum(len(p)+3 for p in ps)
   for p,expect in zip(ps,expected):
    ok,program,count=arm.packet(p,mode)
    assert ok==len(program)+1 and events(program,mode,p)==expect,(frame,mode,p[:16].hex())
    ins+=count;program_bytes+=len(program)
    # Conservative concrete representation study: keep every SNES-visible
    # command and map descriptor, replace only internal manifest packets.
    # New program chunks have16B envelope,2B target sequence, E1+CRC16=3B.
    keep=mode==2 or p[0] not in (3,10,11,15)
    chunks=math.ceil(len(program)/238)
    proposed_wire+=(len(p)+3 if keep else 0)+len(program)+21*chunks
    proposed_packets+=int(keep)+chunks
    result.append(dict(sequence=u16(p,2),op=p[0],program=program.hex(),events=len(expect),instructions=count))
   assert arm.call('complete273',[])==1
   dw=proposed_wire-original_wire;dp=proposed_packets-len(ps)
   rows.append(dict(frame=frame,mode=('event24','runs16','refs16')[mode],packets=len(ps),events=sum(map(len,expected)),
    program_bytes=program_bytes,original_E1_wire=original_wire,proposed_E1_wire=proposed_wire,
    delta_wire=dw,delta_transactions=dp,producer_instructions=ins,producer_CPI1_ms=ins/84000,
    wire_delta_ms=dw*8/2625000*1000,setup_delta_ms=dp*.008,
    additive_sensitivity_ms=ins/84000+dw*8/2625000*1000+dp*.008))
   (d/f'frame{frame}-{mode}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
  if frame%10==5:print('checked',frame,flush=True)
 _,ps=packets(905);guards=[]
 directed_cases=directed(arm,ps)
 for label,i,mutant in negative_cases(ps):
  for mode in (0,1,2):
   arm.call('reset273',[u32(ps[0],4),u16(ps[0],8)])
   for p in ps[:i]:assert arm.packet(p,mode)[0]>0
   ok,emitted,_=arm.packet(mutant,mode);assert ok==0 and not emitted,(label,mode)
   # Failure did not advance context: the original packet can still be
   # validated in this pure producer. This is NOT hardware STOP/restart.
   assert arm.packet(ps[i],mode)[0]>0
  guards.append(label)
 decoder_guards=0
 for malformed in [b'\1\0',b'\1\0\0\0',b'\1\0\0\21',b'\1\xff\3\2',b'\3\0',b'\3\2\0',b'\5\21'+bytes(17),b'\7',b'\4\x40',b'\6\0',b'\xff']:
  try:events(malformed,1)
  except AssertionError:decoder_guards+=1
  else:raise AssertionError(('decoder accepted',malformed.hex()))
 with (d/'costs.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 for malformed in [bytes([9,0,16,0]),bytes([9,4,15,0]),bytes([9,4,16,3]),bytes([10,255,16]),bytes([11,1]),bytes([12,0])]:
  try:events(malformed,2,bytes(32))
  except AssertionError:decoder_guards+=1
  else:raise AssertionError(('reference accepted',malformed.hex()))
 # A grammar-valid receipt claim is not evidence of the actual DMA target.
 # Keep this counterexample explicit: the future RTL must bind both paths
 # to one checked descriptor, or retain the old semantic comparison.
 tile=next(p for p in ps if p[0]==7)
 genuine=oracle(tile,u16(ps[0],30),ps[0][36])
 first=genuine[0][1];wrong=first+1
 forged=bytes([1,wrong&255,wrong>>8,1])
 assert events(forged,2,tile)!=genuine
 binding_counterexample=dict(packet=tile.hex(),program=forged.hex(),
  syntax_valid=True,semantic_equal=False,
  meaning='Legal range grammar/identity alone does not prove the tile DMA target or completion.')
 result=dict(passed=True,frames=71,producer_executions=213,packets=total_packets,semantic_events=total_events,
  guards=guards,guard_executions=len(guards)*3,decoder_negative_cases=decoder_guards,
  directed_codec_cases=directed_cases,directed_codec_executions=len(directed_cases)*3,
  binding_counterexample=binding_counterexample,
  stack_observed=0x2003f000-arm.low_sp,size=(d/'size.log').read_text(),source_sha256=sha(ROOT/'tools/nes_primitive273.c'),
  ELF_sha256=sha(d/'output.elf'),pins=pin,rows=rows,scope=__doc__,
  integrated_RTL=False,retimed_SPI=False,hardware_cycles=False,full_RUN=False,
  note='Producer validation/trace equality is not DMA receipt/STOP/finalACK proof. CPI1 addition is sensitivity, not a measured schedule or bound.')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pins')},indent=2))

if __name__=='__main__':main()
