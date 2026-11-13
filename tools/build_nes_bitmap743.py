# SPDX-License-Identifier: MIT
"""Mark nine aligned OBJ slots with one 16-bit receipt mask on the 694 client."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from build_nes_trace_replay import Code
from prepare_nes_longrun694 import codec, optimal
from nes_raw506 import sha


def assemble(body, labels, *, entry=None):
    start = labels['obj_unit212'] & 65535
    resume = (labels['same_byte556'] & 65535) + 6
    assert body[start-codec.DEST:start-codec.DEST+5] == bytes.fromhex('a900048568')
    assert body[resume-codec.DEST:resume-codec.DEST+2] == bytes.fromhex('a660')
    if entry is None:
        entry = codec.DEST + len(body)
    # All eight masks touch exactly two bytes. Inputs were already checked
    # for OBJ alignment, nonzero size and bounds by the caller.
    masks = b''.join((0x1ff << bit).to_bytes(2,'little') for bit in range(8))
    c = Code(0x7e0000 + entry + len(masks))
    c.labels.update(labels)
    c.labels['original743'] = start + 3
    c.labels['continue743'] = resume
    c.emit(0xa5,0x64,0xc9,0x20,0x01)  # LDA bytes / CMP #288
    c.branch(0xf0,'nine743')
    c.emit(0xa9,0,4)
    c.jump('original743')
    c.label('nine743')
    c.emit(0xa5,0x62,0x29,0xe0,0,0x4a,0x4a,0x4a,0x4a,0xaa)
    c.long(0xbf,0x7e0000+entry)       # mask[(byte_offset >> 5) & 7]
    c.emit(0x85,0x6e,0xa5,0x62,0xeb,0x29,0xff,0,0xaa,0x18)
    c.absolute(0x6d,0x1254)            # Y adds the selected bank's bitmap offset
    c.emit(0xa8,0xa5,0x6e)
    c.absolute(0x3c,0x1300)            # BIT receipt + 1024/8,X
    c.branch(0xf0,'clean743')
    c.jump('mark_bad212')              # Reject before either bitmap write
    c.label('clean743')
    c.absolute(0x1d,0x1300)
    c.absolute(0x9d,0x1300)
    c.emit(0xa5,0x6e)
    c.absolute(0x19,0x13a0)
    c.absolute(0x99,0x13a0)
    c.jump('continue743')
    patched = bytearray(body)
    patched[start-codec.DEST:start-codec.DEST+3] = bytes([0x4c])+(entry+len(masks)).to_bytes(2,'little')
    patched.extend(masks+c.finish())
    return bytes(patched), {k:v for k,v in c.labels.items() if k.endswith('743')}


def build(client,raw,out,*,control=False):
    assert sha(client/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
    labels=json.loads((client/'labels.json').read_text())
    source=(client/'body.bin').read_bytes()
    body,new_labels=(source,{}) if control else assemble(source,labels)
    with patch.object(codec,'pack',optimal):
        codec.build(raw,out,edit_body=lambda original,table:body,allow_extension=True,prefix_sizes=(96,) if control else (512,384,256,128,112,96,80,64))
    (out/'labels.json').write_text(json.dumps(labels|new_labels,indent=2)+'\n')
    assert (out/'body.bin').read_bytes()==body
    info=json.loads((out/'build.json').read_text())
    print('WRAM bytes, prefix, ROM free:',len(body),info['prefix_B'],info['physical_free_B'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('client','raw','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--control96',action='store_true',help='Repack the original consumer with the same 96-byte boot prefix')
    args=p.parse_args()
    build(args.client,args.raw,args.out,control=args.control96)
