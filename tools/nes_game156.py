# SPDX-License-Identifier: MIT
"""Materialize sound-channel isolation plus completed-pad-read trace from155."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out,arm=False):
 e=baseline/'nes-game155/evidence'
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game155-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 if arm:names=list(json.loads((e/'arm/preparation155.json').read_bytes())['copied'])
 else:names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,count=1):
  p=out/n;s=p.read_text();assert s.count(a)==count,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 added={}
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x64','rx[1]!=0x65',1),('nes_rom_verify.c','rx[1]==0x64','rx[1]==0x65',1),('nes_rom_verify.c','rx[1]!=0x64','rx[1]!=0x65',1),('nes_run136.inc','candidate->board_id=0x64','candidate->board_id=0x65',1),('nes_run136.inc','0xde','0xdf',6),('nes_menu_diagnostic.c','155','156',7),('nes_menu_diagnostic.c','board_expected_hex=64','board_expected_hex=65',1),('nes_checkpoint112.c','155','156',2),('VERSION','NES-GAME155-DEV','NES-GAME156-DEV',1)]:edit('src/'+n,a,b,c)
  edit('src/nes_run136.h',' bool start_sent,stop_ok,passed;', ''' uint32_t pad_ticks[16];uint8_t pad_buttons[16];
 uint16_t pad_total;uint8_t pad_valid,pad_count,pad_flags;
 bool start_sent,stop_ok,passed;''')
  helper=(ROOT/'src/nes/diagnostics/nes_pad_trace156.inc').read_text()
  edit('src/nes_run136.inc','static bool identify136(',helper+'\nstatic bool identify136(')
  edit('src/nes_run136.inc',' nes_run136.error=nes_run136.first_error?', ' (void)pad156(io); /* auxiliary only, after STOP; never SD during RUN */\n nes_run136.error=nes_run136.first_error?')
  edit('src/nes_menu_diagnostic.c','char text[1156]','char text[3072]')
  edit('src/nes_menu_diagnostic.c',' printf("%s",text);', ''' n=pad156_format(text,sizeof(text),n);
 if(n<=0||(size_t)n>=sizeof(text))return;
 printf("%s",text);''')
  helper=(ROOT/'src/nes/diagnostics/nes_pad_format156.inc').read_text()
  edit('src/nes_menu_diagnostic.c','static void save_report(',helper+'\nstatic void save_report(')
 else:
  edit('rtl/nes.v','.CS             (apu_cs),',".CS             (apu_cs && (cpu_rnw || addr[4:0]==5'h17)), //156 channel-write isolation; frame counter/read path retained")
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h64,","snapshot<={8'h65,",2),('nes_run_observer134.sv',"8'hde","8'hdf",5),('nes_screen_status151.sv',"8'hde","8'hdf",1)]:edit(n,a,b,c)
  edit('nes_game_pad150.sv','input wire strobe,read_clock,output wire serial','input wire strobe,read_clock,output wire serial,\n output reg trace_valid,output reg [7:0] trace_buttons')
  edit('nes_game_pad150.sv',' reg old_read;',' reg old_read;\n reg [3:0] trace_bits;reg [7:0] trace_shift;')
  edit('nes_game_pad150.sv','shift<=0;old_read<=0;','shift<=0;old_read<=0;trace_bits<=0;trace_shift<=0;trace_valid<=0;trace_buttons<=0;')
  edit('nes_game_pad150.sv','   request_meta<=request_toggle;', '''   trace_valid<=0;
   if(strobe)begin trace_bits<=0;trace_shift<=0;end
   else if(old_read && !read_clock && trace_bits<8)begin
    trace_shift<={serial,trace_shift[7:1]};trace_bits<=trace_bits+1'b1;
    if(trace_bits==7)begin trace_buttons<={serial,trace_shift[7:1]};trace_valid<=1;end
   end
   request_meta<=request_toggle;''')
  edit('fxpak_nes_screen137_top.sv',' wire [1:0] pad_clock;', ' wire pad_trace_valid;wire [7:0] pad_trace_buttons;\n wire [1:0] pad_clock;')
  edit('fxpak_nes_screen137_top.sv','.serial(pad_serial));','.serial(pad_serial),.trace_valid(pad_trace_valid),.trace_buttons(pad_trace_buttons));')
  edit('fxpak_nes_screen137_top.sv',' nes_run_observer134 observer(', ' nes_run_observer134 observer(.pad_event(pad_trace_valid),.pad_buttons(pad_trace_buttons),')
  edit('nes_run_observer134.sv',' input wire clk,reset,core_reset,cpu_sample,rom_fault,',' input wire clk,reset,core_reset,cpu_sample,rom_fault,\n input wire pad_event,input wire [7:0] pad_buttons,')
  edit('nes_run_observer134.sv',' reg [7:0] reply;', ''' reg [1:0] pad_pending;
 wire [55:0] pad_page;
 nes_pad_trace156 trace(.clk(clk),.reset(reset),.active(!core_reset),.freeze(fault_trigger),
  .event_valid(pad_event),.buttons(pad_buttons),.command(command),.page(pad_page));
 reg [7:0] reply;''')
  edit('nes_run_observer134.sv','samples<=0;sticky_fault<=0;', 'pad_pending<=0;samples<=0;sticky_fault<=0;')
  edit('nes_run_observer134.sv','   sck_previous<=sck_sync[1];', '   sck_previous<=sck_sync[1];\n   pad_pending<={pad_pending[0],1\'b0};\n   if(pad_pending[1])snapshot<=pad_page;')
  edit('nes_run_observer134.sv',"command==8'h75)","command==8'h75 || command==8'h76 || command[7:4]==4'h8)")
  edit('nes_run_observer134.sv',"       case(incoming)","       if(incoming==8'h76 || incoming[7:4]==4'h8)pad_pending<=1;\n       else case(incoming)")
  n='nes_pad_trace156.sv';shutil.copy2(ROOT/'src/nes/diagnostics'/n,out/n);added[n]=sha(out/n)
  qsf=out/'board.qsf'
  qsf.write_text(qsf.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_pad_trace156.sv\nset_global_assignment -name ROUTER_TIMING_OPTIMIZATION_LEVEL MAXIMUM\n')
  sdc=out/'board.sdc'
  sdc.write_text(sdc.read_text()+'\n'+(ROOT/'src/nes/diagnostics/nes_game156_budget.sdc').read_text())
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation156.json' if arm else 'materialization156.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added=added,ids=['65','DF'],physical=False),indent=2)+'\n')
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
