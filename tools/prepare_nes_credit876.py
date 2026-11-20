"""Borrow one input read at a checked section-5 queue return after planner release."""
import argparse
import re
from pathlib import Path

from check_nes_game478 import crc
from check_nes_strip869 import digest
from nes_raw506 import once
from prepare_nes_deadline875 import compact_plan


def prepare(base, patch, policy):
    assert digest(base/'obj-nes-100/firmware.stm') == '83f4b6031b0372fc4af3f07e54c51992bd63abe72d0b2d281bdb88f0c809f201'
    patch.mkdir(parents=True)
    name = 'nes_native_runtime165.c'
    original=(base/name).read_text()
    src = once(original, ' bool input_wait=reason<=1', ''' /* The completed planner owns its output copy. A checked table credit
  * can service one receiver poll before SEAL. A D0 with no offered
  * block leaves the receiver idle; COMMIT still belongs to step(). */
 if(reason==1 && progress && r->state==NES_NATIVE165_COMMITTED &&
    s->transport.last[1]==5 && s->transport.last[0]==2 &&
    s->resident && s->resident->prepared)reason=4;
 bool input_wait=reason<=1''')
    if policy=='retry':
        src=once(src,'progress && r->state==NES_NATIVE165_COMMITTED &&',
                 'progress && r->state==NES_NATIVE165_IDLE && s->prefetch_left==7 &&')
    if policy=='control':
        src=original
    if policy=='pause':
        # Service input in the following unresolved plan wait. The ordinary
        # pause receives progress=true only after a checked D2 retirement.
        anchor=' if(input_wait || reason==3 || reason==4){'
        src=once(original,anchor,''' if(reason==0 && !progress && r->state==NES_NATIVE165_IDLE &&
    s->prefetch_left==7 && s->transport.last[1]==5 && s->transport.last[0]==2 &&
    s->resident && s->resident->prepared)input_wait=true;
'''+anchor)
    (patch/name).write_text(src, newline='\n')
    compact_plan(base, patch)
    name = 'nes_native165.c'
    src = (base/name).read_text()
    query = bytes.fromhex('d000000000ff')
    wire = query + bytes([crc(query,8,7,0),0xa5])
    values = ','.join(hex(x) for x in wire)
    src = once(src,'static bool status(', 'static const uint8_t status_request876[8]={'+values+'};\nstatic bool status(')
    src, count = re.subn(r'frame\(tx,0xd0,0,0\);\s*if\(!fn\(ctx,tx,', 'if(!fn(ctx,status_request876,', src)
    assert count==4
    (patch/name).write_text(src, newline='\n')
    name = 'nes_native_sink165.c'
    src=once((base/name).read_text(),'b[0]=(uint8_t)v;b[1]=(uint8_t)(v>>8);','uint16_t word=(uint16_t)v;memcpy(b,&word,sizeof word);')
    (patch/name).write_text(src, newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('patch',type=Path)
    parser.add_argument('--policy',choices=('committed','retry','control','pause'),default='committed')
    args=parser.parse_args()
    prepare(args.base,args.patch,args.policy)
