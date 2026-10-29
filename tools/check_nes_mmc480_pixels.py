# SPDX-License-Identifier: MIT
"""Compare observed NES PPU colors to actual65816/SNES screenshot, no plan golden."""
import argparse
import hashlib
import json
from pathlib import Path
import re

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
for n in ['live', 'palette', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
source = a.live/'NES-first-colors.hex'
screen = a.live/'frame-1.rgb'
indices = bytes.fromhex(source.read_text())
pixels = screen.read_bytes()
assert len(indices) == 256*224 and len(pixels) == 256*239*3
palette = list(map(int, re.search(r'\[64\]=\{([^}]+)', a.palette.read_text())[1].split(',')))
assert len(palette) == 64 and max(indices)<64
expected = [palette[x] for x in indices]
actual = [(pixels[i]>>3)|((pixels[i+1]>>3)<<5)|((pixels[i+2]>>3)<<10) for i in range(0,len(pixels),3)]
# Mesen SnesPpu::ApplyHiResMode/SendFrame: non-overscan224 lines are
# centered in the239 buffer, with7 top and8 bottom black rows. Fixed emulator
# coordinate contract, NOT a fitted image offset or discarded NES pixels.
assert all(x==0 for x in actual[:7*256]) and all(x==0 for x in actual[231*256:])
actual = actual[7*256:231*256]
bad = [i for i in range(len(expected)) if expected[i] != actual[i]]
result = {'passed': not bad, 'scope': __doc__, 'pixels': len(expected), 'mismatches': len(bad), 'comparison': 'All NES scanline8..231 -> all SNES visible224 rows, at fixed Mesen239 buffer offset7. RGB8 high5bits compared to exact native_palette165 RGB15; no offset fitting or mismatch tolerance', 'Mesen_coordinate_contract': 'https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesPpu.cpp#L1319', 'black_border_pixels_checked': 256*15, 'first_mismatch_xy': [bad[0]%256,bad[0]//256] if bad else None, 'mismatch_rows': {str(y):sum(y*256<=i<(y+1)*256 for i in bad) for y in range(224) if any(y*256<=i<(y+1)*256 for i in bad)}, 'source_SHA256': sha(source), 'screen_SHA256': sha(screen), 'palette_SHA256': sha(a.palette), 'physical_hardware': False}
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed': not bad, 'pixels': len(expected), 'mismatches': len(bad), 'first_xy': result['first_mismatch_xy']}))
if bad:
    raise SystemExit(1)
