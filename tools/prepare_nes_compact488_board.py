# SPDX-License-Identifier: MIT
"""Copy the pinned482 whole-board closure, replacing only its paired program ROM."""
import argparse,json,shutil
from pathlib import Path
from check_nes_game478 import sha
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for n in ['baseline','client','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
old=json.loads((ROOT/'analysis/supply485-verification.json').read_text())['whole_board_inputs']
for n,h in old.items():
    rel=Path(n);assert not rel.is_absolute() and '..' not in rel.parts
    assert sha(a.baseline/rel)==h,n
    dest=a.out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.baseline/rel,dest)
f=a.out/'nes_sink_bus165.sv';s=f.read_text()
for before,after in [('program_rom[0:4095]','program_rom[0:8191]'),("15'h0fc0","15'h1fc0"),('program_rom[address_sync[11:0]]','program_rom[address_sync[12:0]]')]:
    assert s.count(before)==1,before;s=s.replace(before,after)
f.write_text(s,encoding='utf8',newline='\n')
program=bytes.fromhex((a.client/'sink-program.hex').read_text());assert len(program)==8192
shutil.copyfile(a.client/'sink-program.hex',a.out/'sink-program.hex')
pins={n:sha(a.out/n) for n in old}
r={'baseline_inputs':old,'board_inputs':pins,'changed':[n for n in old if old[n]!=pins[n]],'program_SHA256':__import__('hashlib').sha256(program).hexdigest(),'client_SHA256':sha(a.client/'sink165.sfc'),'scope':__doc__}
assert set(r['changed'])=={'nes_sink_bus165.sv','sink-program.hex'}
(a.out/'source-pins.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
print(json.dumps({'changed':r['changed'],'program_SHA256':r['program_SHA256']}))
