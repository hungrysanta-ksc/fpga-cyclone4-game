"""Linked718 READ/POP, real E0 CRC/identity and useful-work DMA progress bound.

Endpoint controls availability and DMA bit, not a physical timing proof.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_receive682 import Burst
from check_nes_game478 import ELFFile,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from test_nes_raw506_joint import member_offset
from check_nes_dma637 import QuietProbe

class Probe(Burst):
 def __init__(self,src,mode):
  self.mode=mode;self.e0=0
  super().__init__(src,mode)
  if mode in ('STOP_before','STOP_after_READ','bad_CRC','bad_retire','failed_IO'):self.case=mode
  with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
   for cu in ELFFile(f).get_dwarf_info().iter_CUs():
    for d in cu.iter_DIEs():
     if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_sink_window184' and d.attributes.get('DW_AT_byte_size'):
      self.layout['nes_sink_window184']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}}
  self.w=self.rt+self.layout['nes_native_runtime165']['transport']
  k='nes_sink_window184'
  for n,v,b in [('transfer',self.spi|1,4),('guard',self.check|1,4),('ctx',self.rt,4),('wait',self.syms['wait634']|1,4),('poll_limit',4,4),('initialized',1,1),('ever_sent',1,1),('sent',1,2),('retired',1,2)]:self.put(self.w,k,n,v,b)
  self.head=bytes([2,2,55,0,48,0,0,0,0xb8,3]);self.u.mem_write(self.w+self.layout[k]['last'],self.head)
  if mode=='empty':self.packets=[]
  if mode=='complete':self.put(self.state,'nes_native165','state',2,1)
  if mode=='exhausted':
   self.put(self.state,'nes_native165','state',1,1);self.put(self.rt,'nes_native_runtime165','prefetch_left',0,1)
 def hook(self,u,at,size,user):
  if at==self.check and self.mode=='STOP_after_E0' and self.e0:
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if at==self.spi and u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]==0xe0:
   self.e0+=1;self.ops.append(0xe0);r=bytearray(20);r[1]=0xf7
   progress=self.mode in ('progress1','progress3') and self.index>=(1 if self.mode=='progress1' else 3)
   r[2]=2|(8 if progress else 0);r[4]=r[6]=1
   r[7:19]=bytes([0,self.head[0]])+self.head[2:]+b'\x65\x9a'
   if self.mode=='wrong_identity':r[10]^=1
   if self.mode=='future_retire':r[6]=2
   if self.mode=='fault':r[2]|=0x80
   if self.mode=='live_progress':r[2]=11;r[6]=0
   r[19]=crc(r[1:19],8,7,0)^(self.mode=='E0_CRC')
   u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(r));u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,at,size,user)

def caller(src,case):
 m=QuietProbe(src,'normal');m.heads=[];m.test_sink=sink=0x20015800
 plan,window=0x20016300,0x20016b00
 m.samples=m.drains=0;m.reasons=[];m.stop_at=int(case=='STOP');m.bad_drain=int(case=='bad_credit');m.reject_final=case=='bad_final'
 m.u.mem_write(m.data_symbols['nes_cost471_available'],bytes(4))
 for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',45|(46<<32),8)]:m.put(sink,'nes_native_sink165',k,v,n)
 for k,v,n in [('window',window,4),('guard',m.guard|1,4),('bank_history',0 if case=='cold' else 2,1)]:m.put(plan,'nes_plan200',k,v,n)
 m.put(window,'nes_sink_window184','wait',m.guard|1,4)
 m.put(window,'nes_sink_window184','status_flags',10 if case=='DMA_done' else 2,1)
 m.u.mem_write(window+m.layout['nes_sink_window184']['last'],bytes([7,1] if case=='last_tile' else [2,2])+bytes(8))
 for k,v,n in [('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),('target',1,1)]:m.put(m.resident,'nes_resident211',k,v,n)
 for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)]:m.put(m.video,'nes_native_video165',k,v,n)
 ok=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192])
 assert bool(ok)==(case not in ('STOP','bad_credit','bad_final')),(case,ok)
 assert m.drains==int(case not in ('cold','last_tile')),(case,m.drains)
 assert m.reasons==([] if case in ('cold','last_tile','DMA_done','bad_credit') else [4]),(case,m.reasons)
 assert any(h[0]==3 for h in m.heads)==(case not in ('STOP','bad_credit'))
 assert m.get(sink,'nes_native_sink165','ack635',8)==(45|((48 if ok else 46)<<32))
 return dict(case=case,committed=bool(ok),drains=m.drains,input_reasons=m.reasons,scope='Actual seal eligibility and final identity; endpoint and DMA retirement callbacks injected')

def run(src):
 rows=[]
 cases={'cap7':(True,7,7),'empty_after3':(True,3,3),'progress1':(True,1,1),'progress3':(True,3,3),
 'empty':(True,0,0),'complete':(True,0,0),'exhausted':(True,0,0),'STOP_after3':(False,3,2),
 'CRC_third':(False,2,2),'cache_CRC':(False,1,1),'cache_token':(False,1,1),
 'STOP_after_E0':(False,1,1),'wrong_identity':(False,1,1),'future_retire':(False,1,1),
 'fault':(False,1,1),'live_progress':(False,1,1),'E0_CRC':(False,1,1),
 'STOP_before':(False,0,0),'STOP_after_READ':(False,0,0),'bad_CRC':(False,0,0),
 'bad_retire':(False,1,0),'failed_IO':(False,0,0)}
 for mode,expected in cases.items():
  m=Probe(src,mode);ok=m.call('wait634',[m.rt,m.check|1,4,0])
  assert (bool(ok),m.index,m.e0)==expected,(mode,ok,m.index,m.e0,m.ops)
  assert not any(op in (0xd3,0xe1,0xea) for op in m.ops)
  assert m.index<=7
  rows.append(dict(case=mode,success=bool(ok),checked_blocks=m.index,E0=m.e0,operations=m.ops,
   remaining=m.get(m.rt,'nes_native_runtime165','prefetch_left'),new_COMMIT_or_final_ACK=False))
 return dict(passed=True,firmware=sha(src/'obj-nes-100/firmware.stm'),scope=__doc__,cases=rows,
  callers=[caller(src,c) for c in ('normal','DMA_done','cold','last_tile','STOP','bad_credit','bad_final')])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=run(a.arm);a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS718',len(r['cases']),'input / checked DMA progress / STOP guards')
