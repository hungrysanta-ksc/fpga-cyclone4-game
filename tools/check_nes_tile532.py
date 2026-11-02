# SPDX-License-Identifier: MIT
"""Check wrapped credit refill and retire an older bulk before its four-record window expires."""
import argparse
import json
from pathlib import Path
import struct

from check_nes_quiet528 import ARM,ELFFile,member_offset
from check_nes_supply485_arm import Endpoint,crc,sha


class Window(Endpoint):
    def __init__(self,mode):
        super().__init__(mode)
        self.polls=0
        self.writes=[]
        self.live=False

    def exchange(self,tx,clock):
        if not self.live:
            return super().exchange(tx,clock)
        self.calls.append(tx.hex())
        if tx[0]==0xe8:
            self.polls+=1
            r=bytearray(20);r[1:4]=bytes([0xd7,4,int(self.polls>10)])
            if self.end:r[3:6]=b'\x02\x00\x01'
        elif tx[0]==0xe0:
            if self.mode!='busy':self.retired=self.sent
            used=(self.sent-self.retired)&65535
            r=bytearray(20);r[1:3]=bytes([0xf7,int(used!=0)|2|(4 if used==4 else 0)])
            r[3:7]=struct.pack('>HH',self.sent,self.retired)
            r[7:19]=self.last
            if self.mode=='bad_identity':r[9]^=1
            if self.mode=='STOP_after_refresh':
                self.mode='STOP_after_E9'
                self.accepted=1
        elif tx[0]==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            b=tx[1:-2];assert b[0] in (2,4) and b[1]==2
            assert ((self.sent-self.retired)&65535)<3
            self.writes.append(int.from_bytes(b[10:12],'little'))
            self.sent=(self.sent+1)&65535
            self.last=bytes([0,b[0]])+b[2:10]+b'\x65\x9a'
            return bytes(len(tx))
        elif tx[0]==0xe9:
            assert self.polls>10
            self.end=True
            return bytes(len(tx))
        else:raise AssertionError(tx[0])
        r[19]=crc(r[1:19],8,7,0)
        if tx[0]==0xe0 and self.mode=='bad_crc':r[19]^=1
        return bytes(r)


def check(src,mode,deferred=False):
    m=ARM(src,mode);ep=Window(mode);m.endpoint=ep
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        d=next(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
               if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and
               d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and 'DW_AT_byte_size' in d.attributes)
        fields={c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}
    rt=m.p
    m.p,m.w,m.s=[rt+fields[k] for k in ('plan','transport','sink')]
    m.setup()
    for k,v in [('video',m.video),('resident',m.resident)]:m.u.mem_write(rt+fields[k],v.to_bytes(4,'little'))
    for k,v,n in [('ctx',rt,4),('quiet_map',m.syms['quiet528']|1,4),('generation',907,2),('started',1,1),
                  ('bulk_pending',1,1),('bulk_until',65532,2)]:
        m.put(m.p,'nes_plan200',k,v,n)
    ep.sent=65532;ep.retired=65529;ep.live=True
    head=bytes([7,0,0,0,1,0,0,0,139,3])
    ep.last=bytes([0,7])+head[2:10]+b'\x65\x9a'
    for k,v,n in [('sent',ep.sent,2),('retired',ep.retired,2),('ever_sent',1,1)]:m.put(m.w,'nes_sink_window184',k,v,n)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],head)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.resident,'nes_resident211','map_upload',0x5555,8)
    ok=m.call('nes_plan200_end',[m.p])
    if ok and deferred and not ep.end:
        assert m.get(m.p,'nes_plan200','count') and not m.get(m.p,'nes_plan200','finished')
        ok=m.call('nes_plan200_progress',[m.p,1])
    assert bool(ok)==ep.end==(mode in ('normal','busy'))
    assert ep.writes==(list(range(0,1024,128)) if mode=='normal' else [0] if mode=='ambiguous_E1' else [])
    if mode=='normal':assert ep.sent==4 and not m.get(m.p,'nes_plan200','bulk_pending')
    return dict(mode=mode,maps=len(ep.writes),E0=sum(x.startswith('e0') for x in ep.calls)-1,END=ep.end,
                window_error=m.get(m.w,'nes_sink_window184','error'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--deferred-end',action='store_true')
    a=p.parse_args();rows=[check(a.arm,k,a.deferred_end) for k in ('normal','busy','bad_crc','bad_identity','STOP_after_refresh','ambiguous_E1')]
    a.out.write_text(json.dumps(dict(sha=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n')
