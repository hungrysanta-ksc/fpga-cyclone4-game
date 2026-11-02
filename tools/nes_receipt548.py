# SPDX-License-Identifier: MIT
"""Certify complete compact rows at successful fixed-fill receipt, then intersect bank records."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import nes_history547 as history
from nes_raw506 import once

# Two bitsets per record, low byte for zero, high byte for $FF. Other values
# and fragments are restored normally. Section 5 enforces sequential offsets.
PENDING=0x14a0
BANKS=0x14a2
ROW_BYTES=64
RAW_START=1121
ROWS=6
original_packet=history.packet
original_raw=history.raw_emitter


def packet(source):
    source=original_packet(source)
    # Forced-blank startup. Clear the window/layer registers in one loop,
    # then program the four nonzero values. The main-screen enable comes last.
    source=once(source,"(0x212c,0x11),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),","")
    source=once(source,"c.emit(0xa2,8,0);c.label('clear_window181')","c.emit(0xa2,14,0);c.label('clear_window181')")
    source=once(source,"for a,v in [(0x2123,2),(0x2125,2),(0x2126,0),(0x2127,7)]:c.store(a,v)",
                "c.store(0x2123,2);c.absolute(0x8d,0x2125);c.store(0x2127,7);c.store(0x212c,0x11)")
    # All three zero fields are rejected before any BEGIN state is consumed.
    source=once(source,"checkimm(0x1228,0);checkimm(0x1200,1);checkimm(0x1202,0);checkimm(0x120a,0)",
                "lda(0x1228);c.absolute(0x0d,0x1202);c.absolute(0x0d,0x120a);cond(0xd0,'bad_packet');checkimm(0x1200,1)")
    source=once(source,"c.label('begin');","c.label('begin');c.absolute(0x9c,0x14a0);")
    return once(source,"lda(0x60);cond(0xf0,'accepted');c.emit(0xc9,65,0)",
                "lda(0x60);cond(0xf0,'fill_receipt548');c.emit(0xc9,65,0)")


def certificate(c):
    # Called after the last WRAM fill chunk and its STOP check. $1234 is the
    # independently checked exclusive end of the sequential section-5 packet.
    c.label('fill_receipt548')
    c.absolute(0xad,0x120a);c.emit(0x18,0x69,64,0,0x85,0x62)
    c.long(0xaf,0x400010);c.branch(0xf0,'zero548')
    c.emit(0x1a);c.branch(0xd0,'accept548')
    c.emit(0xa9,0,1);c.branch(0x80,'bits548')
    c.label('zero548');c.emit(0xa9,1,0)
    c.label('bits548');c.emit(0x85,0x60,0xa2);c.word(RAW_START+ROW_BYTES)
    c.label('range548');c.absolute(0xec,0x1234);c.branch(0xf0,'end_ok548');c.branch(0xb0,'accept548')
    c.label('end_ok548');c.emit(0xe4,0x62);c.branch(0x90,'next548')
    c.emit(0xa5,0x60);c.absolute(0x0c,PENDING)
    c.label('next548');c.emit(0x06,0x60,0x8a,0x18,0x69,64,0,0xaa,0xe0);c.word(RAW_START+ROWS*ROW_BYTES+1)
    c.branch(0x90,'range548')
    c.label('accept548');c.jump('accepted')

    c.label('prepare547');c.emit(0x64,0x78)
    c.absolute(0xad,0x1258);c.emit(0xc9,0x80,1);c.branch(0xd0,'exit547')
    c.absolute(0xae,0x1034);c.emit(0xe2,0x20);c.absolute(0x9e,0x125a);c.emit(0xc2,0x20,0x8a,0x0a,0xaa)
    # Old and pending must certify the SAME fill value. The mask is used
    # for six shifts only; the old tag gates visibility until final commit.
    c.absolute(0xbd,BANKS);c.absolute(0x2d,PENDING);c.emit(0x85,0x78,0xeb,0x05,0x78,0x85,0x78)
    c.absolute(0xad,PENDING);c.absolute(0x9d,BANKS)
    c.absolute(0xad,0x125c);c.emit(0x3a);c.branch(0xf0,'exit547');c.emit(0x64,0x78)
    c.label('exit547');c.emit(0x60)


def value_packet(source):
    source=packet(source)
    source=once(source,"c.absolute(0x9c,0x14a0)","c.emit(0xa2,10,0);c.label('clear548');c.absolute(0x9e,0x14a0);c.emit(0xca,0xca);c.branch(0x10,'clear548')")
    # Both bytes have already compared equal. The fixed-source loop can
    # restore every uniform value, including a nonzero long op5 repeat.
    return once(source,"c.emit(0x09,0);c.branch(0xf0,'length545')\n lda(0x1200);c.emit(0xc9,5);c.branch(0xf0,'word516')","c.label('generic548')")


def values(c):
    """Zero means unproven. A checked byte v is recorded as v+1 (1..256)."""
    current=0x14a0
    committed=0x14ac
    c.label('fill_receipt548')
    c.long(0xaf,0x400010);c.emit(0x29,255,0,0x1a,0x85,0x60)
    c.absolute(0xad,0x120a);c.emit(0x18,0x69,64,0,0x85,0x62)
    # X is the record byte index. Y is this row's exclusive end. Given
    # the independently bounded packet, at+64 <= Y <= end proves coverage.
    c.emit(0xa2,0,0,0xa0);c.word(RAW_START+ROW_BYTES)
    c.label('range548');c.absolute(0xcc,0x1234);c.branch(0xf0,'end_ok548');c.branch(0xb0,'accept548')
    c.label('end_ok548');c.emit(0xc4,0x62);c.branch(0x90,'next548')
    c.emit(0xa5,0x60);c.absolute(0x9d,current)
    c.label('next548');c.emit(0xe8,0xe8,0x98,0x18,0x69,64,0,0xa8,0xe0,12,0);c.branch(0x90,'range548')
    c.label('accept548');c.jump('accepted')

    c.label('prepare547');c.emit(0x64,0x78)
    c.absolute(0xad,0x1258);c.emit(0xc9,0x80,1);c.branch(0xd0,'exit547')
    c.absolute(0xae,0x1034);c.emit(0xe2,0x20);c.absolute(0x9e,0x125a);c.emit(0xc2,0x20)
    # STZ and REP did not disturb the bank index; choose the table end.
    c.emit(0x8a);c.branch(0xf0,'first548');c.emit(0xa0,22,0);c.branch(0x80,'bank548');c.label('first548');c.emit(0xa0,10,0)
    c.label('bank548');c.emit(0xa2,10,0)
    # Descending row order packs row zero into bit zero. CMP sets carry
    # on equality; missing and changed entries clear it before ROL.
    c.label('compare548');c.absolute(0xbd,current);c.branch(0xf0,'miss548')
    c.absolute(0xd9,committed);c.branch(0xf0,'save548')
    c.label('miss548');c.emit(0x18)
    c.label('save548');c.absolute(0x99,committed);c.emit(0x26,0x78,0x88,0x88,0xca,0xca);c.branch(0x10,'compare548')
    c.absolute(0xad,0x125c);c.emit(0x3a);c.branch(0xf0,'exit547');c.emit(0x64,0x78)
    c.label('exit547');c.emit(0x60)


def build(out,any_value=True):
    def guarded(source):
        source=(value_packet if any_value else packet)(source)
        # M=16 on fail. Preserve the same error code/sticky state and reply
        # length, invalidating both bank tags before publishing the error ACK.
        return once(source,"c.label('fail');sta(0x122a);imm(2);sta(0x1228);lda(0x122a)",
                    "c.label('fail');sta(0x122a);c.emit(0xa0,2,0);c.absolute(0x8c,0x1228);c.absolute(0x9c,0x125a)")
    with patch.object(history,'packet',guarded),patch.object(history,'raw_emitter',lambda:original_raw(values if any_value else certificate)):
        result=history.build(out,True)
    result.update(candidate='receipt548',shadow_B=0,receipt_B=36 if any_value else 6,any_value=any_value)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--any-value',dest='any_value',action='store_true')
    mode.add_argument('--bitmap',dest='any_value',action='store_false')
    parser.set_defaults(any_value=True)
    args=parser.parse_args();print(build(args.out,args.any_value)['body_bytes'])
