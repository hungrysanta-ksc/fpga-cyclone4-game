# SPDX-License-Identifier: MIT
"""Leave a right-page prefix eligible for merging while ordinary packets arrive."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from build_nes_trace_replay import Code
from prepare_nes_longrun694 import codec
from pack_nes_static751 import pack
from nes_raw506 import sha

def build(client,raw,out):
    body=bytearray((client/'body.bin').read_bytes())
    labels=json.loads((client/'labels.json').read_text())
    assert sha(client/'body.bin')=='74818b9f1ff02db6be843f4355f74ad57d42d99ea6f4cefbbbe9ba643e16b693'
    pos=(labels['selected526']&65535)-codec.DEST
    saved=bytes(body[pos:pos+3]);assert saved==bytes.fromhex('20 84 37')
    helper=codec.DEST+len(body)
    c=Code(0x7e0000+helper);c.labels.update(labels)
    # The selector always enters in A16. X points at a checked WRAM descriptor.
    # Only the exact right-page start can be held. Final SEAL executes sparse
    # pages through the normal final upload, without relying on this idle path.
    c.long(0xbf,0x7e4000);c.emit(0x29,0xff,0x7f,0xc9,0,0x58)
    c.branch(0xd0,'select759')
    c.long(0xbf,0x7e4004);c.emit(0xc9,0,6);c.branch(0xb0,'select759')
    c.jump('defer_beam')
    c.label('select759');c.emit(*saved);c.absolute(0x4c,codec.DEST+pos+3)
    body[pos:pos+3]=bytes([0x4c])+helper.to_bytes(2,'little');body.extend(c.finish())
    with patch.object(codec,'pack',pack):
        codec.build(raw,out,edit_body=lambda *_:bytes(body),allow_extension=True,prefix_sizes=[512],
                    medium_pages=True,boot_bytes=320,short_errors=False,fast_backrefs=True)
    (out/'labels.json').write_text(json.dumps(labels,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','raw','out'):p.add_argument(n,type=Path)
    a=p.parse_args();build(a.client,a.raw,a.out)
