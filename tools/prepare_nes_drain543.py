# SPDX-License-Identifier: MIT
"""Test one checked queue drain after map emission, before remaining ordinary data."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once, sha

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    proof=json.loads((root/'analysis/windows541-verification.json').read_text())
    assert sha(a.arm/'obj-nes-100/firmware.stm')==proof['firmware_SHA256']
    name='nes_native_sink165.c'
    s=(a.arm/name).read_text()
    s=once(s,'#include "nes_plan_service200.h"', '#include "nes_plan_service200.h"\n#include "nes_sink_window184.h"')
    s=once(s,' if(!map527(s,p,r->map_upload,false))return false;', ''' if(!map527(s,p,r->map_upload,false))return false;
 /* Use the existing checked retirement/STOP/deadline path. Do not issue a
  * new packet until the already emitted map is consumed. This is NOT a DMA
  * completion promise: the inactive-bank consumer still arbitrates a new
  * head and STOP immediately before each actual DMA. */
 if(r->map_upload && s->plan){
  uint8_t retired_ack[12];
  if(!nes_window184_drain(s->plan->window,retired_ack))return fail(s,2);
 }''')
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/name).write_text(s,encoding='utf8',newline='\n')
