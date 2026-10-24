# SPDX-License-Identifier: MIT
"""Actual Cortex-M4 guards for one complete BG run; SPI tested separately."""
import argparse,ctypes as c,json
from pathlib import Path
from check_nes_frontier342 import A,Native,Resident
from nes_delta231 import sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);o=ap.parse_args();o.out.mkdir(parents=True,exist_ok=False)
 a=A(o.source/'output.elf',None)
 assert a.call('layout285',[3])==c.sizeof(Native) and a.call('layout285',[5])==c.sizeof(Resident)
 def put(n,v):a.uc.mem_write(a.symbols[n],v.to_bytes(4,'little'))
 def get(n):return int.from_bytes(a.uc.mem_read(a.symbols[n],4),'little')
 def init(slots):
  a.call('reset285',[]);a.uc.mem_write(a.symbols['input285']+Native.generation.offset,b'\x03\0');assert a.call('begin285',[])==1
  a.uc.mem_write(a.symbols['input285']+Native.state.offset,b'\x04');a.uc.mem_write(a.symbols['resident285']+Resident.serial.offset,(3).to_bytes(4,'little'))
  bits=bytearray(144)
  for x in slots:bits[x//8]|=1<<(x%8)
  a.uc.mem_write(a.symbols['resident285']+Resident.used.offset,bytes(bits))
  b=b'\x82\x03\0'+b''.join(b'\x80\x03\0'+x.to_bytes(2,'little')+b'\x07\0' for x in slots)
  a.uc.mem_write(a.symbols['batch285'],b);put('batch_size285',len(b));put('batch_count285',len(slots)+1)
 cases=[]
 init([82,83,84]);assert a.call('advance344',[])==1 and get('prefixes344')==1 and get('run_first344')==82 and get('run_last344')==84;cases.append('unused lower slots do not block complete disjoint run')
 assert get('reserve_bytes293')==24 and get('reserve_plans293')==4;cases.append('original batch capacity reserved')
 n=get('output_size285');assert a.call('advance344',[])==1 and get('output_size285')==n;cases.append('one prefix per frame')
 a.call('stop286',[]);assert a.call('advance344',[])==0 and get('prefixes344')==0 and get('reserve_bytes293')==0;cases.append('STOP clears run and reservation')
 init([82,84]);assert a.call('advance344',[])==1 and get('prefixes344')==0;cases.append('no speculative gap fill')
 init([82,83,90]);assert a.call('advance344',[])==1 and get('run_last344')==83 and get('batch_count285')==1;cases.append('preserve later noncontiguous run')
 init([82,83]);a.uc.mem_write(a.symbols['resident285']+Resident.used.offset,bytes(144));assert a.call('advance344',[])==0;cases.append('unowned slot rejected')
 init([82,83]);a.uc.mem_write(a.symbols['input285']+Native.state.offset,b'\x03');assert a.call('advance344',[])==0 and get('output_size285')==0;cases.append('COMMIT barrier')
 init([82,83]);a.uc.mem_write(a.symbols['resident285']+Resident.fault.offset,b'\x01');assert a.call('advance344',[])==0;cases.append('fault blocks publication')
 init([82,83]);a.uc.mem_write(a.symbols['resident285']+Resident.serial.offset,(2).to_bytes(4,'little'));assert a.call('advance344',[])==1 and get('prefixes344')==0;cases.append('cold bank initialization unchanged')
 r=dict(passed=True,cases=cases,ELF_sha256=sha(o.source/'output.elf'),scope=__doc__);(o.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
