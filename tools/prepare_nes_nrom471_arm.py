# SPDX-License-Identifier: MIT
"""Materialize471 ARM codec and nested cycle accounting without changing transport decisions."""
import argparse,shutil
from pathlib import Path
from nes_delta231 import ROOT,BASE
p=argparse.ArgumentParser();p.add_argument('--receiver',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
src=BASE/'probes/nes-nrom418/arm01/src'
names=['nes_native165.c','nes_native_runtime165.c','nes_runtime_board165.inc','nes_game149_spi.inc','nes_native165_bulk.inc','nes_budget210.c']
for n in names:shutil.copyfile(a.receiver if n=='nes_native165.c' else src/n,d/n)
for n in ['nes_cost471.h','nes_cost471.c']:shutil.copyfile(ROOT/'src/nes/experimental471'/n,d/n)
def once(s,x,y):assert s.count(x)==1,(x[:70],s.count(x));return s.replace(x,y,1)
for n,fn,signature in [('nes_game149_spi.inc','nes_game149_transfer','const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]'),('nes_native165_bulk.inc','nes_native165_bulk','const struct nes_rom_spi_io *io,const uint8_t *tx,uint8_t *rx,unsigned count')]:
 f=d/n;s=f.read_text(encoding='utf8');s='#include "nes_cost471.h"\n'+s;s=once(s,'bool '+fn+'(', 'static bool '+fn+'_inner471(')
 count='8' if fn=='nes_game149_transfer' else 'count';s+='\nbool '+fn+'('+signature+'){\n uint32_t t=nes_cost471_now();bool ok='+fn+'_inner471(io,tx,rx'+('' if count=='8' else ',count')+');\n nes_cost471_op(tx?tx[0]:255,'+count+',t);return ok;\n}\n';f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_runtime_board165.inc';s=f.read_text(encoding='utf8');s='#include "nes_cost471.h"\n'+s;s=once(s,' (void)io;\n struct {',' (void)io;nes_cost471_scene_crc=content_epoch;nes_cost471_begin();\n struct {');s=once(s,' while(nes_runtime165_step(&native_runtime165)){}',' while(nes_runtime165_step(&native_runtime165)){}\n nes_cost471_end();');f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_native_runtime165.c';s=f.read_text(encoding='utf8');s='#include "nes_cost471.h"\n'+s;s=once(s,' struct nes_native165 *r=s->receiver;',' uint32_t cost_mark471;\n struct nes_native165 *r=s->receiver;');s=s.replace(' nes_trace166.mark_tick=s->ticks(s->ctx);',' cost_mark471=nes_cost471_now();nes_trace166.mark_tick=s->ticks(s->ctx);')
for k,n in enumerate(['RECEIVE','PLAN','SEAL']):
 old=f' nes_budget210_time(B210_{n},s->ticks(s->ctx)-nes_trace166.mark_tick);';s=once(s,old,old+f'nes_cost471_phase({k},cost_mark471);')
f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_native165.c';s=f.read_text(encoding='utf8');s='#include "nes_cost471.h"\n'+s
s=once(s,' if(!fn(ctx,tx,rx,n+3)||crc16(rx+1,n)!=(uint16_t)((rx[n+1]<<8)|rx[n+2]))return fail(s,23);',' if(!fn(ctx,tx,rx,n+3)){nes_cost471_transfer_stops++;return fail(s,23);}\n if(crc16(rx+1,n)!=(uint16_t)((rx[n+1]<<8)|rx[n+2])){nes_cost471_crc_errors++;return fail(s,23);}')
f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_budget210.c';s=f.read_text(encoding='utf8');s='#include "nes_cost471.h"\n'+s;assert s.count(' return n;')==1;s=s.replace(' return n;',' return nes_cost471_append(text,size,n);');f.write_text(s,encoding='utf8',newline='\n')
print('471 ARM source codec, per-op and nested phases, separate CRC/deadline counters prepared')
