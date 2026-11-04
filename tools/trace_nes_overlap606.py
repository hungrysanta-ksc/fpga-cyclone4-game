"""Trace the 604 binary's indivisible transactions, from 954 input through previous-ACK protected publication."""
import argparse
import json
from pathlib import Path
import re
import struct

from check_nes_rows604 import check_geometry, fixture, simulate
from check_nes_wire600 import ROOT, pin, read
from trace_nes_prefix605 import Trace
from analyze_nes_wire600 import Receiver


class Transfers(Trace):
    def input_exchange(self,tx):
        start=self.stamp()/1e6
        rx=super().input_exchange(tx)
        self.io.append(dict(op=hex(tx[0]),n=len(tx),start=start,end=self.stamp()/1e6))
        return rx

    def output_exchange(self,tx):
        if not hasattr(self,'io'):return super().output_exchange(tx)
        start=self.stamp()/1e6
        rx=super().output_exchange(tx)
        self.io.append(dict(op=hex(tx[0]),n=len(tx),start=start,end=self.stamp()/1e6,
                            packet=tx[1] if tx[0]==0xe1 else None,section=tx[2] if tx[0]==0xe1 else None))
        return rx


def measure(d,src,a,link,candidate):
    prior=read(ROOT/'analysis/prefix605-trace.json')
    pin(src/'obj-nes-100/firmware.stm',prior['firmware_SHA256'])
    g=954;geom,raw=fixture(a.data,d,g)
    m=Transfers(src,False,400)
    lut=re.search(r'\{(.+?)\}',(src/'nes_palette165.inc').read_text())[1]
    m.u.mem_write(m.lut,struct.pack('<64H',*map(int,lut.split(','))))
    assert link.request('reset')=='OK'
    p=read(ROOT/'analysis/whole580-verification.json')['phases'][0]['parameters']
    m.start(link,g,a.warm,p['driver_extra_us'],'normal');m.io=[];m.prefix=[];m.emits=[]
    for _ in range(512):
        assert m.call('nes_runtime165_step',[m.rt])
        if m.saw_ea:break
    assert m.saw_ea and m.saw_seal and m.state_value()==0
    check_geometry(m,geom,raw)
    old=next(r for r in prior['frames'] if r['generation']==g)
    assert m.first_bg==old['first_E9'] and m.prefix==old['prefix']
    assert all(b['start']>=a['end'] for a,b in zip(m.io,m.io[1:]))
    # The source parser is linked, with modeled transfers on this negative path.
    r=Receiver(src,bytes(128));r.start(m.blocks)
    for _ in range(6):assert r.pump()
    assert r.index==6 and r.state_value()==1
    at=0x20013000;tok=(r.start_token+6)&65535
    abort=m.blocks[0][:3]+bytes.fromhex('e002'+'00'*8)
    r.u.mem_write(at,abort)
    assert r.call('nes_native165_packet',[r.state,tok,at,len(abort)]) and r.state_value()==0
    r.u.mem_write(at,m.blocks[-1])
    assert not r.call('nes_native165_packet',[r.state,(tok+1)&65535,at,len(m.blocks[-1])])
    assert r.state_value()!=4
    r.receive(m.blocks,geom,raw,g)
    return [dict(generation=g,io=m.io,guards=['output model final ACK/EA','ABORT after six POPs',
                 'late COMMIT rejected','cold full receive'],receiver_B=r.layout['nes_native165']['size'],
                 elapsed_ms=m.stamp()/1e6)]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('board','probe','arm','warm','data','out','report'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    r=simulate(a,'trace',a.arm/'src',True,measure)
    a.report.write_bytes((json.dumps(r,indent=2)+'\n').encode())
