# SPDX-License-Identifier: MIT
"""Reuse the serviced joypad latch inside an admitted raw VBlank DMA group."""
import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import patch
import nes_output489
import nes_prefix523
import nes_seal538
import nes_tile532
from nes_raw506 import once


def raw_emitter(register_rows=False,reuse_pad=True):
    source=inspect.getsource(nes_output489.emit_raw_dma489)
    source=once(source,"sta(0x74);sta(0x76);sta(0x2116)","sta(0x76);sta(0x2116)")
    source=once(source,"lda(0x125c);c.emit(0xc9,1,0);c.branch(0xf0,'raw_return489')",
                "lda(0x125c);c.emit(0x3a);c.branch(0xf0,'raw_return489')")
    source=source.replace("call(c,'raw_service489');cond(0x90,'raw_return489')",
                          "call(c,'raw_service489');c.branch(0x90,'raw_return489')")
    source=once(source,"    c.label('raw_service489');call(c,'service');lda(0x1236);c.branch(0xd0,'raw_stop489');c.emit(0x38,0x60)",
        """    # Within an already admitted VBlank group, a latched pad cannot change.
    # STOP is sampled at EVERY original row boundary. If autojoy was busy,
    # keep the full service until it records this blank's pad. No byte budget,
    # final beam gate, coverage or ACK rule changes.
    c.label('raw_service489');c.emit(0xe2,0x20);lda(0x6001);c.branch(0x30,'raw_slow542')
    lda(0x1238);c.branch(0xd0,'raw_ready542');c.label('raw_slow542');c.emit(0xc2,0x20)
    call(c,'service');lda(0x1236);c.branch(0xd0,'raw_stop489')
    c.label('raw_ready542');c.emit(0xc2,0x20,0x38,0x60)""")
    source=once(source,"imm(0x8000+PROGRAM_BYTES489-66);sta(0x4302);imm(0);sta(0x4304)",
                "imm(0x8000+PROGRAM_BYTES489-66);sta(0x4302);c.absolute(0x9c,0x4304)")
    if not reuse_pad:
        # Control: keep MMC540's exact full service at every row. Isolate the
        # register cursor from the optional pad-latch shortcut.
        source=inspect.getsource(nes_output489.emit_raw_dma489)
        source=once(source,"sta(0x74);sta(0x76);sta(0x2116)","sta(0x76);sta(0x2116)")
        source=source.replace("call(c,'raw_service489');cond(0x90,'raw_return489')",
                              "call(c,'service');lda(0x1236);cond(0xd0,'raw_stop489')")
        source=once(source,"    c.label('raw_service489');call(c,'service');lda(0x1236);c.branch(0xd0,'raw_stop489');c.emit(0x38,0x60)\n","")
        source=once(source,"c.emit(0xc2,0x20,0x18,0x60)","c.emit(0xc2,0x20,0x18);c.jump('raw_return489')")
    if register_rows:
        # service preserves X/Y; after raw_advance489 the uploader reloads X
        # from its independent command cursor. No DMA progress is shared with
        # admission or receipt state.
        source=once(source,"sta(0x76);sta(0x2116)","c.emit(0xaa);sta(0x2116)")
        source=source.replace("lda(0x1240);sta(0x68)","c.absolute(0xac,0x1240)")
        source=source.replace("lda(0x76);sta(0x2116)","c.emit(0x8a);sta(0x2116)")
        source=source.replace("c.absolute(0xee,0x76);c.absolute(0xce,0x68)","c.emit(0xe8,0x88)")
        source=once(source,"lda(0x76);c.emit(0x38);c.absolute(0xed,0x1240);c.emit(0x18,0x69,8,0);sta(0x76)",
                    "c.emit(0x8a,0x38);c.absolute(0xed,0x1240);c.emit(0x18,0x69,8,0,0xaa)")
    namespace=dict(vars(nes_output489))
    exec(compile(source,'dma542-raw-service','exec'),namespace)
    return namespace['emit_raw_dma489']


def build(out,register_rows=False,reuse_pad=True):
    with patch.object(nes_prefix523,'upload',lambda s:nes_seal538.group_upload(s,True)), \
         patch.object(nes_output489,'emit_raw_dma489',raw_emitter(register_rows,reuse_pad)):
        result=nes_tile532.build(out,paired=True)
    result.update(candidate='dma542',group_budget=4192,final_last_line=246,
                  raw_STOP_every_row=True,raw_pad_reused_only_within_admitted_blank=reuse_pad,register_rows=register_rows)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--register-rows',action='store_true')
    p.add_argument('--full-service',action='store_true')
    a=p.parse_args();print(build(a.out,a.register_rows,not a.full_service)['body_bytes'])
