# SPDX-License-Identifier: MIT
"""Selected479 MMC3/core/source smoke with seeded ROM and checked SPI START/STOP.

Loader loaded/verified state is seeded explicitly. No full loader, live ARM,
65816 or physical hardware proof; the20 host cases cover the separate loader.
"""
import argparse
import json
from pathlib import Path
import sys
from nes_delta231 import ROOT, sha


def once(s, old, new):
    assert s.count(old) == 1, old[:120]
    return s.replace(old, new)


p = argparse.ArgumentParser(description=__doc__)
for n in ['board', 'rom', 'out']:
    p.add_argument('--' + n, type=Path, required=True)
a = p.parse_args()
assert sha(a.rom) == 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
tb = (ROOT/'tests/nes-nrom429/core_tb.sv').read_text()
tb = once(tb, 'ram.prg,0,16383', 'ram.prg,0,262143')
tb = once(tb, 'ram.chr,0,8191', 'ram.chr,0,131071')
tb = once(tb, 'wait(frames>=4)', 'wait(frames>=8)')
tb = once(tb, '$countones(seen)<2', '$countones(seen)<1')
start = tb.index('  if(!seen[6\'h21])')
end = tb.index('  if(!dut.core.native_spi.sealed)', start)
tb = tb[:start] + '''  status_frame(8'h65,0);
  if(rx[1]!==8'h79)$fatal(1,"wrong MMC3 profile %h",rx[1]);
''' + tb[end:]
tb = tb.replace('#150000000;', '#300000000;')
tb = tb.replace('PASS NROM429 full geometry', 'PASS MMC479 full geometry')
tb = tb.replace('PASS NROM426 actual seeded NROM core pixel', 'PASS MMC479 actual seeded MMC3 core source STOP')
runner = (ROOT/'tools/test_nes_nrom426_core.py').read_text()
runner = once(runner, "len(raw)==24592 and raw[:6]==b'NES\\x1a\\x01\\x01'", "len(raw)==0x60010 and raw[:8]==b'NES\\x1a\\x10\\x10\\x42\\x00'")
runner = runner.replace('raw[16:16400]', 'raw[16:0x40010]').replace('raw[16400:]', 'raw[0x40010:]')
runner = once(runner, "shutil.copyfile(ROOT/'tests/nes-nrom426/core_tb.sv',d/'core_tb.sv')", "(d/'core_tb.sv').write_text("+repr(tb)+",newline='\\n')\nmodel=d/'rom_boot_model.sv'\ns=model.read_text().replace('65535','262143').replace('32767','131071').replace(\"24'h10000\",\"24'h40000\").replace(\"24'h208000\",\"24'h220000\").replace('a[15:0]','a[17:0]').replace('a[14:0]','a[16:0]').replace('assign #25','assign #70');model.write_text(s,newline='\\n')")
runner = runner.replace('PASS NROM426 actual seeded NROM core pixel', 'PASS MMC479 actual seeded MMC3 core source STOP')
runner = runner.replace("'scope':'actual 227 board/NES core and NROM mapper, seeded PSRAM/verified loader, manual SNES bus program read and pad writes, core pixels and SPI STOP; not actual loader, 65816 execution, actual controller or hardware'", "'scope':"+repr(__doc__))
sys.argv = ['test_nes_nrom426_core.py', '--board', str(a.board), '--rom', str(a.rom), '--out', str(a.out)]
exec(compile(runner, str(ROOT/'tools/test_nes_nrom426_core.py'), 'exec'), {'__name__': '__main__', '__file__': str(ROOT/'tools/test_nes_nrom426_core.py')})
r = json.loads((a.out/'result.json').read_text())
r['blocks_sha256'] = sha(a.out/'nrom429-blocks.txt')
r['block_count'] = len((a.out/'nrom429-blocks.txt').read_text().splitlines())
r['loader_verified_state_seeded'] = True
r['PSRAM_read_model_ns'] = 70
r['physical_hardware'] = False
(a.out/'result.json').write_text(json.dumps(r, indent=2)+'\n')
print(json.dumps(r))
