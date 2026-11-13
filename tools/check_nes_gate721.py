"""721D checked DMA notice gating and merged token boundary, linked M4.

The initial notice/identity is injected; unchanged678 separately verifies its
CRC/identity publication. No fixture notice authorizes DMA or final display.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_tail717 import Probe
from nes_raw506 import sha

def check(src,case):
 m=Probe(src,case);m.case='normal';m.setup();m.case=case;e=m.endpoint
 m.put(m.w,'nes_sink_window184','wait',0x0807ff91,4)
 oldtoken=2 if case=='old_token' else 1
 newtoken=1 if case in ('old_token','mutated_token','repeat') else 2
 d=bytes([1,1])+struct.pack('<HHHI',32,0,907,oldtoken)
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2),('bank_history',2,1),('bulk_valid',1,1)]:m.put(m.p,'nes_plan200',k,v,n)
 m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],d)
 m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes([2,2])+bytes(8))
 m.put(m.w,'nes_sink_window184','status_flags',2 if case=='no_notice' else 10,1)
 if case=='stale_after_E1':m.put(m.w,'nes_sink_window184','sent',1,2)
 e.jobs=[] if case in ('empty','repeat') else [(1,32,32,newtoken)]
 if case=='repeat':e.stale=d;e.stale_reads=2
 ok=m.call('nes_plan200_progress',[m.p,2]);positive=case in ('normal','empty','repeat','no_notice','stale_after_E1')
 assert bool(ok)==positive,(case,ok,e.calls[-3:])
 queried=any(x.startswith('e8') for x in e.calls)
 assert queried==(case not in ('STOP','no_notice','stale_after_E1')),(case,e.calls)
 assert e.bulk==int(case=='normal'),(case,e.bulk)
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(case=case,query=queried,bulk=e.bulk,passed=True,final_ACK_required=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();cases=('normal','no_notice','stale_after_E1','empty','repeat','old_token','mutated_token','bad_E8_CRC','wrong_generation','STOP')
 rows=[check(a.arm,c) for c in cases]
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows),indent=2)+'\n');print('PASS721D',len(rows),'notice/stale/token/CRC/STOP/final-ACK guards')
