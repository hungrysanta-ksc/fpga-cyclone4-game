"""Shorten the successful 65816 tile descriptor checks with a shared reject branch."""
import hashlib
import json
from boot_nes_column854 import build
from build_nes_trace_replay import Code
from prepare_nes_history888 import WORK as BASE

WORK = BASE.parent/'nes-bulk889'
ORIGIN = 0x7e2000


def replacement():
    client = BASE/'client02'
    old = (client/'body.bin').read_bytes()
    assert hashlib.sha256(old).hexdigest()=='32898cdac38c166da8543154fed01714221e69f0d4daab32a310035089fcf4a8'
    labels = json.loads((client/'labels.json').read_bytes())
    start, end = labels['bulk194'], labels['begin']
    body = old[start-ORIGIN:end-ORIGIN]
    # All forward long conditionals in this interval jump to the same
    # bad-packet owner. Keep the descriptor reads, comparisons and order.
    far = bytes([3,0x4c])+int(labels['bad_packet']&0xffff).to_bytes(2,'little')
    code = Code(start)
    code.labels.update(labels)
    previous = 0
    for branch in (0xf0,0x90,0xf0,0xf0,0xf0,0xf0,0xf0,0xd0,0xf0,0x90):
        index = body.index(bytes([branch])+far,previous)
        code.emit(*body[previous:index])
        code.branch(branch ^ 0x20,'reject889')
        previous = index+5
    alignment = body[previous:body.index(bytes([0xf0])+far,previous)]
    assert alignment.hex()=='8d0c120d0a128570ad011229ff00f007a570291f008005a570290f00'
    code.emit(*alignment[:11])  # OR of offset and length is in scratch $70.
    code.emit(0x4a)  # Validated sections 0 and 1 select 16B and 32B.
    code.branch(0x90,'bg889')
    code.emit(0xa5,0x70,0x29,31,0)
    code.branch(0x80,'align889')
    code.label('bg889')
    code.emit(0xa5,0x70,0x29,15,0)
    code.label('align889')
    code.branch(0xd0,'reject889')
    code.emit(0x18)  # The original length bound left carry clear on success.
    code.jump('data')
    code.label('reject889')
    code.jump('bad_packet')
    new = code.finish()
    assert len(new)<=len(body)
    labels['bg_align194']=code.labels['bg889']
    labels['aligned194']=code.labels['align889']
    return old,labels,start-ORIGIN,new.ljust(len(body),b'\xea')


def prepare():
    old,labels,pos,new = replacement()
    build(BASE/'client02',WORK/'client03',old[:pos]+new+old[pos+len(new):],labels)


if __name__=='__main__':
    prepare()
