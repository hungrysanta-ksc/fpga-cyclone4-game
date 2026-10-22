# SPDX-License-Identifier: MIT
"""Execute the actual Cortex-M4 output serializer on all71 pinned C plans.

SPI endpoint below is a checked event model. It is separately replaceable by
RTL RPC. Instruction counts are not hardware cycles or a full RUN/IRQ bound.
"""
from pathlib import Path
import argparse,collections,json,struct,subprocess,sys
from nes_delta231 import BASE,ROOT,sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile

def crc(data,bits=16):
 c=65535 if bits==16 else 0;top=1<<(bits-1);poly=0x1021 if bits==16 else 7
 for b in data:
  c^=b<<(bits-8)
  for _ in range(8):c=((c<<1)^poly if c&top else c<<1)&((1<<bits)-1)
 return c
def u16(p,a=0):return int.from_bytes(p[a:a+2],'little')
def u32(p,a=0):return int.from_bytes(p[a:a+4],'little')

class Endpoint:
 def __init__(self):
  self.accepted=self.retired=0;self.queue=collections.deque();self.token=1;self.head=None;self.tiles=[];self.transfers=[];self.packets=[];self.max_used=0;self.fault=0
 def begin(self,serial,packets):
  assert not self.queue and self.head is None
  self.serial=serial;self.generation=u16(packets[0],8);self.bank=(serial-1)&1;self.sequence=0;self.tiles=[p for p in packets if p[0]==7];self.tile_at=0;self.closed=not self.tiles;self.maps=[]
  self.load_tile()
 def load_tile(self):
  if self.tile_at<len(self.tiles):
   p=self.tiles[self.tile_at];self.head=dict(token=self.token,length=u16(p,14),kind=p[1],slot=u16(p,10)//(32 if p[1] else 16));self.token+=1;self.closed=False
  else:self.head=None;self.closed=True
 def consume(self,p):
  if p[0]==7:
   assert self.head and u32(p,16)==self.head['token'];self.tile_at+=1;self.load_tile()
  elif p[0]==12:
   assert self.closed and not self.head and u32(p,16)==self.token
   self.token+=1;self.maps.append((u16(p,10)*2,bytes(p[20:])))
  self.retired=(self.retired+1)&65535
 def service(self):
  # One retirement per poll. E1 leaves packets pending so the real ARM credit
  # loop must exercise the full4packet window. No artificial free credits.
  if self.queue:self.consume(self.queue.popleft())
 def transfer(self,tx):
  if tx[0]==0xe0:
   assert len(tx)==24;self.service();r=bytearray(24);used=(self.accepted-self.retired)&65535
   r[1]=0xf8;r[2]=self.fault|(1 if used else 0)|(4 if used==4 else 0)
   r[3:5]=self.accepted.to_bytes(2,'big');r[5:7]=self.retired.to_bytes(2,'big');r[7]=int(self.closed)|(2 if self.head else 0);r[8:12]=self.token.to_bytes(4,'little')
   if self.head:
    h=self.head;r[12:16]=h['token'].to_bytes(4,'little');r[16:18]=h['length'].to_bytes(2,'little');r[18]=(self.bank<<2)|h['kind'];r[19:21]=h['slot'].to_bytes(2,'little')
   r[21:23]=self.generation.to_bytes(2,'little');r[23]=crc(r[1:23],8)
  else:
   assert tx[0]==0xe1 and crc(tx[:-2])==int.from_bytes(tx[-2:],'big')
   p=bytes(tx[1:-2]);assert 16<=len(p)<=256 and len(p)==16+u16(p,12)
   assert u16(p,2)==self.sequence and u32(p,4)==self.serial and u16(p,8)==self.generation
   assert ((self.accepted-self.retired)&65535)<4
   self.sequence+=1;self.accepted=(self.accepted+1)&65535;self.queue.append(p);self.packets.append(p);self.max_used=max(self.max_used,(self.accepted-self.retired)&65535);r=bytes(len(tx))
  self.transfers.append((bytes(tx),bytes(r)));return bytes(r)

class ARM:
 def __init__(self,elf,endpoint):
  self.uc=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);self.uc.mem_map(0x08000000,0x10000);self.uc.mem_map(0x20000000,0x40000)
  with elf.open('rb') as f:
   e=ELFFile(f)
   for seg in e.iter_segments():
    if seg['p_type']=='PT_LOAD':self.uc.mem_write(seg['p_vaddr'],seg.data())
   self.symbols={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
  self.endpoint=endpoint;self.instructions=0;self.low_sp=0x2003f000;self.uc.hook_add(UC_HOOK_CODE,self.hook)
 def hook(self,uc,address,size,user):
  self.instructions+=1;self.low_sp=min(self.low_sp,uc.reg_read(UC_ARM_REG_SP))
  if address==0x0800fff0:uc.emu_stop();return
  if address==(self.symbols['io259']&~1):
   at=uc.reg_read(UC_ARM_REG_R0);n=uc.reg_read(UC_ARM_REG_R1);tx=bytes(uc.mem_read(at,n));rx=self.endpoint.transfer(tx)
   uc.mem_write(at,rx);uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  elif address==(self.symbols['trace259']&~1):uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def call(self,name,args):
  for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):self.uc.reg_write(r,v)
  self.uc.reg_write(UC_ARM_REG_SP,0x2003f000);self.uc.reg_write(UC_ARM_REG_LR,0x0800fff1);self.uc.reg_write(UC_ARM_REG_XPSR,0x01000000)
  self.uc.emu_start(self.symbols[name]|1,0x0800fff2,count=20000000)
  assert self.uc.reg_read(UC_ARM_REG_PC)==0x0800fff0,'ARM limit/fault';return self.uc.reg_read(UC_ARM_REG_R0)

