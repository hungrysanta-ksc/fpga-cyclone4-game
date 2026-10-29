# SPDX-License-Identifier: MIT
"""Bind the selected ARM/RTL fail-stop runs to 458's QSF input hashes."""
import collections,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=BASE/'probes/nes-nrom461';pins=json.loads((ROOT/'analysis/nrom458-artifacts.json').read_text())['qsf_sources'];out={}
for n,fault,reads,err in [('08','corrupt',17,6),('09','source',16,4)]:
 d=p/f'joint{n}';r=json.loads((d/'result.json').read_text());assert r['passed'] and r['fault']==fault and r['report']=={'compared':16,'error':err,'stop_ok':1}
 for name,h in pins.items():assert sha(d/name)==h,(n,name)
 req=sorted(d.glob('H-*.req'));ops=collections.Counter(x.read_bytes()[8] for x in req if len(x.read_bytes())>=9 and x.read_bytes()[0]==1);assert ops[0x63]==0 and ops[0x64]==1 and ops[0x67]==reads and ops[0x68]==16
 out[n]={'fault':fault,'result_sha256':sha(d/'result.json'),'qsf_inputs_matched':len(pins),'spi_ops':{hex(k):v for k,v in sorted(ops.items())}}
r={'passed':True,'runs':out,'scope':'actual 418 ARM verification code with 457 board RTL via transaction RPC; seeded PSRAM/loader; no physical hardware or timing'};(ROOT/'analysis/nrom461-joint.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
