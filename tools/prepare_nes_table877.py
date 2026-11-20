"""Compare checked table-pair scheduling and publication before palette/OAM reuse."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base, patch, policy, shared):
    assert digest(base/'obj-nes-100/firmware.stm')=='45c4f19cd1e60ca85d08c1935c28f457ec9ad858a38177fb3629c93351e1131e'
    name='nes_native_sink165.c'
    src=(base/name).read_text()
    if policy=='pair':
        src=once(src,'if(!packet(s,2,5,offset+201,joined+201,240))', '''/* The first half serviced the plan. Permit one adjoining ordinary
   * head while the old bulk target remains in the checked receipt window. */
  struct nes_plan200 *plan=s->plan;
  bool room=plan && plan->window && (!plan->bulk_pending ||
    (uint16_t)(plan->window->sent-plan->bulk_until)<3);
  if(!packet(s,room?24:2,5,offset+201,joined+201,240))''')
    elif policy in ('table','interleave','fifo'):
        src=once(src,''' if(same&&s->displayed&&s->ack635[r->target]&&s->ack635[1-r->target]){
  if(!send635(s,p,r->target))return false;
 }else{''',''' bool reuse=same&&s->displayed&&s->ack635[r->target]&&s->ack635[1-r->target];
 if(!reuse){''')
        if policy in ('table','fifo'):
            src=once(src,' uint8_t descriptor[168];',''' /* Both immutable section-5 heads may use the queue while the tile
  * producer finishes. Reuse still requires the original target-bank check. */
 if(reuse && !send635(s,p,r->target))return false;
 uint8_t descriptor[168];''')
        else:
            src=once(src,' if(!reuse){',' if(reuse){\n  if(!p->patch_count && !send635(s,p,r->target))return false;\n }else{')
            src=once(src,'  if(!packet(s,2,5,offset+201,joined+201,240))',
                     '''  /* Let the first table head retire during reuse validation. The
   * final table still directly precedes SEAL in queue order. */
  if(reuse && !send635(s,p,r->target))return false;
  if(!packet(s,2,5,offset+201,joined+201,240))''')
    # Fixed-width ARM fields are already on the little-endian wire ABI.
    src=once(src,'for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));',
             'memcpy(b+4,&s->serial,4);')
    src=once(src,'for(unsigned i=0;i<4;i++){b[4+i]=(uint8_t)(s->serial>>(8*i));b[8+i]=(uint8_t)(r->epoch>>(8*i));}',
             'memcpy(b+4,&s->serial,4);memcpy(b+8,&r->epoch,4);')
    patch.mkdir(parents=True)
    (patch/name).write_text(src,newline='\n')
    if policy=='fifo':
        name='nes_sink_window184.c'
        src=once((base/name).read_text(),
                 'if(s->ever_sent && (p[0]!=3 || s->last[1]!=5) && !nes_window184_drain(s,ack))',
                 '''/* Like a table head, the checked reuse head retains its own receipt.
  * FIFO order keeps SEAL behind it. Only a full raw-patch SEAL from
  * the reordered sender can use this case; send still checks credit. */
 bool tail=s->last[1]==5 || (s->last[0]==9 && s->last[1]==4 && n==184 && p[38]);
 if(s->ever_sent && (p[0]!=3 || !tail) && !nes_window184_drain(s,ack))''')
        (patch/name).write_text(src,newline='\n')
    if shared:
        # D2 and D3 are the same eight-byte layout as the loader command.
        # Widening the 16-bit token supplies the required zero high byte.
        name='nes_native165.c'
        src=(base/name).read_text()
        private=next(line for line in src.splitlines() if line.startswith('static void frame('))
        src=once(src,private,'#include "nes_rom_spi.h"')
        for op in ('0xd2','0xd3'):
            src=once(src,'frame(tx,'+op,'nes_rom_spi_frame(tx,'+op)
        (patch/name).write_text(src,newline='\n')
        name='nes_rom_spi.c'
        src=once((base/name).read_text(),'void nes_rom_spi_frame(', 'extern uint8_t nes_wire_crc807(const uint8_t *,unsigned);\nvoid nes_rom_spi_frame(')
        start=src.index('uint8_t crc=0;')
        stop=src.index('out[7]=0xa5;',start)
        src=src[:start]+'out[6]=nes_wire_crc807(out,6);'+src[stop:]
        (patch/name).write_text(src,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('patch',type=Path)
    p.add_argument('policy',choices=('pair','table','interleave','fifo','control'))
    p.add_argument('--shared',action='store_true')
    a=p.parse_args()
    prepare(a.base,a.patch,a.policy,a.shared)
