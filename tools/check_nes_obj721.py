"""721 linked producer query only, paired against719; no new BG flush."""
import argparse,json
from pathlib import Path
from check_nes_supply720 import check
from nes_raw506 import sha

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r={}
 for label,src,new in [('previous',a.base,False),('candidate',a.arm,True)]:
  r[label]=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),cases=[check(src,new,c) for c in ('normal','empty','bad_E8_CRC','wrong_generation','STOP')])
 for n in ('nes_planner211.c','nes_native_sink165.c','nes_native_sink165.h','nes_native_runtime165.c','nes_sink_window184.c'):
  assert sha(a.base/n)==sha(a.arm/n),n
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__+' Independent endpoint delayed receipts; no modeled final display ACK.',variants=r),indent=2)+'\n')
 print('PASS721 10 paired query/CRC/identity/STOP/final ACK guards;719 map/planner identical')
