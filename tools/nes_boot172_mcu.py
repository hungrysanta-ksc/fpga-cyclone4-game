# SPDX-License-Identifier: MIT
"""Paired172 identity and bounded SNES startup readiness gate."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(prior,out):
    assert not out.exists();out.mkdir(parents=True)
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='2e7dc90c810601bb351a3d267549db268985e923f78a9eb7bbf6012bdb7f1917'
    m=json.loads((prior/'preparation-prefetch171.json').read_bytes());pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/n,p);r['copied'][n]=h
    def put(n,s):
        (out/n).write_text(s,encoding='utf-8',newline='\n');r['changed' if n in pins else 'added'][n]=sha(out/n)
    for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
        s=(out/n).read_text();t=s
        for a,b in [('NES-GAME-171','NES-GAME-172'),('GAME 171','GAME 172'),('game171.nes','game172.nes'),('fpga_n171.bi3','fpga_n172.bi3'),('last-171.txt','last-172.txt'),('NES171 seq=','NES172 seq='),('nes-progress-171.txt','nes-progress-172.txt'),('NES-GAME171-DEV','NES-GAME172-DEV')]:t=t.replace(a,b)
        assert s!=t,n;put(n,t)
    put('src/nes_boot172.inc',(ROOT/'src/nes/firmware/nes_boot172.inc').read_text())
    n='src/nes_runtime_board165.inc';s=(out/n).read_text()
    anchor='/* This MUST remain a distinct call:';assert s.count(anchor)==1
    s=s.replace(anchor,'#include "nes_boot172.inc"\n'+anchor)
    anchor=' (void)nes_runtime165_begin(';assert s.count(anchor)==1
    s=s.replace(anchor,' if(!native_boot172(io)){native_io165=NULL;return;}\n'+anchor)
    put(n,s)
    for n in ['preparation-boot172.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.prior,a.out)
