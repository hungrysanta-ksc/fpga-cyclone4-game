# SPDX-License-Identifier: MIT
"""Reuse the existing96-bit history RAM for the pre-BEGIN admission boundary.

Only one new sticky bit (a producer COMMIT was seen); no control feedback,
timing exception, bus command or extra payload RAM. Schema changes explicitly.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def transform(name,s):
 def rep(a,b):
  nonlocal s
  assert s.count(a)==1,(name,a,s.count(a));s=s.replace(a,b)
 if name=='nes_native_export165.sv':
  rep(' output wire busy,output reg [3:0] error',' output wire [3:0] observe_state173,\n output wire busy,output reg [3:0] error')
  rep(' assign busy=state!=IDLE;',' assign observe_state173=state;\n assign busy=state!=IDLE;')
 elif name=='nes_live_joint.sv':
  rep('output wire out_native_spi_fault,','output wire out_native_spi_fault,out_history_freeze173,')
  rep('assign out_history157={scanline,cycle,history_flags157,rom_address,game148_hint_physical,ppumem_addr};','''//173 schema A3. Existing history RAM freezes on first admission rejection
// AFTER a producer COMMIT, or ROM fault/STOP through the existing observer.
// No captured value participates in core, arbiter, exporter or sink control.
assign out_history157={8'ha3,native_generation,native_errors,native_export_state173,
 native_initialized,native_active,native_frame_owned,native_geometry_valid,
 native_fill_busy,native_fill_done,native_fill_success,native_fill_error,
 native_export_error,native_row_count,native_group_count,native_object_count,native_palette_count};
reg native_committed173;
always @(posedge clk)begin
 if(reset)native_committed173<=0;
 else if(native_tx_valid && native_tx_ready && native_tx_data[95:93]==7 && native_tx_data[76:64]==3)native_committed173<=1;
end
assign out_history_freeze173=native_committed173 && native_release_frame && native_export_error==2;''')
  rep('wire native_host_valid;','wire [3:0] native_export_state173;\nwire native_host_valid;')
  rep('nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(', 'nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(\n .observe_state173(native_export_state173),')
 elif name=='nes_run_observer134.sv':
  rep(' input wire [95:0] history_sample157,',' input wire history_freeze173,\n input wire [95:0] history_sample157,')
  rep('nes_ppu_history157 history(.clk(clk),.reset(reset),.active(!core_reset),.freeze(fault_trigger),','nes_ppu_history157 history(.clk(clk),.reset(reset),.active(!core_reset),.freeze(fault_trigger || history_freeze173),')
 elif name=='fxpak_nes_screen137_top.sv':
  rep(' wire [95:0] history_sample157;',' wire [95:0] history_sample157;wire history_freeze173;')
  rep('nes_live_joint core(', 'nes_live_joint core(.out_history_freeze173(history_freeze173),')
  rep('nes_run_observer134 observer(', 'nes_run_observer134 observer(.history_freeze173(history_freeze173),')
 else:raise ValueError(name)
 return s

CHANGED=['nes_native_export165.sv','nes_live_joint.sv','nes_run_observer134.sv','fxpak_nes_screen137_top.sv']
def prepare(prior,client,out):
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p)
 for n in CHANGED:(out/n).write_text(transform(n,(out/n).read_text()),encoding='utf-8',newline='\n')
 assert sha(client/'sink-program.hex')=='e1c350b76fea340a1ed9fa643929ce80bd0371b748b374d57ce8d90d85188fc5'
 shutil.copy2(client/'sink-program.hex',out/'sink-program.hex')
 r={'sources':{n:sha(out/n) for n in pins},'baseline':pins,'changed':CHANGED+['sink-program.hex'],'public_sources':{'tools/nes_admission173.py':sha(Path(__file__))},'history_schema':'A3/native173','save_sram_used':False,'datapath_control_changed':False}
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','client','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.prior,a.client,a.out)
