"""Resource-only full ARM link. Retained recipe is NOT wired into production."""
import argparse, hashlib, json, shutil
from pathlib import Path

def prepare(base,out):
    expected=json.loads(Path('analysis/trial666-package.json').read_text())['firmware_SHA256']
    assert hashlib.sha256((base/'src/obj-nes-100/firmware.stm').read_bytes()).hexdigest()==expected
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    shutil.copyfile(Path(__file__).with_name('nes_supply671.c'),out/'src/nes_supply671.c')
    p=out/'src/Makefile';s=p.read_text();anchor='SRC += nes_cost471.c';assert s.count(anchor)==1
    s=s.replace(anchor,'SRC += nes_supply671.c\n'+anchor)
    s+='\nLDFLAGS += -Wl,--undefined=recipe671\n';p.write_text(s,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
