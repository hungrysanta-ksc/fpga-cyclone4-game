# SPDX-License-Identifier: MIT
"""Execute split commands on ARM and compare bytes, descriptors and refs."""
from pathlib import Path
import argparse,collections,json,shutil,struct,subprocess
from nes_delta231 import BASE,ROOT,sha
from nes_split274 import source
from probe_nes_arm264 import ARM,plans,u16,u32,expand
from guard_nes_arm270 import Endpoint
from probe_nes_primitive273 import Producer,events,oracle

def build(d):
 (d/'nes_output264.c').write_text(source(),encoding='utf-8',newline='\n')
 (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global io259,trace259\n.thumb_func\nio259:\n bx lr\n.thumb_func\ntrace259:\n bx lr\n')
 (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 for name,args,label in [
  ('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map','nes_output264.c','stubs.s','-o','output.elf'],'build'),
  ('size',['output.elf'],'size'),('objdump',['-dr','output.elf'],'disassembly')]:
  r=subprocess.run([str(tool/f'arm-none-eabi-{name}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  (d/f'{label}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')
 for n in ('nes_split274.inc','nes_split274.py','probe_nes_split274.py'):shutil.copyfile(ROOT/'tools'/n,d/n)

def manifest(p):
 if p[0]==10:return p[16:]
 data=p[16:];assert data[0]==3
 at=1;out=bytearray()
 while at<len(data):
  tag=data[at];at+=1;n=(tag&127)+1
  if tag&128:out.extend(bytes(n))
  else:assert at+n<=len(data);out.extend(data[at:at+n]);at+=n
 return bytes(out)

def canonical(pp,original=False):
 writes=[];maps=[];tiles=[];man=bytearray();requirements=None;seal=0;begin=0
 for p in pp:
  op,kind=p[:2];at=u16(p,10)
  if op in (2,4,5,8):
   data=p[16:];data=data if op==2 else data*(u16(p,14)//len(data))
   writes.extend((kind,at+i,b) for i,b in enumerate(data))
  elif op==7:tiles.append((kind,at,u16(p,14)))
  elif op==1:begin+=1
  elif op==9:
   assert original and p[16]==3;i=17
   while i<len(p):
    off=u16(p,i);n=p[i+2]*2;i+=3;maps.append((off,p[i:i+n]));i+=n
   assert i==len(p)
  elif op in (12,14):maps.extend((u16(q,10)*2,q[20:]) for q in expand(p))
  elif op in (10,11):
   assert at==len(man);man.extend(manifest(p));assert len(man)<=256
  elif op==15:assert requirements is None;requirements=p[16:]
  elif op==3:
   seal+=1
   if original:assert requirements is None;requirements=p[16:]
   else:assert len(p)==16 and pp[-1] is p
  else:assert op==13 and not original
 assert begin==seal==1 and len(man)==256 and requirements is not None
 return writes,maps,tiles,bytes(man),requirements

def verify(pp,out):
 assert canonical(pp,True)==canonical(out)
 assert [p[0] for p in out[:2]]==[13,1]
 serial=u32(pp[0],4);generation=u16(pp[0],8)
 for i,p in enumerate(out):
  assert len(p)==16+u16(p,12)<=256
  assert u16(p,2)==i and u32(p,4)==serial and u16(p,8)==generation

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);build(d)
 ep=Endpoint();arm=ARM(d/'output.elf',ep);arm.call('reset259',[])
 primitive=Producer(BASE/'probes/nes-joint273/arm05/output.elf')
 prior,groups=plans();rows=[];pins={};sizes=collections.Counter()
 for serial,pp in groups.items():
  ep.begin(serial,pp);blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp)
  arm.uc.mem_write(0x20010000,blob);path=prior/f'expected-{u16(pp[0],8)}.bin'
  arm.uc.mem_write(0x20018000,path.read_bytes());arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  pins[str(path)]=sha(path);before=arm.instructions;start=len(ep.packets);tr=len(ep.transfers)
  assert arm.call('frame259',[0x20010000,len(blob),serial,u16(pp[0],8)])==1
  out=ep.packets[start:];verify(pp,out);assert not ep.queue
  primitive.call('reset273',[serial,u16(pp[0],8)])
  scroll=u16(out[0],30);raw=out[0][36];max_slot=0;programs=[]
  for p in out:
   ok,program,instructions=primitive.packet(p,2)
   assert ok==len(program)+1 and events(program,2,p)==oracle(p,scroll,raw)
   slot=len(p)+(2+len(program) if program else 0)
   assert slot<=256,(serial,p[:16].hex(),len(program),slot)
   max_slot=max(max_slot,slot);sizes[slot]+=1
   programs.append(dict(sequence=u16(p,2),program=program.hex(),required_slot_bytes=slot))
  assert primitive.call('complete273',[])==1
  f=serial+904
  (d/f'frame{f}.packets').write_bytes(b''.join(len(p).to_bytes(2,'little')+p for p in out))
  (d/f'frame{f}.programs.json').write_text(json.dumps(programs,indent=2)+'\n',encoding='utf-8',newline='\n')
  rows.append(dict(frame=f,packets=len(out),ordinary=sum(p[0] in (2,4,5,8) for p in out),
   instructions=arm.instructions-before,SPI_bytes=sum(len(tx) for tx,rx in ep.transfers[tr:]),max_combined_slot=max_slot))
  if f%10==5:print('checked',f,flush=True)
 r=dict(passed=True,frames=rows,scope=__doc__,max_credit=ep.max_used,stack_observed=0x2003f000-arm.low_sp,
  size=(d/'size.log').read_text(),ELF_sha256=sha(d/'output.elf'),C_sha256=sha(d/'nes_output264.c'),
  primitive_ELF_sha256=sha(BASE/'probes/nes-joint273/arm05/output.elf'),input_hashes=pins,
  original_plan_file_hashes={str(p):sha(p) for p in sorted(prior.glob('req-*.bin'))},
  program_transmitted=False,program_executed_by_FPGA=False,max_slot=max(sizes),
  packet_count=sum(x['packets'] for x in rows),ordinary_count=sum(x['ordinary'] for x in rows))
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in r.items() if k not in ('frames','input_hashes','original_plan_file_hashes')},indent=2))

if __name__=='__main__':main()
