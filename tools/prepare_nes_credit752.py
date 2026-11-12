# SPDX-License-Identifier: MIT
"""Build against the 749 page firmware used with the reset-booted 751 ROM."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def folded_crc(name,covered):
    return '''/* CRC-8/ATM over the complete COVERED. The two high bits feed
 * the low terms when multiplying by x^8 modulo x^8+x^2+x+1. */
static uint8_t FUNCTION(const uint8_t *bytes){
 uint8_t crc=0;
 for(unsigned n=18;n;n--){
  unsigned x=crc^*bytes++;
  x^=(x>>6)^(x>>7);
  crc=(uint8_t)(x^(x<<1)^(x<<2));
 }
 return crc;
}
'''.replace('FUNCTION',name).replace('COVERED',covered)


def prepare(base, out, policy):
    assert sha(base/'src/obj-nes-100/firmware.stm') == '62d63f1559e776d52b6434ad72d48862bfc12168baa57049dd8cde3e85a9bb8e'
    out.mkdir(parents=True, exist_ok=False)
    if policy in ('seal','combined','credit'):
        name = 'nes_sink_window184.c'
        source = (base/'src'/name).read_text()
        source = once(source, 'static bool status(', folded_crc('seal_crc752','E0 reply') + 'static bool status(')
        ready = 's->last[0]==3'
        if policy=='credit':
            # The raw counter selects the CRC algorithm only. No count or
            # identity is adopted before its full CRC and bounds checks pass.
            ready += ' && ((unsigned)rx[5]*256+rx[6])!=s->retired'
        source = once(source, 'uint8_t c=nes_wire723_crc8(rx+1,18);',
                      'uint8_t c='+ready+'?seal_crc752(rx+1):nes_wire723_crc8(rx+1,18);')
        (out/name).write_text(source,encoding='utf8',newline='\n')
        if policy in ('seal','credit'):return
    if policy=='receipt':
        name = 'nes_sink_window184.c'
        source = (base/'src'/name).read_text()
        idle = '  if(!wait474(s,s->last[0]==3?2:1,s->retired!=before))return false;'
        source = once(source, idle, '''  /* A single in-flight BG may retire during the CRC check of the first
   * snapshot. Try one fresh guarded E0 before the regular quiet wait. */
  if(!i && target==s->sent && (uint16_t)(target-before)==1 &&
     s->last[0]==7 && !s->last[1] && s->poll_limit>1)continue;
'''+idle)
        (out/name).write_text(source,encoding='utf8',newline='\n')
        return
    name = 'nes_plan_service200.c'
    source = (base/'src'/name).read_text()
    if policy=='bgcrc':
        source=once(source,'static bool read509(',folded_crc('reply_crc752','status payload')+'static bool read509(')
        source=once(source,'if(nes_wire723_crc8(rx+1,18)!=rx[19])',
                    '''/* The unverified kind and length only select an equivalent CRC
  * implementation. All descriptor, receipt and token checks still follow. */
 bool short_bg=rx[6]==1 && !rx[7] && rx[8]==48 && !rx[9];
 if((short_bg?reply_crc752(rx+1):nes_wire723_crc8(rx+1,18))!=rx[19])''')
        (out/name).write_text(source,encoding='utf8',newline='\n')
        return
    if policy in ('look','lookbg'):
        # FINISH poll validates any new descriptor on its stack, and complete485
        # still validates the old BG's E0 receipt before it can submit a new E1.
        source = once(source, 'return complete485(p) && nes_plan200_progress(p,NES_ORDINARY553);',
                      'return nes_plan200_progress(p,NES_ORDINARY553);')
        if policy=='look':
            (out/name).write_text(source,encoding='utf8',newline='\n')
            return
    source = once(source, '   if(p->ending && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){',
                  '   bool input_after_bg=false;\n   if(p->ending && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){')
    source = once(source, '''    if(!nes_window184_drain(p->window,ack) ||
       (!(p->window->status_flags&8) &&''', '''    if(!nes_window184_drain(p->window,ack))return fail(p,5);
    /* Drain validated the map receipt. A ready 48B BG can begin consuming
     * before input borrows SPI. Its own receipt is still owed. */
    input_after_bg=!d[1] && d[2]==48 && !d[3] && !(p->window->status_flags&8);
    if((!input_after_bg && !(p->window->status_flags&8) &&''')
    if policy=='mapobj':
        # The small-BG case has no expensive OBJ to hide. Only lend the
        # empty queue to input if OAM follows a map and a large OBJ.
        f='nes_native_sink165.c'
        raw=(base/'src'/f).read_text()
        anchor=' uint8_t cmd[116];'
        raw=once(raw,anchor,''' struct nes_plan200 *plan=s->plan;
 if(plan && plan->ending && plan->bank_history==2 && plan->bulk_valid &&
    plan->bulk[1]==1 && plan->bulk[3] && plan->window &&
    plan->window->last[1]==2 && plan->window->wait){
  struct nes_sink_window184 *w=plan->window;
  uint8_t ack[12];
  if(!nes_window184_drain(w,ack) || !w->wait(w->ctx,w->guard,4,false))return fail(s,5);
 }
'''+anchor)
        (out/f).write_text(raw,encoding='utf8',newline='\n')
    if policy=='repay':
        source=once(source,'   if(!nes_sink195_submit(p->sink,d))return fail(p,5);',
                    '   if(!nes_sink195_submit(p->sink,d))return fail(p,5);\n   if(input_after_bg)p->bg_input_due=true;')
        source=once(source,'p->early=p->ending=false;','p->bg_input_due=p->early=p->ending=false;')
        h='nes_plan_service200.h'
        header=once((base/'src'/h).read_text(),'bool early,ending;', 'bool early,ending,bg_input_due;')
        (out/h).write_text(header,encoding='utf8',newline='\n')
        f='nes_native_sink165.c'
        raw=(base/'src'/f).read_text()
        anchor=' if(!map527(s,p,r->map_upload,false))return false;'
        raw=once(raw,anchor,anchor+'''
 /* Repay one coalesced input opportunity at the completed map boundary.
  * A failed drain/STOP cannot permit the following OAM publication. */
 if(s->plan && s->plan->bg_input_due){
  struct nes_sink_window184 *w=s->plan->window;
  uint8_t ack[12];
  if(!w || !w->wait || !nes_window184_drain(w,ack) ||
     !w->wait(w->ctx,w->guard,4,false))return fail(s,5);
  s->plan->bg_input_due=false;
 }
''')
        (out/f).write_text(raw,encoding='utf8',newline='\n')
    if policy=='overlap':
        old = 'p->bulk_until=p->window->sent;'
        source = once(source, old, old+'''
   if(input_after_bg && !p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);''')
    (out/name).write_text(source, encoding='utf8', newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('base','out'):parser.add_argument(key,type=Path)
    parser.add_argument('--policy',choices=('overlap','priority','receipt','seal','combined','look','lookbg','bgcrc','repay','credit','mapobj'),required=True)
    a=parser.parse_args()
    prepare(a.base,a.out,a.policy)
