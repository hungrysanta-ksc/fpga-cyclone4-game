# SPDX-License-Identifier: MIT
"""Materialize a small first-fault PPU snapshot from exact released152 RTL."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out):
 e=baseline/'nes-game152/evidence'
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game152-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 qsf=(e/'asm/board.qsf').read_text()
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',qsf)
 inputs={};changes=[]
 for n in names+['board.sdc','game-program.hex']:
  src=e/'asm'/n;assert sha(src)==pins['asm/'+n]
  dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);inputs[n]=sha(src)
 def edit(n,old,new,count=1):
  p=out/n;s=p.read_text();assert s.count(old)==count,(n,old,s.count(old));p.write_text(s.replace(old,new),encoding='utf8',newline='\n')
 # Pure observation. All fields originate in the NES clock domain. No core
 # state, ROM request, cache, data, timing or mapper decision is changed.
 edit('rtl/ppu.sv','output wire [13:0] game148_hint_logic,','output wire [63:0] ppu_fault_state154,\noutput wire [13:0] game148_hint_logic,')
 edit('rtl/ppu.sv',"assign game148_hint_logic={1'b0,bg_patt1,bg_name_table[7:4],vram_din};", """assign game148_hint_logic={1'b0,bg_patt1,bg_name_table[7:4],vram_din};
//154 fault-only observation: line9/dot9/bg1/sprite1/render1/ALE1/read5/write5/
// vram14/latch8/pins8/hint1/address-valid1 =64. Captured by observer on fault.
assign ppu_fault_state154={scanline,cycle,bg_patt1,sprite_load_en,is_rendering_d,ALE,
 read_2007_delayed,write_2007_delayed,vram_a,vram_a_byte,vram_pins,
 game147_prefetch_hint,rom_ppu_address_valid};""")
 for n in ['rtl/nes.v','nes_probe.sv']:
  edit(n,'output wire [21:0] game148_hint_physical,','output wire [63:0] ppu_fault_state154,\noutput wire [21:0] game148_hint_physical,')
  edit(n,'.rom_ppu_address_valid(rom_ppu_address_valid),','.ppu_fault_state154(ppu_fault_state154),.rom_ppu_address_valid(rom_ppu_address_valid),')
 edit('nes_live_joint.sv','output wire out_fault_trigger,','output wire [63:0] out_ppu_fault_state154,\noutput wire out_fault_trigger,')
 edit('nes_live_joint.sv',' nes_probe dut(.*);',' wire [63:0] ppu_fault_state154;\n assign out_ppu_fault_state154=ppu_fault_state154;\n nes_probe dut(.*);')
 edit('fxpak_nes_screen137_top.sv','wire [63:0] fault_context;','wire [63:0] fault_context;wire [63:0] ppu_fault_state154;')
 edit('fxpak_nes_screen137_top.sv','.out_fault_trigger(fault_trigger),','.out_ppu_fault_state154(ppu_fault_state154),.out_fault_trigger(fault_trigger),')
 edit('fxpak_nes_screen137_top.sv','.fault_trigger(fault_trigger),','.ppu_fault_state154(ppu_fault_state154),.fault_trigger(fault_trigger),')
 n='nes_run_observer134.sv'
 edit(n,'input wire fault_trigger,','input wire [63:0] ppu_fault_state154,\n input wire fault_trigger,')
 edit(n,'reg context_valid;reg [63:0] first_context;','reg context_valid;reg [63:0] first_context;reg [63:0] first_ppu154;')
 edit(n,"command==8'h72)","command==8'h72 || command==8'h74 || command==8'h75)")
 edit(n,'context_valid<=0;first_context<=0;','context_valid<=0;first_context<=0;first_ppu154<=0;')
 edit(n,'first_context<=fault_context;end','first_context<=fault_context;first_ppu154<=ppu_fault_state154;end')
 edit(n,"        default:snapshot<=", """        8'h74:snapshot<={8'hdd,7'd0,context_valid,first_ppu154[63:24]};
        8'h75:snapshot<={8'hdd,7'd0,context_valid,first_ppu154[23:0],4'd0,first_error,8'd1};
        default:snapshot<=""")
 for n,old,new,count in [('nes_rom_spi.sv',"snapshot<={8'h62,","snapshot<={8'h63,",2),('nes_run_observer134.sv',"8'hdc","8'hdd",3),('nes_screen_status151.sv',"8'hdc","8'hdd",1)]:edit(n,old,new,count)
 (out/'board.qsf').write_text(qsf);(out/'board.qpf').write_text('PROJECT_REVISION = "board"\n')
 changed=[n for n,h in inputs.items() if sha(out/n)!=h]
 assert sha(out/'nes_rom_service.sv')==inputs['nes_rom_service.sv']
 assert sha(out/'game-program.hex')==inputs['game-program.hex']
 (out/'materialization154.json').write_text(json.dumps(dict(inputs152=inputs,changed=changed,ids=['63','DD'],ppu_error_fixed=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
