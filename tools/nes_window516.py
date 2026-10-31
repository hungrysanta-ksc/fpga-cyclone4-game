# SPDX-License-Identifier: MIT
"""Reuse an early, freshly measured VBlank only for the sealed, fixed-size final display."""
import argparse
import inspect
import json
from pathlib import Path
import nes_output489 as base
from nes_client181 import call

LAST_LINE = 246

def emit_final516(c):
    def load(address): c.absolute(0xad,address)
    c.label('wait_final516')
    # Only the established visible display path can borrow a blank. The
    # original batch wait and its 4192-byte credit are never replenished here.
    c.emit(0xe2,0x20)
    load(0x1024);c.branch(0xf0,'fresh516')
    load(0x4212);c.branch(0x10,'fresh516')
    load(0x213f);load(0x213f);c.emit(0x89,0x40);c.branch(0xd0,'fresh516')
    load(0x2137);load(0x213f);c.emit(0x89,0x40);c.branch(0xf0,'fresh516')
    load(0x213d);c.emit(0xeb);load(0x213d);c.emit(0x29,1);c.branch(0xd0,'fresh516')
    c.emit(0xeb,0xc9,225);c.branch(0x90,'fresh516')
    c.emit(0xc9,LAST_LINE+1);c.branch(0xb0,'fresh516')
    load(0x4212);c.branch(0x10,'fresh516')
    c.emit(0xc2,0x20);call(c,'service');load(0x1236);c.branch(0xf0,'borrow516')
    c.jump('cancel169')
    c.label('borrow516');c.emit(0x38,0x60)
    c.label('fresh516');c.emit(0xc2,0x20);c.jump('wait169')

def fill_source(s):
    anchor=" c.absolute(0xac,0x120c);c.emit(0xa2,32,0);c.label('repeat1814')"
    code=""" lda(0x1201);c.emit(0xc9,5);c.branch(0xd0,'word516')
 lda(0x1200);c.emit(0xc9,5);c.branch(0xd0,'word516')
 c.emit(0xc2,0x20);c.long(0xaf,0x400010);c.branch(0xd0,'word16_516')
 lda(0x120c);sta(0x60);imm(0x8008);sta(0x4300);imm(16);sta(0x4302)
 c.emit(0xe2,0x20);c.store(0x4304,0x40);c.emit(0xc2,0x20)
 c.label('zero_chunk516');call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 lda(0x60);cond(0xf0,'accepted');c.emit(0xc9,65,0);c.branch(0x90,'zero_tail516');imm(64)
 c.label('zero_tail516');sta(0x4305);sta(0x62);lda(0x60);c.emit(0x38);c.absolute(0xed,0x62);sta(0x60)
 c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20);c.branch(0x80,'zero_chunk516')
 c.label('word16_516');c.emit(0xe2,0x20);c.label('word516')
"""
    s=base.once(s,"c.branch(0xd0,'literal1814')","cond(0xd0,'literal1814')")
    return base.once(s,anchor,code+anchor)

def build(out, *, emitter=emit_final516, entry="wait_final516", fill=False, gate=True):
    original=base.emit_upload489
    src=inspect.getsource(original)
    anchor="    ns=dict(nes_dirty212.__dict__);"
    src=base.once(src,anchor,f"""    s=once(s,"call(c,'wait169');cond(0x90,'return')","call(c,'{entry}');cond(0x90,'return')")
    s=once(s,' client.emit_extra(c)',' emit_final516(c)\\n client.emit_extra(c)')
"""+anchor)
    src=base.once(src,'ns.update(emit_raw_dma489=', 'ns.update(emit_final516=emit_final516,emit_raw_dma489=')
    ns=dict(base.__dict__,emit_final516=emitter)
    exec(compile(src,'window516-uploader','exec'),ns)
    source=base.source
    if fill:base.source=lambda template:fill_source(source(template))
    if gate:base.emit_upload489=ns['emit_upload489']
    try:result=base.build(out)
    finally:base.emit_upload489,base.source=original,source
    result.update(candidate='window516',last_allowed_line=LAST_LINE,new_WRAM_B=0)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=('gate','fill','both'),default='gate')
    a=p.parse_args();print(build(a.out,fill=a.mode!='gate',gate=a.mode!='fill')['body_bytes'])
