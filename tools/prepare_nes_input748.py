# SPDX-License-Identifier: MIT
"""Move one bounded input callback from the checked map window to OAM retirement."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha

BASES = {'523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655',
         '3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386'}


def prepare(base, out, control=False):
    assert sha(base / 'src/obj-nes-100/firmware.stm') in BASES
    name = 'nes_native_sink165.c'
    s = (base / 'src' / name).read_text()
    # Identical data and packet implementation. Put the already zero-filled
    # padding in zero-initialized RAM so that the added code fits in Flash.
    s = once(s, 'static const uint8_t zero[240]={0};',
             'static const uint8_t zero[240] __attribute__((section(".bss.nes_zero748")))={0};')
    if not control:
        s = once(s, ' /*719 The ACK', ' struct nes_sink_window184 *input_after_oam=NULL;\n /*719 The ACK')
        s = once(s, '    if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);', '''    /* Only one idle input turn moves. Subsequent E0 samples, timeout
     * and STOP checks use the original deadline and credit owner. */
    if(!input_after_oam && s->enqueue && s->plan->bulk_valid &&
       s->plan->bulk[1]==0 && s->plan->bulk[2]==48 && !s->plan->bulk[3]){
     if(!w->guard(w->ctx))return fail(s,5);
     input_after_oam=w;
    }else if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);''')
        s = once(s, ' if(!span(s,5,0,p->hdma', ''' if(input_after_oam){
  uint8_t ack[12];
  /* The latest OAM packet covers prior tiles in FIFO order. Only the
   * normal checked drain permits reason 4 to borrow SPI on an empty queue. */
  if(input_after_oam->last[1]!=4 || !nes_window184_drain(input_after_oam,ack) ||
     !input_after_oam->wait(input_after_oam->ctx,input_after_oam->guard,4,false))
   return fail(s,5);
 }
 if(!span(s,5,0,p->hdma''')
    out.mkdir(parents=True, exist_ok=False)
    (out / name).write_text(s, encoding='utf8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--control', action='store_true')
    args = parser.parse_args()
    prepare(args.base, args.out, args.control)
