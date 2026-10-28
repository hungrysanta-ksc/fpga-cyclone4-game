# SPDX-License-Identifier: MIT
"""Count actual loader SPI calls on the 408 FatFS/model fixture, not RTL."""
import argparse
import json
import re
import sys
from pathlib import Path
from nes_delta231 import ROOT

p = argparse.ArgumentParser()
p.add_argument('--build', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
out = a.out.resolve()
assert not out.exists()
temp = out.parent / (out.name + '-instrumented.c')
assert not temp.exists()
s = (ROOT / 'tests/nes-nrom408/full_tb.c').read_text()
def once(text, old, new):
    assert text.count(old) == 1
    return text.replace(old, new)
s = once(s, 'static int scenario;', 'static int scenario;\nstatic unsigned long long traffic[256];')
s = once(s, '(void)io;if(sticky)return false;', '(void)io;traffic[tx[0]]++;if(sticky)return false;')
s = once(s, 'scenario=test;memset(filedata', 'memset(traffic,0,sizeof(traffic));scenario=test;memset(filedata')
s = once(s, '  printf("NROM408 case=', '  if(i==OK){for(unsigned op=0;op<256;op++)if(traffic[op])printf("TRAFFIC %02x %llu\\n",op,traffic[op]);}\n  printf("NROM408 case=')
temp.write_text(s, newline='\n')
runner = (ROOT / 'tools/test_nes_nrom408_fatfs.py').read_text()
runner = once(runner, "str(tests/'full_tb.c')", 'str(Path(' + repr(str(temp)) + '))')
runner = once(runner, "sha(tests/'full_tb.c')", 'sha(Path(' + repr(str(temp)) + '))')
sys.argv = ['test_nes_nrom408_fatfs.py', '--build', str(a.build), '--out', str(out)]
exec(compile(runner, str(ROOT / 'tools/test_nes_nrom408_fatfs.py'), 'exec'), {'__file__': str(ROOT / 'tools/test_nes_nrom408_fatfs.py'), '__name__': '__main__'})
log = (out / 'test.log').read_text()
counts = {op: int(n) for op,n in re.findall(r'^TRAFFIC ([0-9a-f]{2}) (\d+)$', log, re.M)}
assert counts['61'] == 0x60000 and counts['67'] == counts['68'] == counts['6a'] == 0x60000
total = sum(counts.values())
result = {'scope': 'actual FatFS and loader C with modeled SPI/PSRAM/run; instrumentation counts calls, not hardware timing', 'frames': total, 'opcodes': counts, 'frame_bytes': 8, 'assumed_spi_hz': 2625000, 'wire_only_seconds': total*64/2625000, 'excludes': ['select gaps', 'CPU/IRQ', 'disk', 'FPGA/PSRAM latency', 'additional hardware polling', 'actual game frames']}
(out / 'traffic.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
