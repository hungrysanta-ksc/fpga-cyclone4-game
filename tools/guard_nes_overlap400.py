# SPDX-License-Identifier: MIT
"""Real M4 N5 receive-ahead on recorded payloads and explicit ownership fixtures.
This checks display-identity isolation, not a live frame schedule.
"""
import argparse,json,struct,subprocess
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile,crc
from nes_delta231 import BASE,sha

class Source:
 def __init__(self):
  self.frames=[];self.frame=self.at=self.token=0;self.ea=[];self.arm=None;self.empty_once=False;self.transfers400=0
  for f in range(905,917):
   rows=json.loads((BASE/f'probes/nes-joint398/live11/arm{f}.json').read_text())['transfers']
   blocks=[bytes.fromhex(r['rx'])for r in rows if r.get('source_phase367')==2 and r['rx']]
   self.frames.append(blocks)
 def transfer(self,w):
  self.transfers400+=1
  if w[0]==0xd4:
   assert len(w)==13 and w[6]==crc(w[:6],8)and w[7]==0xa5
   if w[5]:self.at+=1;self.token+=1
   assert int.from_bytes(w[1:3],'big')+w[5]==self.token
   assert int.from_bytes(w[3:5],'little')==self.frame+1
   self.payload=self.frames[self.frame][self.at];r=bytearray(13)
   if self.empty_once and w[5]:self.empty_once=False;r[8:12]=bytes((0xaa,0,self.token>>8,self.token&255))
   else:r[8:12]=bytes((0xab,len(self.payload)-2,self.token>>8,self.token&255))
   r[12]=crc(r[8:12],8);return bytes(r)
  if w[0]==0xd5:
   assert len(w)==8 and w[5]==3 and self.at==len(self.frames[self.frame])-1
   self.frame+=1;self.at=0;self.token+=1;return bytes(8)
  if w[0]==0xea:self.ea.append(w);assert crc(w[:-2])==int.from_bytes(w[-2:],'little');return bytes(len(w))
  assert not any(w)and len(w)==len(self.payload);return self.payload

