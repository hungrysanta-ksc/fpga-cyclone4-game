# SPDX-License-Identifier: MIT
"""Observe ROM entry, verify the actual WRAM copy, then advertise readiness.

Only the SNES ROM image changes. The banked169 renderer and171 FPGA RTL stay.
Stages:1 ROM copy, E1 mismatch,2 WRAM/SPC init,3 ready for the first packet.
"""
from pathlib import Path
import argparse,types,json,inspect
import build_nes_sink165 as original
import nes_banked169 as banked

def build(out):
    # Apply the established169 renderer substitutions, without editing its file.
    source=Path(original.__file__).read_text()
    source=source.replace('from nes_native_local165 import emit,emit_upload,call,OFFSETS,LIMITS','from nes_native_local165 import emit,call,OFFSETS,LIMITS\nfrom nes_banked169 import emit_upload')
    source=source.replace('(0x2107,0x41)','(0x2107,0x31)')
    source=source.replace("call(c,'local165_entry');lda(0x1236)","call(c,'local165_entry');call(c,'large169');lda(0x1236)")
    source=source.replace("b'NES WRAM SINK165'","b'NES BOOT SINK172'")
    source=source.replace("c.label('poll');", "c.emit(0xe2,0x20);c.store(0x7000,3);c.emit(0xc2,0x20)\n c.label('poll');",1)
    source=source.replace('boot.emit(0xc2,0x20,0xa9);', 'boot.store(0x7000,1)\n boot.emit(0xc2,0x20,0xa9);',1)
    anchor="boot.long(0x5c,0x7e2000);rom[:len(boot.finish())]=boot.finish()"
    assert source.count(anchor)==1
    source=source.replace(anchor,"""boot.emit(0xa2,0,0);boot.label('verify172')
 boot.long(0xbf,0x7e2000);boot.long(0xdf,0x008100);boot.branch(0xd0,'bad172')
 boot.emit(0xe8,0xe0);boot.word(len(body));boot.branch(0xd0,'verify172')
 boot.long(0x5c,0x7e2000)
 boot.label('bad172');boot.store(0x7000,0xe1);boot.label('halt172');boot.branch(0x80,'halt172')
 assert len(boot.finish())<=256
 rom[:len(boot.finish())]=boot.finish()""")
    mod=types.ModuleType('boot172');exec(compile(source,'boot172','exec'),mod.__dict__)
    result=mod.build(out)
    result.update(stages={'ROM_COPY':1,'COPY_MISMATCH':225,'WRAM_SPC':2,'READY':3},copy_verified_bytes=result['body_bytes'],scope='172 boot copy readback and ready publication;169 renderer unchanged; not physical boot proof')
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
