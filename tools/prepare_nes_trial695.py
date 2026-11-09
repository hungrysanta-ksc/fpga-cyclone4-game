"""Relabel unchanged MMC690 normal and694 long builds as695/696 respectively."""
import argparse,json
from pathlib import Path
from package_nes_window516 import LABELS
from nes_raw506 import sha

def run(a):
    expected=json.loads(Path('analysis/trial690-package.json').read_text())['firmware_SHA256']
    records={}
    for name,base,number,wanted in [('normal',a.normal,'695',expected),('long',a.long,'696','b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600')]:
        assert sha(base/'src/obj-nes-100/firmware.stm')==wanted
        out=a.out/name;out.mkdir(parents=True,exist_ok=False);pins={}
        for f in LABELS:
            p=base/'src'/f;b=p.read_bytes();assert b'690' in b and number.encode() not in b
            (out/f).write_bytes(b.replace(b'690',number.encode()))
            pins[f]={'before':sha(p),'after':sha(out/f)}
        records[name]={'trial':number,'base_firmware':wanted,'files':pins}
    (a.out/'labels.json').write_text(json.dumps(records,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('normal','long','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
