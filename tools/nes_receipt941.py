"""Replay the 940 ARM against differently grouped, independently checked 65816 receipts."""
import argparse
from pathlib import Path
from unittest.mock import patch

import nes_chain935 as chain
from analyze_nes_palette921 import read, sha
from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_input940 import work as input_work

ARM = input_work('handoffdecode')
BASE = chain.output('bounded')
ORIGIN = 0x7e2000


def image(mode):
    return BASE.parent.parent/'nes-receipt941'/mode


def obj_coordinates(body,labels):
    # The OBJ entry has already selected 32-byte units. Calculate length
    # and start directly, keeping the same checked bitmap and address path.
    site=labels['obj_unit212']-ORIGIN
    assert body[site:site+7]==bytes.fromhex('a9000485688013')
    extra=Code(ORIGIN+len(body))
    extra.emit(0x4a,0x4a,0x4a,0x85,0x6c,0xa5,0x62,0x4a,0x4a,0x4a,0x4a,0x4a)
    extra.emit(0x18,0x69,0,4,0x85,0x6a)
    extra.absolute(0x4c,(labels['units212']+17)&65535)
    body[site:site+7]=bytes.fromhex('a5644a4a4c')+(0x2000+len(body)).to_bytes(2,'little')
    body.extend(extra.finish())


def checked_extent(body,labels):
    # bulk194 has already verified descriptor kind, section, offset, positive
    # length, full identity and cap. Reuse section for the bounds-table index.
    # The shared addition carry and per-section end bound still run.
    left=body.index(bytes.fromhex('8d0c120d0a128570'),labels['bulk194']-ORIGIN)+6
    bad=body.index(bytes.fromhex('4caf27'),left)
    go=bad+3
    extent=body.index(bytes.fromhex('186d0a1290034caf27'),labels['sparse212']-ORIGIN)
    c=Code(ORIGIN+left)
    c.labels.update(bad941=ORIGIN+bad,extent941=ORIGIN+go)
    c.emit(0x89,15,0);c.branch(0xd0,'bad941')
    c.emit(0xa2,0,0,0xa8);c.absolute(0xad,0x1201);c.emit(0x4a)
    c.branch(0x90,'extent941')
    c.emit(0xe8,0xe8,0x98,0x89,16,0);c.branch(0xd0,'bad941')
    c.branch(0x80,'extent941')
    code=c.finish()
    assert len(code)<=bad-left and body[go:go+6]==bytes([0xea])*6
    body[left:bad]=code.ljust(bad-left,bytes((0xea,)))
    body[go:go+6]=bytes.fromhex('ad0c124c')+(0x2000+extent).to_bytes(2,'little')