def build(d):
 src=ROOT/'tools/nes_output259.c';(d/src.name).write_bytes(src.read_bytes())
 (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global io259,trace259\n.thumb_func\nio259:\n bx lr\n.thumb_func\ntrace259:\n bx lr\n')
 (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
 arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 def run(tool,args,label):
  r=subprocess.run([str(arm/tool),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);(d/(label+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')
 run('arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map','nes_output259.c','stubs.s','-o','output.elf'],'build')
 run('arm-none-eabi-size.exe',['output.elf'],'size');run('arm-none-eabi-objdump.exe',['-dr','output.elf'],'disassembly')

def plans():
 prior=BASE/'probes/nes-wholepath247/jointdecode-test02/run';groups=collections.defaultdict(list)
 for f in sorted(prior.glob('req-*.bin')):
  p=f.read_bytes();groups[u32(p,4)].append(p)
 return prior,groups

def verify(packets,out):
 expected=[];ordinary=[]
 for p in packets:
  if p[0]==9:
   j=17
   while j<len(p):
    off=u16(p,j);n=p[j+2]*2;j+=3;expected.append((off,p[j:j+n]));j+=n
   assert j==len(p)
  else:ordinary.append(p)
 got=[(u16(p,10)*2,p[20:]) for p in out if p[0]==12];assert got==expected
 got=[p for p in out if p[0] not in (12,13)];assert len(got)==len(ordinary)
 for a,b in zip(got,ordinary):
  a=bytearray(a);b=bytearray(b);a[2:4]=b[2:4]=b'\0\0'
  if a[0]==7:a[16:20]=b[16:20]=b'\0'*4
  assert a==b

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);build(d)
 endpoint=Endpoint();arm=ARM(d/'output.elf',endpoint);arm.call('reset259',[]);prior,groups=plans();rows=[]
 for serial,packets in groups.items():
  endpoint.begin(serial,packets);blob=b''.join(len(p).to_bytes(2,'little')+p for p in packets);arm.uc.mem_write(0x20010000,blob)
  arm.uc.mem_write(0x20018000,(prior/f'expected-{u16(packets[0],8)}.bin').read_bytes());arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  before=arm.instructions;sent=len(endpoint.packets);transfers=len(endpoint.transfers)
  ok=arm.call('frame259',[0x20010000,len(blob),serial,u16(packets[0],8)])
  assert ok==1,(serial,bytes(arm.uc.mem_read(arm.symbols['state259'],20)).hex())
  out=endpoint.packets[sent:];verify(packets,out);assert not endpoint.queue and endpoint.closed
  certificates=[p[16:] for p in out if p[0]==13];reference=bytes.fromhex((BASE/'probes/nes-joint255/test03/certs.hex').read_text())[32*(serial-1):32*serial]
  assert certificates==[reference],(serial,certificates,reference)
  tr=endpoint.transfers[transfers:];wire=sum(len(tx) for tx,rx in tr)
  rows.append(dict(frame=serial+904,serial=serial,packets=len(out),SPI_bytes=wire,status_reads=sum(tx[0]==0xe0 for tx,rx in tr),ARM_instructions=arm.instructions-before,map_ranges=len(endpoint.maps)))
  (d/f'frame{serial+904}.packets').write_bytes(b''.join(len(p).to_bytes(2,'little')+p for p in out))
  (d/f'frame{serial+904}.transfers.json').write_text(json.dumps([(tx.hex(),rx.hex()) for tx,rx in tr]))
 result=dict(passed=True,frames=rows,max_queue_used=endpoint.max_used,stack_observed=0x2003f000-arm.low_sp,arm_size=(d/'size.log').read_text(),source_sha256=sha(ROOT/'tools/nes_output259.c'),ELF_sha256=sha(d/'output.elf'),scope=__doc__,hardware_cycles=False,full_RUN=False,planner_input='actual2472 C output packets pinned; planner not re-executed on ARM',normal_commands_exact=True)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='frames'}))

if __name__=='__main__':main()
