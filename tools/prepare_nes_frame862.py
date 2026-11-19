"""Build the passive DMA observer around the original MMC855 or MMC860 client."""
import argparse
import shutil
from pathlib import Path
from prepare_nes_trial802 import PROBES, rename_edition
from prepare_nes_trial816 import fit

ROOT=Path(__file__).resolve().parents[1]
WORK=PROBES/'nes-frame862'
PARENTS={862:855,863:860}


def replace(path,a,b):
    s=path.read_text()
    assert s.count(a)==1,(path,a)
    path.write_text(s.replace(a,b),newline='\n')


def board(temp, edition):
    src=temp/f'nes-trial816-board{PARENTS[edition]}'
    out=temp/f'nes-trial816-board{edition}'
    out.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,out/sub)
    for p in src.iterdir():
        if p.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(p,out/p.name)
    shutil.copyfile(ROOT/'tests/nes-functional/nes_frame862.sv',out/'nes_frame862.sv')
    qsf=out/'board.qsf'
    pins=[s for s in (ROOT/'src/fpga/pin.qsf').read_text().splitlines()
          if ('SNES_PA_IN[' in s or 'SNES_PAWR_IN' in s) and
          ('set_location_assignment' in s or 'IO_STANDARD' in s)]
    assert len(pins)==18
    with qsf.open('a') as f:
        f.write('\n'+'\n'.join(pins)+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_frame862.sv\n')
    top=out/'fxpak_nes_screen137_top.sv'
    replace(top,'input wire CLKIN,SNES_SYSCLK,','input wire CLKIN,SNES_SYSCLK,SNES_PAWR_IN,input wire [7:0] SNES_PA_IN,')
    replace(top,'nes_screen_status151 screen_status(','nes_screen_status151 screen_status(.pawr_n(SNES_PAWR_IN),.port_id(SNES_PA_IN),')
    # Borrow only auxiliary post-STOP diagnostic histories; retain first fault, live input and STOP.
    obs=out/'nes_run_observer134.sv'
    s=obs.read_text()
    a=s.index(' nes_ppu_history157 history(')
    b=s.index(' reg [7:0] reply;',a)
    obs.write_text(s[:a]+" assign pad_page=56'd0,history_page157=56'd0;\n"+s[b:],newline='\n')
    p=out/'nes_screen_status151.sv'
    replace(p,'input wire clk,reset,active,','input wire clk,reset,active,pawr_n,input wire [7:0] port_id,')
    replace(p,'reg [3:0] byte_count','reg [5:0] byte_count')
    replace(p,'byte_count!=9','byte_count!=63')
    replace(p,"command==8'h73&&","(command==8'h73||command==8'h78)&&")
    replace(p,'  case(byte_count)',"  if(command==8'h78)reply=trace_reply;else case(byte_count)")
    replace(p,' assign selected=',""" (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] pawr_sync;
 reg pawr_prev;
 reg [7:0] pa_meta,pa_sync,pa_prev;
 reg [15:0] trace_generation;
 always @(posedge clk)begin
  pawr_sync<={pawr_sync[0],pawr_n};pawr_prev<=pawr_sync[1];
  pa_meta<=port_id;pa_sync<=pa_meta;pa_prev<=pa_sync;
  if(qualified && addr_previous==24'h006018)trace_generation[7:0]<=data_previous;
  if(qualified && addr_previous==24'h006019)trace_generation[15:8]<=data_previous;
 end
 wire pa_end=pawr_sync[1]&&!pawr_prev;
 wire head_read=rd_sync[1]&&!rd_previous && addr_previous==24'h400000 && data_previous==3;
 wire [7:0] trace_reply;
 nes_frame862 trace(.clk(clk),.reset(reset),.active(active_sync[1]),.head(head_read),
   .show(pa_end && pa_prev==0),
   .ack(qualified && addr_previous==24'h00601c && data_previous==8'ha5),
   .e0_end(ss_sync[1] && command==8'he0),
   .beat(pa_end && !rd_previous && addr_previous[23:16]==8'h7f),
   .source(addr_previous[15:0]),.port_id(pa_prev),.generation(trace_generation),
   .read_byte(byte_count-6'd7),.reply(trace_reply));
 assign selected=""")


HEADER="""
#ifndef NES_FRAME862_H
#define NES_FRAME862_H
#include <stdint.h>
struct frame862 {
 uint32_t start,rx,finish,probe;
 uint16_t tick,gen,bg,obj;
 uint8_t dirty,seal,good,bank,wire[44];
};
_Static_assert(sizeof(struct frame862)==72,"trace layout");
extern uint8_t control862;
extern struct frame862 *row862;
extern unsigned short count862,drop862;
extern uint32_t ptrcache[];
void read862(struct frame862 *);
#endif
"""


def arm(edition):
    parent=PARENTS[edition]
    src=PROBES/f'nes-trial{parent}/link/src'
    out=WORK/f'patch{edition}'
    rename_edition(src,out,parent,edition)
    (out/'nes_frame862.h').write_text(HEADER,newline='\n')
    for name in ('nes_budget210.c','nes_native_runtime165.c','nes_sink_window184.c','nes_runtime_board165.inc'):
        (out/name).write_text('#include "nes_frame862.h"\n'+(src/name).read_text(),newline='\n')
    p=out/'nes_budget210.c'
    replace(p,'void nes_budget210_reset(void){','''struct frame862 *row862;
unsigned short count862,drop862;
uint8_t control862;
void nes_budget210_reset(void){row862=0;count862=drop862=0;''')
    replace(p,' s->frame_start=elapsed;', ''' row862=0;
 if(elapsed>=3500 && elapsed<4000){
  if(count862<8192/sizeof(struct frame862)){
   row862=(struct frame862 *)(void *)ptrcache+count862++;
   memset(row862,0,sizeof *row862);
   row862->tick=elapsed;
  }else ++drop862;
 }
 s->frame_start=elapsed;''')
    replace(p,' s->last_display=elapsed;', ''' if(row862){
  row862->gen=v->generation;row862->bg=v->bg_count;row862->obj=v->obj_count;
  row862->dirty=__builtin_popcountll(v->map_dirty);
  if(!control862)read862(row862);
  row862=0;
 }
 s->last_display=elapsed;''')
    # Monitor firmware keeps game-last, progress, existing bins and rates;
    # reserve Flash by omitting the full-session per-op text appendix.
    replace(p,'return nes_cost471_append(text,size,n);','return n;')
    p=out/'nes_native_runtime165.c'
    replace(p,'  if(!nes_sink212_seal','  if(row862){row862->start=cost_mark471;row862->bank=s->resident->target;}\n  if(!nes_sink212_seal')
    replace(p,'nes_cost471_phase(2,cost_mark471);','nes_cost471_phase(2,cost_mark471);\n  if(row862)row862->finish=nes_cost471_now();')
    p=out/'nes_sink_window184.c'
    replace(p,'#include "nes_sink_window184.h"','#include "nes_sink_window184.h"\n#include "nes_cost471.h"')
    replace(p,'if(!io(s,tx,rx,20))return false;', '''if(!io(s,tx,rx,20))return false;
 if(row862 && row862->seal && !row862->good)row862->rx=nes_cost471_now();''')
    replace(p,'  /* Every retired', '''  if(row862 && row862->seal && s->retired==s->sent && s->last[0]==3)row862->good=1;
  /* Every retired''')
    replace(p,' if(!send(s,p,n))return false;', ''' if(!send(s,p,n))return false;
 if(row862 && p[0]==3)row862->seal=n-16;''')
    p=out/'nes_runtime_board165.inc'
    with p.open('a') as f:
        f.write('''
void read862(struct frame862 *r){
 uint8_t tx[44]={0x78};
 uint32_t t=nes_cost471_now();
 if(!nes_native165_bulk(native_io165,tx,r->wire,sizeof tx))r->good=0;
 r->probe=nes_cost471_now()-t;
}
''')
    p=out/'nes_menu_diagnostic.c'
    s=p.read_text()
    p.write_text('#include "nes_frame862.h"\n'+s,newline='\n')
    replace(p,' return !strcmp(name,"NES MMC3',f' if(!strcmp(name,"NES CONTROL {edition}.nh1"))return 387;\n return !strcmp(name,"NES MMC3')
    replace(p,' nes_boot_probe798=(unsigned char)(selected-384);',' control862=(selected==387);\n if(control862)selected=384;\n nes_boot_probe798=(unsigned char)(selected-384);')
    # Both observer memories were repurposed in the fitted diagnostic board.
    s=p.read_text()
    begin=s.index('static int pad165_format')
    end=s.index('static void save_report',begin)
    p.write_text(s[:begin]+s[end:],newline='\n')
    replace(p,' n=pad165_format(text,4096,n);','')
    replace(p,' n=history165_format(text,4096,n);','')
    replace(p,' if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);',f''' if(f_open(&log,control862?"/sd2snes/nes-frame-ctl{edition}.bin":"/sd2snes/nes-frame-mmc{edition}.bin",FA_CREATE_ALWAYS|FA_WRITE)==FR_OK){{
  uint16_t header[4]={{0x8621,{edition}|(control862?0x8000:0),count862,drop862}};
  if(f_write(&log,header,sizeof header,&written)==FR_OK && written==sizeof header)
   f_write(&log,ptrcache,count862*sizeof(struct frame862),&written);
  f_close(&log);
 }}
 if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);''')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('board','fit','arm'))
    p.add_argument('edition',type=int,choices=PARENTS)
    p.add_argument('temp',type=Path)
    p.add_argument('--work',type=Path,default=WORK)
    a=p.parse_args()
    WORK=a.work
    if a.action=='board':
        board(a.temp,a.edition)
    elif a.action=='fit':
        fit(a.temp,a.edition,Path('C:/altera_lite/25.1std/quartus/bin64'))
    else:
        arm(a.edition)
