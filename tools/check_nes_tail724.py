"""Execute linked seal ordering/history with modeled producer and queue endpoints.

Producer ready/empty/fault is injected; real poll CRC/identity/STOP guards are
run separately. Raw compaction is checked independently before map service.
Full linked ARM/65816 replay is required for timing and map DMA guarantees.
"""
import argparse,json
from pathlib import Path
from check_nes_deadline719 import Deadline
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_raw506 import sha

class Tail(Deadline):
 def hook(self,u,at,size,user):
  for name in ('map527','nes_plan200_progress','packet_wire'):
   if at==self.syms.get(name):
    self.order.append(name)
    if name=='map527' and self.expected:
     out=self.video+self.layout['nes_native_video165']['bg_keys']+4096
     assert bytes(u.mem_read(out,len(self.expected)))==self.expected
    if name=='nes_plan200_progress' and self.case724!='cold' and 'packet_wire' not in self.order:
     if self.case724=='ready':
      u.mem_write(self.window719+self.layout['nes_sink_window184']['last'],bytes([7,1])+bytes(8))
     if self.case724=='producer_fault':
      u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,at,size,user)

def check(src,case,patch):
 m=Tail(src,'normal');m.case724=case;m.order=[];m.expected=b''
 m.clock719=10000000;m.event719=True;m.heads=[];m.test_sink=sink=0x20015800;plan=0x20016300;window=m.window719=0x20016b00
 stamp=m.clock719-(2795400-200000);m.samples=m.drains=0;m.reasons=[]
 m.stop_at=int(case=='STOP');m.bad_drain=int(case=='bad_credit');m.reject_final=case=='bad_final'
 m.u.mem_write(m.data_symbols['nes_cost471_available'],(1).to_bytes(4,'little'))
 for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',45|(46<<32),8),('ack_clock719',stamp,4)]:m.put(sink,'nes_native_sink165',k,v,n)
 for k,v,n in [('window',window,4),('guard',m.guard|1,4),('bank_history',0 if case=='cold' else 2,1)]:m.put(plan,'nes_plan200',k,v,n)
 for k,v,n in [('wait',m.guard|1,4),('poll_limit',65536,4),('status_flags',2,1)]:m.put(window,'nes_sink_window184',k,v,n)
 m.u.mem_write(window+m.layout['nes_sink_window184']['last'],bytes([2,2])+bytes(8))
 for k,v,n in [('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),('target',1,1)]:m.put(m.resident,'nes_resident211',k,v,n)
 for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1),('patch_count',patch,1)]:m.put(m.video,'nes_native_video165',k,v,n)
 if patch:
  raw=bytes((i*17+i//64)&255 for i in range(2048));at=m.video+m.layout['nes_native_video165']['patch']
  m.u.mem_write(at,raw+bytes(244)+b'\x01\0'*3)
  m.expected=bytes(raw[t*64+p*16+r*2+b] for p in range(3) for r in range(patch) for t in range(32) for b in range(2))
 ok=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192]);positive=case in ('ready','empty','cold')
 assert bool(ok)==positive,(case,patch,ok,m.order)
 assert m.order[0]=='map527'
 if case=='cold':assert m.order[1]=='packet_wire'
 else:assert m.order[1]=='nes_plan200_progress'
 if case=='ready':assert m.drains==m.samples==0
 if case=='empty':assert (m.drains,m.samples)==(3,2)
 if case=='producer_fault':assert not m.heads and not m.drains
 assert m.get(sink,'nes_native_sink165','ack635',8)==45|((48 if ok else 46)<<32)
 assert (m.get(sink,'nes_native_sink165','ack_clock719',4)!=stamp)==bool(ok)
 m.call('nes_sink165_reset',[sink,m.callback|1,0]);assert not m.get(sink,'nes_native_sink165','ack635',8)
 return dict(case=case,patch_rows=patch,drains=m.drains,input_callbacks=m.samples,final_ack=bool(ok),passed=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();cases=[check(a.arm,c,0) for c in ('ready','empty','cold','producer_fault','STOP','bad_credit','bad_final')]+[check(a.arm,c,n) for c in ('ready','producer_fault') for n in (1,2)]
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=cases),indent=2)+'\n');print('PASS724',len(cases),'ordering/compaction/fault/ACK/reset boundaries')
