"""Instrument the final MMC872 and MMC897 links, leaving their output schedulers intact."""
import sys
from nes_raw506 import once
from prepare_nes_frame900 import PARENTS, PROBES, WORK
from prepare_nes_trial802 import rename_edition

HEADER='''
#ifndef NES_FRAME900_H
#define NES_FRAME900_H
#include <stdint.h>
struct row900 { uint16_t tick,gen,bg,input_age,e0_age,probe; uint8_t obj,dirty,valid,bank;
 uint8_t wire[26]; };
_Static_assert(sizeof(struct row900)==42,"trace ABI");
struct log900 {uint16_t magic,edition,mode,used,drop[2],row_size,capacity;struct row900 rows[194];};
_Static_assert(sizeof(struct log900)<=8192,"menu scratch");
extern uint32_t ptrcache[];
#define log900p ((struct log900 *)(void *)ptrcache)
extern unsigned char mode900;
void input900(uint16_t);
void e0900(uint16_t,unsigned);
int read900(uint8_t *);
#endif
'''
CORE='''
unsigned char mode900;
static struct mark900 {uint32_t clock;uint16_t gen,valid;} in900[2],ack900;
static unsigned latest900;
void input900(uint16_t g){
 latest900^=1;in900[latest900]=(struct mark900){nes_cost471_now(),g,1};
}
void e0900(uint16_t g,unsigned bank){
 if(!ack900.valid || ack900.gen!=g)ack900=(struct mark900){nes_cost471_now(),g,1+(bank<<1)};
}
static void record900(uint32_t tick,const struct nes_native_video165 *v){
 unsigned w=(tick>=3000 && tick<3500)?1:(tick>=5500 && tick<6000)?2:0;
 if(!w || (mode900 && mode900!=3 && mode900!=w))return;
 struct log900 *log=log900p;
 if(log->used>=log->capacity){++log->drop[w-1];return;}
 struct row900 *r=&log->rows[log->used++];
 memset(r,0,sizeof *r);r->tick=tick;r->gen=v->generation;r->bg=v->bg_count;r->obj=v->obj_count;
 r->dirty=__builtin_popcountll(v->map_dirty);
 r->bank=ack900.valid>>1;
 unsigned i=in900[latest900].gen==r->gen?latest900:latest900^1;
 uint32_t t=nes_cost471_now(),a=(t-in900[i].clock)>>9,b=(t-ack900.clock)>>9;
 if(in900[i].valid && in900[i].gen==r->gen && a<=65535){r->input_age=a;r->valid|=1;}
 if(ack900.valid && ack900.gen==r->gen && b<=65535){r->e0_age=b;r->valid|=2;}
 if(mode900!=3 && read900(r->wire))r->valid|=4;
 r->probe=(nes_cost471_now()-t)>>9;
}
'''


def prepare(n):
    parent,_,arm,_=PARENTS[n]
    src=PROBES/arm/'src'
    dest=WORK/f'patch{n}'
    rename_edition(src,dest,parent,n)
    (dest/'nes_frame900.h').write_text(HEADER,newline='\n')
    def load(name):
        return '#include "nes_frame900.h"\n'+(src/name).read_text()
    def store(name,s):
        (dest/name).write_text(s,newline='\n')
    name='nes_budget210.c'
    s=once(load(name),'void nes_budget210_reset(void){',CORE+f'''
void nes_budget210_reset(void){{
 latest900=0;in900[0].valid=in900[1].valid=ack900.valid=0;
 memset(log900p,0,16);log900p->magic=0x9001;log900p->edition={n};
 log900p->row_size=sizeof(struct row900);log900p->capacity=194;log900p->mode=mode900;
''')
    s=once(s,' s->last_display=elapsed;',' record900(s->frame_start,v);\n s->last_display=elapsed;')
    store(name,once(s,'return nes_cost471_append(text,size,n);','return n;'))
    name='nes_native165.c'
    s=once(load(name),' if((s->state==NES_NATIVE165_RECEIVING &&',
           ' if(s->state==NES_NATIVE165_COMPLETE)input900(s->generation);\n if((s->state==NES_NATIVE165_RECEIVING &&')
    store(name,s)
    name='nes_sink_window184.c'
    s=once(load(name),'  /* Every retired',
           '  if(s->retired==s->sent && s->ever_sent && s->last[0]==3)e0900(s->last[8]|(s->last[9]<<8),(s->last[4]-1)&1);\n  /* Every retired')
    store(name,s)
    name='nes_runtime_board165.inc'
    store(name,load(name)+'''
int read900(uint8_t *rx){
 static const uint8_t query[26] __attribute__((section(".data.nes_trace_tx"),aligned(4)))={0x78};
 return nes_native165_bulk(native_io165,query,rx,sizeof query);
}
''')
    name='nes_menu_diagnostic.c'
    s='#include "nes_frame900.h"\n'+(dest/name).read_text()
    a=s.index('static int pad165_format')
    b=s.index('static __attribute__((noinline)) void write_report893' if parent==897 else 'static void save_report',a)
    s=s[:a]+s[b:]
    for fn in ('pad165_format','history165_format'):
        s=once(s,f' n={fn}(text,4096,n);','')
    s=once(s,' return !strcmp(name,"NES MMC3', ''.join(
        f' if(!strcmp(name,"NES {kind} {n}.nh1"))return {code};\n'
        for kind,code in [('EARLY',410),('LATE',411),('CONTROL',412)])+' return !strcmp(name,"NES MMC3')
    s=once(s,' nes_boot_probe798=(unsigned char)(selected-384);',
           ' mode900=selected>=410?(unsigned char)(selected-409):0;if(mode900)selected=384;\n nes_boot_probe798=(unsigned char)(selected-384);')
    path=f'"/sd2snes/nes-frame-mmc{n}.bin"'
    save=f'write_report893({path},"frames",(const char *)log900p,16+log900p->used*sizeof(struct row900));'
    if parent==872:
        save=f'''if(f_open(&log,{path},FA_CREATE_ALWAYS|FA_WRITE)==FR_OK){{
  UINT bytes=16+log900p->used*sizeof(struct row900);
  if(f_write(&log,log900p,bytes,&written)!=FR_OK || written!=bytes)printf("frame log short\\n");
  f_close(&log);
 }}'''
    s=once(s,' if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);',' '+save+'\n if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);')
    store(name,s)


if __name__=='__main__':prepare(int(sys.argv[1]))
