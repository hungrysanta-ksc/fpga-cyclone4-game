# SPDX-License-Identifier: MIT
"""060 full ARM link input from private059; no menu call or installable image."""
from pathlib import Path
import argparse,json,shutil
from nes_sd_readback import materialize
from nes_mcu_loader import source as source056
from nes_spi_boot import sha,put

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 old=json.loads((a.baseline/'verification-preparation.json').read_text());assert old['candidate']=='NES-SPI-READBACK-059'
 for n,h in old['sources'].items():assert sha(a.baseline/'src'/n)==h,n
 assert (a.baseline/'src/nes_h1_stm32.c').read_text()==source056()
 assert not a.out.exists()
 shutil.copytree(a.baseline,a.out,ignore=shutil.ignore_patterns('obj*','.dep*','*.elf','*.stm','*.map','*.lst'))
 materialize(a.out/'src')
 mk=a.out/'src/Makefile';s=mk.read_text();needle='-Wl,--undefined=nes_rom_verified_start';assert s.count(needle)==1
 put(mk,s.replace(needle,needle+' -Wl,--undefined=nes_sd_readback_probe'))
 names=['nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_spi.h','nes_rom_verify.c','nes_rom_verify.h','nes_sd_readback.h','Makefile']
 put(a.out/'sd-readback-preparation.json',json.dumps(dict(candidate='NES-SD-READBACK-060',menu_entry=False,start_enabled=False,
  files={n:sha(a.out/'src'/n) for n in names}),indent=2)+'\n')
 print('Prepared060 full SD binding, uncalled entry; compile-only')

if __name__=='__main__':main()
