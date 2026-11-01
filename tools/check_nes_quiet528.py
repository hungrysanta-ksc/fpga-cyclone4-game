# SPDX-License-Identifier: MIT
"""Drive the linked END flush through blocked/ready E8 responses and observe actual E1/E9 order."""
import argparse
import json
from pathlib import Path

from check_nes_hardware494_termination import member_offset
from check_nes_map527 import ARM, MapEndpoint, crc, sha
from check_nes_supply485_arm import ELFFile


class QuietEndpoint(MapEndpoint):
    def __init__(self,case):
        super().__init__(case)
        self.remaining=0 if case in ('ready_E9','bulk') else 4
        self.case=case

    def exchange(self,tx,clock):
        rx=super().exchange(tx,clock)
        if tx[0]==0xe8 and self.remaining:
            assert not rx[6]
            b=bytearray(rx)
            b[3]=0
            b[19]=crc(b[1:19],8,7,0) ^ (self.case=='bad_E8_CRC')
            self.remaining-=1
            if self.case=='STOP_after_poll':
                self.mode='STOP_after_E9'
                self.accepted=1
            return bytes(b)
        if tx[0]==0xe1 and tx[1] in (2,4) and self.case=='STOP_after_map':
            self.mode='STOP_after_E9'
            self.accepted=1
        return rx


def check(src,case):
    m=ARM(src,case)
    rt=m.p
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        d=next(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
               if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name')
               and d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and 'DW_AT_byte_size' in d.attributes)
        layout={c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}
    m.p,m.w,m.s=[rt+layout[n] for n in ('plan','transport','sink')]
    m.endpoint=QuietEndpoint(case)
    m.setup()
    m.endpoint.calls.clear()
    for n,v in (('video',m.video),('resident',m.resident)):
        m.u.mem_write(rt+layout[n],v.to_bytes(4,'little'))
    for n,v,b in [('ctx',rt,4),('quiet_map',m.syms['quiet528']|1,4),('generation',907,2),('started',1,1)]:
        m.put(m.p,'nes_plan200',n,v,b)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.s,'nes_native_sink165','map_next',5,1)
    mask=0 if case=='empty' else sum(1<<i for i in (4,5,10,63))
    m.put(m.resident,'nes_resident211','map_upload',mask,8)
    if case=='three_credits':
        m.put(m.w,'nes_sink_window184','sent',1,2)
        m.put(m.w,'nes_sink_window184','retired',65534,2)
    if case=='bulk':
        m.endpoint.jobs=[(0,0,16,1)]
    ok=bool(m.call('nes_plan200_end',[m.p]))
    tx=[bytes.fromhex(v) for v in m.endpoint.calls]
    maps=[int.from_bytes(b[11:13],'little')//64 for b in tx if b[0]==0xe1 and b[1] in (2,4)]
    expected={'maps':[5,10,63],'STOP_after_map':[5],'ambiguous_E1':[5]}.get(case,[])
    assert maps==expected,(case,maps)
    assert ok==(case not in ('bad_E8_CRC','STOP_after_poll','STOP_after_map','ambiguous_E1')),case
    assert sum(b[0]==0xe9 for b in tx)==int(ok)
    if case=='bulk':assert [b[1] for b in tx if b[0]==0xe1]==[7]
    if case=='ambiguous_E1':assert m.get(m.s,'nes_native_sink165','map_next')==5
    return dict(case=case,END_accepted=ok,map_rows=maps,operations=[b[0] for b in tx])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    cases=('maps','empty','ready_E9','three_credits','bulk','bad_E8_CRC','STOP_after_poll','STOP_after_map','ambiguous_E1')
    rows=[check(a.arm,c) for c in cases]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
