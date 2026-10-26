# SPDX-License-Identifier: MIT
"""Actual386 adaptive DMA service on unchanged377ARM/375RTL shared schedule.

Includes native range analysis, column gather, job compaction and DMA time.
Warm prior-bank WRAM/VRAM are explicit fixtures; cold prefix remains original.
"""
import json,shutil
import probe_nes_spool384 as previous
from nes_delta231 import BASE,ROOT,sha

previous.NATIVE=BASE/'probes/nes-burst386/native08'
engine=previous.engine;old_prepare=engine.prepare

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0]
 # The service files may change;the cadence/phase/ownership testbench may not.
 assert sha(d/'joint266_tb.sv')==sha(BASE/'probes/nes-spool383/joint04/joint266_tb.sv'),'Use the reference fixed-start/phase/observation options'
 shutil.copyfile(ROOT/'tools/probe_nes_burst387.py',d/'probe_nes_burst387.py')
 (d/'manifest387.json').write_text(json.dumps(dict(native=str(previous.NATIVE),
  native_result=sha(previous.NATIVE/'result.json'),ROM_body_bytes=3290,
  payload_record_WRAM_bytes=24705,DP_extra_live_bytes=30,
  scope=__doc__,RTL_changed=False,ARM_changed=False),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
