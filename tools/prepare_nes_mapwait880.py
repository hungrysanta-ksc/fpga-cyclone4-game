"""Hold the first scroll behind bounded, checked DMA-progress reads after map credit."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base,patch,post_end=False):
    assert digest(base/'obj-nes-100/firmware.stm')=='19dad89d242601d9139116828dfe204491125d9bed306b29bbefcd9e6a6a0c4a'
    name='nes_native_sink165.c'
    src=(base/name).read_text()
    anchor='''  if((uint32_t)map && w && w->last[1]==2){
   uint8_t ack[12];
   if(!nes_window184_drain(w,ack))return fail(s,5);'''
    src=once(src,'bool nes_scroll810(','''/* Reaching the bound releases ordinary scheduling. Only a checked
 * receipt with bit 3 set reports an idle map DMA completion. */
static __attribute__((noinline)) bool wait_map880(struct nes_sink_window184 *w,unsigned limit){
 uint8_t ack[12];
 do {
  if(!nes_window184_drain(w,ack))return false;
  if(w->status_flags&8)break;
 }while(--limit);
 return true;
}
bool nes_scroll810(''')
    src=once(src,anchor,'''  if((uint32_t)map && w && w->last[1]==2){
   if(!wait_map880(w,96))return fail(s,5);''')
    src=once(src,'''  uint8_t ack[12];
  struct nes_sink_window184 *w=s->plan->window;
  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);
  for(unsigned poll=0;!s->strip_dma_seen && poll<120;poll++){
   if(!nes_window184_drain(w,ack))return fail(s,5);
   if(w->status_flags&8)break;
  }''','''  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);
  if(!s->strip_dma_seen && !wait_map880(s->plan->window,120))return fail(s,5);''')
    patch.mkdir(parents=True)
    (patch/name).write_text(src,newline='\n')
    name='nes_native165.c'
    raster=once((base/name).read_text(),'static void __attribute__((noipa)) raster_tail879','static inline void raster_tail879')
    (patch/name).write_text(raster,newline='\n')
    if post_end:
        name='nes_native_runtime165.c'
        src=once((base/name).read_text(),'nes_cost474_pause(ctx,check,reason,progress)',
                 'nes_cost474_pause(ctx,check,reason,progress,'
                 'reason==2 && r->state==NES_NATIVE165_COMPLETE ? 84u*96u : 84u*128u)')
        (patch/name).write_text(src,newline='\n')
        name='nes_cost471.h'
        src=once((base/name).read_text(),'bool nes_cost474_pause(void *,bool (*)(void *),unsigned,bool);',
                 'bool nes_cost474_pause(void *,bool (*)(void *),unsigned,bool,unsigned);')
        (patch/name).write_text(src,newline='\n')
        name='nes_cost471.c'
        src=once((base/name).read_text(),'unsigned reason,bool progress){',
                 'unsigned reason,bool progress,unsigned quiet_cycles){')
        src=once(src,'while(elapsed<84u*128u);','while(elapsed<quiet_cycles);')
        (patch/name).write_text(src,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('patch',type=Path)
    p.add_argument('--post-end',action='store_true')
    a=p.parse_args()
    prepare(a.base,a.patch,a.post_end)
