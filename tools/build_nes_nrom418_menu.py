# SPDX-License-Identifier: MIT
"""Create isolated fixed-profile menu source and a self-generated NROM ROM.

This is a build input, not a paired firmware/FPGA package or hardware approval.
"""
import argparse
import json
from pathlib import Path
from nes_delta231 import BASE,sha

p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
source=BASE/'probes/nes-repeat227/arm01/src/nes_menu_diagnostic.c'
s=source.read_text()
old='''nes_menu_sd_probe("/sd2snes/nes/game227.nes",
  "/sd2snes/fpga_n227.bi3",false,&report)'''
new='''nes_menu_sd_probe("/sd2snes/nes/nrom16.nes",
  "/sd2snes/fpga_nrom16.bi3",false,&report)'''
assert s.count(old)==1;s=s.replace(old,new)
(d/'nes_menu_diagnostic.c').write_text(s,newline='\n')
# SEI; CLD; LDX #$ff; TXS; JMP $8005. Vectors all address valid code.
# No audio, input or visual assertion; this is a bounded boot-loop fixture.
rom=bytearray(b'NES\x1a'+bytes([1,1])+bytes(10))
prg=bytearray([0xea]*16384);prg[:8]=bytes([0x78,0xd8,0xa2,0xff,0x9a,0x4c,0x05,0x80])
prg[-6:]=bytes([0x00,0x80,0x00,0x80,0x00,0x80])
rom.extend(prg);rom.extend(bytes(8192));(d/'nrom16.nes').write_bytes(rom)
result={'profile':'NROM16 horizontal CHR-ROM8','menu_source':sha(d/'nes_menu_diagnostic.c'),
 'baseline_menu_source':sha(source),'self_generated_test_rom':sha(d/'nrom16.nes'),
 'rom_bytes':len(rom),'expected_fpga_reply_id':'78','menu_rom_path':'/sd2snes/nes/nrom16.nes',
 'menu_fpga_path':'/sd2snes/fpga_nrom16.bi3','scope':'isolated source and self-generated boot-loop only; no paired package, video/input/audio test, FIT or hardware'}
(d/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
