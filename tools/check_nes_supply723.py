"""Linked723 warm row callback and independent CRC8 guards.

Row completion is explicitly invoked in this boundary fixture; the unchanged
planner's real row traversal is exercised by the two-phase replay.
"""
import argparse,json,struct,random
from pathlib import Path
from check_nes_tail717 import Probe
from check_nes_supply485_arm import ELFFile,crc,sha
from test_nes_raw506_joint import member_offset

class Row(Probe):
 def __init__(self,src,case):
  super().__init__(src,case)
  with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
   elf=ELFFile(f)
   for cu in elf.get_dwarf_info().iter_CUs():
    for d in cu.iter_DIEs():
     if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and d.attributes.get('DW_AT_byte_size'):
      self.layout['nes_native_runtime165']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}}
  self.rt=0x20003000;k=self.layout['nes_native_runtime165'];self.p=self.rt+k['plan'];self.w=self.rt+k['transport'];self.s=self.rt+k['sink']
  self.setup()
  for n,v in [('resident',self.resident),('video',self.video),('ticks',self.guard485|1)]:self.put(self.rt,'nes_native_runtime165',n,v,4)

def row(src,history,case):
 m=Row(src,'normal');e=m.endpoint
 m.put(m.p,'nes_plan200','bank_history',history,1);m.put(m.p,'nes_plan200','early',1,1)
 m.put(m.p,'nes_plan200','sent',2,2);e.accepted=2
 q=struct.pack('<HHHBB',907,5,4,0,255)+bytes(i//2 for i in range(16))+b'\xff'*16;m.u.mem_write(m.q,q)
 assert m.call('resident_plan213',[m.rt,0,m.q])
 armed=m.get(m.resident,'nes_resident211','finish_bg_row',4)
 assert bool(armed)==(history==2)
 assert m.get(m.resident,'nes_resident211','first_bg_rows')==(1 if history==2 else 3)
 assert e.accepted==2
 if history==2:
  m.case=case
  if case=='bad_E8_CRC':e.mode=case
  ok=m.call('finish_bg549',[m.rt])
  assert bool(ok)==(case=='normal'),(case,ok,e.calls)
  assert e.accepted==2+int(case=='normal')
  assert not m.get(m.resident,'nes_resident211','finish_bg_row',4)
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(history=history,case=case,armed=bool(armed),E9=e.accepted,passed=True)

def pair(src,case):
 m=Row(src,'normal');e=m.endpoint
 for n,v,w in [('bank_history',2,1),('early',1,1),('sent',1,2)]:m.put(m.p,'nes_plan200',n,v,w)
 e.accepted=1
 for i in range(2):
  q=struct.pack('<HHHBB',907,5+i,4+i,0,255)+bytes(j//2 for j in range(16))+b'\xff'*16
  m.u.mem_write(m.q,q)
  if i:
   m.case=case
   if case=='bad_E8_CRC':e.mode=case
  ok=m.call('resident_plan213',[m.rt,0,m.q])
  if not i:
   assert ok and e.accepted==1
   assert not m.get(m.resident,'nes_resident211','finish_bg_row',4)
  else:
   assert bool(ok)==(case=='normal'),(case,ok,e.calls)
   assert e.accepted==1+int(case=='normal')
 if case=='normal':
  assert m.get(m.resident,'nes_resident211','finish_bg_row',4)
  assert m.call('finish_bg549',[m.rt]) and e.accepted==2
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(case=case,E9=e.accepted,passed=True)

def offer(src,history,early,final):
 m=Row(src,'normal');m.put(m.p,'nes_plan200','bank_history',history,1);m.put(m.p,'nes_plan200','early',early,1)
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 # This boundary fixture has no changed rows; cold reset otherwise marks
 # both maps stale and asks the bulk-only endpoint to accept map payloads.
 m.u.mem_write(m.resident+m.layout['nes_resident211']['map_stale'],bytes(16))
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map_dirty'],bytes(8))
 assert m.call('offer527',[m.rt,final])
 queried=any(x.startswith('e8') for x in m.endpoint.calls)
 assert queried==(not final and not(history==2 and early)),(history,early,final,m.endpoint.calls)
 assert not m.endpoint.bulk and not m.get(m.s,'nes_native_sink165','displayed')
 return dict(history=history,fresh_BG=early,final=final,E8=queried,passed=True)

def status(src,case):
 m=Row(src,'normal');last=bytes((2,2))+struct.pack('<HIH',1,1,907)
 for n,v,w in [('sent',1,2),('retired',0,2),('ever_sent',1,1),('wait',0,4)]:m.put(m.w,'nes_sink_window184',n,v,w)
 m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
 def exchange(tx,clock):
  assert tx[0]==0xe0;m.endpoint.calls.append(tx.hex())
  r=bytearray(20);r[1:3]=bytes((0xf7,{'live':11,'reserved':26,'no_ACK':8}.get(case,10)))
  r[3:7]=struct.pack('>HH',1,1);r[7:19]=bytes((0,2))+last[2:]+bytes((0x65,0x9a))
  if case=='identity':r[10]^=1
  if case=='credit':r[6]=2
  if case=='fake_final':r[7]=1
  r[19]=crc(r[1:19],8,7,0)^(case=='CRC')
  return bytes(r)
 m.endpoint.exchange=exchange;m.case=case
 ok=m.call('nes_window184_through',[m.w,0x20012000,1])
 assert bool(ok)==(case=='normal'),(case,ok,m.endpoint.calls)
 assert not m.get(m.s,'nes_native_sink165','displayed')
 return dict(case=case,accepted=bool(ok),passed=True)

def run(a):
 rows=[row(a.arm,h,c) for h in (0,1,2) for c in ('normal','STOP','bad_E8_CRC')]
 pairs=[pair(a.arm,c) for c in ('normal','STOP','bad_E8_CRC')]
 offers=[offer(a.arm,h,e,f) for h in (0,1,2) for e in (0,1) for f in (0,1)]
 statuses=[status(a.arm,c) for c in ('normal','live','reserved','no_ACK','identity','credit','fake_final','CRC','STOP')]
 m=Row(a.arm,'normal');rng=random.Random(723);counts=[]
 for n in range(247):
  b=bytes(rng.randrange(256) for _ in range(n));m.u.mem_write(0x20012000,b or b'\0')
  count=m.instructions;got=m.call('nes_wire723_crc8',[0x20012000,n]);assert got==crc(b,8,7,0)
  counts.append(m.instructions-count)
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows,pairs=pairs,offers=offers,E0=statuses,CRC8_lengths=247,CRC8_instruction_counts=counts),indent=2)+'\n')
 print('PASS723 9 row/cold/STOP/CRC +3 first-pair +12 map-offer +9 E0 boundaries +247 CRC8 lengths')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
