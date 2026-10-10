# SPDX-License-Identifier: MIT
"""Reuse134 shell with factored SPI/boot checks and targeted loader mapping."""
from pathlib import Path
import json,shutil
from nes_board134 import prepare as prepare134
from nes_cdc125_sta import ROOT,sha,put

def prepare(baseline,o):
 e=baseline/'nes-board134/evidence'
 m=json.loads((ROOT/'analysis/board134-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 names=prepare134(baseline,o)
 # Require every copied HDL file to be the actually selected134 implementation.
 for n in names+['nes_clock_pll123.v','nes_run_observer134.sv','fxpak_nes_run134_top.sv']:
  assert sha(e/'fit02'/n)==pins['fit02/'+n] and sha(o/n)==pins['fit02/'+n],n
 changes={}
 for stem in ['nes_rom_spi','nes_rom_boot','nes_rom_loader']:
  n=stem+'.sv';old=sha(o/n)
  shutil.copy2(ROOT/'src/nes/diagnostic'/(stem+'135.sv'),o/n)
  changes[n]=dict(before=old,after=sha(o/n))
 put(o/'materialization135.json',json.dumps(dict(base_manifest=m['manifest_sha256'],changed=changes,inputs={n:sha(o/n) for n in names}),indent=2)+'\n')
 return names
