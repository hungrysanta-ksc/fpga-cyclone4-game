# SPDX-License-Identifier: MIT
"""Speculate pending MMC3 CHR writes; never commit mapper state early."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha

def patch_mapper(s):
 # Only the pure mapper4 prediction port sees the prospective register value.
 s=s.replace(' input [13:0] game148_hint_logic,',' input wire game158_preview_write,\n input [13:0] game148_hint_logic,')
 assert s.count(' input wire game158_preview_write,')==2
 s=s.replace('MMC3 mapper(.game148_hint_logic','MMC3 mapper(.game158_preview_write(game158_preview_write),.game148_hint_logic')
 a='reg [8:0] game148_bank;\nalways @* begin\n case ({game148_hint_logic[12] ^ chr_a12_invert,game148_hint_logic[11:10]})'
 b='''//158 Raw CPU write bus is stable before cart_ce commits the register.
// This pure prediction does not drive normal CHR mapping or IRQ inputs.
wire preview158=enable && game158_preview_write && prg_ain[15:13]==3'b100;
wire invert158=(preview158 && !prg_ain[0])?prg_din[7]:chr_a12_invert;
wire [7:0] bank0_158=(preview158 && prg_ain[0] && bank_select==0)?{1'b0,prg_din[7:1]}:chr_bank_0;
wire [7:0] bank1_158=(preview158 && prg_ain[0] && bank_select==1)?{1'b0,prg_din[7:1]}:chr_bank_1;
wire [7:0] bank2_158=(preview158 && prg_ain[0] && bank_select==2)?prg_din:chr_bank_2;
wire [7:0] bank3_158=(preview158 && prg_ain[0] && bank_select==3)?prg_din:chr_bank_3;
wire [7:0] bank4_158=(preview158 && prg_ain[0] && bank_select==4)?prg_din:chr_bank_4;
wire [7:0] bank5_158=(preview158 && prg_ain[0] && bank_select==5)?prg_din:chr_bank_5;
reg [8:0] game148_bank;
always @* begin
 case ({game148_hint_logic[12] ^ invert158,game148_hint_logic[11:10]})'''
 assert s.count(a)==1;s=s.replace(a,b)
 start=s.index(' case ({game148_hint_logic[12] ^ invert158');end=s.index('assign game148_chr_offset',start)
 region=s[start:end]
 for i in range(6):region=region.replace(f'chr_bank_{i}',f'bank{i}_158')
 return s[:start]+region+s[end:]

def prepare(baseline,out,arm=False):
 e=baseline/'nes-game157/evidence';m=json.loads((ROOT/'analysis/game157-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation157.json').read_bytes())['copied']) if arm else re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,c=1):
  p=out/n;s=p.read_text();assert s.count(a)==c,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x66','rx[1]!=0x67',1),('nes_rom_verify.c','rx[1]==0x66','rx[1]==0x67',1),('nes_rom_verify.c','rx[1]!=0x66','rx[1]!=0x67',1),('nes_run136.inc','candidate->board_id=0x66','candidate->board_id=0x67',1),('nes_run136.inc','0xe0','0xe1',10),('nes_menu_diagnostic.c','157','158',10),('nes_menu_diagnostic.c','board_expected_hex=66','board_expected_hex=67',1),('nes_checkpoint112.c','157','158',2),('VERSION','NES-GAME157-DEV','NES-GAME158-DEV',1)]:edit('src/'+n,a,b,c)
 else:
  p=out/'cart_nrom.sv';p.write_text(patch_mapper(p.read_text()),encoding='utf8',newline='\n')
  edit('rtl/nes.v','cart_top multi_mapper (',"cart_top multi_mapper (.game158_preview_write(mw_int && !reset_noSS),")
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h66,","snapshot<={8'h67,",2),('nes_run_observer134.sv',"8'he0","8'he1",5),('nes_screen_status151.sv',"8'he0","8'he1",1),('nes_pad_trace156.sv',"8'he0","8'he1",2),('nes_ppu_history157.sv',"8'he0","8'he1",2)]:edit(n,a,b,c)
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation158.json' if arm else 'materialization158.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['67','E1'],physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
