# SPDX-License-Identifier: MIT
"""Bind actual NROM board/core, SNES bus and fixture evidence by hash."""
import json,re
from nes_delta231 import BASE,ROOT,sha
d=BASE/'probes/nes-nrom426/core04';r=json.loads((d/'result.json').read_text())
fixture=BASE/'probes/nes-nrom424/fixture02/nrom16.nes';board=BASE/'probes/nes-nrom407/map01'
assert r['passed'] and r['fixture_sha256']==sha(fixture) and r['cart_sha256']==sha(board/'cart_nrom.sv')
assert r['tb_sha256']==sha(d/'core_tb.sv')==sha(ROOT/'tests/nes-nrom426/core_tb.sv')
log=(d/'simulation.log').read_text(errors='replace');m=re.search(r'PASS NROM426 actual seeded NROM core pixel colors=([0-9a-f]+) pixels=(\d+)',log)
assert m and 'Errors: 0, Warnings: 84' in log
color=int(m[1],16);assert color&(1<<0x21) and color&(1<<0x16)
for f in ('nes_live_joint.sv','nes_rom_spi.sv','nes_rom_loader.sv','nes_rom_boot.sv','fxpak_nes_screen137_top.sv','sink-program.hex'):
 assert sha(d/f)==sha(board/f),f
res={'passed':True,'rom_sha256':sha(fixture),'cart_sha256':sha(d/'cart_nrom.sv'),'testbench_sha256':sha(d/'core_tb.sv'),
 'pixel_colors':m[1],'checked_pixels':int(m[2]),'simulation_warnings':84,'seeded_psram_and_verified':True,
 'snes_bus':'manually driven program read and pad writes, not 65816 execution',
 'snes_display_ack':False,'actual_loader_in_same_run':False,'actual_physical_pad':False,'actual_hardware':False,
 'inputs':{n:sha(d/n) for n in ('board.qsf','nes_live_joint.sv','nes_rom_spi.sv','nes_rom_loader.sv','nes_rom_boot.sv','fxpak_nes_screen137_top.sv','sink-program.hex','simulation.log')}}
(ROOT/'analysis/nrom426-core.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
