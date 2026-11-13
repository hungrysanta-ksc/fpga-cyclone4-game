# SPDX-License-Identifier: MIT
"""Put the last tile receipt and checked OAM ahead of a long contiguous map run."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, single=False):
    assert sha(base/'src/obj-nes-100/firmware.stm') in {
        '523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655',
        '3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386'}
    s=(base/'src/nes_native_sink165.c').read_text()
    # 733's verified short zero representation pays for the admission policy.
    s=once(s,'if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;',
             'if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}')
    s=once(s,'if(n)memcpy(b+16,data,n)','if(n && data)memcpy(b+16,data,n)')
    s=once(once(s,'zero[240]','zero[2]'),'offset,zero,n)','offset,NULL,n)')
    s=once(s,' if(!map527(s,p,r->map_upload,false))', ''' bool same=same635(s,p);
 bool reuse=same && s->displayed && s->ack635[r->target] && s->ack635[1-r->target];
 /* Rows form two 2 KiB pages. Look for any contiguous 24-row span in a
  * single page. Keep the entire span together and preserve all queue checks. */
 uint64_t pairs=r->map_upload & (r->map_upload>>1);
 uint64_t four=pairs & (pairs>>2);
 uint64_t eight=four & (four>>4);
 uint64_t run=eight & (eight>>8) & (eight>>16);
 bool early=reuse && s->plan && s->plan->bank_history==2 &&
      (run & UINT64_C(0x1ff000001ff)) && !s->obj_next;
 if(early){
  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);
  if(!send635(s,p,r->target))return false;
 }
 if(!map527(s,p,r->map_upload,false))''')
    s=once(s,' bool same=same635(s,p);\n if(same&&s->displayed&&s->ack635[r->target]&&s->ack635[1-r->target]){\n  if(!send635',
             ' if(reuse){\n  if(!early && !send635')
    if single:
        s=once(s,'bool nes_sink212_seal(', """static bool one_obj739(const uint8_t *dirty){
 unsigned prior=0;
 bool found=false;
 for(unsigned i=128;i<144;i++){
  unsigned bits=dirty[i],starts=bits & ~((bits<<1)|prior);
  if(starts){
   if(found || (starts&(starts-1)))return false;
   found=true;
  }
  prior=bits>>7;
 }
 return found;
}
bool nes_sink212_seal(""")
        s=once(s,'if(early){\n  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);\n  if(!send635(s,p,r->target))return false;',
               """early=early && s->plan->window && one_obj739(r->dirty);
 if(early){
  if(!send635(s,p,r->target))return false;
  /* Wait only for the already-issued staging owner; subsequent ordinary
   * packets retain independent credit. A not-yet-ready OBJ yields to map. */
  uint8_t ack[12];
  if(s->plan->bulk_pending &&
     !nes_window184_through(s->plan->window,ack,s->plan->bulk_until))return fail(s,5);
  if(!nes_plan200_progress(s->plan,NES_ORDINARY553))return fail(s,5);""")
    out.mkdir(parents=True,exist_ok=False)
    (out/'nes_native_sink165.c').write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--single',action='store_true')
    a=p.parse_args()
    prepare(a.base,a.out,a.single)
