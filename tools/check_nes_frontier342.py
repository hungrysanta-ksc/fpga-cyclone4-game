# SPDX-License-Identifier: MIT
"""Actual M4 frontier guards; prefill is stubbed, integrated schedules test SPI."""
import argparse,ctypes as c,json
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_delta231 import sha
class Native(c.Structure):
 _fields_=[('maps',c.c_uint16*1056),('rows',c.c_uint8*224),('palette',c.c_uint8*64),('objects',c.c_uint64*128),('raster',c.c_uint64*224),('exceptions',c.c_uint32*128),('tiles',c.c_uint32*512),('raw',c.c_uint8*2048),('generation',c.c_uint16),('counts',c.c_uint16*6),('at',c.c_uint16*6),('records',c.c_uint16),('bytes',c.c_uint16),('ntiles',c.c_uint16),('missing',c.c_uint16),('last_tile',c.c_uint16),('state',c.c_uint8),('next_kind',c.c_uint8),('lane',c.c_uint8),('error',c.c_uint8),('patch_count',c.c_uint8),('token_valid',c.c_uint8),('next_token',c.c_uint16),('status',c.c_uint8*8),('ready',c.c_uint8)]
class Resident(c.Structure):
 _fields_=[('bg',c.c_uint16*1024),('obj',c.c_uint32*128),('resident',c.c_uint8*288),('used',c.c_uint8*144),('dirty',c.c_uint8*144),('stale',c.c_uint64*2),('upload',c.c_uint64),('epoch',c.c_uint32),('serial',c.c_uint32),('writes',c.c_uint32),('hits',c.c_uint32),('generation',c.c_uint16),('bg_slots',c.c_uint16),('obj_slots',c.c_uint16),('active',c.c_uint8),('target',c.c_uint8),('displayed',c.c_uint8),('open',c.c_uint8),('prepared',c.c_uint8),('fault',c.c_uint8),('write',c.c_uint32),('ctx',c.c_uint32),('head',c.c_uint16*256),('next',c.c_uint16*1152)]
class A(ARM):
 def hook(self,u,address,size,user):
  if address==self.symbols['prefill287']&~1:
   self.instructions+=1;u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,address,size,user)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);o=ap.parse_args();o.out.mkdir(parents=True,exist_ok=False)
 a=A(o.source/'output.elf',None)
 assert a.call('layout285',[3])==c.sizeof(Native);assert a.call('layout285',[5])==c.sizeof(Resident)
 def write(n,v):a.uc.mem_write(a.symbols[n],int(v).to_bytes(4,'little'))
 def word(n):return int.from_bytes(a.uc.mem_read(a.symbols[n],4),'little')
 def init(used,slot):
  a.call('reset285',[]);a.uc.mem_write(a.symbols['input285']+Native.generation.offset,b'\x01\0');assert a.call('begin285',[])==1
  a.uc.mem_write(a.symbols['input285']+Native.state.offset,b'\x04')
  bits=bytearray(144)
  for i in used:bits[i//8]|=1<<(i%8)
  a.uc.mem_write(a.symbols['resident285']+Resident.used.offset,bytes(bits))
  p=b'\x82\x01\0'+b'\x80\x01\0'+slot.to_bytes(2,'little')+b'\x07\0'
  a.uc.mem_write(a.symbols['batch285'],p);write('batch_size285',len(p));write('batch_count285',2)
 cases=[]
 init({1,2,4,5},5);assert a.call('advance342',[])==1 and word('prefixes342')==0 and word('frontier342')==3;cases.append('lower unused slot blocks prefix')
 init(set(range(1,13)),12);assert a.call('advance342',[])==1 and word('frontier342')==9 and word('checks342')==8 and word('prefixes342')==0
 assert a.call('advance342',[])==1 and word('frontier342')==13 and word('prefixes342')==1;cases.append('eight checks per call then safe arbitrary slot12')
 assert word('reserve_bytes293')==10 and word('reserve_plans293')==2 and word('batch_count285')==0;cases.append('original batch capacity reserved')
 before=word('output_size285');assert a.call('advance342',[])==1 and word('output_size285')==before;cases.append('prefix emitted once')
 a.call('stop286',[]);assert a.call('advance342',[])==0 and word('reserve_bytes293')==0 and word('prefixes342')==0;cases.append('STOP cancels frontier and reservations')
 init(set(range(1,6)),5);a.uc.mem_write(a.symbols['input285']+Native.state.offset,b'\x03');assert a.call('advance342',[])==0 and word('output_size285')==0;cases.append('private PREPARED cannot publish')
 init(set(range(1,6)),5);a.uc.mem_write(a.symbols['resident285']+Resident.fault.offset,b'\x01');assert a.call('advance342',[])==0;cases.append('fault cannot publish')
 init({1},1);write('batch_size285',3);write('batch_count285',1);assert a.call('advance342',[])==1 and word('prefixes342')==0;cases.append('clear alone does not start ROM')
 out=dict(passed=True,cases=cases,ELF_sha256=sha(o.source/'output.elf'),input_size=c.sizeof(Native),resident_size=c.sizeof(Resident),scope=__doc__)
 (o.out/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
