# SPDX-License-Identifier: MIT
"""Use the two required raw rows when the independent six-row receipt is 0x1d."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from build_nes_static751 import codec, pack, sha


def build(client, raw, out):
    assert sha(client/'body.bin') == '74818b9f1ff02db6be843f4355f74ad57d42d99ea6f4cefbbbe9ba643e16b693'
    labels=json.loads((client/'labels.json').read_text())
    b=bytearray((client/'body.bin').read_bytes())
    def offset(name):
        return (labels[name]&0xffff)-codec.DEST
    def jmp(at):
        return b'\x4c'+(codec.DEST+at).to_bytes(2,'little')
    i=offset('raw_dma489')
    assert b[i:i+10]==bytes.fromhex('a478c01500d003')+jmp(offset('pairs624'))
    # Preserve A16 (destination) for both entries. The independent receipt
    # initializer sets these masks only for a fully covered warm 384B patch.
    dispatch=len(b)
    b.extend(bytes.fromhex('a478c01500f008c01d00f003')+jmp(offset('generic624'))+jmp(offset('pairs624')))
    b[i:i+3]=jmp(dispatch)
    row=offset('row624_1')
    service=bytes(b[row:row+3])
    assert service[0]==0x20
    # The middle pair is already certified only in mask 0x1d. Both actual
    # 64B writes retain the existing service/STOP, bank and DMA setup.
    skip=len(b)
    b.extend(bytes.fromhex('a478c01d00d003')+jmp(offset('row624_2'))+service+jmp(row+3))
    b[row:row+3]=jmp(skip)
    assert len(b)<=0x1900 and len(b)-len((client/'body.bin').read_bytes())==34
    with patch.object(codec,'pack',pack):
        codec.build(raw,out,edit_body=lambda *_:bytes(b),allow_extension=True,prefix_sizes=[512],
                    medium_pages=True,boot_bytes=320,fast_backrefs=True)
    (out/'labels.json').write_bytes((client/'labels.json').read_bytes())
    info=json.loads((out/'build.json').read_text())
    info.update(body_SHA256=sha(out/'body.bin'),certified_masks=[21,29],body_bytes=len(b))
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('client','raw','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    build(a.client,a.raw,a.out)
