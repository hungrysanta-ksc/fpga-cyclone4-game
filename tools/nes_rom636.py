# SPDX-License-Identifier: MIT
"""Fit the exact 635 WRAM program in the five physical ROM blocks of board613."""
import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path
from build_nes_trace_replay import Code
from nes_raw506 import sha
from nes_native_local165 import call

BOOT=288
STORED=5056
DEST=0x2000


def pack(body, prefix):
    locations=defaultdict(list)
    literals=bytearray()
    out=bytearray()
    def flush():
        if literals:
            out.append(len(literals))
            out.extend(literals)
            literals.clear()
    for i in range(prefix):
        locations[body[i:i+3]].append(i)
    at=prefix
    while at<len(body):
        best=0
        for prev in reversed(locations[body[at:at+3]]):
            n=3
            while n<66 and at+n<len(body) and body[prev+n]==body[at+n]:n+=1
            if n>best:best,pos=n,prev
            if n==66:break
        if best>=4 or (best==3 and at-pos<=255):
            flush()
            if at-pos<=255:
                out.extend((192+best-3,at-pos))
            else:
                out.append(128+best-3);out.extend((DEST+pos).to_bytes(2,'little'))
            size=best
        else:
            literals.append(body[at]);size=1
            if len(literals)==127:flush()
        for i in range(at,at+size):locations[body[i:i+3]].append(i)
        at+=size
    flush();out.append(0)
    return bytes(out)


def build(base,out,*,edit_body=None,allow_extension=False):
    selected=json.loads(Path('analysis/reuse635-verification.json').read_text())
    assert sha(base/'sink165.sfc')==selected['phases'][0]['runs']['idle_short']['client']
    rom=(base/'sink165.sfc').read_bytes()
    info=json.loads((base/'build.json').read_text())
    original_length=length=info['body_bytes']
    body=rom[96:96+length]
    if edit_body is not None:
        body=edit_body(body,json.loads((base/'labels.json').read_text()))
        if allow_extension:
            assert original_length<=len(body)<=0x1900
            length=len(body)
        else:
            assert len(body)==length
    for prefix in range(length//128*128,0,-128):
        stream=pack(body,prefix)
        if BOOT+prefix+len(stream)<=STORED:break
    else:raise ValueError('ROM capacity')
    first=0x8000+BOOT
    limit=first+prefix+len(stream)
    c=Code(0x8000)
    cut=rom.index(b'\xc2\x20\xa9'+(original_length-1).to_bytes(2,'little')+b'\xa2\x60\x80')
    c.emit(*rom[:cut],0xc2,0x30)
    def immediate(op,value):c.emit(op);c.word(value)
    def bad_if(branch):
        c.emit(branch^0x20,3);c.jump('bad')
    immediate(0xa9,prefix-1);immediate(0xa2,first);immediate(0xa0,DEST)
    c.emit(0x54,0x7e,0x00);immediate(0xa2,0)
    c.label('prefix');c.long(0xbf,first);c.long(0xdf,0x7e0000+DEST);bad_if(0xd0)
    c.emit(0xe8,0xe8);immediate(0xe0,prefix);c.branch(0xd0,'prefix')
    c.emit(0xe2,0x20,0x64,2)
    c.label('pass');immediate(0xa2,first+prefix);immediate(0xa0,DEST+prefix)
    c.label('token');call(c,'read')
    c.branch(0xf0,'end');c.branch(0x30,'reference');c.emit(0x85,3)
    c.label('literal');call(c,'read')
    call(c,'byte')
    c.emit(0xc6,3);c.branch(0xd0,'literal');c.branch(0x80,'token')
    c.label('reference');c.emit(0x85,8,0x29,63,0x18,0x69,3,0x85,3,0xa5,8,0x89,64)
    c.branch(0xf0,'absolute')
    call(c,'read');c.emit(0x85,4,0x64,5,0xc2,0x20,0x98,0x38,0xe5,4,0x85,4,0xe2,0x20)
    c.branch(0x80,'checkref');c.label('absolute')
    for i in (4,5):
        call(c,'read');c.emit(0x85,i)
    c.label('checkref');c.emit(0x84,6,0xc2,0x20,0xa5,4);immediate(0xc9,DEST);bad_if(0x90)
    c.emit(0xc5,6);bad_if(0xb0);c.emit(0xe2,0x20)
    c.label('back');c.emit(0xda,0xa6,4);c.absolute(0xbd,0);c.emit(0xe8,0x86,4,0xfa)
    call(c,'byte')
    c.emit(0xc6,3);c.branch(0xd0,'back');c.branch(0x80,'token')
    c.label('end');immediate(0xc0,DEST+length);bad_if(0xd0)
    immediate(0xe0,limit);bad_if(0xd0);c.emit(0xa5,2);c.branch(0x30,'ready')
    c.emit(0xa9,128,0x85,2);c.jump('pass')
    c.label('ready');c.emit(0xa9,0,0x48,0xab);c.long(0x5c,0x7e2000)
    c.label('read');immediate(0xe0,limit);c.branch(0xb0,'bad')
    c.long(0xbf,0);c.emit(0xe8,0x09,0,0x60)  # ORA #0 restores byte flags after INX.
    c.label('byte');immediate(0xc0,DEST+length);c.branch(0xb0,'bad')
    c.emit(0x24,2);c.branch(0x30,'compare');c.absolute(0x99,0);c.emit(0xc8,0x60)
    c.label('compare');c.absolute(0xd9,0);c.branch(0xd0,'bad');c.emit(0xc8,0x60)
    c.label('bad');c.emit(0xe2,0x20,0xa9,0xe1);c.long(0x8f,0x007000);c.emit(0x80,0xfe)
    loader=c.finish();assert len(loader)<=BOOT
    updated=bytearray([255]*32768);updated[:len(loader)]=loader
    updated[BOOT:limit-0x8000]=body[:prefix]+stream;updated[-64:]=rom[-64:]
    out.mkdir(parents=True,exist_ok=False)
    (out/'sink165.sfc').write_bytes(updated)
    (out/'body.bin').write_bytes(body)
    (out/'sink-program.hex').write_text(''.join(f'{b:02x}\n' for b in updated[:STORED]+updated[-64:]),newline='\n')
    shutil.copyfile(base/'labels.json',out/'labels.json')
    info.update(physical_ROM_B=5120,body_bytes=length,program_bytes=5120,loader_B=len(loader),
                prefix_B=prefix,encoded_B=len(stream),physical_free_B=0x8000+STORED-limit,
                verify_entry=c.labels['compare'],boot_error=c.labels['bad'])
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();build(a.base,a.out)
