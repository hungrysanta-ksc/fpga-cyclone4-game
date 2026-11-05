"""Bind the verified 608 program to board612 and relabel identical ARM610 code."""
import argparse,json,shutil
from pathlib import Path
from check_nes_wire600 import ROOT,read,sha
from package_nes_window516 import LABELS
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('board','arm'))
    for n in ('base','out','client'):p.add_argument('--'+n,type=Path,required=n!='client')
    a=p.parse_args();ev=read(ROOT/'analysis/oe612-verification.json')
    assert not a.out.exists()
    if a.mode=='board':
        assert sha(a.client/'sink165.sfc')==ev['client_SHA']
        rom=(a.client/'sink165.sfc').read_bytes()
        assert bytes.fromhex((a.client/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
        for n,h in ev['inputs'].items():
            assert sha(a.base/n)==h
            dest=a.out/n;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy((a.client if n=='sink-program.hex' else a.base)/n,dest)
        pins={n:sha(a.out/n) for n in ev['inputs']}
        assert [n for n in pins if pins[n]!=ev['inputs'][n]]==['sink-program.hex']
        (a.out/'inputs613.json').write_text(json.dumps(pins,indent=2)+'\n',newline='\n')
    else:
        assert sha(a.base/'src/obj-nes-100/firmware.stm')==ev['ARM_SHA']
        shutil.copytree(a.base,a.out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
        for n in LABELS:
            f=a.out/'src'/n;s=f.read_text();assert '577' in s
            f.write_text(s.replace('577','613'),newline='\n')
