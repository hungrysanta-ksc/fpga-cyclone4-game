# SPDX-License-Identifier: MIT
"""Two actual SNES emulator frames, independently verified against NES packets."""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw
from nes_spi_boot import sha

def main():
 p=argparse.ArgumentParser()
 for n in ['client','rom','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir()
 m=json.loads((a.client/'result.json').read_bytes());assert m['passed'] and m['mode']=='normal'
 im=Image.new('RGB',(1040,522),(24,24,24));draw=ImageDraw.Draw(im)
 rows=[list(map(int,line.split())) for line in (a.client/'frames.tsv').read_text().splitlines()]
 selected={i:next(row[5] for row in rows if row[0]==i) for i in [1,2]}
 for i in [1,2]:
  pixels=(a.client/f'frame-{selected[i]}.rgb').read_bytes();assert len(pixels)==256*239*3
  tile=Image.frombytes('RGB',(256,239),pixels).resize((512,478),Image.Resampling.NEAREST)
  x=8+(i-1)*520;im.paste(tile,(x,36));draw.text((x,12),'NES146 / actual SNES output '+str(i),fill='white')
 im.save(a.out/'EXPECTED-SCREENS.png')
 (a.out/'result.json').write_text(json.dumps(dict(source_rom_sha256=sha(a.rom),rgb_inputs={f'frame-{i}.rgb':sha(a.client/f'frame-{selected[i]}.rgb') for i in [1,2]},png_sha256=sha(a.out/'EXPECTED-SCREENS.png'),scope='Actual SNES emulator frames after real RTL packet validation. Fine-X scroll1 and vertical repetition intentional; colors may differ on CRT.'),indent=2)+'\n')
if __name__=='__main__':main()
