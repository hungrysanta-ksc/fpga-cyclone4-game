# SPDX-License-Identifier: MIT
"""Keep small diffs; build large candidates in inactive SNES VRAM, flip at vblank.

VRAM byte layouts: A BG0000/OBJ4000/map6000, B BGc000/OBJ8000/mapa000.
WRAM1032 active slot,1034 target,1036 region,1038 offset,103a size,
103c source,103e wait counter. No cartridge SRAM. Existing packet/ACK unchanged.
"""
from pathlib import Path
import argparse,inspect,types
import nes_native_local165 as old
import build_nes_sink165 as original

def emit_upload(c,prefix='upload165'):
    source=inspect.getsource(old.emit_upload)
    source=source.replace("label('vram');c.absolute(0xbd,0x1102);c.emit(0x4a)","label('vram');c.absolute(0xbd,0x1102);call(c,'resolve169');c.emit(0x4a)")
    source=source.replace("label('scroll')","label('scroll');call(c,'select169')")
    ns={'call':old.call};exec(compile(source,'banked169-upload','exec'),ns)
    result=ns['emit_upload'](c,prefix)
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def jump(s):c.jump(s)
    def cond(op,s):c.emit(op^0x20,3);jump(s)
    def call(s):old.call(c,s)
    # Resolve legacy logical destinations into the currently visible slot.
    c.label('resolve169');c.emit(0x48);lda(0x1032);cond(0xd0,'resolve_b169');c.emit(0x68,0xc9,0,0x80);cond(0x90,'resolve_ret169');c.emit(0x38,0xe9,0,0x20,0x60)
    c.label('resolve_b169');c.emit(0x68,0xc9,0,0x40);cond(0x90,'resolve_bg169');c.emit(0xc9,0,0x80);cond(0x90,'resolve_obj169');c.emit(0x18,0x69,0,0x20,0x60)
    c.label('resolve_bg169');c.emit(0x18,0x69,0,0xc0,0x60)
    c.label('resolve_obj169');c.emit(0x18,0x69,0,0x40)
    c.label('resolve_ret169');c.emit(0x60)
    # Called only inside final vblank, A8/X16. No read-modify-write PPU ports.
    c.label('select169');lda(0x1032);cond(0xd0,'select_b169')
    for a,v in [(0x210b,0),(0x2101,1),(0x2107,0x31)]:c.store(a,v)
    c.emit(0x60);c.label('select_b169')
    for a,v in [(0x210b,6),(0x2101,2),(0x2107,0x51)]:c.store(a,v)
    c.emit(0x60)
    # Fresh vblank with bounded polling and STOP/pad service in both phases.
    c.label('wait169');c.emit(0xc2,0x20);imm(65535);sta(0x103e)
    for label,op in [('active169',0x30),('blank169',0x10)]:
        c.label(label);call('service');lda(0x1236);cond(0xd0,'cancel169')
        c.absolute(0xce,0x103e);cond(0xf0,'cancel169');c.emit(0xe2,0x20);lda(0x4212);c.emit(0xc2,0x20);cond(op,label)
        imm(65535);sta(0x103e)
    c.emit(0x38,0x60)
    c.label('cancel169');c.emit(0xe2,0x20);c.store(0x1025,0xe4);c.emit(0xc2,0x20,0x18,0x60)
    # Only E2/E3 may enter fallback. All packet/length validation already passed.
    c.label('large169');c.emit(0xe2,0x20);lda(0x1025);c.emit(0xc9,0xe2);cond(0xf0,'large_start169');c.emit(0xc9,0xe3);cond(0xd0,'large_return169')
    c.label('large_start169');c.emit(0xc2,0x20);lda(0x1030);c.emit(0xc9,0x60,0x10);cond(0x90,'large_return169') # >=4096+96
    lda(0x1032);c.emit(0x49,1,0);sta(0x1034);c.absolute(0x9c,0x1036)
    c.label('large_region169');c.absolute(0x9c,0x1038)
    c.label('large_chunk169');c.absolute(0xae,0x1036);c.absolute(0xbd,0x1000);c.emit(0x38);c.absolute(0xed,0x1038);cond(0xf0,'large_next169');c.emit(0xc9,1,0x10);cond(0x90,'size169');imm(4096)
    c.label('size169');sta(0x103a)
    # Source bank7F plus validated candidate and bounded region-relative offset.
    c.absolute(0xbd,0x1000) # X remains region*2 across wait/service
    pos=len(c.data);c.long(0xbf,0);srcfix=pos+1
    c.emit(0x18);c.absolute(0x6d,0x1020);c.absolute(0x6d,0x1038);sta(0x103c)
    call('wait169');cond(0x90,'large_return169')
    # Inactive destination table indexed by region*2 + target*6.
    lda(0x1034);c.emit(0x0a);sta(0x1072);c.emit(0x0a,0x18);c.absolute(0x6d,0x1072);c.absolute(0x6d,0x1036);c.emit(0xaa)
    pos=len(c.data);c.long(0xbf,0);dstfix=pos+1;c.emit(0x18);c.absolute(0x6d,0x1038);c.emit(0x4a);sta(0x2116)
    lda(0x103c);sta(0x4302);lda(0x103a);sta(0x4305);c.emit(0xe2,0x20)
    for a,v in [(0x4300,1),(0x4301,0x18),(0x4304,0x7f),(0x420b,1)]:c.store(a,v)
    c.emit(0xc2,0x20);lda(0x1038);c.emit(0x18);c.absolute(0x6d,0x103a);sta(0x1038);jump('large_chunk169')
    c.label('large_next169');c.absolute(0xee,0x1036);c.absolute(0xee,0x1036);lda(0x1036);c.emit(0xc9,6,0);cond(0x90,'large_region169')
    # Prepare only palette/OAM for the atomic final vblank. HDMA is WRAM-local.
    for slot,source,size,kind in [(0,0x6000,512,1),(8,0x6200,544,2)]:
        lda(0x1020);c.emit(0x18,0x69);c.word(source);sta(0x1100+slot)
        imm(0);sta(0x1102+slot);imm(size);sta(0x1104+slot);imm(kind);sta(0x1106+slot)
    call('service');lda(0x1236);cond(0xd0,'cancel169')
    lda(0x1034);sta(0x1032);imm(2);sta(0x1026);c.emit(0xe2,0x20);c.store(0x1025,2);c.emit(0xc2,0x20)
    # Caller invokes ordinary uploader once: fresh vblank, palette/OAM then flip.
    c.label('large_return169');c.emit(0xc2,0x20,0x60)
    for values,fix in [([0,0x4000,0x5000],srcfix),([0,0x4000,0x6000,0xc000,0x8000,0xa000],dstfix)]:
        c.data[fix:fix+3]=(c.base+len(c.data)).to_bytes(3,'little')
        for v in values:c.word(v)
    return result|{'large_update':'inactive VRAM, max6 chunks4096 plus final palette/OAM flip','active_slot':0x1032}

def build(out):
    src=Path(original.__file__).read_text()
    src=src.replace('from nes_native_local165 import emit,emit_upload,call,OFFSETS,LIMITS','from nes_native_local165 import emit,call,OFFSETS,LIMITS\nfrom nes_banked169 import emit_upload')
    src=src.replace('(0x2107,0x41)','(0x2107,0x31)')
    src=src.replace("call(c,'local165_entry');lda(0x1236)","call(c,'local165_entry');call(c,'large169');lda(0x1236)")
    src=src.replace("b'NES WRAM SINK165'","b'NES BANKED SINK169'")
    mod=types.ModuleType('build_banked169');exec(compile(src,'build_banked169','exec'),mod.__dict__)
    return mod.build(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
