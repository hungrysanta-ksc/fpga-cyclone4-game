# SPDX-License-Identifier: MIT
"""Experimental505 nonblocking immutable-prefix VRAM drain; not an installer.

Only main poll, after prior packet ACK. Retain mutable last descriptor until
SEAL. Actual V counter bounds DMA; final checks/visibility remain unchanged.
"""
import argparse,inspect,json
from pathlib import Path
import nes_output489 as base
once=base.once
old_source=base.source
old_upload=base.emit_upload489

def source(s):
    s=old_source(s)
    s=once(s,"c.label('poll');call(c,'service');lda(0x1236);cond(0xd0,'quiet')", "c.label('poll');call(c,'service');lda(0x1236);cond(0xd0,'quiet');call(c,'early505')")
    s=once(s,"sta(0x1254);c.absolute(0x9c,0x1250)","sta(0x1254);c.absolute(0x9c,0x1250);c.absolute(0x9c,0x1252);c.absolute(0x9c,0x1260)")
    s=once(s,"call(c,'raw_boot489')","call(c,'raw_boot489');c.absolute(0x9c,0x1260)")
    s=once(s,"c.absolute(0x9c,0x1228);imm(1);c.jump('reply')","c.absolute(0x9c,0x1260);c.absolute(0x9c,0x1228);imm(1);c.jump('reply')")
    s=once(s,"c.label('fail');sta(0x122a);","c.label('fail');sta(0x122a);call(c,'invalidate505');")
    s=once(s,"c.label('quiet');call(c,'service');","c.label('quiet');call(c,'invalidate505');call(c,'service');")
    return s

def alter_upload(s):
    s=once(s,"c.label('no_raw212');c.absolute(0x9c,0x1252);c.absolute(0x9c,0x1256)","c.label('no_raw212');c.absolute(0x9c,0x1256)")
    body="""c.long(0xbf,0x7e4000);sta(0x4302);c.long(0xbf,0x7e4002);c.emit(0x4a);sta(0x2116);lda(0x103a);sta(0x4305)
 c.emit(0xe2,0x20)
 for a,v in [(0x4300,1),(0x4301,0x18),(0x4304,0x7f),(0x420b,1)]:c.store(a,v)"""
    s=once(s,body,"call(c,'dma505')")
    s=once(s," client.emit_extra(c)"," emit_early505(c)\n client.emit_extra(c)")
    return s

def emit_early505(c):
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def cond(op,s):c.emit(op^0x20,3);c.jump(s)
    from nes_client181 import call
    # Existing DMA setup shared by the early drain and the final uploader.
    c.label('dma505')
    c.long(0xbf,0x7e4000);sta(0x4302);c.long(0xbf,0x7e4002);c.emit(0x4a);sta(0x2116);lda(0x103a);sta(0x4305)
    c.emit(0xe2,0x20)
    for a,v in [(0x4300,1),(0x4301,0x18),(0x4304,0x7f),(0x420b,1)]:c.store(a,v)
    c.emit(0xc2,0x20,0x60)
    c.label('early505');lda(0x1228);c.emit(0xc9,1,0);cond(0xd0,'early_return505')
    lda(0x1024);c.emit(0x29,255,0);c.branch(0xf0,'early_target505')
    lda(0x1034);c.absolute(0xcd,0x1032);cond(0xf0,'early_return505')
    c.label('early_target505');lda(0x1250);c.emit(0xc9,16,0);cond(0x90,'early_return505')
    c.emit(0x38,0xe9,8,0);c.absolute(0xcd,0x1252);cond(0x90,'early_return505');cond(0xf0,'early_return505')
    c.absolute(0xae,0x1252);c.long(0xbf,0x7e4004);sta(0x103a)
    c.emit(0xc9,1,16);cond(0xb0,'early_return505');c.emit(0x18,0x69,128,1);sta(0x74)
    # Read the real beam. Clear the high/low flipflop before latching.
    c.emit(0xe2,0x20);lda(0x4212);cond(0x10,'early_return8_505')
    c.label('beam505');lda(0x213f);lda(0x2137);lda(0x213d);sta(0x1262);lda(0x213d);c.emit(0x29,1);sta(0x1263);c.emit(0xc2,0x20)
    lda(0x1262);c.emit(0xc9,225,0);cond(0x90,'early_return505');c.emit(0xc9,1,1);cond(0xb0,'early_return505')
    imm(260);c.emit(0x38);c.absolute(0xed,0x1262)
    for _ in range(7):c.emit(0x0a)
    c.absolute(0xcd,0x74);cond(0x90,'early_return505')
    # Charge384 byte-equivalent for post-latch code/setup;128B/line is below
    #1364/8. Never wait for a blank here. One immutable descriptor per poll.
    imm(1);sta(0x1260);call(c,'dma505')
    lda(0x1252);c.emit(0x18,0x69,8,0);sta(0x1252)
    c.label('early_return8_505');c.emit(0xc2,0x20)
    c.label('early_return505');c.emit(0x60)
    # A canceled tentative bank must not certify partially updated VRAM as
    #a reusable base. Clear only its152B coverage plus implicit-raw certificate.
    c.label('invalidate505');lda(0x1260);c.branch(0xf0,'invalidate_return505')
    c.absolute(0xae,0x1254);c.emit(0xa0,76,0);imm(0)
    c.label('invalidate_loop505');c.absolute(0x9d,0x1320);c.emit(0xe8,0xe8,0x88);c.branch(0xd0,'invalidate_loop505')
    c.absolute(0xae,0x1034);c.emit(0xe2,0x20);c.absolute(0x9e,0x125a);c.emit(0xc2,0x20);c.absolute(0x9c,0x1260)
    c.label('invalidate_return505');c.emit(0x60)

def build(out):
    # Apply after489 raw handling, retaining raw-specific dispatch and all
    #semantic checks. No edits to frozen489 generators.
    code=inspect.getsource(old_upload).replace('def emit_upload489(', 'def emit_upload505(')
    code=once(code,'    import nes_client181','    s=alter_upload(s)\n    import nes_client181')
    code=once(code,'ns.update(emit_raw_dma489=emit_raw_dma489,client=Client)','ns.update(emit_raw_dma489=emit_raw_dma489,client=Client,emit_early505=emit_early505)')
    ns=dict(base.__dict__);ns.update(alter_upload=alter_upload,emit_early505=emit_early505)
    exec(compile(code,'early505-uploader','exec'),ns)
    base.source=source;base.emit_upload489=ns['emit_upload505']
    try:r=base.build(out)
    finally:base.source=old_source;base.emit_upload489=old_upload
    r.update(candidate='early505',scope=__doc__,new_WRAM_B=4,new_WRAM_range='1260..1263',body_delta_vs489=r['body_bytes']-4311,new_ARM_code_B=0,new_FPGA_control=0,physical=False)
    assert r['body_bytes']<=4311+512 and r['program_bytes']==5120
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=build(a.out);print(json.dumps({k:r[k]for k in ['body_bytes','body_delta_vs489','body_free','new_WRAM_B']}))
