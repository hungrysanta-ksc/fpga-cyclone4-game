# SPDX-License-Identifier: MIT
"""Use the firmware's already linked CCITT table for the complete output E1 frame."""
import argparse
from pathlib import Path
from nes_raw506 import once


def prepare(src, out):
    name='nes_sink_window184.c'
    text=(src/name).read_text()
    a=text.index('static uint16_t crc16(')
    b=text.index('\n',a)
    text=text[:a]+text[b+1:]
    text=once(text,'#include <string.h>','#include <string.h>\n#include "crc.h"')
    text=once(text,'uint16_t c=0xffff;\n for(unsigned i=0;i<=n;i++)c=crc16(c,tx[i]);',
              'uint16_t c=crc_xmodem_block(0xffff,tx,n+1);')
    out.mkdir(parents=True,exist_ok=False)
    (out/name).write_text(text,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('src','out'):p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args();prepare(a.src,a.out)
