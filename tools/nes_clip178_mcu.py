# SPDX-License-Identifier: MIT
"""Pair the178 clipping converter and20-byte sink with the pinned177 firmware."""
from pathlib import Path
import argparse,json
from nes_game147 import sha
from nes_clip178 import converter,header,sink

def prepare(prior,out):
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='a8b5159e184e47c8c7a54b8c94287f35c433fced23cdbf2f907cf547d941aea8'
    m=json.loads((prior/'preparation-boundary177.json').read_bytes())
    assert not out.exists();out.mkdir(parents=True)
    r=dict(copied={},changed={},added={})
    for n,h in (m['copied']|m['changed']|m['added']).items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes());r['copied'][n]=h
    for n,fn in [('nes_native_video165.c',converter),('nes_native_video165.h',header),('nes_native_sink165.c',sink)]:
        p=out/'src'/n;p.write_text(fn(p.read_text()),encoding='utf8',newline='\n');r['changed']['src/'+n]=sha(p)
    names=[('NES-GAME-177','NES-GAME-178'),('GAME 177','GAME 178'),('game177.nes','game178.nes'),('fpga_n177.bi3','fpga_n178.bi3'),('last-177.txt','last-178.txt'),('NES177 seq=','NES178 seq='),('nes-progress-177.txt','nes-progress-178.txt'),('NES-GAME177-DEV','NES-GAME178-DEV')]
    for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
        p=out/n;s=p.read_text()
        for a,b in names:s=s.replace(a,b)
        p.write_text(s,encoding='utf8',newline='\n');r['changed'][n]=sha(p)
    # History layout remains177; runtime, transport, timers, controller and audio unchanged.
    for n in ['nes_run136.inc','nes_runtime_board165.inc','nes_native165.c','nes_sink_spi165.c']:
        assert (out/'src'/n).read_bytes()==(prior/'src'/n).read_bytes(),n
    r.update(public_sources={str('tools/'+n):sha(Path(__file__).parent/n) for n in ['nes_clip178.py','nes_clip178_mcu.py']},seal_bytes=20,accepted_masks=[24,30],paired_snes_required=True,hardware_package=False)
    for n in ['preparation-clip178.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
