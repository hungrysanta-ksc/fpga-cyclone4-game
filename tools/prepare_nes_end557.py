# SPDX-License-Identifier: MIT
"""Offer one extra checked E8 before backing off when END has exclusive use of SPI."""
import argparse
from pathlib import Path
from nes_raw506 import once


def prepare(src,out):
    name='nes_plan_service200.c'
    code=(src/name).read_text()
    begin=code.index('static bool drive554(')
    end=code.index('static bool flush(',begin)
    drive=once(code[begin:end],' if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;', ''' /* A busy terminal E8 may become ready during its own SPI transfer.
   * One fresh sample per retry budget. poll checks STOP, count, CRC and any
   * advertised bulk before the existing E9 branch may publish the buffer. */
  if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;
  if(!flags && p->ending && !allow_payload && !p->quiet_map)
   if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;''')
    out.mkdir(parents=True,exist_ok=False)
    (out/name).write_text(code[:begin]+drive+code[end:],newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('src','out'):p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args();prepare(a.src,a.out)
