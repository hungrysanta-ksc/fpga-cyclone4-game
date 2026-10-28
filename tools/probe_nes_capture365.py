# SPDX-License-Identifier: MIT
"""Shared board capture/source admission, real collector queries and input ROM load.

Uses the retained338/355/359/BG5OBJ2 implementation. Output M4 runs live and
65816 ordinary bus traces are replayed; map DMA/final display remain bus models.
"""
import sys,shutil,json
cadence_enabled='--cadence' in sys.argv
if cadence_enabled:sys.argv.remove('--cadence')
early_release='--early-release' in sys.argv
if early_release:sys.argv.remove('--early-release')
if '--keep-source' not in sys.argv:sys.argv.append('--keep-source')
import probe_nes_objpath362 as previous
from nes_capture365 import functional,cadence,cadence366,COMMON
from nes_delta231 import ROOT,BASE,sha
engine=previous.engine
old_prepare=engine.prepare

def prepare(*a,**k):
    oracle_files=[]
    if a[1]>907:
        args=list(a);bundle=a[0].parent/(a[0].name+'-plans');bundle.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(a[3]/'chr.hex',bundle/'chr.hex')
        for f in range(905,a[1]+1):
            original=BASE/f'probes/nes-joint284/test04/plans{f-904}.bin'
            if f<=907:assert sha(original)==sha(a[3]/original.name)
            shutil.copyfile(original,bundle/original.name);oracle_files.append(original)
        args[3]=bundle;a=tuple(args)
    src,pins=old_prepare(*a,**k);d=a[0];functional(d,early=early_release)
    if cadence_enabled:(cadence366 if early_release else cadence)(d)
    src=[n for n in src if n not in ('nes_plan_rom267.sv','nes_capture_lease201.sv','nes_joint266.sv')]
    for n in COMMON:
        if n not in src:src.append(n)
        pins['shared365/'+n]=sha(d/n)
    for n in ('nes_capture365.py','probe_nes_capture365.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    for f in oracle_files:pins[str(f)]=sha(f)
    (d/'manifest365.json').write_text(json.dumps(dict(sources=src,shared_boundary={n:sha(d/n) for n in COMMON},cadence=cadence_enabled,early_release=early_release),indent=2)+'\n',newline='\n')
    return src,pins

engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
