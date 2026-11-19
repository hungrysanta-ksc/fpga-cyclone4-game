"""Replace only MMC872's alternating-word WRAM expansion, preserving packet admission and STOP."""
import argparse
import json
from pathlib import Path

from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import sha


def prepare(base, out):
    assert sha(base/'sink165.sfc') == '850cdcc68a0b9301d195f2cb9acf2adf9024032c5218f1d952c0ee678e6d9970'
    body = bytearray((base/'body.bin').read_bytes())
    labels = json.loads((base/'labels.json').read_text())
    start, end = labels['word516'], labels['literal1814']
    c = Code(start)
    c.labels.update(labels)
    # The shared checked destination was just written to $2181 and DP $7a.
    # WRAM bank bit 1 selects $7f. Advance in order, as on the WRAM port.
    c.emit(0xc2,0x20,0xa6,0x7a,0x8a,0x18)  # REP #$20; LDX $7a; TXA; CLC
    c.absolute(0x6d,0x120c); c.emit(0x85,0x60)  # ADC expanded length; STA end
    c.label('word_chunk873')
    c.emit(0xa0,32,0); c.long(0xaf,0x400010)  # LDY #32 words; LDA packet word
    c.labels['repeat1814'] = start+len(c.data)
    c.long(0x9f,0x7f0000); c.emit(0xe8,0xe8,0xe4,0x60)  # STA long,X; INX twice; CPX end
    c.branch(0xf0,'word_service873')
    c.emit(0x88); c.branch(0xd0,'repeat1814')
    c.label('word_service873')
    c.emit(0xe2,0x20)
    c.labels['repeat_done1815'] = start+len(c.data)
    call(c,'service'); c.emit(0xc2,0x20)
    c.branch(0xd0,'word_stop873')
    c.emit(0xe4,0x60); c.branch(0xd0,'word_chunk873')
    c.jump('accepted')
    c.label('word_stop873'); c.jump('stop_packet')
    code = c.finish()
    assert len(code) <= end-start
    body[start-0x7e2000:end-0x7e2000] = code.ljust(end-start,b'\xea')
    build(base,out,bytes(body),c.labels)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path); parser.add_argument('out',type=Path)
    args=parser.parse_args()
    prepare(args.base,args.out)
