# SPDX-License-Identifier: MIT
"""Use otherwise idle END polls to send prepared ordinary payload, one packet per poll."""
import argparse
from pathlib import Path
from nes_raw506 import sha, once


def prepare(arm,out):
    assert sha(arm/'obj-nes-100/firmware.stm')=='1eba4ecf90ab8834e937f6d4667d214ca5a065223fb6bf88ddb4d2c207db7af1'
    name='nes_plan_service200.c'
    source=(arm/name).read_text()
    start=source.index('static bool flush(')
    loop=source.index(' for(unsigned i=0;',start)
    end=source.index('static bool append(',loop)
    header=once(source[start:loop],'uint8_t flags;unsigned n','unsigned n')
    body=source[loop:end]
    body=once(body,'p->transfer(p->ctx,b,b,n+8)','p->transfer(p->ctx,p->buffer,p->buffer,p->bytes+8)')
    body=once(body,'flags==0 && p->quiet_map','flags==0 && (p->quiet_map||allow_payload)')
    body=once(body,'if(room && !p->quiet_map(p->ctx))return fail(p,5);','''if(room){
    if(!p->quiet_map)return true;
    if(!p->quiet_map(p->ctx))return fail(p,5);
   }''')
    source=source[:start]+'''/* The trailing E9 is framed exactly once. A nonempty count after return
 * keeps this buffer owned by the plan until the real E9 transfer succeeds. */
static bool drive554(struct nes_plan200 *p,bool allow_payload){
 uint8_t flags;
'''+body+header+' return drive554(p,p->ending && p->quiet_map);\n}\n'+source[end:]
    source=once(source,'if(!append(p,&end)||!flush(p))return false;\n p->ending=true;return true;',
                'if(!append(p,&end))return false;\n p->ending=true;return flush(p);')
    source=once(source,'if(p->finished)return valid(p);','''if(p->finished)return valid(p);
 if(p->count){
  /* Recheck tile and E9 first. A SEAL caller must drive END to completion.
   * Ordinary callers may enqueue one payload after checked, reserved credit. */
  if(!drive554(p,mode!=NES_FINAL553))return false;
  if(p->count)return true;
 }''')
    out.mkdir(parents=True,exist_ok=False)
    (out/name).write_text(source,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    prepare(a.arm,a.out)
