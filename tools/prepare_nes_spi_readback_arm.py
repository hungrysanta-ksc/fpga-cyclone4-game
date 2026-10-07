# SPDX-License-Identifier: MIT
"""Add uncalled059 verification functions to a verified private056 build tree.

This is a full-link check only. The old056 SD/menu path remains unmodified and
does not call the new59 protocol. Do not install this firmware.
"""
from pathlib import Path
import argparse,json,shutil
from nes_mcu_loader import source
from nes_spi_boot import ROOT,sha,put
from nes_rom_geometry import replace

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();src=a.baseline/'src';assert (src/'nes_h1_stm32.c').read_text()==source()
 for n in ['nes_rom_spi.c','nes_rom_spi.h','nes_mcu_loader.h']:
  assert sha(src/n)==sha(ROOT/'src/nes/firmware'/n),n
 assert not a.out.exists()
 shutil.copytree(a.baseline,a.out,ignore=shutil.ignore_patterns('obj*','.dep*','*.elf','*.stm','*.map','*.lst'))
 for n in ['nes_rom_verify.c','nes_rom_verify.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,a.out/'src'/n)
 mk=a.out/'src/Makefile';s=mk.read_text()
 s=replace(s,'SRC += nes_h1_session.c nes_h1_stm32.c nes_rom_spi.c','SRC += nes_h1_session.c nes_h1_stm32.c nes_rom_spi.c nes_rom_verify.c')
 s=replace(s,'LDFLAGS += -Wl,--undefined=nes_mcu_load_probe','LDFLAGS += -Wl,--undefined=nes_mcu_load_probe -Wl,--undefined=nes_rom_verify -Wl,--undefined=nes_rom_verified_start')
 put(mk,s)
 names=['nes_h1_stm32.c','nes_rom_spi.c','nes_rom_spi.h','nes_rom_verify.c','nes_rom_verify.h','Makefile']
 put(a.out/'verification-preparation.json',json.dumps(dict(candidate='NES-SPI-READBACK-059',functions_uncalled=True,menu_entry=False,sd_binding=False,
  sources={n:sha(a.out/'src'/n) for n in names}),indent=2)+'\n')
 print('Prepared059 uncalled verification functions; compile-only, no menu/SD hookup')

if __name__=='__main__':main()
