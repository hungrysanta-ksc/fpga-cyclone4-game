# SPDX-License-Identifier: MIT
"""Give the existing section-5 cost selector both consecutive mode tables."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    assert sha(a.arm/'obj-nes-100/firmware.stm')=='e78d1180d515213df092a15188b27e1874d91c7c4bc100afe5930d94697c22c1'
    a.out.mkdir(parents=True,exist_ok=False)
    name='nes_native_sink165.c'
    source=once((a.arm/name).read_text(),'''const uint8_t *parts[4]={raw,p->patch.mode[0],p->patch.mode[1],p->patch.enable};
  const unsigned lengths[4]={packed,81,81,81};
  for(unsigned part=0;part<4;part++){''','''const uint8_t *parts[3]={raw,(const uint8_t *)&p->patch.mode,p->patch.enable};
  const unsigned lengths[3]={packed,sizeof p->patch.mode,sizeof p->patch.enable};
  for(unsigned part=0;part<3;part++){''')
    (a.out/name).write_text(source,newline='\n')
