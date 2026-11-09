"""Linked718B ordinary admission: DMA event, empty input, STOP and bounded fault.

Inject drain/next-input endpoints; real seal range, packet and final ACK code.
"""
import argparse,json
from pathlib import Path
from check_nes_dma637 import QuietProbe
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR,sha

class Progress(QuietProbe):
 def hook(self,u,at,size,user):
  if at==self.syms.get('nes_window184_drain') and hasattr(self,'window718'):
   if self.mode718 not in ('no_event','STOP') and self.drains>=2:
    self.put(self.window718,'nes_sink_window184','status_flags',10,1)
  super().hook(u,at,size,user)

def check(src,case):
 m=Progress(src,'normal');m.mode718=case;m.heads=[];m.test_sink=sink=0x20015800
 plan,window=0x20016300,0x20016b00;m.window718=window
 m.samples=m.drains=0;m.reasons=[];m.stop_at=2 if case=='STOP' else 0;m.bad_drain=int(case=='bad_credit');m.reject_final=case=='bad_final'
 m.u.mem_write(m.data_symbols['nes_cost471_available'],bytes(4))
 for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',45|(46<<32),8)]:m.put(sink,'nes_native_sink165',k,v,n)
 for k,v,n in [('window',window,4),('guard',m.guard|1,4),('bank_history',0 if case=='cold' else 2,1)]:m.put(plan,'nes_plan200',k,v,n)
 m.put(window,'nes_sink_window184','wait',0 if case=='no_callback' else m.guard|1,4)
 m.put(window,'nes_sink_window184','poll_limit',4,4)
 m.put(window,'nes_sink_window184','status_flags',10 if case=='DMA_done' else 2,1)
 m.u.mem_write(window+m.layout['nes_sink_window184']['last'],bytes([7,1] if case=='last_tile' else [2,2])+bytes(8))
 for k,v,n in [('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),('target',1,1)]:m.put(m.resident,'nes_resident211',k,v,n)
 for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)]:m.put(m.video,'nes_native_video165',k,v,n)
 ok=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192])
 positive=case in ('normal','DMA_done','cold','last_tile')
 assert bool(ok)==positive,(case,ok,m.drains,m.samples)
 expected={'normal':(3,2),'DMA_done':(1,0),'cold':(0,0),'last_tile':(0,0),'STOP':(2,2),
  'bad_credit':(1,0),'bad_final':(3,2),'no_event':(5,4),'no_callback':(1,0)}[case]
 assert (m.drains,m.samples)==expected,(case,m.drains,m.samples)
 assert m.reasons==[4]*m.samples
 assert any(h[0]==3 for h in m.heads)==(positive or case=='bad_final')
 assert m.get(sink,'nes_native_sink165','ack635',8)==(45|((48 if ok else 46)<<32))
 return dict(case=case,committed=bool(ok),drains=m.drains,input_reasons=m.reasons,history_only_after_final_ACK=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),
  cases=[check(a.arm,c) for c in ('normal','DMA_done','cold','last_tile','STOP','bad_credit','bad_final','no_event','no_callback')])
 a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS718B nine map DMA / empty work / STOP / final ACK boundaries')
