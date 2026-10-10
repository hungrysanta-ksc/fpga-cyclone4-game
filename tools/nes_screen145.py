# SPDX-License-Identifier: MIT
"""NES145: exact144 NES fixture and loader,60s bounded MCU display."""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def put(p,s):p.write_text(s,encoding='utf8',newline='\n')
def fixture(base):
 e=base/'nes-pattern144/evidence-final'
 m=json.loads((ROOT/'analysis/screen144-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 f=e/'fixture/screen144.nes';assert sha(f)==pins['fixture/screen144.nes']
 return f.read_bytes()
def prepare(base,out,kind):
 assert kind in ['arm','host'] and not out.exists()
 e=base/'nes-pattern144/evidence-final';fixture(base)
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
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
  p=root/n;parts=re.split(r'(\b0x[0-9a-fA-F]+)',p.read_text(encoding='utf8'));put(p,''.join(x if i%2 else x.replace('144','145') for i,x in enumerate(parts)))
 p=root/'nes_run136.inc';put(p,once(p.read_text(),'i<600','i<1200'))
 if kind=='arm':put(root/'VERSION','RELEASE_VERSION = "NES-SCREEN145"\n')
 else:
  p=root/'host109.c';s=p.read_text()
  for a,z in [('?4:603','?4:1203'),('>=30000000000ull','>=60000000000ull'),('last==60000','last==120000'),('stopped==60000','stopped==120000')]:s=once(s,a,z)
  put(p,s)
 put(out/'preparation145.json',json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h},fixture_unchanged144=True,loader_spi_unchanged144=True,display_polls=1200),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['arm','host'],required=True);a=p.parse_args();prepare(a.baseline,a.out,a.kind)
