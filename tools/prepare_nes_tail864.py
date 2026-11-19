"""Isolate the shipped 201+240B section-5 layout on the full-width MMC855 path."""
import argparse
from nes_raw506 import once
from prepare_nes_trial802 import PROBES


def prepare(control=False, untrimmed=False):
    name='nes_native_sink165.c'
    original=(PROBES/'nes-trial855/link/src'/name).read_text()
    donor=(PROBES/'nes-trial860/link/src'/name).read_text()
    start='  if(!span(s,5,offset,raw,packed))'
    end='  size[5]='
    section=donor[donor.index('  const uint8_t *tables='):donor.index(end)]
    text=original if control else once(original,original[original.index(start):original.index(end)],section)
    # The original loop encodes six little-endian uint16_t lengths. The
    # Cortex-M4 uses that layout natively. All emitted SEALs are compared.
    if not untrimmed:
        text=once(text,'for(unsigned i=0;i<6;i++)put16(descriptor+i*2,size[i]);',
                  'memcpy(descriptor,size,sizeof size);')
        text=once(text,'for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));',
                  'memcpy(b+4,&s->serial,4);')
    out=PROBES/'nes-tail864'/('control-patch' if control else 'untrimmed-patch' if untrimmed else 'patch')
    out.mkdir(parents=True,exist_ok=True)
    (out/name).write_text(text,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    variant=p.add_mutually_exclusive_group()
    variant.add_argument('--control',action='store_true')
    variant.add_argument('--untrimmed',action='store_true')
    prepare(**vars(p.parse_args()))
