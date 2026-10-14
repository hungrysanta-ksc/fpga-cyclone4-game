# SPDX-License-Identifier: MIT
"""Paired175 MCU: keep174 runtime; accept history v2 and label A4 events."""
from pathlib import Path
import argparse,json
from nes_game147 import sha

def prepare(prior,out):
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='89c98add72ed3a6d983f9961c96b7ac2d7da6a889ba0fc5d5595da25dacfaa87'
    assert not out.exists();out.mkdir(parents=True)
    m=json.loads((prior/'preparation-batch174.json').read_bytes())
    pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes());r['copied'][n]=h
    for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION','src/nes_run136.inc']:
        s=(out/n).read_text()
        for a,b in [('NES-GAME-174','NES-GAME-175'),('GAME 174','GAME 175'),('game174.nes','game175.nes'),('fpga_n174.bi3','fpga_n175.bi3'),('last-174.txt','last-175.txt'),('NES174 seq=','NES175 seq='),('nes-progress-174.txt','nes-progress-175.txt'),('NES-GAME174-DEV','NES-GAME175-DEV')]:s=s.replace(a,b)
        if n.endswith('nes_menu_diagnostic.c'):
            assert s.count('LAST16_NES_CLOCKS_INCLUDING_FAULT')==1
            s=s.replace('LAST16_NES_CLOCKS_INCLUDING_FAULT','LAST16_NATIVE_LIFECYCLE_A4')
        if n.endswith('nes_run136.inc'):
            assert s.count('rx[5]!=1||rx[6]!=96||rx[7]!=1')==1
            s=s.replace('rx[5]!=1||rx[6]!=96||rx[7]!=1','rx[5]!=2||rx[6]!=96||rx[7]!=1')
        (out/n).write_text(s,encoding='utf-8',newline='\n');r['changed'][n]=sha(out/n)
    r['public_sources']={'tools/nes_lifecycle175_mcu.py':sha(Path(__file__))}
    for n in ['preparation-lifecycle175.json','preparation-runlease165.json']:
        (out/n).write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
