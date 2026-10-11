# SPDX-License-Identifier: MIT
"""Read the small PPU fault snapshot only after the existing safe STOP checks."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out):
 e=baseline/'nes-game153/evidence'
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game153-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prior=json.loads((e/'arm/preparation153.json').read_bytes())
 assert not out.exists();out.mkdir(parents=True);copied={};changed={}
 for n in prior['copied']:
  src=e/'arm'/n;assert sha(src)==pins['arm/'+n];dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);copied[n]=sha(src)
 def edit(n,old,new,count=1):
  p=out/'src'/n;s=p.read_text();assert s.count(old)==count,(n,old,s.count(old));p.write_text(s.replace(old,new),encoding='utf8',newline='\n');changed['src/'+n]=sha(p)
 for n,old,new,count in [('nes_h1_stm32.c','rx[1]!=0x62','rx[1]!=0x63',1),('nes_rom_verify.c','rx[1]==0x62','rx[1]==0x63',1),('nes_rom_verify.c','rx[1]!=0x62','rx[1]!=0x63',1),('nes_run136.inc','candidate->board_id=0x62','candidate->board_id=0x63',1),('nes_run136.inc','0xdc','0xdd',4),('nes_menu_diagnostic.c','153','154',7),('nes_menu_diagnostic.c','board_expected_hex=62','board_expected_hex=63',1),('nes_checkpoint112.c','153','154',2),('VERSION','NES-GAME153-DEV','NES-GAME154-DEV',1)]:edit(n,old,new,count)
 edit('nes_run136.h','uint8_t first_error,stop_error,context_valid;','uint8_t first_error,stop_error,context_valid;\n uint32_t ppu_state_hi,ppu_state_lo;uint8_t ppu_state_valid;')
 decoder='''/*154 Supplemental state: malformed auxiliary data is untrusted, not a new
 * game fault. Existing transport/clock guards and STOP checks stay mandatory. */
static bool ppu154(const struct nes_rom_spi_io *io) {
 uint8_t tx[8]={0x74,0,0,0,0,0,0,0},hi[8]={0},lo[8]={0};
 if(!nes_rom_spi_transfer(io,tx,hi))return false;
 tx[0]=0x75;if(!nes_rom_spi_transfer(io,tx,lo))return false;
 if(hi[1]!=0xdd||lo[1]!=0xdd||hi[2]!=1||lo[2]!=1||
    lo[6]!=nes_run136.rom_error||!lo[6]||lo[7]!=1)return false;
 nes_run136.ppu_state_hi=((uint32_t)hi[3]<<24)|((uint32_t)hi[4]<<16)|((uint32_t)hi[5]<<8)|hi[6];
 nes_run136.ppu_state_lo=((uint32_t)hi[7]<<24)|((uint32_t)lo[3]<<16)|((uint32_t)lo[4]<<8)|lo[5];
 nes_run136.ppu_state_valid=1;return true;
}
'''
 edit('nes_run136.inc','static bool screen146(',decoder+'static bool screen146(')
 edit('nes_run136.inc',' nes_run136.error=nes_run136.first_error?', ' if(nes_run136.rom_error)(void)ppu154(io); /* after STOP/retained observer checks */\n nes_run136.error=nes_run136.first_error?')
 edit('nes_menu_diagnostic.c','screen_telemetry_trusted=0\\n','screen_telemetry_trusted=0\\nppu_state_valid=%u\\nppu_state_hi=%08lx\\nppu_state_lo=%08lx\\n')
 edit('nes_menu_diagnostic.c','nes_run136.screen_frames,nes_run136.screen_phase_mask);','nes_run136.screen_frames,nes_run136.screen_phase_mask,nes_run136.ppu_state_valid,(unsigned long)nes_run136.ppu_state_hi,(unsigned long)nes_run136.ppu_state_lo);')
 (out/'preparation154.json').write_text(json.dumps(dict(copied=copied,changed=changed,added={},ids=['63','DD'],ppu_deadline_fixed=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
