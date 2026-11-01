# SPDX-License-Identifier: MIT
"""Run the second offer and its credit/STOP/backpressure branches on the linked ARM."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import ELFFile,sha
from check_nes_map527 import ARM,MapEndpoint,exercise
from check_nes_hardware494_termination import member_offset
from check_nes_supply485_arm import crc
from check_nes_tile532 import check as end_guard


class CreditEndpoint(MapEndpoint):
    def exchange(self,tx,clock):
        if tx[0]!=0xe0 or self.mode not in ('refreshed','full','bad_identity'):
            return super().exchange(tx,clock)
        self.calls.append(tx.hex())
        reply=bytearray(20)
        used=(self.sent-self.retired)&65535
        reply[1]=0xf7
        reply[2]=int(used>0)|(2 if self.retired else 0)|(4 if used==4 else 0)
        reply[3:5]=self.sent.to_bytes(2,'big');reply[5:7]=self.retired.to_bytes(2,'big')
        reply[7:19]=self.last
        if self.mode=='bad_identity' and self.sent:reply[9]^=1
        reply[19]=crc(reply[1:19],8,7,0)
        return bytes(reply)


def offer(src,mode,*,early=None,count=0,first=False,expect_deferred=False):
    m=ARM(src,mode)
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        die=next(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
                 if d.tag=='DW_TAG_structure_type' and 'DW_AT_byte_size' in d.attributes and
                 'DW_AT_name' in d.attributes and d.attributes['DW_AT_name'].value==b'nes_native_runtime165')
        layout={c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in die.iter_children() if c.tag=='DW_TAG_member'}
    rt=0x20001000
    m.w,m.s,m.p=[rt+layout[n] for n in ('transport','sink','plan')]
    m.endpoint=CreditEndpoint(mode);m.setup();m.endpoint.calls.clear()
    if early is not None:
        m.put(m.p,'nes_plan200','early',int(early),1)
        m.put(m.p,'nes_plan200','count',count,1)
    for n,address in [('video',m.video),('resident',m.resident)]:
        m.u.mem_write(rt+layout[n],address.to_bytes(4,'little'))
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    cursor=0 if first else {'sentinel':128,'end':64}.get(mode,8)
    m.put(m.s,'nes_native_sink165','map_next',cursor,1)
    if first:
        # Here the test asks for an inherited bank with rows 8..10 dirty.
        # The reset fixture otherwise marks every row stale for a cold bank.
        m.u.mem_write(m.resident+m.layout['nes_resident211']['map_stale'],bytes(16))
    m.put(m.video,'nes_native_video165','map_dirty',7<<8,8)
    data=bytes(range(256))*16;m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],data)
    if mode in ('refreshed','full','bad_identity'):
        m.endpoint.sent=1;m.endpoint.retired=65534 if mode=='full' else 1
        m.put(m.w,'nes_sink_window184','sent',1,2);m.put(m.w,'nes_sink_window184','retired',65534,2)
        m.put(m.w,'nes_sink_window184','ever_sent',1,1)
        # The cached count wraps. The checked returned identity is required
        # when all outstanding packets have been retired.
        ack=b'\0\x02'+bytes(8)+b'\x65\x9a'
        m.endpoint.last=ack
        m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],ack[1:2]+b'\x02'+ack[2:10])
    if mode=='old_bulk':
        m.put(m.p,'nes_plan200','bulk_pending',1,1);m.put(m.p,'nes_plan200','bulk_until',65533,2)
    if mode=='bulk':m.endpoint.jobs=[(0,0,16,1)]
    if mode=='STOP':m.endpoint.mode='STOP_after_E9';m.endpoint.accepted=1
    ok=m.call('offer527',[rt])
    calls=[bytes.fromhex(x) for x in m.endpoint.calls]
    if expect_deferred:
        assert ok==1 and not calls and m.get(m.s,'nes_native_sink165','map_next',1)==cursor
        return dict(mode=mode,ok=ok,early=early,count=count,first=first,deferred=True)
    maps=[b[1:-2] for b in calls if b[0]==0xe1 and b[1] in (2,4)]
    assert bool(ok)==(mode not in ('bad_identity','STOP','bad_E8_CRC','ambiguous_E1')),mode
    assert len(maps)==int(mode in ('normal','refreshed','ambiguous_E1')),mode
    if maps:
        b,=maps;assert int.from_bytes(b[10:12],'little')==512 and b[16:]==data[512:704]
    assert m.get(m.s,'nes_native_sink165','map_next',1)==(11 if maps and ok else cursor)
    if mode=='bulk':assert [b[1] for b in calls if b[0]==0xe1]==[7]
    if mode in ('full','bad_identity'):assert [b[0] for b in calls]==[0xe0]
    return dict(mode=mode,ok=ok,ops=[hex(b[0]) for b in calls],maps=len(maps))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    rows=[offer(a.arm,k) for k in ('normal','refreshed','full','bad_identity','sentinel','end','old_bulk','bulk','STOP','bad_E8_CRC','ambiguous_E1')]
    first=[exercise(a.arm,k) for k in ('DATA','RLE','empty','last_row','three_credits','bulk','STOP','bad_E8_CRC','ambiguous_E1')]
    end=[end_guard(a.arm,k) for k in ('normal','busy','bad_crc','bad_identity','STOP_after_refresh','ambiguous_E1')]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),second=rows,first=first,end=end),indent=2)+'\n')
