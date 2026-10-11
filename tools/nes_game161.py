# SPDX-License-Identifier: MIT
"""Preserve the active CHR byte across fills; shorten visible snapshot hold."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha
from build_nes_game161 import build
PATCH161_BEFORE = """     ppu_previous_cached<=ppu_cached;ppu_previous_tag<=ppu_tag;ppu_previous_byte<=ppu_byte;"""
PATCH161_AFTER = """     //161 Keep the previous slot while it supplies the live CHR demand.
     // Filling the other slot must not evict a byte before its sample.
     if(!ppu_rom || !ppu_previous_hit)begin
      ppu_previous_cached<=ppu_cached;ppu_previous_tag<=ppu_tag;ppu_previous_byte<=ppu_byte;
     end"""
def patch161(edit):
 edit('nes_rom_service.sv',PATCH161_BEFORE,PATCH161_AFTER)
 edit('nes_rom_service.sv','   ppu_prefetch_address<22\'h220000 && !prefetch_hit;',
      '   ppu_prefetch_address<22\'h220000 && !prefetch_hit &&\n   !(busy && pending_ppu && pending_address==ppu_prefetch_address);')
def prepare(baseline,out,arm=False):
 e=baseline/'nes-game160/evidence';m=json.loads((ROOT/'analysis/game160-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation160.json').read_bytes())['copied']) if arm else re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'asm/board.qsf').read_text())+['board.sdc','game-program.hex','board.qsf','board.qpf']
 inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,c=1):
  p=out/n;s=p.read_text();assert s.count(a)==c,(n,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n,a,b,c in [('nes_h1_stm32.c','rx[1]!=0x69','rx[1]!=0x6a',1),('nes_rom_verify.c','rx[1]==0x69','rx[1]==0x6a',1),('nes_rom_verify.c','rx[1]!=0x69','rx[1]!=0x6a',1),('nes_run136.inc','candidate->board_id=0x69','candidate->board_id=0x6a',1),('nes_run136.inc','0xe3','0xe4',10),('nes_menu_diagnostic.c','160','161',10),('nes_menu_diagnostic.c','board_expected_hex=69','board_expected_hex=6A',1),('nes_checkpoint112.c','160','161',2),('VERSION','NES-GAME160-DEV','NES-GAME161-DEV',1)]:edit('src/'+n,a,b,c)
 else:
  patch161(edit)
  shutil.copy2(build(out/'client'),out/'game-program.hex')
  for n,a,b,c in [('nes_rom_spi.sv',"snapshot<={8'h69,","snapshot<={8'h6a,",2),('nes_run_observer134.sv',"8'he3","8'he4",5),('nes_screen_status151.sv',"8'he3","8'he4",1),('nes_pad_trace156.sv',"8'he3","8'he4",2),('nes_ppu_history157.sv',"8'he3","8'he4",2)]:edit(n,a,b,c)
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 (out/('preparation161.json' if arm else 'materialization161.json')).write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['6A','E4'],physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.arm)
