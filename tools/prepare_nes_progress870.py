"""Retain checked map DMA progress across following OBJ transactions in the same frame."""
import argparse
import hashlib
from pathlib import Path

from nes_raw506 import once


def prepare(base, out, variant):
    producer=variant!='A'
    fixed_rows=variant in ('C','E','F','G')
    overlap=variant=='D'
    map_head=variant in ('E','F')
    assert hashlib.sha256((base/'obj-nes-100/firmware.stm').read_bytes()).hexdigest() == (
        'b0ca526dbd82a784dc9c55afd3c33618a209337655f3bbf4cb4f55e681787e7c')
    out.mkdir(parents=True,exist_ok=False)
    def edit(name, pairs):
        src=(base/name).read_text()
        for old,new in pairs:
            src=once(src,old,new)
        (out/name).write_text(src,newline='\n')
    if producer:
        edit('nes_native_sink165.h', [('bool map_pair683;', 'bool map_pair683, strip_dma_seen;')])
        edit('nes_native_sink165.c', [
            ('s->map_next=0;s->map_pair683=false;', 's->map_next=0;s->map_pair683=false;s->strip_dma_seen=false;'),
            ('for(unsigned poll=0;poll<120;poll++){', 'for(unsigned poll=0;!s->strip_dma_seen && poll<120;poll++){')])
        edit('nes_plan_service200.c', [("""if(!nes_window184_drain(p->window,ack) ||
       (!(p->window->status_flags&8) &&
        !p->window->wait(p->window->ctx,p->window->guard,4,false)))return fail(p,5);""",
            """if(!nes_window184_drain(p->window,ack))return fail(p,5);
    if(p->window->status_flags&8){
     if(p->window->last[0]==10)p->sink->strip_dma_seen=true;
    }else if(!p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);""")])
        if overlap:
            # FINAL remains mandatory before SEAL. A completed map needs no
            # extra END wait before the ordinary packet's own arbitrator.
            dst=out/'nes_native_sink165.c'
            code=once(dst.read_text(),'if(!p->scroll_issued && !p->map_dirty && s->plan &&',
                      'if(!s->strip_dma_seen && !p->scroll_issued && !p->map_dirty && s->plan &&')
            dst.write_text(once(code,'!s->strip_dma_seen && poll<120','poll<120'),newline='\n')
        if map_head:
            dst=out/'nes_native_sink165.c'
            old="""if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);
  for(unsigned poll=0;!s->strip_dma_seen && poll<120;poll++){"""
            new="""/* A checked strip can keep draining while later OBJ plans run.
   * Once its queue head changes, another E0 cannot prove strip progress. */
  bool strip=w->last[0]==10 || s->strip_dma_seen;
  if(!nes_plan200_progress(s->plan,strip?NES_ORDINARY553:NES_FINAL553))return fail(s,5);
  for(unsigned poll=0;!s->strip_dma_seen && poll<120;poll++){
   if(strip && w->last[0]!=10)break;"""
            dst.write_text(once(dst.read_text(),old,new),newline='\n')
        if variant=='F':
            # The second palette range cannot make another map DMA possible.
            # Normal window admission still waits for credit if both slots fill.
            dst=out/'nes_native_sink165.c'
            dst.write_text(once(dst.read_text(),'if(section==3 && at==128',
                                'if(!s->strip_dma_seen && section==3 && at==128'),newline='\n')
        if variant=='G':
            # The ordinary packet already services the tile producer, whose
            # checked strip drain is the owner of the map/OBJ handoff.
            dst=out/'nes_native_sink165.c'
            code=once(dst.read_text(),'s->plan->window && s->plan->bank_history==2 &&',
                      's->plan->window && s->plan->window->last[0]!=10 && !s->strip_dma_seen && s->plan->bank_history==2 &&')
            dst.write_text(code,newline='\n')
        if fixed_rows:
            # This layout has one verified repeat at rows 3, 4 and 5.
            # Any other content remains eligible for ordinary checked map packets.
            dst=out/'nes_native_sink165.c'
            code=once(dst.read_text(), 'if (y && (y<h->keep || y>h->keep+1)) row+=32;',
                      'if (y && y!=4 && y!=5) row+=32;')
            start=code.index('    unsigned keep=1;')
            end=code.index('    h->differing=diff;',start)
            code=code[:start]+"""    if (memcmp(map+3*32,map+4*32,128)) return;
    memcpy(h->words,map,4*64);
    memcpy(h->words+4*32,map+6*32,17*64);
"""+code[end:]
            dst.write_text(once(code,'h->keep=keep;', 'h->keep=1;'),newline='\n')
        return
    edit('nes_sink_window184.h',[('bool initialized,ever_sent;', 'bool initialized,ever_sent,strip_dma_seen;')])
    edit('nes_sink_window184.c',[
        ('s->sent++;s->ever_sent=true;', 'if(p[0]==1)s->strip_dma_seen=false;\n s->sent++;s->ever_sent=true;'),
        ('  }\n  /* Every retired packet', '''   /* The physical progress bit follows a completed map DMA. op10 registers
    * one complete strip. Latch only after the empty queue identity check. */
   if(s->last[0]==10 && (s->status_flags&8))s->strip_dma_seen=true;
  }
  /* Every retired packet''')])
    edit('nes_native_sink165.c',[('for(unsigned poll=0;poll<120;poll++){',
                                'for(unsigned poll=0;!w->strip_dma_seen && poll<120;poll++){')])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('variant',choices=list('ABCDEFG'))
    prepare(**vars(p.parse_args()))
