"""Recreate pre-frame bank histories with the frozen ARM planner; save data only for the two dense inputs."""
import argparse
import re
import struct
from pathlib import Path

from check_nes_game478 import Machine
from check_nes_wire600 import ROOT, pin, read
from nes_transfer512 import legacy_packets


def main(a):
    p=read(ROOT/'analysis/body581-verification.json')['inputs']
    pin(a.arm/'obj-nes-100/firmware.stm',read(ROOT/'analysis/trial577-package.json')['firmware_SHA256'])
    table=re.search(r'\{(.+?)\}',(a.arm/'nes_palette165.inc').read_text())[1]
    lut=struct.pack('<64H',*map(int,table.split(',')))
    m=Machine(a.arm,lut);a.out.mkdir(parents=True,exist_ok=False)
    for g in range(905,954):
        geom,raw=[a.data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
        for f in (geom,raw):pin(f,p[f.name])
        geom,raw=geom.read_bytes(),raw.read_bytes()
        r=m.frame(legacy_packets(geom,raw,g)[0],geom,raw,g,g-904)
        if g+1 in (952,954):
            for k,typ in [('video','nes_native_video165'),('resident','nes_resident211')]:
                (a.out/f'{g+1}-{k}.bin').write_bytes(m.u.mem_read(getattr(m,k),m.layout[typ]['size']))
            print(g,'committed',r['bank'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','data','out'):p.add_argument('--'+k,required=True,type=Path)
    main(p.parse_args())
