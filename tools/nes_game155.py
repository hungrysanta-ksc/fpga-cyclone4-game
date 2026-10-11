# SPDX-License-Identifier: MIT
"""Advance ordinary BG reads in idle slots; preserve demand/error contracts."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha

def patch_ppu(source):
 old="""assign game147_prefetch_hint=read_2007_delayed[3] && vram_r && !ALE &&
    is_rendering_d && !sprite_load_en && cycle<336 &&
    (cycle[2:0]==4 || cycle[2:0]==6);
assign game148_hint_logic={1'b0,bg_patt1,bg_name_table[7:4],vram_din};"""
 new="""//155 The name byte is latched at dot2. Use the attribute interval to
// prepare the ordinary low plane, then the low-plane interval for the high
// plane. The existing service issues predictions only in idle demand slots.
// PPUDATA overlap keeps its original address formula and priority. Physical
// tags, current-demand validity, sample deadlines and IRQ inputs are unchanged.
wire overlap155=read_2007_delayed[3] && vram_r && !ALE &&
    is_rendering_d && !sprite_load_en && cycle<336 &&
    (cycle[2:0]==4 || cycle[2:0]==6);
wire normal155=is_rendering_d && !sprite_load_en && cycle>0 && cycle<336 &&
    read_2007_delayed==0 && write_2007_delayed==0 &&
    (cycle[2:0]>=3 && cycle[2:0]<=6);
assign game147_prefetch_hint=overlap155 || normal155;
assign game148_hint_logic=overlap155 ?
    {1'b0,bg_patt1,bg_name_table[7:4],vram_din} :
    {1'b0,bg_patt1,bg_name_table,(cycle[2:0]>=5),vram[14:12]};"""
 assert source.count(old)==1
 return source.replace(old,new)

def prepare(baseline,out,arm=False):
 e=baseline/'nes-game154/evidence'
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game154-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 if arm:
  names=list(json.loads((e/'arm/preparation154.json').read_bytes())['copied']);section='arm'
 else:
  qsf=(e/'asm/board.qsf').read_text();section='asm'
  names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',qsf)+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,count):
  p=out/n;s=p.read_text();assert s.count(a)==count,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n,a,b,count in [('nes_h1_stm32.c','rx[1]!=0x63','rx[1]!=0x64',1),('nes_rom_verify.c','rx[1]==0x63','rx[1]==0x64',1),('nes_rom_verify.c','rx[1]!=0x63','rx[1]!=0x64',1),('nes_run136.inc','candidate->board_id=0x63','candidate->board_id=0x64',1),('nes_run136.inc','0xdd','0xde',6),('nes_menu_diagnostic.c','154','155',7),('nes_menu_diagnostic.c','board_expected_hex=63','board_expected_hex=64',1),('nes_checkpoint112.c','154','155',2),('VERSION','NES-GAME154-DEV','NES-GAME155-DEV',1)]:edit('src/'+n,a,b,count)
 else:
  p=out/'rtl/ppu.sv';p.write_text(patch_ppu(p.read_text()),encoding='utf8',newline='\n')
  for n,a,b,count in [('nes_rom_spi.sv',"snapshot<={8'h63,","snapshot<={8'h64,",2),('nes_run_observer134.sv',"8'hdd","8'hde",5),('nes_screen_status151.sv',"8'hdd","8'hde",1)]:edit(n,a,b,count)
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation155.json' if arm else 'materialization155.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['64','DE'],physical=False),indent=2)+'\n')
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
