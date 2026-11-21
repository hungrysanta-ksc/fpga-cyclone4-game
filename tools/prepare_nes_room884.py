"""Allow one input poll on checked ordinary queue credit after tile FINISH."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base, patch):
    assert digest(base/'obj-nes-100/firmware.stm')=='e17d511726f17ecd68339973ddcde848052a4533e1a19c6588b52bfb4293e13f'
    name='nes_native_runtime165.c'
    src=once((base/name).read_text(),
        '''if(reason==1 && progress && r->state==NES_NATIVE165_IDLE && s->prefetch_left==7 &&
    s->transport.last[1]==5 && s->transport.last[0]==2 &&''',
        '''if(progress && r->state==NES_NATIVE165_IDLE && s->prefetch_left==7 &&
    ((reason==0 && s->plan.finished && s->transport.last[1]>=3) ||
     (reason==1 && s->transport.last[1]==5 && s->transport.last[0]==2)) &&''')
    patch.mkdir(parents=True)
    (patch/name).write_text(src,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('patch',type=Path)
    prepare(**vars(parser.parse_args()))
