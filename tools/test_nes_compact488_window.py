# SPDX-License-Identifier: MIT
"""Replay real serializer packets through linked M4 window CRC16/CRC8/credit/barrier.

Immediate modeled retirement isolates CPU transport work. It is not ARM cycles,
SPI/IRQ/ROM waiting, or an independently executed SNES final display ACK.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha
class Endpoint:
 def __init__(self):self.mode='normal';self.sent=0;self.last=bytes(12);self.calls=[]
 def exchange(self,tx,clock):
  self.calls.append(tx)
  if tx[0]==0xe1:
   assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big');b=tx[1:-2]
   assert 16<=len(b)<=256 and len(b)==16+int.from_bytes(b[12:14],'little')
   self.sent+=1;self.last=bytes([int(b[0]==3),b[0]])+b[2:10]+b'\x65\x9a';return bytes(len(tx))
  assert tx[0]==0xe0
  r=bytearray(20);r[1]=0xf7;r[2]=2 if self.sent else 0;r[3:7]=struct.pack('>HH',self.sent,self.sent);r[7:19]=self.last;r[19]=crc(r[1:19],8,7,0);return bytes(r)
p=argparse.ArgumentParser(description=__doc__)
for n in ['baseline_arm','compact_arm','baseline','compact','out']:p.add_argument('--'+n.replace('_','-'),type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);rows=[]
for compact in [False,True]:
 arm=a.compact_arm if compact else a.baseline_arm;root=a.compact if compact else a.baseline
 m=ARM(arm,'normal')
 for frame in [905,906,911,916,970,975]:
  m.endpoint=Endpoint();m.setup();before=m.instructions;packets=sorted((root/f'frame{frame}').glob('packet*.bin'))
  for f in packets:
   b=f.read_bytes();m.u.mem_write(m.q,b)
   fn='nes_window184_barrier'if b[0]==3 else'nes_window184_enqueue'
   assert m.call(fn,[m.w,m.q,len(b),m.q+256])==1
  e=m.endpoint;assert e.sent==len(packets) and m.get(m.w,'nes_sink_window184','error')==0
  rows.append({'compact':compact,'frame':frame,'M4_window_instructions':m.instructions-before,'E1_wire_B':sum(len(tx)for tx in e.calls if tx[0]==0xe1),'E0_calls':sum(tx[0]==0xe0 for tx in e.calls),'SPI_B':sum(map(len,e.calls))})
r={'passed':True,'scope':__doc__,'baseline_firmware_SHA256':sha(a.baseline_arm/'obj-nes-100/firmware.stm'),'compact_firmware_SHA256':sha(a.compact_arm/'obj-nes-100/firmware.stm'),'rows':rows,'physical':False}
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(r))
