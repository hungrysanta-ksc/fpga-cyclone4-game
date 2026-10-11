# SPDX-License-Identifier: MIT
"""Add passive first-fault ROM history to frozen156; no service decisions changed."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out,arm=False):
 e=baseline/'nes-game156/evidence'
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game156-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation156.json').read_bytes())['copied']) if arm else re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,count=1):
  p=out/n;s=p.read_text();assert s.count(a)==count,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 added={}
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x65','rx[1]!=0x66',1),('nes_rom_verify.c','rx[1]==0x65','rx[1]==0x66',1),('nes_rom_verify.c','rx[1]!=0x65','rx[1]!=0x66',1),('nes_run136.inc','candidate->board_id=0x65','candidate->board_id=0x66',1),('nes_run136.inc','0xdf','0xe0',8),('nes_menu_diagnostic.c','156','157',8),('nes_menu_diagnostic.c','board_expected_hex=65','board_expected_hex=66',1),('nes_checkpoint112.c','156','157',2),('VERSION','NES-GAME156-DEV','NES-GAME157-DEV',1)]:edit('src/'+n,a,b,c)
  edit('src/nes_run136.h',' bool start_sent,stop_ok,passed;',' uint8_t history[16][12],history_valid,history_flags,history_count;\n bool start_sent,stop_ok,passed;')
  helper=(ROOT/'src/nes/diagnostics/nes_ppu_history157.inc').read_text()
  reader,formatter=helper.split('static int history157_format',1)
  edit('src/nes_run136.inc','static bool identify136(',reader+'\nstatic bool identify136(')
  edit('src/nes_run136.inc',' (void)pad156(io);',' (void)history157(io);\n (void)pad156(io);')
  edit('src/nes_menu_diagnostic.c','char text[3072]','char text[4096]')
  edit('src/nes_menu_diagnostic.c','static void save_report(','static int history157_format'+formatter+'\nstatic void save_report(')
  edit('src/nes_menu_diagnostic.c',' n=pad157_format(text,sizeof(text),n);',' n=pad157_format(text,sizeof(text),n);\n n=history157_format(text,sizeof(text),n);')
 else:
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h65,","snapshot<={8'h66,",2),('nes_run_observer134.sv',"8'hdf","8'he0",5),('nes_screen_status151.sv',"8'hdf","8'he0",1),('nes_pad_trace156.sv',"8'hdf","8'he0",2)]:edit(n,a,b,c)
  edit('nes_rom_service.sv',' output wire fault_trigger,',' output wire [11:0] history_flags157,\n output wire fault_trigger,')
  edit('nes_rom_service.sv',' //139 Parallel observation only.', ''' //157 Passive view: request,response,ready,busy,pending_ppu,cpu_need,
 // cpu_sample,ppu_sample,ppu_valid,hint_valid,use_prefetch,prefetch_hit.
 assign history_flags157={rom_request,rom_response,rom_ready,busy,pending_ppu,cpu_need,
                         cpu_sample,ppu_sample,ppu_valid,ppu_prefetch_valid,use_prefetch,prefetch_hit};
 //139 Parallel observation only.''')
  edit('nes_live_joint.sv','output wire out_fault_trigger,','output wire [95:0] out_history157,\noutput wire out_fault_trigger,')
  edit('nes_live_joint.sv','nes_rom_early rom_service(', 'wire [11:0] history_flags157;\nassign out_history157={scanline,cycle,history_flags157,rom_address,game148_hint_physical,ppumem_addr};\nnes_rom_early rom_service(.history_flags157(history_flags157),')
  edit('fxpak_nes_screen137_top.sv',' nes_live_joint core(', ' wire [95:0] history_sample157;\n nes_live_joint core(.out_history157(history_sample157),')
  edit('fxpak_nes_screen137_top.sv',' nes_run_observer134 observer(', ' nes_run_observer134 observer(.history_sample157(history_sample157),')
  edit('nes_run_observer134.sv',' input wire pad_event,',' input wire [95:0] history_sample157,\n input wire pad_event,')
  edit('nes_run_observer134.sv',' wire [55:0] pad_page;', ''' wire [55:0] pad_page,history_page157;
 nes_ppu_history157 history(.clk(clk),.reset(reset),.active(!core_reset),.freeze(fault_trigger),
  .sample(history_sample157),.command(command),.page(history_page157));''')
  edit('nes_run_observer134.sv',"command[7:4]==4'h8)","command[7:4]==4'h8 || command==8'h77 || command[7:5]==3'b101)")
  edit('nes_run_observer134.sv','if(pad_pending[1])snapshot<=pad_page;',"if(pad_pending[1])snapshot<=(command==8'h77 || command[7:5]==3'b101)?history_page157:pad_page;")
  edit('nes_run_observer134.sv',"incoming[7:4]==4'h8)","incoming[7:4]==4'h8 || incoming==8'h77 || incoming[7:5]==3'b101)")
  n='nes_ppu_history157.sv';shutil.copy2(ROOT/'src/nes/diagnostics'/n,out/n);added[n]=sha(out/n)
  q=out/'board.qsf';q.write_text(q.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_ppu_history157.sv\n')
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation157.json' if arm else 'materialization157.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added=added,ids=['66','E0'],physical=False),indent=2)+'\n')
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
