"""Materialize a 727 ARM candidate with one checked drain at the final warm map."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out):
    assert sha(base/'src/obj-nes-100/firmware.stm') in {
        '523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655',
        '3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386'}
    out.mkdir(parents=True, exist_ok=False)
    path = base/'src/nes_plan_service200.c'
    s = once(path.read_text(), '   if(!complete485(p))return false;\n   /* A new ready tile', '   /* A new ready tile')
    begin=s.index('    if(!nes_window184_drain(p->window,ack) ||')
    end=s.index('   if(!nes_sink195_submit',begin)
    s=s[:begin]+"""    /* The latest checked map ACK also covers the earlier FIFO watermark.
     * Reject a future or expired watermark before releasing the previous tile. */
    if((p->bulk_pending && (uint16_t)(p->window->sent-p->bulk_until)>4) ||
       !nes_window184_drain(p->window,ack))return fail(p,5);
    p->bulk_pending=false;
    if(!(p->window->status_flags&8) &&
       !p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);
   }else if(!complete485(p))return false;
"""+s[end:]
    (out/path.name).write_text(s,newline='\n')
    path = base/'src/nes_native_sink165.c'
    s = path.read_text()
    # Reuse 733's zero encoding to pay for the scheduling predicates.
    s = once(s,'if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;',
             'if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}')
    s = once(once(once(s,'if(n)memcpy(b+16,data,n)','if(n && data)memcpy(b+16,data,n)'),
                  'zero[240]','zero[2]'),'offset,zero,n)','offset,NULL,n)')
    s = once(s,' bool same=same635(s,p);\n if(same&&s->displayed&&s->ack635[r->target]&&s->ack635[1-r->target]){\n  if(!send635',
             ' if(reuse){\n  if(!early && !send635')
    s = once(s,' /*719 The ACK timestamp', ''' bool same=same635(s,p);
 bool reuse=same && s->displayed && s->ack635[r->target] && s->ack635[1-r->target];
 /* A page with a completed contiguous 24-row map run can admit the OBJ
  * and checked OAM now. Prepare the compact CHR tables before first scroll. */
 uint64_t rows=r->map_upload;
 rows &= rows>>1;
 rows &= rows>>2;
 rows &= rows>>4;
 bool early=reuse && s->plan && s->plan->bank_history==2 && s->plan->window &&
     s->plan->window->last[1]==2 && (rows & (rows>>8) & (rows>>16) & UINT64_C(0x1ff000001ff));
 if(early && !send635(s,p,r->target))return false;
 /*719 The ACK timestamp''')
    s = once(s,'s->plan->window->last[1]==2 && nes_cost471_available',
             '(early || s->plan->window->last[1]==2) && nes_cost471_available')
    (out/path.name).write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    prepare(a.base,a.out)
