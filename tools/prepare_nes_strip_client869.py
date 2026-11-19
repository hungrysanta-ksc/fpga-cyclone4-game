"""Replace MMC855's single-column consumer with a checked one/two-column consumer."""
import argparse
import json
from pathlib import Path

from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_native_local165 import call

ORIGIN=0x7e2000


def prepare(base,out):
    old=(base/'body.bin').read_bytes()
    labels=json.loads((base/'labels.json').read_bytes())
    start=labels['column_header']
    prefix=bytearray(old[:start-ORIGIN])
    c=Code(start)
    c.labels.update({k:v for k,v in labels.items() if v<start})
    def imm(op,x):
        c.emit(op);c.word(x)
    c.label('column_header')
    c.absolute(0xad,0x1200);imm(0xc9,0x020a)
    c.branch(0xf0,'column_identity');c.jump('reuse635')
    c.label('column_identity')
    c.absolute(0xad,0x120a);imm(0xc9,2048);c.branch(0xd0,'bad_header')
    c.long(0xaf,0x400014);imm(0xc9,2048);c.branch(0xd0,'bad_header')
    c.absolute(0xad,0x120e);c.branch(0xd0,'bad_header')
    c.long(0xaf,0x400016);c.emit(0x4a);c.branch(0xb0,'bad_header')
    imm(0xc9,32);c.branch(0xb0,'bad_header');c.emit(0xaa)
    c.absolute(0xad,0x120c);imm(0xc9,54);c.branch(0xf0,'base')
    imm(0xc9,100);c.branch(0xd0,'bad_header');imm(0xe0,31);c.branch(0xb0,'bad_header')
    c.label('base')
    c.absolute(0xad,0x1034);c.emit(0x0a,0x0a,0xaa)
    c.long(0xaf,0x400010);c.long(0x0f,0x400012);c.branch(0xf0,'bad_header')
    for off in (0,2):
        c.long(0xaf,0x400010+off);c.absolute(0xdd,0x14d0+off);c.branch(0xd0,'bad_header')
    c.emit(0x8a,0x49,4,0,0xaa)
    for off in (0,2):
        c.absolute(0xad,0x1248+off);c.absolute(0xdd,0x14d0+off);c.branch(0xd0,'bad_header')
    imm(0xa9,1472);c.absolute(0x8d,0x120c);c.jump('column_mark')
    c.label('bad_header');c.jump('bad_packet')
    c.label('column_literal')
    c.emit(0xc9,10);c.branch(0xd0,'other');imm(0xe0,4);c.branch(0xf0,'column_write')
    c.label('other');c.jump('literal1814')
    c.label('column_write')
    c.emit(0xc2,0x20)
    c.long(0xaf,0x400016);c.emit(0x85,0x68,0x1a,0x1a,0x85,0x6a)
    c.long(0xaf,0x40000c);imm(0xc9,100);c.branch(0xd0,'range_ready')
    c.emit(0xe6,0x6a,0xe6,0x6a)
    c.label('range_ready');imm(0xa9,24);c.emit(0x85,0x60,0x64,0x62)
    c.label('col')
    # DBR is restored before calling the original STOP/joypad service.
    c.emit(0x8b,0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20)
    c.emit(0xa5,0x62,0xc5,0x68);c.branch(0x90,'omit')
    c.emit(0xc5,0x6a);c.branch(0xb0,'omit')
    c.emit(0xa8,0xa6,0x60)
    c.label('cell');c.long(0xbf,0x400000);c.emit(0x91,0x7a)
    c.label('column_written');c.emit(0xd1,0x7a);c.branch(0xd0,'damage')
    c.emit(0xe8,0xe8,0x98,0x18);imm(0x69,64);c.emit(0xa8);imm(0xc9,1472)
    c.branch(0x90,'cell');c.emit(0x86,0x60);c.branch(0x80,'service_col')
    c.label('damage');c.emit(0xab);c.jump('bad_packet')
    c.label('omit');c.emit(0xaa);imm(0xa0,5)
    c.label('four')
    for row in range(4):
        c.absolute(0xbd,0x5800+row*64);c.absolute(0xdd,0xd800+row*64);c.branch(0xd0,'damage')
    c.emit(0x8a,0x18);imm(0x69,256);c.emit(0xaa,0x88);c.branch(0xd0,'four')
    for row in range(3):
        c.absolute(0xbd,0x5800+row*64);c.absolute(0xdd,0xd800+row*64);c.branch(0xd0,'damage')
    c.label('service_col');c.emit(0xab)
    c.label('column_service');call(c,'service');c.branch(0xf0,'advance');c.jump('stop_packet')
    c.label('advance');c.emit(0xe6,0x62,0xe6,0x62,0xa5,0x62);imm(0xc9,64)
    c.branch(0xf0,'finished');c.jump('col')
    c.label('finished');c.jump('accepted')
    c.label('column_mark')
    # Exact existing 23-row coverage, history and single DMA registration.
    c.emit(*old[labels['column_mark']-ORIGIN:])
    # Dispatch >=9 to the extension, which admits only section2/op10 or
    # the original checked section4/op9. Lower opcodes keep their route.
    assert old[0x247:0x24f]==bytes.fromhex('c90900d0034c6037')
    prefix[0x24a]=0x90
    assert old[0x52f:0x532]==bytes.fromhex('4cd237')
    prefix[0x530:0x532]=(c.labels['column_literal']&65535).to_bytes(2,'little')
    build(base,out,bytes(prefix)+c.finish(),c.labels)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    prepare(**vars(p.parse_args()))
