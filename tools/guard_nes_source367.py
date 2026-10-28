# SPDX-License-Identifier: MIT
"""Execute causal hint guards on the exact integration M4 ELF, no live oracle."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile,crc
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_delta231 import BASE,sha

class Receive(ARM):
 def __init__(self,elf,blocks,mode):
  self.blocks=blocks;self.mode=mode;self.at=0;self.held=False;self.acks=0;self.empty=0;self.wakes=0
  super().__init__(elf,None)
 def hook(self,uc,address,size,user):
  name=next((n for n in ('source_io367','physical267','irq_end284','irq_begin284','wait284') if address==(self.symbols[n]&~1)),None)
  if not name:return super().hook(uc,address,size,user)
  self.instructions+=1;ok=1
  p,n,phase=(uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
  if name=='source_io367':
   if phase==1:
    assert not self.held and n==13;self.held=True
    tx=bytes(uc.mem_read(p,n));assert tx[0]==0xd4 and crc(tx[:6],8)==tx[6] and tx[7]==0xa5
    token=self.at;self.empty=int(self.mode=='empty_wake' and not self.wakes)
    block=b'' if self.empty else self.blocks[self.at];flags=0xa8|bool(block)|(2 if self.at==len(self.blocks)-1 and self.mode!='missing_last' else 0)
    header=bytearray([flags,len(block),token>>8,token&255]);header.append(crc(header,8))
    if self.mode=='header_crc':header[4]^=1
    if self.mode=='token':header[3]^=1;header[4]=crc(header[:4],8)
    if self.mode=='flags':header[0]^=4;header[4]=crc(header[:4],8)
    uc.mem_write(p,bytes(8)+bytes(header))
   else:
    assert self.held;self.held=False
    if n:
     block=self.blocks[self.at]
     if self.mode=='generation' and not self.at:
      block=bytearray(block);block[16]^=3;block=bytes(block)
     c=crc(block)
     if self.mode=='payload_crc':c^=1
     assert n==len(block)+2;uc.mem_write(p,block+c.to_bytes(2,'big'));self.at+=1
     if self.mode=='cancel':uc.mem_write(self.symbols['source_cancel367'],b'\1\0\0\0')
  elif name=='physical267':
   assert not self.held;tx=bytes(uc.mem_read(p,n))
   assert tx[0]==0xd5 and n==8;self.acks+=1
  elif name=='wait284':
   assert not self.held;self.wakes+=1
  uc.reg_write(UC_ARM_REG_R0,ok);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);old=BASE/'probes/nes-capture365/early03';elf=a.source/'output.elf'
 ref=ARM(old/'output.elf',None)
 with (old/'output.elf').open('rb') as f:
  syms=ELFFile(f).get_section_by_name('.symtab');sizes={n:syms.get_symbol_by_name(n)[0]['st_size'] for n in ('receiver280','resident285','history286')}
 assert sizes==dict(receiver280=28,resident285=6016,history286=4910)
 rows=[];cases=[]
 for frame in (907,908):
  blob=(old/f'prior360-{frame-904}.bin').read_bytes();arm=ARM(elf,None)
  for n,size in sizes.items():
   offset=ref.symbols[n]-0x20000000;arm.uc.mem_write(arm.symbols[n],blob[offset:offset+size])
  block=next(bytes.fromhex(x.split()[3]) for x in (old/'blocks.txt').read_text().splitlines() if x.startswith(str(frame)+' '))
  arm.uc.mem_write(0x20028000,block);assert arm.call('block286',[0x20028000,len(block),binascii.crc_hqx(block,65535)])==1
  resident=bytes(arm.uc.mem_read(arm.symbols['resident285'],6016));state=bytes(arm.uc.mem_read(arm.symbols['receiver280'],28))
  start=arm.instructions;n=arm.call('source_hint367',[]);cost=arm.instructions-start;assert n==28
  address=arm.call('source_buffer367',[]);packet=bytes(arm.uc.mem_read(address,n));tags=list(struct.unpack('<7H',packet[12:26]))
  assert packet[:2]==b'\xea\x07' and binascii.crc_hqx(packet[:26],65535)==int.from_bytes(packet[26:],'little')
  assert bytes(arm.uc.mem_read(arm.symbols['resident285'],6016))==resident
  assert bytes(arm.uc.mem_read(arm.symbols['receiver280'],28))==state
  if frame==907:assert set(tags)=={0x197d,0x1918,0x191a,0x1919,0x191b,0x13da,0x13d8}
  else:assert tags==[0x213,0x218,0x216]+[0x213]*4
  # Future packet/planner scratch is deliberately poisoned, not a hint input.
  arm.uc.mem_write(0x20010000,b'\xa5'*16384)
  assert arm.call('source_hint367',[])==28 and bytes(arm.uc.mem_read(address,28))==packet
  rows.append(dict(frame=frame,instructions=cost,tags=tags,packet=packet.hex(),resident_read_only=True))
  # Byte offsets follow the compiled resident211 ABI, checked above by size.
  mutations=[('cold','receiver280',22,b'\1'),('phase_error','receiver280',21,b'\3'),
   ('epoch','resident285',3160,b'\xff\xff\xff\xff'),('serial','resident285',3164,b'\xff\xff\xff\xff'),
   ('generation','resident285',3176,b'\xff\xff'),('bg_bound','resident285',3178,b'\1\4'),
   ('obj_bound','resident285',3180,b'\x81\0'),('active','resident285',3182,b'\2'),
   ('not_displayed','resident285',3184,b'\0'),('open','resident285',3185,b'\1'),
   ('prepared','resident285',3186,b'\1'),('fault','resident285',3187,b'\1'),
   ('cancel','source_cancel367',0,b'\1\0\0\0'),('disabled','hint_mode367',0,b'\0\0\0\0')]
  for name,symbol,offset,value in mutations:
   at=arm.symbols[symbol]+offset;prior=bytes(arm.uc.mem_read(at,len(value)));arm.uc.mem_write(at,value)
   assert arm.call('source_hint367',[])==0,(frame,name)
   arm.uc.mem_write(at,prior);cases.append([frame,name])
 receive=[]
 blocks=[bytes.fromhex(x.split()[3]) for x in (old/'blocks.txt').read_text().splitlines() if x.startswith('905 ')]
 for mode in ('normal','empty_wake','header_crc','token','flags','payload_crc','cancel','missing_last','generation'):
  arm=Receive(elf,blocks,mode)
  for n in ('reset259','reset285','reset280','source_reset367'):arm.call(n,[])
  ok=arm.call('source_receive367',[]);error=int.from_bytes(arm.uc.mem_read(arm.symbols['source_error367'],4),'little')
  assert bool(ok)==(mode in ('normal','empty_wake')),(mode,ok,error)
  assert arm.acks==int(bool(ok)) and not arm.held,(mode,'optimistic ACK or held CS')
  if ok:assert arm.at==len(blocks)
  else:assert arm.call('source_receive367',[])==0 and arm.acks==0
  receive.append(dict(mode=mode,ok=ok,error=error,blocks=arm.at,final_ACKs=arm.acks,wakes=arm.wakes))
 result=dict(passed=True,rows=rows,cases=cases,receive=receive,ELF=sha(elf),pins={str(x):sha(x) for x in (elf,old/'output.elf',old/'blocks.txt',old/'prior360-3.bin',old/'prior360-4.bin',Path(__file__).resolve())})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
