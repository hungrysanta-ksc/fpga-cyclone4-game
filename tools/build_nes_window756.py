# SPDX-License-Identifier: MIT
"""Add checked map deltas to the 751 static ROM; report board overflow independently."""
import argparse
import json
import textwrap
from pathlib import Path
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_group628 import DECODE
from nes_raw506 import sha
from pack_nes_static751 import pack
from prepare_nes_longrun694 import codec


def build(client,raw,out):
    reference=json.loads((client/'build.json').read_text())
    assert sha(client/'body.bin')==reference['body_SHA256']
    labels=json.loads((client/'labels.json').read_text())
    body=bytearray((client/'body.bin').read_bytes())
    c=Code(0x7e2000+len(body))
    c.labels.update(labels)
    def address(name):
        return c.labels[name]&65535
    def hook(original,target):
        index=body.index(original)
        assert body.count(original)==1
        body[index:index+3]=bytes([0x4c])+address(target).to_bytes(2,'little')
        return 0x2000+index+3
    c.label('dispatch756')
    c.absolute(0xad,0x1200)
    c.emit(0xc9,9,2);c.branch(0xf0,'header628')
    c.absolute(0x4c,hook(bytes.fromhex('ad0012c90904f0034caf27ad0a12'),'dispatch756'))
    # All other headers return to the original dispatch, including the OAM ABI.
    lda=lambda addr:c.absolute(0xad,addr)
    sta=lambda addr:c.absolute(0x8d,addr)
    cmp=lambda addr:c.absolute(0xcd,addr)
    def cond(branch,label):
        c.emit(branch^0x20,3);c.jump(label)
    exec(textwrap.dedent(DECODE),dict(c=c,lda=lda,sta=sta,cmp=cmp,cond=cond,call=call))
    c.label('route_copy756')
    # M=8. Check section as well: opcode 9/OAM must still use the ordinary copy.
    lda(0x1200);c.emit(0xc9,9);c.branch(0xd0,'normal_copy756')
    lda(0x1201);c.emit(0xc9,2);cond(0xf0,'decode628')
    c.label('normal_copy756');lda(0x1200)
    c.absolute(0x4c,hook(bytes.fromhex('ad0012c904f007c905f003'),'route_copy756'))
    body.extend(c.finish())
    assert codec.DEST+len(body)<0x4000
    # Same reset loader and two-pass readback. An image beyond five blocks is
    # diagnostic only. Compute its exact excess rather than suppressing timing.
    prefix=reference['prefix_B']
    with patch.object(codec,'pack',pack),patch.object(codec,'STORED',0x2000):
        codec.build(raw,out,edit_body=lambda *_:bytes(body),allow_extension=True,prefix_sizes=[prefix],
                    medium_pages=True,boot_bytes=320,fast_backrefs=True,body_limit=0x1fff)
    (out/'labels.json').write_text(json.dumps(c.labels)+'\n',encoding='utf8')
    meta=json.loads((out/'build.json').read_text())
    meta.update(board_storage_free=5056-320-prefix-meta['encoded_B'],body_free=6400-len(body),
                diagnostic_aperture_B=0x2000,body_SHA256=sha(out/'body.bin'))
    meta.update(copy_verified_bytes=len(body),body_capacity=6400,physical_ROM_B=5120,physical_free_B=meta['board_storage_free'],
                required_physical_bytes=5120-meta['board_storage_free'])
    meta['board_fit']=min(meta['board_storage_free'],meta['body_free'])>=0
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
    print(meta['board_storage_free'],meta['body_free'])
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('client','raw','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    build(a.client,a.raw,a.out)
