# SPDX-License-Identifier: MIT
"""Preview the real retained-latch address on rendering restart; retain159 reads."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha
PATCH160 = """//160 A rising rendering pipeline can start on an even pattern dot without
// an ALE phase. The old external low-address latch is then the real address,
// not the ordinary bg_name_table/plane/fine-y prediction. Preview that one
// boundary while re_sr[1] is already set and re_sr[2] is still clear.
wire restart160 = re_sr[1] && !re_sr[2] && scanline<240 &&
    !sprite_load_en && cycle>0 && cycle<336 &&
    (cycle[2:0]==5 || cycle[2:0]==7) &&
    read_2007_delayed==0 && write_2007_delayed==0;
assign game160_restart_hint=restart160;
assign game147_prefetch_hint=restart160 || overlap155 || normal155;
assign game148_hint_logic=restart160 ?
    {1'b0,bg_patt,bg_name_table[7:4],vram_a_byte} : overlap155 ?"""
def patch160(edit):
 for n in ['rtl/ppu.sv','rtl/nes.v','nes_probe.sv']:
  edit(n,'output wire [63:0] ppu_fault_state154,','output wire game160_restart_hint,\noutput wire [63:0] ppu_fault_state154,')
 for n in ['rtl/nes.v','nes_probe.sv']:
  edit(n,'.ppu_fault_state154(ppu_fault_state154)', '.game160_restart_hint(game160_restart_hint),.ppu_fault_state154(ppu_fault_state154)')
 edit('rtl/ppu.sv','assign game147_prefetch_hint=overlap155 || normal155;\nassign game148_hint_logic=overlap155 ?',PATCH160)
 edit('nes_live_joint.sv','wire [11:0] history_flags157;','wire game160_restart_hint;\nwire [11:0] history_flags157;')
 edit('nes_live_joint.sv','game147_prefetch_hint && (rom_ppu_valid ||','game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid ||')
 anchor='set_max_delay 12.0 -from [get_registers {*|reader|reading_active}] -to [get_ports {ROM_1CE ROM_2CE ROM_OE}]'
 edit('board.sdc',anchor,anchor+'\n'+(ROOT/'src/nes/diagnostics/nes_game160_budget.sdc').read_text())
def prepare(baseline,out,arm=False):
 e=baseline/'nes-game159/evidence';m=json.loads((ROOT/'analysis/game159-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation159.json').read_bytes())['copied']) if arm else re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,c=1):
  p=out/n;s=p.read_text();assert s.count(a)==c,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x68','rx[1]!=0x69',1),('nes_rom_verify.c','rx[1]==0x68','rx[1]==0x69',1),('nes_rom_verify.c','rx[1]!=0x68','rx[1]!=0x69',1),('nes_run136.inc','candidate->board_id=0x68','candidate->board_id=0x69',1),('nes_run136.inc','0xe2','0xe3',10),('nes_menu_diagnostic.c','159','160',10),('nes_menu_diagnostic.c','board_expected_hex=68','board_expected_hex=69',1),('nes_checkpoint112.c','159','160',2),('VERSION','NES-GAME159-DEV','NES-GAME160-DEV',1)]:edit('src/'+n,a,b,c)
 else:
  patch160(edit)
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h68,","snapshot<={8'h69,",2),('nes_run_observer134.sv',"8'he2","8'he3",5),('nes_screen_status151.sv',"8'he2","8'he3",1),('nes_pad_trace156.sv',"8'he2","8'he3",2),('nes_ppu_history157.sv',"8'he2","8'he3",2)]:edit(n,a,b,c)
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation160.json' if arm else 'materialization160.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['69','E3'],physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
