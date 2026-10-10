# SPDX-License-Identifier: MIT
"""Readable CHR-only diagnostic and exact143 MCU materialization."""
from pathlib import Path
import argparse,json,re,shutil,zlib
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from nes_display138 import fixture as old_fixture

FONT={
'N':['10001','11001','10101','10011','10001','10001','10001'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
' ':['00000']*7}

def banner(bank):
 # The unchanged NES program writes sequential tile IDs into each8-row band.
 # A complete256x64 picture is therefore divided into256 NES tiles.
 pix=bytearray(256*64)
 for y in range(64):
  for x in range(256):
   if x<4 or x>=252 or y<4 or y>=60:pix[y*256+x]=3
   elif 7<=x<17 or 239<=x<249:pix[y*256+x]=1 if bank==0 else 3
 def text(s,x,y,scale,color):
  for ch in s:
   for yy,row in enumerate(FONT[ch]):
    for xx,on in enumerate(row):
     if on=='1':
      for dy in range(scale):
       for dx in range(scale):pix[(y+yy*scale+dy)*256+x+xx*scale+dx]=color
   x+=6*scale
 text('NES 144',32,13,3,2)
 text('A' if bank==0 else 'B',190,13,3,1 if bank==0 else 3)
 for y in range(44,53):
  for x in range(32,224):pix[y*256+x]=1+(x//32)%3
 return bytes(pix)

def fixture(base):
 old=old_fixture(base);chrdata=bytearray()
 for bank in range(4):
  pix=banner(bank//2)
  for tile in range(256):
   tx,ty=tile%32*8,tile//32*8
   for plane in range(2):
    for y in range(8):
     chrdata.append(sum(((pix[(ty+y)*256+tx+x]>>plane)&1)<<(7-x) for x in range(8)))
 assert len(chrdata)==16384
 return old[:16+65536]+chrdata

def build(base,out):
 assert not out.exists();out.mkdir(parents=True);rom=fixture(base)
 (out/'screen144.nes').write_bytes(rom)
 for n,data in [('prg',rom[16:65552]),('chr',rom[65552:])]:
  (out/(n+'.hex')).write_text(''.join(f'{v:02x}\n' for v in data))
 (out/'manifest.json').write_text(json.dumps(dict(candidate='NES-SCREEN-144',rom_sha256=sha(out/'screen144.nes'),prg_unchanged=True,crc32=f'{zlib.crc32(rom):08x}',scope='Original readable CHR, unchanged143 NES program, mapper4 64KiB PRG+16KiB CHR. Two banners in alternating4KiB CHR banks.'),indent=2)+'\n')

def put(p,s):p.write_text(s,encoding='utf8',newline='\n')

def prepare(base,out,kind):
 assert kind in ['arm','host'] and not out.exists()
 e=base/'nes-screen143/evidence-final';m=json.loads((ROOT/'analysis/screen143-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for n,h in pins.items():
  if not n.startswith(kind+'/'):continue
  rel=n[len(kind)+1:];p=Path(rel)
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='host' and p.suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  assert sha(e/n)==h,n
  d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 root=out/'src' if kind=='arm' else out
 names=['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc','nes_cf86_session094.c','nes_cf86_session094.h','nes_rom_verify.c']
 if kind=='host':names+=['card.c','config097_card.inc','host109.c','platform.c']
 for n in names:
  p=root/n;parts=re.split(r'(\b0x[0-9a-fA-F]+)',p.read_text(encoding='utf8'));put(p,''.join(x if i%2 else x.replace('143','144') for i,x in enumerate(parts)))
 p=root/'nes_h1_stm32.c';s=p.read_text();old=f'expected_crc=0x{zlib.crc32(old_fixture(base)):08x}u;';assert s.count(old)==1;put(p,s.replace(old,f'expected_crc=0x{zlib.crc32(fixture(base)):08x}u;'))
 # Observed143 phase capture is unreliable. Preserve raw values; do not claim
 # mask completeness or silently turn unknown stages into a pass condition.
 p=root/'nes_menu_diagnostic.c';s=p.read_text();put(p,once(s,'screen_phase_mask=%u\\n','screen_phase_mask=%u\\nscreen_telemetry_trusted=0\\n'))
 if kind=='arm':put(root/'VERSION','RELEASE_VERSION = "NES-SCREEN144"\n')
 else:
  (out/'fixture.nes').write_bytes(fixture(base))
  p=root/'platform.c';put(p,once(p.read_text(),'stop_count?0x63:observe_count136<62?0x31:observe_count136<122?0x32:observe_count136<182?0x33:0x63','0x63'))
 put(out/'preparation144.json',json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['arm','host','fixture'],required=True);a=p.parse_args()
 if a.kind=='fixture':build(a.baseline,a.out)
 else:prepare(a.baseline,a.out,a.kind)
