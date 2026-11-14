"""Frame-start scoped diagnostic. Emit binary rows only after safe base recovery."""
from argparse import ArgumentParser
from pathlib import Path
import json
from prepare_nes_trial763 import PROBES, ROOT, LABELS, digest

HEADER = """
#ifndef NES_FRAME769_H
#define NES_FRAME769_H
#include <stdint.h>
#include <stdbool.h>
struct row769 {
 uint16_t tick, generation, obj, bg;
 uint8_t dirty, flags, beam[3], calls[9], changed[9], output_active, output[4];
};
_Static_assert(sizeof(struct row769)==36,"diagnostic row");
extern struct row769 *live769;
extern uint16_t count769, dropped769;
extern uint32_t ptrcache[];
void begin769(unsigned tick);
void poll769(unsigned reason, bool changed);
bool sample769(uint16_t generation);
#endif
"""

STORAGE = """
/* The menu sorter reloads ptrcache from SRAM on every sort. It cannot run
 * inside the NES session. Persist rows before re-enabling the menu. */
struct row769 *live769;
uint16_t count769,dropped769;
void begin769(unsigned tick){
 live769=0;
 if(tick<2500 || tick>=3000)return;
 if(count769>=8192u/sizeof(struct row769)){++dropped769;return;}
 live769=(struct row769 *)((uint8_t *)(void *)ptrcache+sizeof(struct row769)*count769++);
 memset(live769,0,sizeof(*live769));
 live769->tick=tick;
}
void poll769(unsigned reason,bool changed){
 if(!live769)return;
 if(live769->output_active){
  unsigned lane=reason<5?0:2;
  if(live769->output[lane]==255)live769->flags|=2;
  else {++live769->output[lane];if(changed)++live769->output[lane+1];}
 }
 if(live769->calls[reason]==255){live769->flags|=2;return;}
 ++live769->calls[reason];
 if(changed)++live769->changed[reason];
}
"""

