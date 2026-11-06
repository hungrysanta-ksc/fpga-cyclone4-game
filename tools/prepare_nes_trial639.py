# SPDX-License-Identifier: MIT
"""Relabel the selected 638 image only after both real late-beam checks."""
import argparse
import json
import shutil
from pathlib import Path
from check_nes_wire600 import ROOT,read,sha
from package_nes_window516 import LABELS


def gate(path):
    r=read(path)
    boot=read(ROOT/'analysis/dma637-verification.json')['head_boot']
    assert (r['client'],r['body'])==(boot['ROM'],boot['body_SHA'])
    for name,event in (('mdma','mdma'),('mdma','first'),('latch','latch')):
        v=r['cases'][name]
        exact=v['beam'][event]
        assert exact['line']==252 and 1000<exact['h']<1364
        assert v['race']['size']==1152 and v['race']['next_head_ACK']==0
        assert exact['frame']==v['beam']['last']['frame'] and v['beam']['last']['line']<262
        assert v['race']['quiet']>v['race']['last_write']>v['race']['first_write']
    for name in ('both','head'):
        assert r['cases'][name]['race']['size']==0
    return r


def prepare(base,out,edge):
    gate(edge)
    selected=read(ROOT/'analysis/front638-verification.json')
    assert selected['passed']['both']
    assert all(sha(base/'src/obj-nes-100/firmware.stm')==v['modes']['both']['schedule']['image'] for v in selected['cases'])
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    for name in LABELS:
        f=out/'src'/name
        original=f.read_bytes()
        assert b'577' in original and b'639' not in original
        f.write_bytes(original.replace(b'577',b'639'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','out','edge'):p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args();prepare(a.base,a.out,a.edge)
