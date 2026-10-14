# SPDX-License-Identifier: MIT
"""Pair names and strict history schema2 reader with exact deployed178 runtime."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_reject180 import replace


def prepare(prior,out):
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='69441af67e909e0a32b687f421aacb9193a942de8afededb7993c3cc0ca4ebc1'
    m=json.loads((prior/'preparation-clip178.json').read_bytes())
    assert not out.exists();out.mkdir(parents=True)
    r=dict(copied={},changed={},added={})
    for n,h in (m['copied']|m['changed']|m['added']).items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes());r['copied'][n]=h
    names=[('NES-GAME-178','NES-GAME-180'),('GAME 178','GAME 180'),('game178.nes','game180.nes'),('fpga_n178.bi3','fpga_n180.bi3'),('last-178.txt','last-180.txt'),('NES178 seq=','NES180 seq='),('nes-progress-178.txt','nes-progress-180.txt'),('NES-GAME178-DEV','NES-GAME180-DEV')]
    for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
        p=out/n;s=p.read_text()
        for a,b in names:s=s.replace(a,b)
        if n.endswith('nes_menu_diagnostic.c'):s=replace(s,'LAST16_BOUNDARY177_LOW22','LAST16_REJECT180_V2')
        p.write_text(s,encoding='utf8',newline='\n');r['changed'][n]=sha(p)
    n='src/nes_run136.inc';p=out/n
    p.write_text(replace(p.read_text(),'rx[6]!=96||rx[7]!=1||','rx[6]!=96||rx[7]!=2||'),encoding='utf8',newline='\n');r['changed'][n]=sha(p)
    r.update(history_schema=2,hardware_package=False,public_sources={n:sha(ROOT/n) for n in ['tools/nes_reject180_mcu.py','tools/nes_reject180.py']})
    for n in ['preparation-reject180.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