def prepare(out,base,number,opt,long_run=False):
    src=PROBES/("nes-trial763/linked763/src" if base==763 else "nes-timer767/arm/src")
    a=json.loads((ROOT/"analysis/trial763-package.json").read_bytes())["variants"]["763"]
    b=json.loads((ROOT/"analysis/trial767-package.json").read_bytes())
    assert digest(src/"obj-nes-100/firmware.stm")== (a if base==763 else b)["firmware"]
    out.mkdir(parents=True,exist_ok=False)
    def write(name,text):
        (out/name).write_text(text,encoding="utf8",newline="\n")
    def source(name):
        return (src/name).read_text()
    write("nes_frame769.h",HEADER)
    for name in LABELS:
        write(name,source(name).replace(str(base),str(number)))
    name="nes_budget210.c"
    s=source(name).replace("void nes_budget210_reset(void){","void nes_budget210_reset(void){live769=0;count769=dropped769=0;")
    s=s.replace(" s->frame_start=elapsed;", " begin769(elapsed);\n s->frame_start=elapsed;")
    s=s.replace(" uint64_t mask=v->map_dirty;", """ if(live769){
  live769->generation=v->generation;live769->bg=v->bg_count;live769->obj=v->obj_count;
  live769->dirty=__builtin_popcountll(v->map_dirty);
 }
 uint64_t mask=v->map_dirty;""")
    if long_run:
        old = PROBES/"nes-trial763/linked766/src/nes_budget210.c"
        block=old.read_text().split(" if((uint32_t)(elapsed-s->epoch693)>=6000u)",1)[1].split("s->open=true;",1)[0]
        start=s.index(" begin769(elapsed);")
        stop=s.index("s->open=true;",start)
        s=s[:start]+" begin769(s->comparison_closed693 ? 6000u : elapsed);\n if((uint32_t)(elapsed-s->epoch693)>=6000u)"+block+s[stop:]
    # Diagnostic replaces verbose startup & per-op DWT printout, retains ordinary
    # timing bins, physical flags and comparison windows in a compact report.
    a=s.index(' int n=nes_report623(text,size,0,"budget_schema');b=s.index(' for(unsigned i=0;i<12;i++){',a)
    s=s[:a]+''' int n=nes_report623(text,size,0,"frame769=1\\ntick_ms=10\\ndisplay_5_40_55=%lu,%lu\\nrows=%u\\ndropped=%u\\n",
    (unsigned long)nes_budget210.displayed_window[0],(unsigned long)nes_budget210.displayed_window[1],count769,dropped769);
'''+s[b:]
    assert "displayed_window" in source(name)
    s=s.replace("return nes_cost471_append(text,size,n);","return n;")
    write(name,'#include "nes_frame769.h"\n'+s+STORAGE)
    name="nes_sink_window184.c"
    s=source(name).replace("static bool status(struct nes_sink_window184 *s,uint8_t ack[12])",
                            "static bool status(struct nes_sink_window184 *s,uint8_t ack[12],unsigned reason)")
    assert s.count("status(s,ack)")==4
    for reason in ("0","0","1","s->last[0]==3?3:(s->sent==before?4:2)"):
        s=s.replace("status(s,ack)",f"status(s,ack,{reason})",1)
    s=s.replace(" s->status_flags=rx[2];"," unsigned old_flags=s->status_flags;\n s->status_flags=rx[2];")
    s=s.replace(" s->retired=r;", " poll769(reason,delta!=0 || ((old_flags^rx[2])&8)!=0);\n s->retired=r;")
    write(name,'#include "nes_frame769.h"\n'+s)
    name="nes_plan_service200.c"
    s=source(name)
    a=s.index(" return true;",s.index("static bool read509"))
    s=s[:a]+''' /* Classify a checked wire response by its phase and descriptor token.
  * REARM progress is the empty/new epoch acknowledgement. */
 poll769(4+phase,phase==NES_PLAN215_REARM ? rx[3]==1 :
         phase==NES_PLAN215_RETIRE ? rx[3]==2 :
         (rx[6] && (!p->bulk_valid || memcmp(rx+6,p->bulk,12))) || (rx[3]&2));
'''+s[a:]
    write(name,'#include "nes_frame769.h"\n'+s)
    name="nes_native_runtime165.c"
    s=source(name).replace("  nes_native165_consumed(r); /* Final ACK", """  if(live769){
   if(!sample769(s->generation))return fail(s,NES_RUNTIME165_IO);
   live769=NULL;
  }
  nes_native165_consumed(r); /* Final ACK""")
    start="  if(!nes_sink212_seal("
    end="  nes_trace166.seal_ticks+="
    assert s.count(start)==s.count(end)==1
    s=s.replace(start,"  if(live769)live769->output_active=1;\n"+start)
    s=s.replace(end,"  if(live769)live769->output_active=0;\n"+end)
    assert 'sample769' in s
    write(name,'#include "nes_frame769.h"\n'+s)
    name="nes_runtime_board165.inc"
    s=source(name)+"""
bool sample769(uint16_t generation){
 uint8_t tx[8]={0x78},rx[8]={0};
 if(!nes_rom_spi_transfer(native_io165,tx,rx))return false;
 if(rx[1]==0x78 && rx[2]==(uint8_t)generation && rx[6]==0x5a && rx[7]==0xa5){
  memcpy(live769->beam,rx+3,3);live769->flags|=1;
 }
 return true;
}
"""
    if long_run:
        assert base==767
        a=s.index(" if(native_runtime165.receiver&&")
        b=s.index(" if(!native_first165",a)
        s=s[:a]+s[b:]
    write(name,'#include "nes_frame769.h"\n'+s)
    name="nes_menu_diagnostic.c"
    s=(out/name).read_text()
    target=" if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);"
    assert s.count(target)==1
    s=s.replace(target, f''' if(f_open(&log,"/sd2snes/nes-frame-mmc{number}.bin",FA_CREATE_ALWAYS|FA_WRITE)==FR_OK){{
  UINT length=count769*sizeof(struct row769);
  FRESULT result=f_write(&log,ptrcache,length,&written);
  if(result!=FR_OK || written!=length)printf("frame log write failed\\n");
  f_close(&log);
 }}
'''+target)
    write(name,'#include "nes_frame769.h"\n'+s)
    if opt:
        write("nes_native_sink165.c",coalesce(source("nes_native_sink165.c")))

def coalesce(s):
    wait="    if(!w->wait(w->ctx,w->guard,4,false))return fail(s,5);"
    assert s.count(wait)==1
    return s.replace(wait,wait+"\n"+wait)

if __name__=="__main__":
    a=ArgumentParser()
    a.add_argument("base",type=int,choices=(763,767))
    a.add_argument("number",type=int)
    a.add_argument("out",type=Path)
    a.add_argument("--coalesce",action="store_true")
    a.add_argument("--long",action="store_true")
    o=a.parse_args()
    prepare(o.out,o.base,o.number,o.coalesce,o.long)
