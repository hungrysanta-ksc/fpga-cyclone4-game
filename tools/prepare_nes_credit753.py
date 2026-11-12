# SPDX-License-Identifier: MIT
"""Borrow one checked input block per quiet final-receipt poll after the initial batch."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, policy):
    assert sha(base/'src/obj-nes-100/firmware.stm') == 'e1357cb6ddb58fff5705321807e65fab8326940642e4625d2aed1818cc35985b'
    if policy in ('inputcrc','sealcrc'):
        # Same CRC polynomial, initial state and response bytes. The seed is
        # zero and the two high bits fold back under x^8+x^2+x+1.
        if policy=='inputcrc':
            name='nes_native165.c'
            source=(base/'src'/name).read_text()
            begin=source.index('static uint8_t crc8(')
            end=source.index('static bool fail(',begin)
            source=source[:begin]+"""static uint8_t crc8(const uint8_t *p,unsigned n){
 uint8_t crc=0;
 while(n--){
  unsigned x=crc^*p++;
  x^=(x>>6)^(x>>7);
  crc=(uint8_t)(x^(x<<1)^(x<<2));
 }
 return crc;
}
"""+source[end:]
        else:
            from prepare_nes_credit752 import folded_crc
            name='nes_sink_window184.c'
            source=(base/'src'/name).read_text()
            source=once(source,'static bool status(',folded_crc('seal_crc753','E0 reply')+'static bool status(')
            source=once(source,'uint8_t c=nes_wire723_crc8(rx+1,18);',
                       'uint8_t c=s->last[0]==3?seal_crc753(rx+1):nes_wire723_crc8(rx+1,18);')
        out.mkdir(parents=True,exist_ok=False)
        (out/name).write_text(source,encoding='utf8',newline='\n')
        return
    name = 'nes_native_runtime165.c'
    source = (base/'src'/name).read_text(encoding='utf8')
    if policy in ('prefix','prefixcrc'):
        # Test only at the end of the existing guarded initial batch. Small
        # packets and cold banks return directly to the regular E0 loop.
        anchor='   if(reason!=2)break;\n   if(!check(ctx))return false;'
        source=once(source,anchor,anchor+"""
   if(!s->prefetch_left && s->plan.bank_history==2 && r->ready183 &&
      (r->status183[5] || r->status183[6]>=128)){
    if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
    if(!check(ctx))return false;
   }""")
        if policy=='prefixcrc':
            prepare(base,out,'sealcrc')
        else:
            out.mkdir(parents=True,exist_ok=False)
        (out/name).write_text(source,encoding='utf8',newline='\n')
        return
    if policy=='objburst':
        # The committed output plan keeps the last verified descriptor until
        # EA. Four 32-byte OBJ tiles or more signal a longer VBlank job.
        # Decide the budget once when the next receiver ownership starts.
        source=once(source,'if(r->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;',
                    """if(r->state==NES_NATIVE165_COMMITTED){
   const uint8_t *last=s->plan.bulk;
   bool large_obj=s->plan.bank_history==2 && s->plan.bulk_valid && last[1]==1 &&
                  (last[3] || last[2]>=128);
   s->prefetch_left=large_obj?8:7;
  }""")
        out.mkdir(parents=True,exist_ok=False)
        (out/name).write_text(source,encoding='utf8',newline='\n')
        return
    anchor = ' return nes_cost474_pause(ctx,check,reason,progress);'
    # ready183 comes only from a validated D0 following a successful D2.
    # The previous generation still owns its output ACK, EA and display.
    condition = 'reason==2 && !progress && !s->prefetch_left && r->ready183'
    if policy == 'large':
        # Half-page and larger READs are the expensive shared-bus jobs.
        condition += ' && (r->status183[5] || r->status183[6]>=128)'
    if policy == 'geometry':
        condition += ' && r->next_kind==0'
    if policy == 'one':
        # On entry at a SEAL with a newly committed receiver, arm exactly one
        # additional slot. Keep this allowance separate from the first batch.
        header = 'nes_native_runtime165.h'
        h = (base/'src'/header).read_text()
        h = once(h, 'uint8_t prefetch_left;', 'uint8_t prefetch_left;\n bool extra_seal_block;')
        source = once(source, 'if(r->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;',
                      'if(r->state==NES_NATIVE165_COMMITTED){s->prefetch_left=7;s->extra_seal_block=true;}')
        source = once(source, 's->prefetch_left=0;', 's->prefetch_left=0;s->extra_seal_block=false;')
        condition += ' && s->extra_seal_block'
    code = ' if('+condition+'){\n'
    if policy == 'one':
        code += '  s->extra_seal_block=false;\n'
    code += '''  /* A positive cached input status owns the sealed head until POP.
   * Re-check the old display receipt after this one READ/POP pair. */
  if(!check(ctx))return false;
  if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
  return check(ctx);
 }
'''
    out.mkdir(parents=True, exist_ok=False)
    if policy == 'one':
        (out/header).write_text(h,encoding='utf8',newline='\n')
    (out/name).write_text(once(source,anchor,code+anchor),encoding='utf8',newline='\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('base','out'):p.add_argument(key,type=Path)
    p.add_argument('--policy',choices=('ready','geometry','one','large','inputcrc','sealcrc','objburst','prefix','prefixcrc'),required=True)
    a=p.parse_args()
    prepare(a.base,a.out,a.policy)
