# SPDX-License-Identifier: MIT
# Pinned033 builder adaptation in ignored output; original033 sources are unchanged.
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve();repo=Path(__file__).resolve().parents[1];assert str(out).isascii() and not out.exists();out.mkdir()
 source=repo/'tools/build_nes_h1_pattern.py'
 assert sha(source)=='b193ba8a2924f9cd4964a7858305af0aa0897ea645a0389a7d1f0cb73b48baad'
 text=source.read_text()
 changes=[("NES-H1-PATTERN-033","NES-H1-BOARD-034"),("NES H1 033","NES H1 034"),("NES H1 PATTERN 033","NES H1 BOARD 034"),("nes-h1-pattern-033.sfc","nes-h1-board-034.sfc"),
 ("FONT={**FONT,","FONT={**FONT,\n '4':['00010','00110','01010','10010','11111','00010','00010'],"),
 ("c.store(0x6002,1);c.store(0x6003,0)","c.absolute(0xad,0x600b);c.absolute(0x8d,0x6002);c.absolute(0xad,0x600c);c.absolute(0x8d,0x6003)"),
 ("Cold common reset epoch1 assumption; board loader/reset epoch handoff unresolved.","Epoch read from034 board registers600B/C; loader must hold SNES reset through ARM and verify generation before release.")]
 for old,new in changes:assert old in text,old;text=text.replace(old,new)
 generated=out/'derived-builder.py';generated.write_text('import sys\nsys.path.insert(0,'+repr(str(repo/'tools'))+')\n'+text,encoding='utf-8',newline='\n')
 cp=subprocess.run([sys.executable,'-B','-X','utf8',str(generated),'--out',str(out/'build')],capture_output=True)
 (out/'builder.log').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,'builder.log'
 rom=(out/'build/nes-h1-board-034.sfc').read_bytes();assert len(rom)==65536
 compact=bytearray([255])*24576
 compact[:0x3200]=rom[:0x3200];compact[0x3fc0:0x4000]=rom[0x7fc0:0x8000];compact[0x4000:0x6000]=rom[0x8000:0xa000]
 def read(i):
  bank,off=divmod(i,32768)
  if bank:return compact[0x4000+off] if off<0x2000 else 255
  if off<0x3200:return compact[off]
  return compact[0x3fc0+(off&63)] if off>=0x7fc0 else 255
 assert bytes(read(i) for i in range(65536))==rom
 (out/'build/h1-program.hex').write_text(''.join(f'{b:02x}\n' for b in compact))
 (out/'build/program-full.hex').write_text(''.join(f'{b:02x}\n' for b in rom))
 meta={'candidate':'NES-H1-BOARD-034','base_builder_sha256':sha(source),'derived_builder_sha256':sha(generated),'driver_sha256':sha(__file__),'program_sha256':sha(out/'build/h1-program.hex'),'rom_sha256':sha(out/'build/nes-h1-board-034.sfc'),'pattern_sha256':sha(out/'build/h1-pattern.hex'),'roundtrip_bytes':65536,'hardware_eligible':False}
 (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
if __name__=='__main__':main()
