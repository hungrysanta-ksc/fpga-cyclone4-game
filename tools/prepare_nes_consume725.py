"""One existing prefix DMA inside an independently validated bulk transaction.

The parser has checked the held head identity/descriptor before entry. Bit1
of the existing open-transaction word is transient ownership, not a new ACK.
Idle callers retain new-head priority; STOP and the fresh beam stay shared.
"""
import argparse,json
from pathlib import Path
from unittest.mock import patch
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import sha
import nes_rom636 as codec
from prepare_nes_longrun694 import optimal

ORIGIN=0x7e2000

def run(a):
    assert sha(a.base/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
    body=bytearray((a.base/'body.bin').read_bytes())
    labels=json.loads((a.base/'labels.json').read_text())
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    c.label('owned_bulk725')
    if a.after_payload:c.emit(0xa9,0xa5);c.absolute(0x8d,0x6050);c.emit(0xc2,0x20)
    c.labels['owned_return725']=labels['accepted194'] if a.after_payload else labels['data']
    # Existing open=1 is restored before data, STOP handling or any ACK.
    c.absolute(0xee,0x1228);c.absolute(0xee,0x1228)
    call(c,'prefix523')
    c.absolute(0xce,0x1228);c.absolute(0xce,0x1228)
    c.absolute(0xad,0x1236);c.emit(0xf0,3);c.jump('stop_packet');c.jump('owned_return725')
    c.label('priority725')
    c.absolute(0xad,0x1228);c.emit(0x29,2)
    if a.after_payload:
        # The just-consumed tile has not received its packet ACK yet. Only
        # earlier accepted map commands may borrow this owned-head boundary.
        c.emit(0xd0,3);c.jump('legacy_head725')
        c.absolute(0xad,0x4303);c.emit(0x29,0x70,0xc9,0x50)
        c.emit(0xf0,3);c.jump('skip8_523');c.jump('grant524')
        c.label('legacy_head725')
    else:
        c.emit(0xf0,3);c.jump('grant524')
    c.absolute(0xad,0x6000);c.emit(0x29,1)
    c.emit(0xf0,3);c.jump('skip8_523');c.jump('grant524')
    # Keep alignment rejection and all descriptor/CRC/identity tests intact.
    if a.after_payload:
        at=labels['accepted194']-ORIGIN-7
        assert body[at:at+7]==bytes.fromhex('a9a58d5060c220')
        body[at:at+7]=bytes([0x4c])+(c.labels['owned_bulk725']&65535).to_bytes(2,'little')+bytes([0xea])*4
    else:
        at=labels['begin']-ORIGIN-3
        assert body[at:at+3]==bytes([0x4c])+(labels['data']&65535).to_bytes(2,'little')
        body[at:at+3]=bytes([0x4c])+(c.labels['owned_bulk725']&65535).to_bytes(2,'little')
    lo,hi=[labels[n]-ORIGIN for n in ('ready524','grant524')]
    assert body[lo:hi]==bytes.fromhex('ad00602901d056'),body[lo:hi].hex()
    body[lo:hi]=bytes([0x4c])+(c.labels['priority725']&65535).to_bytes(2,'little')+bytes([0xea])*(hi-lo-3)
    body.extend(c.finish())
    with patch.object(codec,'pack',optimal):
        codec.build(a.raw635,a.out,edit_body=lambda old,syms:bytes(body),allow_extension=True)
    (a.out/'labels.json').write_text(json.dumps(c.labels,indent=2)+'\n')
    info=json.loads((a.base/'build.json').read_text());packed=json.loads((a.out/'build.json').read_text())
    for n in ('body_bytes','prefix_B','encoded_B','loader_B','physical_free_B','verify_entry','boot_error'):info[n]=packed[n]
    info.update(candidate='consume725B' if a.after_payload else 'consume725A',body_SHA256=sha(a.out/'body.bin'),body_identical693=False,
        copy_verified_bytes=len(body),body_free=0x1900-len(body),new_persistent_WRAM_B=0,
        transient_owner='1228 bit1 inside current validated bulk; restored before common continuation',
        after_payload=a.after_payload,
        source_sha=sha(Path(__file__)),scope=__doc__)
    (a.out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps({n:info[n] for n in ('body_bytes','physical_free_B','prefix_B','encoded_B')}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--after-payload',action='store_true')
    for n in ('base','raw635','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
