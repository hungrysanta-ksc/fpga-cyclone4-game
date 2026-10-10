# SPDX-License-Identifier: MIT
"""Render measured emulator RGB references, not an invented expected screen."""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw
from nes_spi_boot import sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--client-test',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 m=json.loads((a.client_test/'result.json').read_bytes());assert m['passed'] and m['mode']=='normal' and m['comparison_phases_exact_rgb']==3
 assert not a.out.exists();a.out.mkdir()
 canvas=Image.new('RGB',(768,804),(24,24,24));d=ImageDraw.Draw(canvas);inputs={}
 for i,(name,label) in enumerate([('phase-49.rgb','A / BLUE / ~3 sec'),('phase-50.rgb','B / CPU TILES / ~3 sec'),('phase-51.rgb','C / ROM ATLAS / ~3 sec'),('frame-1.rgb','D / LIVE / fine noise-like pattern is expected')]):
  src=a.client_test/name;inputs[name]=sha(src);im=Image.frombytes('RGB',(256,239),src.read_bytes()).resize((384,358),Image.Resampling.NEAREST)
  x,y=(i%2)*384,(i//2)*402;d.text((x+8,y+12),label,fill='white');canvas.paste(im,(x,y+38))
 out=a.out/'EXPECTED-SCREENS.png';canvas.save(out)
 (a.out/'result.json').write_text(json.dumps(dict(source_rom_sha256=m['inputs']['rom'],rgb_inputs=inputs,png_sha256=sha(out),scope='Exact emulator frames; CRT scaling/colors/scan artifacts may differ.'),indent=2)+'\n')
if __name__=='__main__':main()