def prepare(mode):
    assert sha(BASE/'sink165.sfc')=='5aef7ca01174caacea0484866f38593c2008162ba9ff9c43e0c17a7c51a4a6a2'
    labels = read(BASE/'labels.json')
    body = bytearray((BASE/'body.bin').read_bytes())
    if mode in ('prefixcheck','alignedcheck'):
        checked_extent(body,labels)
    if mode in ('boot','pairbase'):
        build(BASE,image(mode),bytes(body),labels,compact_mvn=True,minimum=2 if mode=='pairbase' else 3)
        return
    if mode in ('prefix','prefixcheck'):
        c=Code(ORIGIN+len(body))
        c.labels.update(labels)
        # A leading 512B OBJ owns exactly the first sixteen 32B units.
        # The old path checks nonzero starts, short spans, and all residual units.
        c.emit(0xa5,0x62);c.branch(0xd0,'scalar941')
        c.emit(0xa5,0x64,0x38,0xe9,0,2);c.branch(0x90,'scalar941')
        c.emit(0xa8);c.absolute(0xae,0x1254)
        c.absolute(0xad,0x1300);c.branch(0xd0,'rejected941')
        c.emit(0x3a);c.absolute(0x8d,0x1300);c.absolute(0x9d,0x13a0)
        c.emit(0x98);c.branch(0xf0,'address941')
        c.emit(0x4a,0x4a,0x4a,0x4a,0x4a,0x85,0x6c,0xa2,130,0,0x8a,0x18)
        c.absolute(0x6d,0x1254);c.emit(0xa8,0xa9,1,0,0x85,0x6e);c.jump('bits212')
        c.label('address941');c.absolute(0x4c,(labels['same_byte556']+6)&65535)
        c.label('rejected941');c.jump('mark_bad212')
        c.label('scalar941');c.emit(0xa9,0,4);c.absolute(0x4c,(labels['obj_unit212']+3)&65535)
        site=labels['obj_unit212']-ORIGIN
        assert body[site:site+3]==bytes((0xa9,0,4))
        body[site:site+3]=bytes((0x4c,))+(len(body)+0x2000).to_bytes(2,'little')
        body.extend(c.finish())
        build(BASE,image(mode),bytes(body),c.labels,compact_mvn=True,minimum=2)
        return
    if mode in ('pair','span','objspan'):
        c=Code(ORIGIN+len(body))
        c.labels.update(labels)
        # Complete the original per-bank bitmap address calculation first.
        site=labels['bits212']-4-ORIGIN
        assert body[site:site+4]==bytes.fromhex('6d5412a8')
        c.emit(*body[site:site+4])
        if mode=='pair':
            c.emit(0xa5,0x60,0xc9,2,0)
            c.branch(0xd0,'scalar941')
        c.emit(0xa5,0x6e,0xc9,1,0)
        c.branch(0xd0,'scalar941')
        # Each whole group contributes exactly two bytes to each checked plane.
        c.label('pair941')
        c.emit(0xa5,0x6c,0x38,0xe9,16,0)
        c.branch(0x90,'scalar941')
        c.emit(0x85,0x6c);c.absolute(0xbd,0x1280);c.branch(0xd0,'rejected941')
        c.emit(0x3a);c.absolute(0x9d,0x1280);c.absolute(0x99,0x1320)
        c.emit(0xe8,0xe8,0xc8,0xc8,0xa5,0x6c);c.branch(0xd0,'pair941')
        c.absolute(0x4c,(labels['same_byte556']+6)&65535)
        c.label('scalar941');c.jump('bits212')
        c.label('rejected941');c.jump('mark_bad212')
        body[site:site+4]=bytes((0x4c,))+(0x2000+len(body)).to_bytes(2,'little')+bytes((0xea,))
        body.extend(c.finish())
        if mode=='objspan':obj_coordinates(body,labels)
        build(BASE,image(mode),bytes(body),c.labels,compact_mvn=True,minimum=2)
        return
    start = labels['units212']+17
    end = labels['same_byte556']+6
    assert body[start-ORIGIN:start-ORIGIN+3]==bytes.fromhex('290700')
    assert body[end-ORIGIN:end-ORIGIN+2]==bytes.fromhex('a660')
    c=Code(start)
    c.labels.update(labels)
    # The incoming word is the first unit, $6c is its independently bounded length.
    c.emit(0x29,7,0,0xaa)
    c.long(0xbf,labels['masks920'])
    c.emit(0x85,0x6e,0xa5,0x6a,0x4a,0x4a,0x4a,0xaa,0x18)
    c.absolute(0x6d,0x1254)
    c.emit(0xa8,0xe2,0x20,0xa5,0x6e)
    c.label('grow941')
    # Accumulate this byte's touched bits before accessing either WRAM plane.
    # DEC stays 16-bit even for future callers larger than 255 units.
    c.emit(0xc2,0x20,0xc6,0x6c,0xe2,0x20)
    c.branch(0xf0,'apply941')
    c.emit(0x0a)
    c.branch(0xb0,'boundary941')
    c.emit(0x05,0x6e)
    c.branch(0x80,'grow941')
    c.label('boundary941')
    c.emit(0x6a)
    c.label('apply941')
    c.absolute(0x3c,0x1280)
    c.branch(0xd0,'duplicate556')
    c.emit(0x85,0x6e)
    c.absolute(0x1d,0x1280);c.absolute(0x9d,0x1280)
    c.emit(0xa5,0x6e)
    c.absolute(0x19,0x1320);c.absolute(0x99,0x1320)
    c.emit(0xc2,0x20,0xa5,0x6c)
    c.branch(0xf0,'registered941')
    c.emit(0xe8,0xc8,0xe2,0x20,0xa9,1,0x85,0x6e)
    c.branch(0x80,'grow941')
    c.label('registered941')
    if mode in ('aligned','objaligned','alignedcheck'):
        start=labels['bits212']
        c=Code(start)
        c.labels.update(labels)
        c.label('step941')
        c.emit(0xe2,0x20,0xa5,0x6e,0xc9,1)
        c.branch(0xd0,'mark941')
        # A span aligned to bit zero can retire eight actual units at once.
        # Test the low count only: a shorter low part just takes scalar steps.
        c.emit(0xa5,0x6c,0xc9,8)
        c.branch(0x90,'single941')
        c.emit(0xe9,7,0x85,0x6c,0xa9,0xff,0x85,0x6e)
        c.label('single941');c.emit(0xa5,0x6e)
        c.label('mark941')
        c.absolute(0x3c,0x1280);c.branch(0xd0,'duplicate556')
        c.absolute(0x1d,0x1280);c.absolute(0x9d,0x1280)
        c.emit(0xa5,0x6e);c.absolute(0x19,0x1320);c.absolute(0x99,0x1320)
        c.emit(0x06,0x6e);c.branch(0x90,'dec941')
        c.emit(0xa9,1,0x85,0x6e,0xe8,0xc8)
        c.label('dec941');c.emit(0xc2,0x20,0xc6,0x6c);c.branch(0xd0,'step941')
    # Relocate the unchanged address/append tail and keep external entry points fixed.
    tail = labels['scale556']
    moved=bytes(body[end-ORIGIN:tail-ORIGIN]);assert moved[-1]==0x60
    free=tail-start
    code=c.finish()
    if mode in ('aligned','objaligned','alignedcheck'):
        position=moved.index(bytes.fromhex('ad34100a85740a1865746560aa'))
        # X still selects the section. A nonzero target bank selects the next
        # three words in the destination table. The original bank is a checked bit.
        moved=moved[:position]+bytes.fromhex('ad3410f0068a18690600aa')+moved[position+13:]
        assert moved[-4:]==bytes.fromhex('20082960')
        moved=moved[:-4]+bytes.fromhex('4c0829')
        # Split only at an instruction boundary. No relative branch crosses the split.
        split=position if position+len(code)+3<=free else 8
        assert moved[split:split+1] in (bytes((0xad,)),bytes((0x65,)),bytes((0x6d,)))
    else:
        split=0
    sequence=code+moved[:split]+bytes((0x4c,))+(len(body)+0x2000).to_bytes(2,'little')
    assert len(sequence)<=free
    body[start-ORIGIN:tail-ORIGIN]=sequence.ljust(free,b'\xea')
    body.extend(moved[split:])
    if mode=='objaligned':obj_coordinates(body,labels)
    build(BASE,image(mode),bytes(body),c.labels,shared_byte=(mode=='groups'),compact_mvn=(mode!='groups'),minimum=2 if mode in ('aligned','objaligned','alignedcheck') else 3)


def replay(temp,mode,phase,cache):
    assert sha(ARM/'link/src/obj-nes-100/firmware.stm')=='efaef97babd87abfec81f7f269f8fb315c754ce38dd59e27ac35ae1a3f67b545'
    with patch.object(chain,'output',lambda _:image(mode)):
        chain.replay(temp,'final',phase,cache,'bounded',work_arm=ARM,tag='941'+mode)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay'))
    p.add_argument('mode',choices=('boot','pairbase','groups','mvn','aligned','pair','span','objspan',
                                   'objaligned','prefix','prefixcheck','alignedcheck'))
    p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int)
    p.add_argument('cache',nargs='?')
    a=p.parse_args()
    if a.action=='prepare':prepare(a.mode)
    else:replay(a.temp,a.mode,a.phase,a.cache)
