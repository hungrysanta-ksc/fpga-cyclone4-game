# SPDX-License-Identifier: MIT
"""Flush a second confirmed warm BG prefix before the planner reaches OBJ."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once, sha


def compact(src):
    # Reuse every long-form validation predicate, including the separate
    # all-zero row rule for kinds 2/3. Only skip construction of discarded bytes.
    long=(src/'nes_plan_wire196.h').read_text()
    path=src/'nes_plan_wire199.h'
    short=once(path.read_text(),'#include "nes_plan_wire196.h"','#include "nes_plan191.h"')
    start=short.index(' uint16_t crc;')
    check=long[long.index(' if(!q||'):long.index(' for(unsigned i=0;i<32;i++)')]
    check=once(check,'||!crc','')
    check=once(check,' for(unsigned i=0;i<16;i++)if(q->row[i]>7)return 0;',
               ' bool identity=true;for(unsigned i=0;i<16;i++){if(q->row[i]>7)return 0;if(q->row[i]!=i/2)identity=false;}')
    emit_short=short[short.index(' out[0]='):short.index(' return 7;')+len(' return 7;')]
    emit_long=long[long.index(' for(unsigned i=0;i<32;i++)'):long.index(' uint16_t c=0xffff;')]
    path.write_bytes((short[:start]+check+' if(q->kind>=2||(!am&&identity)){\n'+emit_short+'\n }\n'+emit_long+' return n;\n}\n#endif\n').encode())


def prepare(base,out,split=False,direct=False,map_drain=False):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='09843e823008af829ab5faeb12cff0aa03a064cc45b784e85bdc1ca91ff52c22'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    path=out/'src/nes_plan_service200.c'
    code=once(path.read_text(),' if(!p->early&&q->kind==0&&(!p->defer_first||p->count>=4))return nes_plan549_first(p);',
              ''' if(q->kind==0){
  if(!p->early&&(!p->defer_first||p->count>=4))return nes_plan549_first(p);
  /* Confirmed BG records in plan order. Preserve the first warm row flush,
   * cold packetization and the existing guarded E8/E9 ownership transfer. */
  if(p->defer_first&&p->sent==1&&p->count==7)return flush(p);
 }''')
    if split:
        code=once(code,'p->sent==1&&p->count==7','((p->sent==1&&p->count==6)||(p->sent==2&&p->count==1))')
    path.write_bytes(code.encode())
    # The consecutive diagnostic headers have no data-dependent separator.
    path=out/'src/nes_budget210.c'
    s=path.read_text()
    start=s.index(' int n=snprintf(text,size,"budget_schema')
    end=s.index(' n+=startup;',start)+len(' n+=startup;')
    old=s[start:end]
    fmt1,args=old.split('",\n',1)
    args1,tail=args.split(');\n',1)
    _,header=tail.split('int startup=snprintf(text+n,size-(unsigned)n,\n  "',1)
    fmt2,args2=header.split('",\n',1)
    args2=args2.split(');\n',1)[0]
    path.write_bytes((s[:start]+fmt1+fmt2+'",\n'+args1+',\n'+args2+');\n if(n<0||(unsigned)n>=size)return -1;'+s[end:]).encode())
    if direct:compact(out/'src')
    if map_drain:
        path=out/'src/nes_native_sink165.c'
        s=once(path.read_text(), ' if(!span(s,3,0,p->cgram,512))', ''' /* Allow a long accepted map tail to reach the idle selector before
  * palette heads arrive. No display grant is published by this drain. */
 if(s->plan && s->plan->window && (((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu){
  uint8_t ack[12];
  if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);
 }
 if(!span(s,3,0,p->cgram,512))''')
        path.write_bytes(('#include "nes_sink_window184.h"\n'+s).encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):p.add_argument(name,type=Path)
    p.add_argument('--split',action='store_true',help='Send six records first, then the next confirmed BG to close the prior tile run.')
    p.add_argument('--direct',action='store_true',help='Form validated compact records directly before the early E9.')
    p.add_argument('--map-drain',action='store_true',help='Drain a long accepted map tail before publishing the palette.')
    a=p.parse_args();prepare(a.base,a.out,a.split,a.direct,a.map_drain)
