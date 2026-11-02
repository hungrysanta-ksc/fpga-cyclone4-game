# SPDX-License-Identifier: MIT
"""Verify the linked M4 table for every E1 length and the actual 954 packet."""
import argparse
from binascii import crc_hqx
import json
from pathlib import Path

from test_nes_overlap508_arm import ARM,sha


def check(src, trace):
    m=ARM(src,'normal')
    addr=0x20002300
    def compare(blob):
        m.u.mem_write(addr,blob)
        actual=m.call('crc_xmodem_block',[65535,addr,len(blob)])
        assert actual==crc_hqx(blob,65535)
        return actual
    for length in range(17,258):
        compare(bytes([0xe1])+bytes((i*17+length)&255 for i in range(length-1)))
    for _,_,h,_ in map(json.loads,(trace/'packets.jsonl').read_text().splitlines()):
        packet=bytes.fromhex(h)
        if packet[0:2]==bytes([2,2]) and int.from_bytes(packet[8:10],'little')==954 and int.from_bytes(packet[10:12],'little')==2432:
            assert len(packet)==208
            entry_crc=compare(b'\xe1'+packet)
            return dict(firmware=sha(src/'obj-nes-100/firmware.stm'),lengths=241,packet_crc=entry_crc)
    raise AssertionError('missing packet')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('src','trace','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.src,a.trace),indent=2)+'\n')