def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 src='''#include <stddef.h>
#include "nes_delta231.h"
const unsigned offsets400[]={offsetof(struct nes_resident211,epoch),offsetof(struct nes_resident211,serial),offsetof(struct nes_resident211,generation),offsetof(struct nes_resident211,displayed),offsetof(struct nes_resident211,open),offsetof(struct nes_resident211,prepared),offsetof(struct nes_dirty231,valid),offsetof(struct nes_dirty231,open)};
''';(d/'offsets.c').write_text(src)
 gcc=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin/arm-none-eabi-gcc.exe'
 subprocess.run([str(gcc),'-mcpu=cortex-m4','-mthumb','-I',str(a.elf.parent),'-c',str(d/'offsets.c'),'-o',str(d/'offsets.o')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 with(d/'offsets.o').open('rb')as f:e=ELFFile(f);section=e.get_section_by_name('.rodata');offsets=struct.unpack('<8I',section.data())
 class SegmentedARM(ARM):
  def hook(self,uc,address,size,user):
   if address==(self.symbols['source_io367']&~1):
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR
    ptr=uc.reg_read(UC_ARM_REG_R0);n=uc.reg_read(UC_ARM_REG_R1);phase=uc.reg_read(UC_ARM_REG_R2);w=bytes(uc.mem_read(ptr,n))
    r=self.endpoint.transfer(w)if phase==1 else self.endpoint.payload if n else b''
    if n:uc.mem_write(ptr,r)
    uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   super().hook(uc,address,size,user)
 ep=Source();arm=SegmentedARM(a.elf,ep);ep.arm=arm;arm.symbols['io259']=arm.symbols['physical267']
 def word(n,v=None):
  at=arm.symbols[n]
  if v is not None:arm.uc.mem_write(at,struct.pack('<I',v))
  return int.from_bytes(arm.uc.mem_read(at,4),'little')
 arm.uc.mem_map(0x40000000,0x30000);arm.uc.mem_map(0xe000e000,0x1000);arm.uc.mem_write(0x40020410,struct.pack('<I',256))
 arm.call('reset280',[]);arm.call('source_reset367',[])
 for _ in range(10):assert arm.call('source_receive367',[])==1
 r=arm.symbols['resident285'];dirty=arm.symbols['dirty285']
 for off,val in((offsets[0],1),(offsets[1],10)):arm.uc.mem_write(r+off,struct.pack('<I',val))
 arm.uc.mem_write(r+offsets[2],struct.pack('<H',10));arm.uc.mem_write(r+offsets[4],b'\1');arm.uc.mem_write(r+offsets[5],b'\1')
 word('prefetch_enabled400',0);before400=ep.transfers400
 assert arm.call('source_prefetch400',[])==1 and ep.transfers400==before400
 word('prefetch_enabled400',1);assert arm.call('source_prefetch400',[])==2 and word('prefetched400')==2 and word('prefetch_partial400')==1 and ep.frame==10
 # Fixture the previously displayed output's final ACK; the next receiver is
 # intentionally already complete, reproducing the dangerous lifetime overlap.
 arm.uc.mem_write(r+offsets[3],b'\1');arm.uc.mem_write(r+offsets[4],b'\0');arm.uc.mem_write(r+offsets[5],b'\0');arm.uc.mem_write(dirty+offsets[6],b'\1');arm.uc.mem_write(dirty+offsets[7],b'\0')
 arm.call('publish352',[]);assert word('display_serial352')==10 and word('display_epoch352')==1
 assert arm.call('source_receive367',[])==1 and ep.frame==11 and word('prefetched400')==0
 arm.call('stop286',[]);assert word('prefetched400')==word('prefetch_busy400')==word('display_saved400')==0
 # Cancel a second receive-ahead before its deferred semantic D5 is sent.
 # Do not fixture an old ACK on this path: STOP must revoke both owners.
 ep.frame=ep.at=ep.token=0
 arm.call('reset280',[]);arm.call('source_reset367',[])
 for _ in range(10):assert arm.call('source_receive367',[])==1
 for off,val in((offsets[0],1),(offsets[1],10)):arm.uc.mem_write(r+off,struct.pack('<I',val))
 arm.uc.mem_write(r+offsets[2],struct.pack('<H',10));arm.uc.mem_write(r+offsets[4],b'\1');arm.uc.mem_write(r+offsets[5],b'\1')
 assert arm.call('source_prefetch400',[])>0 and word('prefetched400')==2 and word('prefetch_partial400')==1 and ep.frame==10
 arm.call('stop286',[])
 assert ep.frame==10 and word('prefetched400')==word('prefetch_busy400')==word('display_saved400')==0
 # Long display wait: resume one block per call; a pop+empty response must
 # yield without popping that same packet twice on the following call.
 ep.frame=ep.at=ep.token=0
 arm.call('reset280',[]);arm.call('source_reset367',[])
 for _ in range(10):assert arm.call('source_receive367',[])==1
 for off,val in((offsets[0],1),(offsets[1],10)):arm.uc.mem_write(r+off,struct.pack('<I',val))
 arm.uc.mem_write(r+offsets[2],struct.pack('<H',10));arm.uc.mem_write(r+offsets[4],b'\1');arm.uc.mem_write(r+offsets[5],b'\1')
 assert arm.call('source_prefetch400',[])>0 and word('prefetched400')==2
 ep.empty_once=True
 assert arm.call('source_prefetch400',[])>0 and word('prefetched400')==2 and word('prefetch_partial400')==1
 for _ in range(12):
  if word('prefetched400')==1:break
  assert arm.call('source_prefetch400',[])>0
 assert word('prefetched400')==1 and ep.frame==10
 before400=ep.transfers400;assert arm.call('source_prefetch400',[])==1 and ep.transfers400==before400
 arm.call('stop286',[]);assert ep.frame==10 and word('prefetched400')==word('display_saved400')==0
 result=dict(passed=True,recorded_N5_frames=11,old_display_serial=10,next_input_serial=11,old_identity_preserved=True,prefetched_input_not_received_twice=True,STOP_clears_saved_identity=True,STOP_before_deferred_commit=True,one_block_yield=True,resume_after_pop_empty=True,full_prefetch_before_old_ACK=True,no_op_reports_no_SPI=True,ELF=sha(a.elf),scope=__doc__)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
