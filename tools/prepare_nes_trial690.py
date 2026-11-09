"""Relabel the verified688 ARM; do not change executable instructions."""
import argparse,json
from pathlib import Path
from check_nes_fault641 import ROOT,digest,evidence
from package_nes_window516 import LABELS

def prepare(base,out):
    proof=evidence('status689-verification.json')
    assert proof['request_gate'] and digest(base/'src/obj-nes-100/firmware.stm')==proof['firmware']
    out.mkdir(parents=True,exist_ok=False)
    pins={}
    for name in LABELS:
        p=base/'src'/name;data=p.read_bytes()
        assert b'666' in data and b'690' not in data
        (out/name).write_bytes(data.replace(b'666',b'690'))
        pins[name]=dict(before=digest(p),after=digest(out/name))
    (out.parent/'labels.json').write_text(json.dumps(pins,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
