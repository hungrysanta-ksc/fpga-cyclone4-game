"""Materialize the diagnostic-only changes to the physical MMC925 firmware."""
import shutil
from prepare_nes_trial802 import PROBES, rename_edition
from nes_raw506 import once

WORK=PROBES/'nes-trial927'
HEADER='''
#ifndef NES_FRAME900_H
#define NES_FRAME900_H
#include <stdint.h>
struct row900 {
 uint16_t tick,gen,bg,input_age,e0_age,probe;
 uint8_t obj,dirty,valid,bank,wire[24];
 uint32_t cost[2][3];
};
struct log900 {
 uint16_t magic,edition,mode,used,drop[2],row_size,capacity;
 struct row900 rows[118];
 uint32_t bins[12][2][4],front[12];
 uint16_t displayed55,cycle_available;
 uint32_t prefetch_time[12];
 struct {uint32_t gen,cost[2][3];} pending[2];
};
_Static_assert(sizeof(struct row900)==64 && sizeof(struct log900)<=8192,"menu scratch");
extern uint32_t ptrcache[];
#define log900p ((struct log900 *)(void *)ptrcache)
extern unsigned char mode900,advance927;
void block927(unsigned,uint32_t,uint32_t,uint32_t);
void input900(uint16_t);
void e0900(uint16_t,unsigned);
int page905(uint8_t *,unsigned);
#endif
'''
COUNTERS='''
unsigned char advance927;
#define bygen927 (log900p->pending)
void block927(unsigned g,uint32_t read,uint32_t restore,uint32_t pop){
 unsigned slot=g&1;
 if(bygen927[slot].gen!=g){
  memset(&bygen927[slot],0,sizeof bygen927[slot]);bygen927[slot].gen=g;
 }
 uint32_t *row=bygen927[slot].cost[advance927];
 uint32_t *bin=log900p->bins[nes_budget210.bin][advance927];
 row[0]+=read;row[1]+=restore;row[2]+=pop;
 bin[0]+=read;bin[1]+=restore;bin[2]+=pop;bin[3]++;
}
'''


def prepare(*,regenerate=False):
    parent=PROBES/'nes-trial925/link'
    work=WORK/'link'
    if not regenerate:
        shutil.copytree(parent,work)
    src=work/'src'
    patch=WORK/'patch'
    if not regenerate:
        rename_edition(src,patch,925,927)
    for name in ('nes_budget210.c','nes_native165.c','nes_native_runtime165.c'):
        shutil.copyfile(parent/'src'/name,src/name)
    for file in patch.iterdir():
        shutil.copyfile(file,src/file.name)
    (src/'nes_frame900.h').write_text(HEADER,newline='\n')
    p=src/'nes_budget210.c'
    s=p.read_text()
    s=once(s,'uint32_t commit_clock915,step_begin915;uint16_t commit_gen915;',COUNTERS)
    s=once(s,'log900p->capacity=124','log900p->capacity=118')
    s=once(s,'latest900=0;', 'advance927=0;latest900=0;')
    s=once(s,'edition=925;','edition=927;log900p->cycle_available=nes_cost471_available;')
    s=once(s,' if(native_runtime165.plan.bulk_valid)memcpy(r->descriptor,native_runtime165.plan.bulk,12);',
           ' if(bygen927[r->gen&1].gen==r->gen){memcpy(r->cost,bygen927[r->gen&1].cost,sizeof r->cost);r->valid|=8;}')
    a=s.index(' if(mode900!=3 && page905')
    b=s.index(' r->probe=',a)
    s=s[:a]+''' if(mode900!=3 && page905(page,0)){
  memcpy(r->wire,page,sizeof r->wire);
  if(page[1]==0x97 && (page[2]|page[3]<<8)==r->gen)r->valid|=4;
 }
'''+s[b:]
    p.write_text(s,newline='\n')
    p=src/'nes_native165.c'
    s=p.read_text()
    for start, mark in [(' if(!fn(ctx,tx,rx,n+3))','uint32_t t0'),(' if(crc_xmodem_block(0xffff,rx+1,n)','uint32_t t1'),
                        (' nes_rom_spi_frame(tx,0xd2,tok,0);','uint32_t t2')]:
        s=once(s,start,' '+mark+'=nes_cost471_now();\n'+start)
    s=once(s,' if(s->state==NES_NATIVE165_COMPLETE)input900',
           ' block927(s->generation,t1-t0,t2-t1,nes_cost471_now()-t2);\n if(s->state==NES_NATIVE165_COMPLETE)input900')
    p.write_text(s,newline='\n')
    p=src/'nes_native_runtime165.c'
    s=p.read_text()
    s=once(s,'   if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);',
           '   uint32_t start927=nes_cost471_now();advance927=1;bool received927=nes_native165_poll(r,transfer,s);advance927=0;\n   log900p->prefetch_time[nes_budget210.bin]+=nes_cost471_now()-start927;\n   if(!received927)return fail(s,NES_RUNTIME165_RECEIVE);')
    s=once(s,' nes_trace166.receive_ticks+=',' log900p->front[nes_budget210.bin]+=nes_cost471_now()-cost_mark471;\n nes_trace166.receive_ticks+=')
    s=once(s,'  step_begin915=cost_mark471;','')
    s=once(s,'commit_clock915=cost_mark471;commit_gen915=r->generation;','')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','proof','replay'),nargs='?',default='prepare')
    parser.add_argument('path',type=Path,nargs='?',help='licensed game for proof, or existing replay root')
    args=parser.parse_args()
    if args.action=='prepare':
        prepare()
    elif args.path is None:
        parser.error('proof and replay require a path')
    elif args.action=='proof':
        from check_nes_supply905_arm import run
        run(args.path,WORK,927)
    else:
        from nes_window924 import replay
        for phase in (1,2):
            for cold in (False,True):
                replay(args.path,'objheader',phase,cold,arm=WORK,edition=927,tag='927final')
