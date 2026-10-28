# SPDX-License-Identifier: MIT
"""Actual M4 final-job serializer on71 recorded plans; event endpoint only."""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,plans,crc,u16,u32
from analyze_nes_jobs393 import source_bits
from nes_delta231 import sha,BASE

class Endpoint:
 def __init__(self,serial):self.serial=serial;self.accepted=0;self.packets=[];self.wire=[];self.consumed=0
 def transfer(self,tx):
  r=bytearray(max(14,len(tx)));r[1]=0xfb;r[3:5]=self.accepted.to_bytes(2,'big');r[5:7]=r[3:5];r[7]=1;r[8]=1;r[11:13]=self.consumed.to_bytes(2,'big');last=24 if tx[0]==0xe0 else 13;r[last]=crc(r[1:last],8)
  if tx[0]==0xe1:
   assert crc(tx)==0 and len(tx)==u16(tx,9)+13 and u32(tx,5)==self.serial and u16(tx,3)==len(self.packets)
   self.packets.append(tx[1:-2]);self.wire.append(tx.hex());self.accepted+=1
   if tx[1]in(0x90,0x92):self.consumed+=1
  else:assert tx[0]in(0xe0,0xe2)
  return bytes(r[:len(tx)])

def decode(packets):
 jobs=[];active=None
 for p in packets:
  body=p[10:]
  if p[0]in(0x90,0x91):
   assert p[1]==0 and active is None;r=body[:12];mode=(r[6]>>2)&3;n=u16(r,4)
   j=dict(record=r.hex(),payload='',region=r[9],canonical=u16(r,10),decoded=n,flags=r[6],fragments=[])
   if p[0]==0x91:assert mode==1 and len(body)==12;active=j;continue
   data=body[12:]
   if mode>1:assert len(data)==(4 if mode==3 else 2);data=(data*((n+len(data)-1)//len(data)))[:2 if r[6]&64 else n]
   elif mode==1:assert len(data)==n
   else:assert not data
   j['payload']=data.hex();j['fragments']=[len(data)];jobs.append(j)
  elif p[0]==0x92:
   assert active is not None and u16(body)==len(bytes.fromhex(active['payload']))
   active['payload']+=body[2:].hex();active['fragments'].append(len(body)-2)
   assert len(bytes.fromhex(active['payload']))<=active['decoded']
   if len(bytes.fromhex(active['payload']))==active['decoded']:jobs.append(active);active=None
 assert active is None
 return jobs

def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);oracle,groups=plans();rows=[]
 for serial,pp in groups.items():
  ep=Endpoint(serial);arm=ARM(a.elf,ep)
  # Execute the real refill/progress/credit code. Only the physical transfer
  # itself is replaced by this event endpoint, as in the live RPC harness.
  arm.symbols['io259']=arm.symbols['physical267'];arm.call('reset259',[])
  arm.uc.mem_map(0x40020000,0x1000);arm.uc.mem_write(0x40020410,(256).to_bytes(4,'little'))
  arm.uc.mem_write(arm.symbols['state259'],struct.pack('<4H2I2B',0,0,0,serial,serial,0,(serial-1)&1,0))
  seal=next(p for p in pp if p[0]==3);arm.uc.mem_write(arm.symbols['seal289'],seal)
  expected=(oracle/f'expected-{serial}.bin').read_bytes();bits,required=source_bits(pp,expected)
  certificate=bytes.fromhex((BASE/f'probes/nes-joint284/test04/prelude{serial+904}.hex').read_text())[16:48]
  arm.uc.mem_write(arm.symbols['wire259']+11,certificate)
  assert arm.call('common394',[0xad,5,32])==1
  arm.uc.mem_write(arm.symbols['mapstale247'],bits*2);arm.uc.mem_write(0x2003c000,expected[:4096]);mapped=False
  for command in pp:
   if command[0]==9:
    if not mapped:assert arm.call('jobs_map394',[0x2003c000])==1;mapped=True
    continue
   arm.uc.mem_write(0x2003d000,command)
   try:ok=arm.call('dispatch289',[0x2003d000,len(command)])
   except Exception:
    from unicorn.arm_const import UC_ARM_REG_PC
    print('FAULT',serial,command[:16].hex(),hex(arm.uc.reg_read(UC_ARM_REG_PC)),flush=True);raise
   assert ok==1,(serial,command[:16].hex(),arm.uc.mem_read(arm.symbols['state259'],20).hex())
  # Empty maps still have a final fence/control. No synthetic map job.
  jobs=decode(ep.packets);seen=set()
  for j in jobs:
   if j['region']!=2:continue
   r=bytes.fromhex(j['record']);data=bytes.fromhex(j['payload']);stride=32 if r[8]==0x81 else 1
   for i in range(len(data)//2):
    w=j['canonical']+i*stride;assert w in required and w not in seen;seen.add(w);assert data[2*i:2*i+2]==expected[2*w:2*w+2]
  assert seen==required and ep.packets[-1][0]==0xa3
  f=serial+904;(d/f'jobs{f}.json').write_text(json.dumps(jobs,indent=2)+'\n');(d/f'wire{f}.json').write_text(json.dumps(ep.wire,indent=2)+'\n')
  rows.append(dict(frame=f,jobs=len(jobs),map_jobs=sum(j['region']==2 for j in jobs),wire=sum(len(bytes.fromhex(x))for x in ep.wire),packets=len(ep.packets),instructions=arm.instructions,stack=0x2003f000-arm.low_sp,coverage_exact=True))
 report=dict(passed=True,cases=rows,ELF=sha(a.elf),scope=__doc__);(d/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,frames=len(rows),selected=[r for r in rows if r['frame']in(905,907,908,914,915,962)]),indent=2))
if __name__=='__main__':main()
