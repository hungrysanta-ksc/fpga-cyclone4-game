# SPDX-License-Identifier: MIT
import argparse
import json
import struct
from pathlib import Path

from check_nes_credit752 import verify
from check_nes_receive682 import Burst, burst
from check_nes_game478 import ELFFile
from test_nes_raw506_joint import member_offset


def extra(src, case):
    class Inject(Burst):
        def hook(self,u,at,size,user):
            if getattr(self,'index',None)==15:
                self.case=case
            return super().hook(u,at,size,user)
    m=Inject(src,'cap7')
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        entries=(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs())
        plan=next(d for d in entries if d.tag=='DW_TAG_structure_type' and
                  d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_plan200'
                  and 'DW_AT_byte_size' in d.attributes)
        history=next(member_offset(c) for c in plan.iter_children() if c.tag=='DW_TAG_member' and
                     c.attributes['DW_AT_name'].value==b'bank_history')
    m.u.mem_write(m.rt+m.layout['nes_native_runtime165']['plan']+history,bytes([1 if case=='cold' else 2]))
    m.packets[7]=b''.join(struct.pack('>HHH',i,953,i) for i in range(6,28))
    m.packets.extend(struct.pack('>HHH',i,953,i) for i in range(28,36))
    m.u.mem_write(0x20018000,bytes([0xa5])*0x8000)
    ok=bool(m.call('wait634',[m.rt,m.check|1,3,0]))
    assert ok==(case in ('normal','cold')) and m.state_value()!=4
    assert m.index=={'normal':16,'cold':7}.get(case,15),(case,m.index)
    assert not {0xd3,0xe0,0xe1,0xea}.intersection(m.ops)
    return dict(case=case,accepted=ok,confirmed_or_popped=m.index)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    result=verify(a.arm,'mapobj')
    result['initial']=[burst(a.arm,k) for k in ('cap7','empty_after3','STOP_after3','CRC_third','cache_CRC','cache_token')]
    result['extra']=[extra(a.arm,k) for k in ('normal','cold','STOP_before','bad_CRC','failed_IO','bad_retire')]
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
