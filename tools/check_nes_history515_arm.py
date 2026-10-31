# SPDX-License-Identifier: MIT
"""Check the released M4's tentative vs. published row maps and reset boundaries."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine, sha
from check_nes_trim514_history import check as check_masks

def run(a):
    check_masks(a)
    report=json.loads(a.out.read_text())
    m=Machine(a.arm,bytes(128))
    s=m.resident
    spec=m.layout['nes_resident211']
    rows=s+spec['published_rows']
    touched=s+spec['size']+16
    def expect(a,b):
        assert bytes(m.u.mem_read(rows,16))==a.to_bytes(8,'little')+b.to_bytes(8,'little')
    def stage(epoch,g,mask):
        assert m.call('nes_resident211_begin',[s,epoch,1,g,m.writer|1,0])
        m.u.mem_write(touched,bytes(255 if mask>>i&1 else 0 for i in range(64)))
        assert m.call('nes_resident211_prepare',[s,touched])
    def ack(serial,g,b):
        assert m.call('nes_resident211_commit',[s,serial,g,b,1])
    full=(1<<64)-1
    a_rows=(1<<63)|1;b_rows=1<<17
    expect(0,0)
    stage(1,905,0);expect(0,0);ack(1,905,0);expect(full,0)
    stage(1,906,a_rows);expect(full,0);ack(2,906,1);expect(full,full)
    stage(1,907,b_rows);expect(full,full);ack(3,907,0);expect(a_rows|b_rows,full)
    stage(2,908,0);expect(0,0);ack(4,908,1);expect(0,full)
    stage(2,909,0);expect(0,full)
    m.call('nes_resident211_abort',[s]);expect(0,0)
    assert not m.call('nes_resident211_commit',[s,5,909,0,1]);expect(0,0)
    report.update(publication_checked=True,firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'))
    a.out.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
