# SPDX-License-Identifier: MIT
"""M4/65816 sensitivity using actual paired boot-core admission/return times.

Replay the measured eight boot windows periodically. This is NOT a matched
first-level core workload or closed-loop NES/ARM co-simulation/physical FPS.
"""
import argparse,bisect,json,math
from pathlib import Path
import test_nes_raw506_joint as joint
from check_nes_game478 import sha
class Calendar:
    def __init__(self,folder):
        assert json.loads((folder/'result.json').read_text())['passed']
        anchors={int(a):int(b)for a,b in (x.split()for x in (folder/'fill1/anchors.tsv').read_text().splitlines())}
        origin=anchors[12]-8;self.period=anchors[20]-anchors[12];self.pairs=[];pending=None
        for line in (folder/'fill1/rom.tsv').read_text().splitlines():
            kind,t,f,row,dot,address=line.split();t=int(t);f=int(f)
            if kind=='G':
                assert pending is None and 12<=f<20 and 242<=int(row)<260
                pending=(t,address)
            else:
                assert kind=='R'and pending and address==pending[1]and 0<t-pending[0]<=7
                self.pairs.append((pending[0]-origin,t-origin));pending=None
        assert pending is None and self.pairs and self.pairs[-1][1]<self.period
        self.starts=[g for g,r in self.pairs]
        self.summary=dict(period_masterclocks=self.period,boot_frames=[12,19],transactions=len(self.pairs),latencies=sorted({r-g for g,r in self.pairs}),trace_SHA256=sha(folder/'fill1/rom.tsv'),anchor_SHA256=sha(folder/'fill1/anchors.tsv'))
        # Requests at grant, one tick after, and across wrap cannot receive a
        # response from an already completed or not-yet-granted transaction.
        for t in [0,self.period-1,self.period,*self.starts,*[x+1 for x in self.starts]]:
            g,r=self.select(t);assert t<=g<r and r-g<=7
    def select(self,t):
        t=math.ceil(t);q,offset=divmod(t,self.period);i=bisect.bisect_left(self.starts,offset)
        if i==len(self.starts):q+=1;i=0
        g,r=self.pairs[i];return q*self.period+g,q*self.period+r
class TraceLink(joint.Link):
    def __init__(self,a):
        self.calendar=Calendar(a.calendar);self.allocations=[];super().__init__(a)
    def next_rom(self,t):
        g,r=self.calendar.select(t-self.a.rom_phase);g+=self.a.rom_phase;r+=self.a.rom_phase
        self.allocations.append(dict(requested=t,grant=g,response=r));return r
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','data','fixture','plans','client','mesen','out','calendar','driver503']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.candidate=True;a.frames=12;a.cpi=2;a.capture_gate=True;a.spi_us=0;a.rom_stride=48;a.rom_phase=0;a.start=3000000
    joint.Link=TraceLink;joint.run(a)
    r=json.loads((a.out/'joint.json').read_text());r['scope']=__doc__;r['parameters']['ROM_safe_slot_stride']=None;r['parameters']['ROM_calendar']=Calendar(a.calendar).summary
    r['full_ROM_RTL']=False;r['ROM_trace_limit']='Saturated boot-core grants,periodic eight-window replay;live gameplay and source byte-cadence are not closed-loop.'
    (a.out/'joint.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS509 actual boot-trace sensitivity;not matched gameplay timing')
