# SPDX-License-Identifier: MIT
"""Exercise the linked 625 receiver callback, with modeled SPI/status and service."""
import argparse
import json
from pathlib import Path
from nes_raw506 import encode, sha
from test_nes_prefetch498_arm import Probe


def run(arm,data,in_place=False):
    g=(data/'frame951.geometry').read_bytes()
    raw=(data/'frame951.raw').read_bytes()
    results=[]
    for fault in ('none','IO','CRC','service_after_D2','deadline_after_D2'):
        m=Probe(arm,g,raw,fault)
        m.packets,_,_=encode(g,raw,951)
        m.put(m.video,'nes_native_video165','generation',950,2)
        m.put(m.state,'nes_native165','generation',950,2)
        guard=m.get(m.w,'nes_sink_window184','guard',4)
        def wait(reason=2,progress=0):
            m.measure_wait=True
            try:
                return m.call('wait634',[m.rt,guard,reason,progress])
            finally:
                m.measure_wait=False
        assert wait() and not m.input_calls
        tx,rx=0x2001b000,0x2001b100
        if in_place:rx=tx  # nes_window184 send() uses io(tx,tx).
        m.syms['runtime_transfer634']=m.get(m.w,'nes_sink_window184','transfer',4)&~1
        for op,armed in ((2,0),(3,7)):
            # Only the SPI wrapper's successful E1 branch is under test;
            # packet/SEAL validation is exercised separately by the receiver.
            m.u.mem_write(tx,bytes((0xe1,op))+bytes(17))
            assert m.call('runtime_transfer634',[m.rt,tx,rx,19])
            if in_place:assert m.u.mem_read(tx+1,1)[0]!=op
            assert m.get(m.rt,'nes_native_runtime165','prefetch_left',1)==armed,('SEAL arm',op,armed)
        for reason,progress in [(0,0),(1,0),(2,1)]:
            assert wait(reason,progress) and not m.input_calls
        for _ in range(8):
            ok=wait()
            if not ok:
                break
        if fault=='none':
            assert ok and m.index==7 and m.input_calls.count(0xd1)==7
            assert m.input_calls[-2:]==[0xd2,0xd0] and m.get(m.state,'nes_native165','generation',2)==951
            assert m.get(m.rt,'nes_native_runtime165','prefetch_left',1)==0
            # Compare decoded prefix against the original geometry, including
            # the little-endian map words already marked received.
            n=m.get(m.state,'nes_native165','at',2)
            assert n and bytes(m.u.mem_read(m.state+m.layout['nes_native165']['maps'],2*n))==g[:2*n]
        else:
            assert not ok and m.get(m.rt,'nes_native_runtime165','result',1)
        assert m.get(m.video,'nes_native_video165','generation',2)==950 and 0xd3 not in m.input_calls
        results.append(dict(fault=fault,calls=m.input_calls,completed_pops=m.index,
                            isolated_stack_B=0x2001e000-m.low_stack))
    return dict(rows=results,firmware=sha(arm/'obj-nes-100/firmware.stm'),
                bytes=(arm/'obj-nes-100/firmware.stm').stat().st_size)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('arm','data','out'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--in-place',action='store_true')
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.arm,a.data,a.in_place),indent=2)+'\n',newline='\n')
