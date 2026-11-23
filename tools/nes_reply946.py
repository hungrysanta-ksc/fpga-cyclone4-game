"""Shorten the 65816 receipt copy while keeping the register order and final strobe."""
from pathlib import Path
import argparse
import shutil
from unittest.mock import patch

from boot_nes_column854 import build
from nes_credit946 import BASE, ROM, ROOT, base
from nes_receipt941 import ORIGIN, BASE as LOADER_BASE, read, sha

MODES=('packed',)


def image(mode):
    return ROOT/('rom-'+mode)


def prepare(mode):
    assert sha(ROM/'sink165.sfc')=='dd66d713015c55a016f78cae5b662488301af12aeb231889454122703abe42c6'
    labels=read(ROM/'labels.json')
    body=bytearray((ROM/'body.bin').read_bytes())
    start=body.index(bytes.fromhex('a20600bd02129d1260caca10f6'),labels['reply']-ORIGIN)
    assert body[start+13:start+16]==bytes.fromhex('a9659a')
    reply=labels['reply']-ORIGIN
    original=bytes.fromhex('e220 8d1060 ad0012 8d1160 c220')
    assert body[reply:start]==original
    # In M=8, park the status in B while loading the opcode. A single
    # 16-bit STA then writes status and opcode in the original bus order.
    packed=bytes.fromhex('e220 eb ad0012 eb c220 8d1060')
    body[reply:start]=packed.ljust(start-reply,bytes([0xea]))
    build(LOADER_BASE,image(mode),bytes(body),labels,compact_mvn=True,minimum=2)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','guards'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int)
    p.add_argument('cache',nargs='?')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='proof':
        from nes_credit946 import run, work
        arm=work(a.mode)
        if not (arm/'link').exists():
            shutil.copytree(BASE/'link',arm/'link')
        assert sha(BASE/'link/src/obj-nes-100/firmware.stm')==sha(arm/'link/src/obj-nes-100/firmware.stm')
        run('proof',a.mode,a.temp,None,None)
    elif a.action=='guards':
        import check_nes_discovery942 as checks
        from nes_credit946 import work
        with patch.object(checks,'ROM',image(a.mode)),patch.object(checks,'work',work):
            checks.check(a.temp,a.mode,tag='946'+a.mode,record='safety946.json')
    else:
        with patch.object(base.prev.chain,'output',lambda _:image(a.mode)):
            base.prev.chain.replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=BASE,tag='946'+a.mode)
