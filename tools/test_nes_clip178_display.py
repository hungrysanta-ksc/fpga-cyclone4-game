# SPDX-License-Identifier: MIT
"""Actual65816: alternate unclipped/clipped, banked fallback, noop and STOP.

Uses the unchanged169 full-upload RGB oracle, then independently masks only
the left8 pixels to the candidate backdrop. No reference implementation of
the new SNES window code is used to construct expected pixels.
"""
from pathlib import Path
import inspect, shutil, struct
import test_nes_banked169 as prior
from nes_clip178 import build, sink, header, replace


def expected_rgb(video, reference, index):
    rgb = bytearray((reference/f'frame-{index}.rgb').read_bytes())
    if index in (2, 4, 6):
        palette = bytearray((video/'frame15/cgram.bin').read_bytes())
        if index == 4:
            palette = bytearray(v ^ 0x11 for v in palette)
        color = struct.unpack_from('<H', palette)[0] & 0x7fff
        pixel = bytes((((color >> s) & 31) << 3) | (((color >> s) & 31) >> 2) for s in (0, 5, 10))
        for y in range(7, 231):
            rgb[(y*256)*3:(y*256+8)*3] = pixel * 8
    return bytes(rgb)


source = inspect.getsource(prior.main)
source = replace(source, 'a=p.parse_args()', "p.add_argument('--reference',type=Path,required=True)\n a=p.parse_args()")
source = replace(source, 'sink_source(f.read_text())', 'sink_source(sink(f.read_text()))')
source = replace(source, " s=(a.out/'native_sink165_host.c').read_text();", " (a.out/'nes_native_video165.h').write_text(header((a.out/'nes_native_video165.h').read_text()),encoding='utf8')\n s=(a.out/'native_sink165_host.c').read_text();")
source = replace(source, " (a.out/'producer169.c').write_text(s,", " s=s.replace('p.valid=true;', 'p.valid=true;p.display_mask=(gen==15||gen==17||gen==19)?0x18:0x1e;')\n (a.out/'producer169.c').write_text(s,")
source = replace(source, ' results=[]', " shutil.copytree(a.reference,a.out/'budget-reference')\n results=[]")
source = replace(source, "([('stop',False)] if a.stop_only else [('overflow',True),('budget',True),('overflow',False),('budget',False),('stop',False)])", "[('budget',False),('stop',False)]")
source = replace(source, "  (d/'capture.lua').write_text(", '''  lua=lua.replace("if a==0x2100 then", "if a==0x212e and revealed then assert(st['ppu.scanline']>=225 and packet and packetbyte(0)==3,'window outside final seal');assert(v==(word(0x123a)==0x18 and 0x11 or 0),'wrong committed window')end\\n if a==0x2100 then")
  (d/'capture.lua').write_text(''')
begin = source.index('  if not reference:\n   for i in range(1,4):')
end = source.index('  results.append(q);', begin)
source = source[:begin] + '''  for i in range(1,4 if mode=='stop' else 7):
   expected=expected_rgb(a.video,a.reference,i)
   actual=(d/f'frame-{i}.rgb').read_bytes()
   (d/f'expected-{i}.rgb').write_bytes(expected)
   assert actual==expected,(mode,i,'clip pixels',sum(x!=y for x,y in zip(actual,expected)))
''' + source[end:]
source = replace(source, "sources=['tools/nes_banked169.py'", "sources=['tools/nes_clip178.py','tools/test_nes_clip178_display.py','tools/nes_banked169.py'")
source = source.replace("'Actual65816 plus actual C sink with file mailbox; E2/E3 full back-slot build, palette/OAM/HDMA flip, six pixel-exact commits and STOP. Not physical SPI/FPS.'",
                        "'Actual65816/C file mailbox;6 alternating1e/18 pixel-exact commits, E3 banked fallback/noop and3 commits before mid-copy STOP. No physical timing, full MCU link or FPS proof.'")
namespace = dict(prior.__dict__)
namespace.update(build=build, sink=sink, header=header, expected_rgb=expected_rgb)
exec(compile(source, 'clip178-display', 'exec'), namespace)

if __name__ == '__main__':
    namespace['main']()
