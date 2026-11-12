# SPDX-License-Identifier: MIT
"""Build a static 65816 receiver sharing the beam latch and VRAM range programming."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from build_nes_trace_replay import Code
from prepare_nes_longrun694 import codec, optimal
from replay_nes_bg750 import edits
from pack_nes_static751 import pack
from nes_raw506 import sha


def assemble(client):
    labels=json.loads((client/'labels.json').read_text())
    body=bytearray((client/'body.bin').read_bytes())
    assert sha(client/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
    def address(k):
        return labels[k]&65535
    def place(at,code,size=None):
        if size is None:
            size=len(code)
        assert len(code)<=size and at-codec.DEST<=len(body)
        body[at-codec.DEST:at-codec.DEST+size]=code+b'\xea'*(size-len(code))
    def absolute(op,at):
        return bytes([op])+at.to_bytes(2,'little')
    patches=edits(client,'bg')
    for at,data in sorted(patches.items()):
        if at<codec.DEST+len(body) and at!=address('no_event680')+3:
            place(at,data)
    # Existing latch code returns a fresh nine-bit counter in A16; a stale
    # latch or active video returns FFFF. The same code serves both callers.
    select=address('selected526')
    ordinary=body.index(bytes.fromhex('8d3e10'),select-codec.DEST)+codec.DEST
    base=codec.DEST+len(body)
    c=Code(0x7e0000+base)
    c.labels.update(labels)
    c.label('latch751')
    c.emit(0xe2,0x20);c.absolute(0xad,0x4212);c.branch(0x10,'invalid751')
    c.absolute(0xad,0x213f);c.absolute(0xad,0x213f)
    c.emit(0x89,0x40);c.branch(0xd0,'invalid751')
    c.absolute(0xad,0x2137);c.absolute(0xad,0x213f)
    c.emit(0x89,0x40);c.branch(0xf0,'invalid751')
    c.absolute(0xad,0x213d);c.emit(0xeb);c.absolute(0xad,0x213d);c.emit(0x29,1,0xeb,0xc2,0x20,0x60)
    c.label('invalid751');c.emit(0xc2,0x20,0xa9,0xff,0xff,0x60)
    latch=c.finish()
    s=Code(0x7e0000+select)
    s.labels.update(labels)
    s.absolute(0x20,base);s.emit(0xc9,225,0);s.branch(0x90,'defer_beam')
    s.emit(0xc9,253,0);s.branch(0xb0,'defer_beam');s.emit(0xe2,0x20)
    s.absolute(0x4c,ordinary)
    room=select+len(s.finish())
    place(select,s.finish(),ordinary-select)
    # One source/destination/length writer. Both callers supply X/Y and A16.
    issue=address('issue523')
    end=address('priority524')
    program=bytes.fromhex('bf00407e8d0243988d0543bf02407e4a8d162160')
    assert room+len(program)<=ordinary
    place(room,program)
    normal=bytes.fromhex('a901188d0043a97f008d0443')+absolute(0x20,room)+bytes.fromhex('e220a9808d1521')+absolute(0x4c,end)
    place(issue,normal,end-issue)
    # Hook only map completion after its original E0 pulse has been published.
    head=address('no_event680')
    map_entry=head-9
    c=Code(0x7e0000+base+len(latch))
    c.labels.update(labels)
    c.emit(*body[map_entry-codec.DEST:head-codec.DEST]);c.emit(0xc0,0,6);c.branch(0xd0,'slow751')
    c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);c.branch(0xb0,'slow751')
    c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0,0xc9,0x40,0);c.branch(0xd0,'slow751')
    c.long(0xbf,0x7e4004);c.emit(0xc9,0x20,1);c.branch(0xd0,'slow751');c.emit(0xa8)
    c.absolute(0x20,base);c.emit(0x38,0xe9,225,0,0xc9,33,0);c.branch(0xb0,'slow751')
    c.absolute(0x20,room);c.emit(0xe2,0x20)
    c.absolute(0xad,0x4212);c.branch(0x10,'skip751');c.absolute(0x9c,0x1238)
    c.absolute(0xad,0x1236);c.branch(0xd0,'skip751');c.jump('priority524')
    c.label('skip751');c.emit(0xc2,0x20)
    c.label('slow751');c.jump('no_event680')
    place(map_entry,absolute(0x4c,base+len(latch)),9)
    # Reuse the original head/end comparison before both selectors.
    reentry=base+len(latch)+len(c.finish())
    oldhead=body.index(bytes.fromhex('ae5212ec5012'),address('prefix523')-codec.DEST)+codec.DEST
    tail=Code(0x7e0000+reentry);tail.labels.update(labels)
    tail.branch(0xd0,'stopped751')
    tail.emit(0xe2,0x20);tail.absolute(0xad,0x6000);tail.emit(0x4a);tail.branch(0xb0,'packet751')
    tail.emit(0xc2,0x20,0xc0,48,0);tail.branch(0xd0,'normal751')
    tail.absolute(0xae,0x1252);tail.absolute(0xec,0x1250);tail.branch(0xf0,'empty751');tail.jump('tail532')
    tail.label('normal751');tail.absolute(0x4c,oldhead)
    tail.label('empty751');tail.jump('skip523')
    tail.label('packet751');tail.jump('skip8_523')
    tail.label('stopped751');tail.jump('stop523')
    place(head+3,absolute(0x4c,reentry))
    place(base,latch+c.finish()+tail.finish())
    return bytes(body),labels


def fused(client):
    """Dispatch both idle and post-DMA work through the original range writer."""
    labels=json.loads((client/'labels.json').read_text())
    raw=(client/'body.bin').read_bytes()
    assert sha(client/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
    body=bytearray(raw)
    addr=lambda name: labels[name]&65535
    def install(at,data):
        i=at-codec.DEST
        assert i<=len(body)
        body[i:i+len(data)]=data
    def jump(at,target):
        install(at,bytes((0x4c,))+target.to_bytes(2,'little'))
    patches=edits(client,'bg')
    for at,data in patches.items():
        if at<codec.DEST+len(raw) and at!=addr('no_event680')+3:
            install(at,data)
    # Keep the existing PPU latch. Return to its original normal decision on
    # 225..252; the high-line entry can only grant an exact admitted 288B OBJ.
    select=addr('selected526')
    at=raw.index(bytes.fromhex('2901d045ebc9e1'),select-codec.DEST)+codec.DEST
    base=codec.DEST+len(raw)
    c=Code(0x7e0000+base); c.labels.update(labels)
    c.emit(0x29,1,0xeb,0xc2,0x20,0xc9,225,0);c.branch(0x90,'defer751')
    c.emit(0xc9,2,1);c.branch(0xb0,'defer751')
    c.emit(0xc0,0x20,1);c.branch(0xd0,'normal751')
    # X is a live entry. Check the immutable descriptor kind before using
    # the extended range. A map with data behind it keeps the normal policy.
    c.emit(0x48,0x8a,0x18,0x69,8,0);c.absolute(0xcd,0x1250);c.branch(0xd0,'restore751')
    c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0,0xc9,0x40,0);c.branch(0xd0,'wrong_kind751')
    c.emit(0x68,0xe2,0x20);c.jump('map_beam_ok526')
    c.label('wrong_kind751');c.emit(0x68);c.jump('defer_beam')
    c.label('restore751');c.emit(0x68)
    c.label('normal751');c.emit(0xc9,253,0);c.branch(0xb0,'defer751')
    c.emit(0xe2,0x20)
    ordinary=raw.index(bytes.fromhex('8d3e10'),select-codec.DEST)+codec.DEST
    c.absolute(0x4c,ordinary)
    c.label('defer751');c.jump('defer_beam')
    jump(at,base)
    install(at+3,b'\xea'*(ordinary-at-3))
    # The published map pulse and service execute once. Re-enter after the
    # normal head scan on an exact sole OBJ following a 1536B transfer.
    reentry=base+len(c.data)
    c.branch(0xd0,'stopped751')
    c.emit(0xe2,0x20);c.absolute(0xad,0x6000);c.emit(0x4a);c.branch(0xb0,'packet751')
    c.emit(0xc2,0x20);c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);c.branch(0xf0,'empty751')
    c.emit(0xc0,48,0);c.branch(0xf0,'tail751')
    c.emit(0xc0,0,6);c.branch(0xd0,'scan751')
    c.long(0xbf,0x7e4004);c.emit(0xc9,0x20,1);c.branch(0xd0,'scan751')
    c.emit(0xa8)
    c.jump('selected526')
    c.label('scan751')
    head=raw.index(bytes.fromhex('ae5212ec5012'),addr('prefix523')-codec.DEST)+codec.DEST
    c.absolute(0x4c,head+8)
    c.label('tail751');c.jump('tail532')
    c.label('empty751');c.jump('skip523')
    c.label('packet751');c.jump('skip8_523')
    c.label('stopped751');c.jump('stop523')
    jump(addr('no_event680')+3,reentry)
    install(base,c.finish())
    return bytes(body),labels


def build(a):
    if a.variant=='tail':
        labels=json.loads((a.client/'labels.json').read_text())
        raw=bytearray((a.client/'body.bin').read_bytes())
        for addr,data in sorted(edits(a.client,'tail').items()):
            offset=addr-codec.DEST
            raw[offset:offset+len(data)]=data
        body=bytes(raw)
    elif a.variant.startswith('fused'):
        body,labels=fused(a.client)
    else:
        body,labels=assemble(a.client)
    encoder=optimal if a.variant=='fused' else pack
    with patch.object(codec,'pack',encoder):
        codec.build(a.raw,a.out,edit_body=lambda *_:body,allow_extension=True,prefix_sizes=[a.prefix],medium_pages=encoder==pack,boot_bytes=320 if encoder==pack else 260,short_errors=encoder==optimal,fast_backrefs=a.variant.endswith('fast'))
    (a.out/'labels.json').write_text(json.dumps(labels,indent=2)+'\n')
    info=json.loads((a.out/'build.json').read_text())
    info.update(body_SHA256=sha(a.out/'body.bin'),copy_verified_bytes=len(body),body_capacity=6400,body_free=6400-len(body))
    (a.out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    print(info['physical_free_B'],info['prefix_B'],info['body_bytes'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('client','raw','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--prefix',type=int,required=True)
    p.add_argument('--variant',choices=('shared','tail','fused','fused512','fusedfast','sharedfast'),default='shared')
    build(p.parse_args())
