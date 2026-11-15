# SPDX-License-Identifier: MIT
"""Fit the previously verified two-row receipt into the existing 685 display ROM."""
import argparse
import json
from hashlib import sha256
from pathlib import Path

from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import sha
from prepare_nes_complete685 import edit as edit685
from prepare_nes_progress680 import ORIGIN, client


def edit(body, labels):
    body, labels = edit685(body, labels)
    assert sha256(body).hexdigest() == "fc4cace99771f87edf92dbe3a240e0049da275145c1e533d2d43bef0aa4890c8"
    body = bytearray(body)
    start = labels["raw_dma489"] - ORIGIN
    generic = labels["generic624"] - ORIGIN
    pairs = labels["pairs624"]
    assert body[start:generic] == bytes.fromhex("a478c01500d0034c") + (pairs & 65535).to_bytes(2, "little")
    # Keep A16 (the VRAM destination) undisturbed for either entry.
    extra = labels["map_beam_ok526"] - ORIGIN - 13
    assert body[extra:extra+13] == bytes([0xea])*13
    first = labels["row624_0"]
    end_marker = bytes.fromhex("64784c") + (labels["raw_return489"]&65535).to_bytes(2,"little")
    end = body.index(end_marker, labels["row624_2"]-ORIGIN) + len(end_marker)
    rows = Code(first)
    rows.labels.update(labels)
    for i in range(3):
        rows.label(f"row624_{i}")
        call(rows, "service")
        rows.branch(0xf0, f"write789_{i}")
        rows.jump("raw_stop489")
        rows.label(f"write789_{i}")
        rows.absolute(0xad, 0x1020)
        rows.emit(0x18, 0x69)
        rows.word(0x69a1 + 128*i)
        rows.absolute(0x8d, 0x4302)
        rows.emit(0xa5, 0x76, 0x18, 0x69)
        rows.word(1 + 8*i)
        rows.absolute(0x8d, 0x2116)
        call(rows, "send64_789")
        if i == 0:
            rows.emit(0xa4, 0x78, 0xc0, 0x1d, 0)
            rows.branch(0xf0, "row624_2")
    rows.emit(0x64, 0x78)
    rows.jump("raw_return489")
    rows.label("send64_789")
    rows.emit(0xa9, 64, 0)
    rows.absolute(0x8d, 0x4305)
    rows.emit(0xe2, 0x20)
    rows.store(0x420b, 1)
    rows.emit(0xc2, 0x20, 0x60)
    encoded = rows.finish()
    available = end - (first - ORIGIN)
    assert len(encoded) <= available
    body[first-ORIGIN:end] = encoded + bytes([0xea])*(available-len(encoded))
    # JMP preserves the flags from CPY. Only the two independently checked masks use pairs624.
    gate=Code(ORIGIN+extra)
    gate.labels.update(labels)
    gate.branch(0xf0,"accepted789")
    gate.emit(0xc0,0x1d,0)
    gate.branch(0xf0,"accepted789")
    gate.jump("generic624")
    gate.label("accepted789")
    gate.jump("pairs624")
    patch=gate.finish()
    assert len(patch)==13
    body[extra:extra+13]=patch
    body[start:generic]=bytes.fromhex("a478c015004c") + ((ORIGIN+extra)&65535).to_bytes(2,"little") + bytes([0xea,0xea])
    labels.update(rows.labels)
    labels.update({"receipt_gate789":ORIGIN+extra})
    return body,labels


def build(base, original, out):
    assert sha(original/"sink165.sfc")=="c79e2b013701fa9cde8a8164da3f0545f2b7c916b8477aa6d74ec405002ebf2e"
    info=client(base,out,extra_edit=edit)
    info.update(candidate="receipt789", reference=sha(original/"sink165.sfc"), masks=[21,29],
                new_persistent_WRAM_B=0, extra_raw_call_stack_B=2)
    (out/"build.json").write_text(json.dumps(info,indent=2)+"\n",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("base","original","out"):p.add_argument(key,type=Path)
    a=p.parse_args()
    build(a.base,a.original,a.out)
