# SPDX-License-Identifier: MIT
"""Group the immutable, checked SEAL commands before waiting for a fresh blank."""
import argparse
import json
import inspect
from pathlib import Path
from unittest.mock import patch

import nes_prefix523
import nes_tile532
import nes_output489
from nes_raw506 import once


def group_upload(source, early_final=False):
    source = nes_prefix523_original(source)
    start = source.index(" c.label('upload_loop212')")
    end = source.index(" lda(0x1258);c.branch(0xf0,'raw_legacy489')", start)
    # The admission list is immutable after SEAL. $103a was the uploader's
    # length scratch. Hold the exclusive end of this group there instead.
    # Every accepted job fits a fresh group (4096 + 96). A compact raw job
    # is appended last and retains its original worst-case charge.
    source = source[:start] + """ c.label('group538');c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);cond(0xb0,'final212')
 imm(4192);sta(0x1256)
 c.label('budget538');c.long(0xbf,0x7e4004);c.emit(0x18,0x69,96,0);sta(0x74)
 lda(0x1256);c.emit(0x38);c.absolute(0xed,0x74);c.branch(0x90,'group_ready538');sta(0x1256)
 c.emit(0x8a,0x18,0x69,8,0,0xaa);c.absolute(0xec,0x1250);c.branch(0x90,'budget538')
 c.label('group_ready538');c.absolute(0x8e,0x103a)
 call(c,'wait169');cond(0x90,'upload_return212')
 imm(0x1801);sta(0x4300);c.emit(0xe2,0x20);c.store(0x4304,0x7f);c.emit(0xc2,0x20)
 c.label('upload_loop212');c.absolute(0xae,0x1252);c.label('transfer212')
""" + source[end:]
    source = once(source,"lda(0x103a);sta(0x4305)","c.long(0xbf,0x7e4004);sta(0x4305)")
    source = once(source,"for a,v in [(0x4300,1),(0x4301,0x18),(0x4304,0x7f),(0x420b,1)]:c.store(a,v)",
                  "c.store(0x420b,1)")
    source = once(source,"sta(0x1252);c.jump('upload_loop212')",
                  "sta(0x1252);c.absolute(0xcd,0x103a);cond(0x90,'upload_loop212');c.jump('group538')")
    if early_final:
        first = source.index(' for slot,source,size,kind')
        last = source.index(' imm(2);sta(0x1026)',first)
        descriptors = source[first:last]
        source = source[:first] + source[last:]
        source = once(source," c.label('group538')",descriptors+" c.label('group538')")
    return source


nes_prefix523_original = nes_prefix523.upload

def raw_service_inline(edit=None):
    source=inspect.getsource(nes_output489.emit_raw_dma489)
    check="call(c,'raw_service489');cond(0x90,'raw_return489')"
    assert source.count(check)==2
    source=source.replace(check,"call(c,'service');lda(0x1236);cond(0xd0,'raw_stop489')")
    source=once(source,"    c.label('raw_service489');call(c,'service');lda(0x1236);c.branch(0xd0,'raw_stop489');c.emit(0x38,0x60)\n","")
    source=once(source,"c.emit(0xc2,0x20,0x18,0x60)","c.emit(0xc2,0x20,0x18);c.jump('raw_return489')")
    if edit is not None:
        source=edit(source)
    namespace=dict(vars(nes_output489))
    exec(compile(source,'seal538-raw-service','exec'),namespace)
    return namespace['emit_raw_dma489']

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--early-final', action='store_true')
    p.add_argument('--inline-raw-service', action='store_true')
    args = p.parse_args()
    raw=raw_service_inline() if args.inline_raw_service else nes_output489.emit_raw_dma489
    with patch.object(nes_prefix523, 'upload', lambda source:group_upload(source,args.early_final)), patch.object(nes_output489,'emit_raw_dma489',raw):
        result = nes_tile532.build(args.out, paired=True)
    result.update(candidate='seal538',group_budget=4192,early_final_descriptors=args.early_final,inline_raw_service=args.inline_raw_service)
    (args.out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
