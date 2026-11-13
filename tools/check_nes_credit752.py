# SPDX-License-Identifier: MIT
"""Exercise the linked 752 ARM through its original receipt, STOP and menu entry points."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_deadline719 import check as deadline
from check_nes_menu533 import check as menu
from check_nes_handoff678 import Handoff, crc, run as map_handoff
from check_nes_obj749 import check as after_bg
from check_nes_receipt742 import check as receipt
from nes_raw506 import sha


def seal_receipts(src):
    m=Handoff(src,'normal')
    m.setup()
    last=bytes((3,0))+struct.pack('<HIH',41,7,957)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    for key,value,size in [('sent',0,2),('ever_sent',1,1),('wait',m.callback|1,4)]:
        m.put(m.w,'nes_sink_window184',key,value,size)
    valid=bytearray((0,0xf7,2,0,0,0,0,1,3))+last[2:]+bytes((0x65,0x9a,0))
    valid[19]=crc(valid[1:19],8,7,0)
    for bit in range(-1,152):
        m.put(m.w,'nes_sink_window184','error',0,1)
        m.put(m.w,'nes_sink_window184','retired',65535,2)
        response=bytearray(valid)
        if bit>=0:response[1+bit//8]^=1<<(bit%8)
        def exchange(tx,clock):
            assert len(tx)==20 and tx[0]==0xe0
            return bytes(response)
        m.endpoint.exchange=exchange
        ok=m.call('nes_window184_through',[m.w,m.q,0])
        assert bool(ok)==(bit==-1)
        assert m.get(m.w,'nes_sink_window184','retired',2)==(65535 if bit>=0 else 0)
    return dict(wrap=True,corrupt_bits=152,bytes_covered=18)


def verify(src,policy):
    handoff_cases=('normal','pending','wrap','wrong_BG','bad_receipt_crc',
                   'bad_descriptor_crc','wrong_generation','STOP')
    if policy.startswith('look'):
        handoff_cases+=('not_ready','previous_BG','previous_BG_mutated')
    deadline_cases=('normal','current_deadline','budget_boundary','budget_after','DMA_done','expiry',
                    'poll_bound','stopped_clock','cold','last_tile','no_clock','stale','wrap',
                    'STOP','bad_credit','bad_final','no_callback')
    receipt_cases=('normal','pending','wrap','expired','future','wrong_map','bad_descriptor_crc','bad_receipt_crc','STOP')
    return dict(firmware=sha(src/'obj-nes-100/firmware.stm'),
                seal_receipts=seal_receipts(src),
                map_input=([deadline(src,c,map_input=(policy,1,288)) for c in ('normal','bad_credit','STOP','bad_final')]
                          +[deadline(src,'normal',map_input=(policy,kind,size)) for kind,size in ((0,48),(1,32))]
                          if policy in ('repay','mapobj') else []),
                BG_descriptor=([map_handoff(src,c) for c in ('normal','bad_E8_CRC','identity','STOP_after_input',
                                                            'failed_input','single_BG','single_OBJ')] if policy=='bgcrc' else []),
                handoff=[after_bg(src,c,policy.startswith('look')) for c in handoff_cases],
                deadline=[deadline(src,c) for c in deadline_cases],
                receipt=[receipt(src,c,True) for c in receipt_cases],
                menu=menu(src,'690'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--policy',required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(verify(a.arm,a.policy),indent=2)+'\n',encoding='utf8',newline='\n')
