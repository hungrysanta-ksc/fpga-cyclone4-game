# SPDX-License-Identifier: MIT
"""Qualify early MMC3 ROM reads with the actual CPU/DMA read direction."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha
OLD='assign rom_cpu_address_valid=prg_addr[15] && prg_allow;'
NEW='''//159 MMC3 writes do not consume ROM data (this adapter has conflict=0).
// Before cart_pre, prg_allow can still be high during a raw CPU/DMA write.
// Do not let that write allocate the shared reader ahead of CHR prediction.
// cpumem_read and real CPU/DMA sample deadlines are unchanged.
assign rom_cpu_address_valid=mr_int && prg_addr[15] && prg_allow;'''
def prepare(baseline,out,arm=False):
 e=baseline/'nes-game158/evidence';m=json.loads((ROOT/'analysis/game158-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation158.json').read_bytes())['copied']) if arm else re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,c=1):
  p=out/n;s=p.read_text();assert s.count(a)==c,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x67','rx[1]!=0x68',1),('nes_rom_verify.c','rx[1]==0x67','rx[1]==0x68',1),('nes_rom_verify.c','rx[1]!=0x67','rx[1]!=0x68',1),('nes_run136.inc','candidate->board_id=0x67','candidate->board_id=0x68',1),('nes_run136.inc','0xe1','0xe2',10),('nes_menu_diagnostic.c','158','159',10),('nes_menu_diagnostic.c','board_expected_hex=67','board_expected_hex=68',1),('nes_checkpoint112.c','158','159',2),('VERSION','NES-GAME158-DEV','NES-GAME159-DEV',1)]:edit('src/'+n,a,b,c)
 else:
  edit('rtl/nes.v',OLD,NEW)
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h67,","snapshot<={8'h68,",2),('nes_run_observer134.sv',"8'he1","8'he2",5),('nes_screen_status151.sv',"8'he1","8'he2",1),('nes_pad_trace156.sv',"8'he1","8'he2",2),('nes_ppu_history157.sv',"8'he1","8'he2",2)]:edit(n,a,b,c)
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation159.json' if arm else 'materialization159.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['68','E2'],physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
