# SPDX-License-Identifier: MIT
"""Restore the internal APU and route mono to the existing board DAC pins."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha
def prepare(baseline,out,arm=False):
 e=baseline/'nes-game161/evidence';m=json.loads((ROOT/'analysis/game161-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation161.json').read_bytes())['copied']) if arm else re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,c=1):
  p=out/n;s=p.read_text();assert s.count(a)==c,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 added={}
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x6a','rx[1]!=0x6b',1),('nes_rom_verify.c','rx[1]==0x6a','rx[1]==0x6b',1),('nes_rom_verify.c','rx[1]!=0x6a','rx[1]!=0x6b',1),('nes_run136.inc','candidate->board_id=0x6a','candidate->board_id=0x6b',1),('nes_run136.inc','0xe4','0xe5',10),('nes_menu_diagnostic.c','161','162',10),('nes_menu_diagnostic.c','board_expected_hex=6A','board_expected_hex=6B',1),('nes_menu_diagnostic.c','apu_channel_writes_blocked=1','apu_channel_writes_blocked=0',1),('nes_checkpoint112.c','161','162',2),('VERSION','NES-GAME161-DEV','NES-GAME162-DEV',1)]:edit('src/'+n,a,b,c)
 else:
  edit('rtl/nes.v',".CS             (apu_cs && (cpu_rnw || addr[4:0]==5'h17)), //156 channel-write isolation; frame counter/read path retained",'.CS             (apu_cs), //162 restore all APU writes, including DMC')
  edit('fxpak_nes_screen137_top.sv',' wire [95:0] history_sample157;', ' wire [15:0] audio_sample;\n wire [95:0] history_sample157;')
  edit('fxpak_nes_screen137_top.sv',' nes_live_joint core(', ' nes_live_joint core(.out_sample(audio_sample),')
  edit('fxpak_nes_screen137_top.sv',' assign DAC_MCLK=0;assign DAC_LRCK=0;assign DAC_SDOUT=0;', ''' nes_dac162 audio(.nes_clk(SNES_SYSCLK),.dac_clk(host_clk),.reset(core_reset),
  .inverted_sample(audio_sample),.DAC_MCLK(DAC_MCLK),.DAC_LRCK(DAC_LRCK),
  .DAC_SDOUT(DAC_SDOUT),.overrun());''')
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h6a,","snapshot<={8'h6b,",2),('nes_run_observer134.sv',"8'he4","8'he5",5),('nes_screen_status151.sv',"8'he4","8'he5",1),('nes_pad_trace156.sv',"8'he4","8'he5",2),('nes_ppu_history157.sv',"8'he4","8'he5",2)]:edit(n,a,b,c)
  n='nes_dac162.sv';shutil.copy2(ROOT/'src/nes/diagnostics'/n,out/n);added[n]=sha(out/n)
  q=out/'board.qsf';q.write_text(q.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_dac162.sv\n')
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation162.json' if arm else 'materialization162.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added=added,ids=['6B','E5'],physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
