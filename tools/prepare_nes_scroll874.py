"""Wait for the checked last map receipt before opening the scroll pair on a two-page update."""
import argparse
import hashlib
from pathlib import Path

from nes_raw506 import once


def gate_at_map_completion(source, policy):
    anchor = ' }\n if(!(n&1))p->hdma[n++]=0;'
    # A single dirty left-page row can only contribute 64 bytes. The long
    # policy requires an actual contiguous 1 KiB prefix of that page.
    eligible = '(uint32_t)map' if policy=='both-pages' else '(uint16_t)map==UINT16_MAX'
    source = once(source, anchor, '''  /* Right-page run plus pending left-page rows. Keep the queue open for
   * inactive map DMA before the first scroll submission. E0 checks the
   * retired count and full last identity; it does not certify display. */
  struct nes_sink_window184 *w=s->plan->window;
  if(LEFT_ROWS && w && w->last[1]==2){
   uint8_t ack[12];
   if(!nes_window184_drain(w,ack))return fail(s,5);
  }
'''.replace('LEFT_ROWS',eligible)+anchor)
    if policy=='long-compact':
        # Share error exits across the sink. Successful packets do not call it.
        source=once(source,'static bool fail(struct nes_native_sink165',
                    'static __attribute__((noinline)) bool fail(struct nes_native_sink165')
    if policy=='shared':
        # These three callers consume only the boolean result. The window
        # still checks the full receipt, including identity, before returning.
        source = once(source,'static bool packet_wire(','''static __attribute__((noinline)) bool drain874(struct nes_sink_window184 *w){
 uint8_t ack[12];return nes_window184_drain(w,ack);
}
static bool packet_wire(''')
        for buffer, following in (('consumed','   for(unsigned sample'),('ack','   if(!nes_window184_drain'),('ack','  struct nes_sink_window184 *w')):
            source=once(source,'uint8_t '+buffer+'[12];\n'+following,following.lstrip() if buffer=='consumed' else following)
        source=once(source,'nes_window184_drain(w,consumed)','drain874(w)')
        assert source.count('if(!nes_window184_drain(w,ack))')==2
        source=source.replace('if(!nes_window184_drain(w,ack))','if(!drain874(w))')
    return source


def gate_at_scroll_submission(source, policy):
    # The pre-arbitrated scroll submission uses selector 24 in section 5.
    # Both versions check the actual queue owner. Only the right-page
    # version also requires the final row cursor before starting the drain.
    source=once(source,'uint8_t b[256],ack[12]={0};','uint8_t b[256];')
    cursor=' && s->map_next==32+23' if policy=='wire' else ''
    return once(source,'if(op==24)op=2;', '''uint8_t ack[12]={0};
 if(op==24){
  if(section==5CURSOR && s->plan && s->plan->window){
   struct nes_sink_window184 *w=s->plan->window;
   if(w->last[0]==2 && w->last[1]==2 && !nes_window184_drain(w,ack))return fail(s,5);
  }
  op=2;
 }'''.replace('CURSOR',cursor))


def prepare(base, patch, policy):
    assert hashlib.sha256((base/'obj-nes-100/firmware.stm').read_bytes()).hexdigest() == (
        '486d0d8de20235c71073453850ee489a98d588c15c315895db6eb72eee5d5f01')
    name = 'nes_native_sink165.c'
    original = (base/name).read_text()
    if policy in ('wire','adjacent'):
        source = gate_at_scroll_submission(original, policy)
    else:
        source = gate_at_map_completion(original, policy)
    patch.mkdir(parents=True)
    (patch/name).write_text(source,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('patch',type=Path)
    p.add_argument('--policy',choices=('both-pages','long','long-compact','shared','wire','adjacent'),default='both-pages')
    a=p.parse_args()
    prepare(a.base,a.patch,a.policy)
