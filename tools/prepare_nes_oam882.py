"""Issue checked OAM reuse before section 5 if the target needs no map upload."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base, patch, single_tile=False, direct_seal=False):
    assert digest(base / 'obj-nes-100/firmware.stm') == '02255c78136fd04e44b49ae91b0f1787db12d45d19a4a9be851fd2865b51e61a'
    name = 'nes_native_sink165.c'
    src = once((base / name).read_text(), ' if(!oam227(s,p->oam))return false;\n }',
               ''' if(!oam227(s,p->oam))return false;
 }else if(!r->map_upload){
  /* With no map DMA to protect, retire the checked reuse head
   * while preparing the section-5 tail. */
  if(!send635(s,p,r->target))return false;
  reuse=false;
 }''')
    if single_tile:
        # The resident planner resets writes at BEGIN and counts actual tile
        # submissions after reuse. The mandatory zero BG accounts for one.
        src = once(src, '}else if(!r->map_upload){',
                   '}else if(!r->map_upload && r->writes==1){')
    if direct_seal:
        src = once(src, 'uint16_t size[6]={(uint16_t)(p->bg_count*16),(uint16_t)(p->obj_count*32),4096,512,544,p->hdma_size};',
                   '''uint8_t descriptor[168];
 put16(descriptor,p->bg_count*16);put16(descriptor+2,p->obj_count*32);
 put16(descriptor+4,4096);put16(descriptor+6,512);
 put16(descriptor+8,544);put16(descriptor+10,p->hdma_size);''')
        src = once(src, 'size[5]=(uint16_t)(offset+249);', 'put16(descriptor+10,offset+249);')
        src = once(src, ' uint8_t descriptor[168];for(unsigned i=0;i<6;i++)put16(descriptor+i*2,size[i]);\n', '')
    patch.mkdir(parents=True)
    (patch / name).write_text(src, newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('patch', type=Path)
    parser.add_argument('--single-tile', action='store_true')
    parser.add_argument('--direct-seal', action='store_true')
    prepare(**vars(parser.parse_args()))
