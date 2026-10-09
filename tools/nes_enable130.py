# SPDX-License-Identifier: MIT
"""Pinned129 with loader state clock-enable inference disabled locally."""
import json,shutil
from nes_loader127 import ROOT,sha,put,replace

def materialize(o,baseline,full=False):
 e=baseline/'nes-reader129/evidence';m=json.loads((ROOT/'analysis/reader129-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prefix='fit01/'
 names=[n[len(prefix):] for n in pins if n.startswith(prefix) and n.endswith(('.sv','.v','.vhd','.qsf','.sdc','.qpf'))]
 if not full:names=[n for n in names if '/' not in n and n.endswith('.sv')]
 inputs={}
 for n in names:
  src=e/prefix/n;assert sha(src)==pins[prefix+n];dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 p=o/'nes_rom_loader.sv';s=p.read_text()
 s=replace(s,' reg [3:0] state;', ' (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) reg [3:0] state;')
 put(p,s)
 put(o/'materialization130.json',json.dumps(dict(inputs=inputs,outputs={p.relative_to(o).as_posix():sha(p) for p in o.rglob('*') if p.is_file()}),indent=2)+'\n')
