"""Actual linked726 BG-complete map admission, separate credit/receipt/final ACK.

The fixture supplies immutable map and validated planner state. Production
row traversal, IRQ, SPI and ROM timing are verified in the full replay.
"""
import argparse,json
from pathlib import Path
from check_nes_supply723 import Row,row,pair,status
from check_nes_rows713 import Peer
from nes_raw506 import sha

def exercise(src,case,paired=False):
 m=Row(src,'normal');e=m.endpoint=Peer('normal');m.case=case
 history=0 if case=='cold' else 1 if case=='recover' else 2
 m.put(m.p,'nes_plan200','bank_history',history,1);m.put(m.p,'nes_plan200','early',1,1)
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 m.put(m.resident,'nes_resident211','target',0,1)
 mask=(1<<64)-1 if case=='cold' else 0x3f
 if case=='sparse':mask=(1<<5)|(1<<7)|(1<<32)
 if case=='empty':mask=0
 m.u.mem_write(m.resident+m.layout['nes_resident211']['map_stale'],mask.to_bytes(8,'little')+bytes(8))
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map_dirty'],bytes(8))
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 if case in ('three_credits','wrap_credit'):
  m.put(m.w,'nes_sink_window184','sent',1 if case=='wrap_credit' else 3,2)
  m.put(m.w,'nes_sink_window184','retired',65534 if case=='wrap_credit' else 0,2)
 if case in ('ready_tile','wrong_generation'):e.jobs=[(0,16,16,1)]
 if case in ('bad_E8_CRC','wrong_generation','ambiguous_E1'):e.mode=case
 if case=='STOP_after_map':
  exchange=e.exchange
  def stop_after(tx,clock):
   reply=exchange(tx,clock)
   if tx[0]==0xe1 and tx[2]==2:m.case='STOP'
   return reply
  e.exchange=stop_after
 before=m.instructions;ok=m.call('offer527',[m.rt,0 if case=='in_row' else 1])
 positive=case not in ('STOP','STOP_after_map','bad_E8_CRC','wrong_generation','ambiguous_E1')
 assert bool(ok)==positive,(case,ok,e.calls)
 maps_expected=[(320,64)] if case=='sparse' else [(0,192),(192,192)] if paired and case=='normal' else [(0,192)] if case in ('normal','ambiguous_E1','STOP_after_map') else []
 assert e.maps==maps_expected,(case,e.maps,e.calls)
 if e.maps:assert m.get(m.s,'nes_native_sink165','map_next')==(6 if case=='sparse' or paired and case=='normal' else 3) or not ok
 if case=='ready_tile':assert e.bulk==1 and m.get(m.p,'nes_plan200','bulk_pending')
 assert not m.get(m.s,'nes_native_sink165','displayed')
 assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 if not ok:
  calls=len(e.calls);assert not m.call('offer527',[m.rt,1]) and len(e.calls)==calls
 m.call('nes_sink165_reset',[m.s,m.syms['nes_window184_barrier']|1,m.w])
 assert not m.get(m.s,'nes_native_sink165','map_next') and not m.get(m.s,'nes_native_sink165','displayed')
 return dict(case=case,passed=True,maps=e.maps,instructions=m.instructions-before,operations=[int(x[:2],16) for x in e.calls])

def run(a):
 cases=('normal','empty','sparse','cold','recover','in_row','three_credits','wrap_credit','ready_tile','STOP','bad_E8_CRC','wrong_generation','ambiguous_E1')
 if a.paired:cases+=('STOP_after_map',)
 result=dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),
  admission=[exercise(a.arm,c,a.paired) for c in cases],
  rows=[row(a.arm,h,c) for h in (0,1,2) for c in ('normal','STOP','bad_E8_CRC')],
  pairs=[pair(a.arm,c) for c in ('normal','STOP','bad_E8_CRC')],
  status=[status(a.arm,c) for c in ('normal','live','reserved','no_ACK','identity','credit','fake_final','CRC','STOP')])
 a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS726',len(cases),'admission +9 row +3 initial pair +9 checked status boundaries')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--paired',action='store_true')
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
