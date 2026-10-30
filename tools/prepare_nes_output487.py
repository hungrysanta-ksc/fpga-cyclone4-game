# SPDX-License-Identifier: MIT
"""Bound a threshold-only RLE search without changing packets or ownership."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import sha

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    assert sha(a.arm/'obj-nes-100/firmware.stm')=='eec710fab1c045ff00ade979dfbfd21dc9c3a19ca391b14b7cca79153a8e0c05'
    a.out.mkdir(parents=True,exist_ok=False);patch=a.out/'patch';patch.mkdir()
    src=a.arm/'nes_native_sink165.c';s=src.read_text(encoding='utf8')
    old='for(unsigned i=1;i<end;i++)if(repeat_bytes(b+i,n-i)>=64)return i;'
    new='for(unsigned i=1;i<end&&i+64<=n;i++)if(repeat_bytes(b+i,64)==64)return i;'
    assert s.count(old)==1
    (patch/src.name).write_text(s.replace(old,new),encoding='utf8',newline='\n')
    r={'scope':__doc__,'baseline_firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),
       'baseline_source_SHA256':sha(src),'patch_source_SHA256':sha(patch/src.name),
       'ABI_changed':False,'new_state_B':0,'new_payload_buffer_B':0,'FPGA_changed':False,
       'hardware_ready':False,'new_package':False}
    (a.out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print(json.dumps(r))
