"""Linked MAP-progress query replaces receipt-only return; no synthesized ACK.

Independent endpoint injects ready/empty/bad CRC/generation and STOP. Prior
descriptor and last map head are fixture state, not live hardware timing.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_tail717 import Probe
from check_nes_supply485_arm import sha

def check(src,new,case):
 m=Probe(src,case);m.case='normal';m.setup();m.case=case;e=m.endpoint
 m.put(m.w,'nes_sink_window184','wait',0x0807ff91,4)
 for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2),('bank_history',2,1),('bulk_valid',1,1)]:m.put(m.p,'nes_plan200',k,v,n)
 m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],bytes([1,1])+struct.pack('<HHHI',32,0,907,0))
 m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes([2,2])+bytes(8))
 e.jobs=[] if case=='empty' else [(1,32,32,1)]
 ok=m.call('nes_plan200_progress',[m.p,2])
 queried=any(x.startswith('e8') for x in e.calls)
 if new:
  assert bool(ok)==(case in ('normal','empty')),(case,ok,e.calls)
  assert queried==(case!='STOP'),(case,e.calls)
  assert e.bulk==int(case=='normal'),(case,e.bulk)
  assert bool(m.get(m.p,'nes_plan200','bulk_pending'))==(case=='normal')
 else:
  assert not queried and not e.bulk,(case,e.calls)
  assert bool(ok)==(case!='STOP')
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 return dict(case=case,query=queried,bulk=e.bulk,success=bool(ok),final_ACK_required=True)

def fence(src,history,case):
 m=Probe(src,'normal');m.setup();e=m.endpoint
 m.put(m.p,'nes_plan200','bank_history',history,1)
 m.put(m.p,'nes_plan200','early',1,1)
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 m.put(m.s,'nes_native_sink165','map_next',64,1)
 assert m.emit(0,5,4) and not e.accepted
 m.case=case
 if case=='bad_E8_CRC':e.mode=case
 ok=m.call('nes_sink527_early',[m.s,m.video,m.resident,1])
 positive=history!=2 or case=='normal'
 assert bool(ok)==positive,(history,case,ok,e.calls)
 assert e.accepted==int(history==2 and positive),(history,case,e.calls)
 assert not m.get(m.s,'nes_native_sink165','displayed') and not e.rearmed
 return dict(history=history,case=case,accepted_E9=e.accepted,success=bool(ok),no_final_ACK=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();rows={}
 for name,src,new in [('base',a.base,False),('candidate',a.arm,True)]:
  rows[name]=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),cases=[check(src,new,c) for c in ('normal','empty','bad_E8_CRC','wrong_generation','STOP')])
 fences=[fence(a.arm,h,c) for h in (0,1,2) for c in ('normal','STOP','bad_E8_CRC')]
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__,variants=rows,BG_fences=fences),indent=2)+'\n')
 print('PASS720 10 paired MAP-query + 9 cold/warm BG-fence boundaries')
