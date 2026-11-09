"""Materialize immutable689D board inputs with only the selected694 ROM changed."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import sha

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','client','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();meta=json.loads((a.base/'inputs689.json').read_text())
    pins={n:meta['changed'].get(n,h) for n,h in meta['base'].items()}
    a.out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(a.base/n)==h,n
        dest=a.out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.base/n,dest)
    rom=(a.client/'sink165.sfc').read_bytes();data=bytes.fromhex((a.client/'sink-program.hex').read_text())
    assert len(data)==5120 and data==rom[:5056]+rom[-64:]
    shutil.copyfile(a.client/'sink-program.hex',a.out/'sink-program.hex')
    changed={n:sha(a.out/n) for n,h in pins.items() if sha(a.out/n)!=h}
    assert set(changed)=={'sink-program.hex'}
    (a.out/'inputs694.json').write_text(json.dumps(dict(base=pins,changed=changed,CPU=sha(a.client/'sink165.sfc'),constraints_changed=False,seed_changed=False),indent=2)+'\n')
    print('BOARD694',len(pins),'inputs pinned; only sink-program.hex changed')
