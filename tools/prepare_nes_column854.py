"""Construct the fixed-span bitmap and exact WRAM comparator on the 853 links."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once

from prepare_nes_column853 import Code, PROBE, PROBES, call, arm as arm853

ROOT = PROBES / 'nes-column854'
ORIGIN = 0x7e2000


def arm(out):
    arm853(out)
    path=out/'nes_native_sink165.c'
    original=path.read_text()
    path.write_text(once(original,'if(j!=col && (a!=want || b!=want))return true;',
                         'if(j!=col && (a!=want || b!=want || (j>col && want)))return true;'))


def client(out, dynamic=False, straight=False, indexed=False, bank_once=False):
    old = PROBE / 'fast'
    labels = json.loads((old / 'labels.json').read_bytes())
    image = (old / 'body.bin').read_bytes()
    start = labels['column_write']
    body = bytearray(image[:start-ORIGIN])
    c = Code(start)
    c.labels.update({k:v for k,v in labels.items() if v<start})
    # The ARM admits only the first 18 words. Its published bank summaries
    # explicitly require zeros in bytes 36..63 of every row.
    header = labels['column_identity']-ORIGIN
    pos = body.index(bytes.fromhex('c9 3f 00'),header)
    body[pos+1] = 36
    if dynamic:
        from emit_nes_column854 import emit
        emit(c,straight,indexed,bank_once)
    else:
        c.label('column_write')
        c.emit(0xc2,0x20,0xa9,22,0,0x85,0x60,0xa5,0x7a,0x49,0,0x80,0x85,0x74)
        c.long(0xaf,0x400014);c.emit(0x85,0x68,0xa2,0,0)
        c.label('column_row')
        # X = relative row start, Y = relative changed cell. DBR = $7F only
        # during the physical map accesses. Never normalize an omitted cell.
        c.emit(0x8a,0x18,0x65,0x68,0xa8,0x8b,0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20)
        c.emit(0xb1,0x74,0x91,0x7a,0xda,0x5a)
        c.emit(0x8a,0x18,0x69,36,0,0x85,0x62)
        c.branch(0x80,'column_compare');c.label('damage_prefix');c.emit(0x7a,0xfa,0xab);c.jump('bad_packet')
        c.label('column_compare')
        for off in range(0,12,2):
            c.absolute(0xbd,0x5800+off);c.absolute(0xdd,0xd800+off)
            c.branch(0xd0,'damage_prefix')
        c.emit(0x8a,0x18,0x69,12,0,0xaa,0xe4,0x62);c.branch(0xd0,'column_compare')
        c.emit(0x8a,0x18,0x65,0x7a,0xa8)
        # OR is zero iff every bit in all 28 physical target bytes is zero.
        for off in range(0,28,2):
            c.absolute(0xb9 if off==0 else 0x19,off)
        c.branch(0xd0,'damage_prefix')
        c.emit(0x7a,0xa6,0x60);c.long(0xbf,0x400000);c.emit(0x91,0x7a)
        c.label('column_written');c.emit(0xd1,0x7a);c.branch(0xd0,'damage_written')
        c.emit(0xfa,0x8a,0x18,0x69,64,0,0xaa,0xe6,0x60,0xe6,0x60)
        c.label('column_service');c.emit(0xab);call(c,'service');c.branch(0xf0,'column_next');c.jump('stop_packet')
        c.label('column_next');c.emit(0xa5,0x60,0xc9,68,0);c.branch(0xf0,'column_done');c.jump('column_row')
        c.label('column_done');c.jump('accepted')

        c.label('damage_written');c.emit(0xfa,0xab);c.jump('bad_packet')

    c.label('column_mark')
    # Identity already fixed op, section, start, span and target. The fixed
    # coverage masks are exactly map units 1184..1206 (little-endian).
    for addr,value in ((0x1234,3520),(0x1084,3520)):
        if addr==0x1234:c.emit(0xa9);c.word(value)
        c.absolute(0x8d,addr)
    c.absolute(0xad,0x1314);c.branch(0xd0,'mark_fail')
    c.absolute(0xad,0x1316);c.emit(0x89,0x7f,0);c.branch(0xd0,'mark_fail')
    c.emit(0xa9,255,255);c.absolute(0x8d,0x1314)
    c.absolute(0xae,0x1254);c.absolute(0x9d,0x13b4)
    c.emit(0xa9,0x7f,0);c.absolute(0x0c,0x1316)
    c.absolute(0x1d,0x13b6);c.absolute(0x9d,0x13b6)
    for off,value in ((0x60,4),(0x62,2048),(0x64,1472)):
        c.emit(0xa9);c.word(value);c.emit(0x85,off)
    assert image[0x8c8:0x8cc]==bytes.fromhex('a6 60 bf 6c')
    c.absolute(0x20,0x28c8);c.emit(0xa2,4,0)
    assert image[0x508:0x50e]==bytes.fromhex('b0 03 4c af 27 bf')
    c.absolute(0x4c,0x2508)
    c.label('mark_fail');c.jump('bad_packet')
    at=body.index(bytes.fromhex('8d 0c 12 4c be 24'),header)+4
    body[at:at+2]=(c.labels['column_mark']&65535).to_bytes(2,'little')
    body.extend(c.finish())
    from boot_nes_column854 import build
    build(old,out,bytes(body),c.labels,straight)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('out',type=Path)
    p.add_argument('--arm',action='store_true')
    p.add_argument('--dynamic',action='store_true')
    p.add_argument('--straight',action='store_true')
    p.add_argument('--indexed',action='store_true')
    p.add_argument('--bank-once',action='store_true')
    args=p.parse_args()
    if args.arm:arm(args.out)
    else:
        indexed=args.indexed or args.bank_once
        straight=args.straight or indexed
        client(args.out,args.dynamic or straight,straight,indexed,args.bank_once)
