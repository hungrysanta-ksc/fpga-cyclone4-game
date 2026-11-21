"""913 linked replay with finite E9-bank lifetime and single hint consumer.

Uses the board's row indexing and measured slot calendar. Scan costs are
sensitivity parameters; this is not a cycle-coupled board simulation.
"""
import argparse
import math
from pathlib import Path
from unittest.mock import patch

from nes_overlap913 import OUT, work, peer, monitor
from replay_nes_rows911 import AheadLink, peer_base_next
from test_nes_banks557 import handoff
from test_nes_raw506_joint import wire_plan


class PortLink(AheadLink):
    def begin(self):
        if self.owner!=self.generation:
            super().begin()
            self.scan_at=0
            self.record=0
            self.hint=None
            self.in_flight=None
            self.started=0
            self.directory={}
            self.admitted=[]

    def index(self,addr):
        return addr if self.pinned else ((addr>>4 ^ addr>>11)&15,addr&7)

    def scan(self):
        batches=self.phases.get(self.owner,{}).get('banks557',[])
        while self.next_batch<len(batches):
            b=batches[self.next_batch]
            if self.record==0:
                box=handoff(batches,self.next_batch)
                if not math.isfinite(box):
                    return None
                self.scan_at=max(self.scan_at,math.ceil(box)+5)
            records=self.plansets[self.owner]
            pos=b['first']+self.record
            if pos==len(records):
                assert self.record+1==b['count']  # terminal short END
                self.next_batch+=1
                self.record=0
                continue
            q=records[pos]
            body=wire_plan(q)
            # Two NES edges per byte minimum. The primary READ can also
            # reserve the port. Keep the lower-cost and contended runs distinct.
            end=self.scan_at+len(body)*self.scan_edges
            if end>=b.get('release',math.inf) or self.record+1==b['count']:
                self.next_batch+=1
                self.record=0
            else:
                self.record+=1
            self.scan_at=end
            if end<b.get('release',math.inf) and body[0]==0x81:
                return end,int.from_bytes(q[4:6],'little'),q[7]
        return None

    def pump(self,now):
        self.begin()
        while self.active:
            if not self.in_flight:
                if not self.hint:
                    self.hint=self.scan()
                if not self.hint:
                    return
                at,tag,mask=self.hint
                if self.pinned and tag not in self.admitted:
                    if len(self.admitted)==16:
                        self.hint=None
                        continue
                    self.admitted.append(tag)
                self.scan_at=max(self.scan_at,self.started)+1
                self.hint=None
                self.in_flight=(max(at,self.started),tag,mask)
                # One decoded hint may wait behind the active tag.
                self.hint=self.scan()
            at,tag,mask=self.in_flight
            row=(mask & -mask).bit_length()-1
            addr=16*tag+row
            if self.pinned and addr in self.directory:
                if max(at,self.free)>=now:return
                self.free=max(at,self.free)+1
            else:
                grant,reply=self.original_select(max(at,self.free))
                if grant>=now:
                    return
                self.free=reply+1
                self.directory[self.index(addr)]=(addr,self.free)
                self.spec.append((self.owner,addr,grant,reply))
            mask &= ~(1<<row)
            if mask:
                self.in_flight=(self.free,tag,mask)
            else:
                self.started=self.free
                self.in_flight=None

    def next_rom(self,t):
        self.pump(t)
        kind,addr=self.pending[0]
        pair=kind==1 and not addr&8
        if pair:
            tag=addr>>4
            original=self.cache[str(self.owner)].get(str(tag%128))
            captures=(self.lookups[str(self.owner)][str(addr)]==1 or
                      original and original[0]==tag and str(addr&15) in original[1])
            if not captures:
                t+=2
                entry=self.directory.get(self.index(addr))
                if entry and entry[0]==addr:
                    self.pending.popleft()
                    self.peer=self.owner,addr+8
                    self.counts[self.owner]+=1
                    return max(t,entry[1])+8+2*(self.lookups[str(self.owner)][str(addr)]==2)
        n=len(self.grants)
        end=peer_base_next(self,t)
        if pair and len(self.grants)>n:
            if not self.pinned or addr>>4 in self.admitted:
                self.directory[self.index(addr)]=(addr,end)
            if not self.active:self.started=end
            self.active=True
        return end


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('temp',type=Path)
    ap.add_argument('phase',type=int,choices=(1,2))
    ap.add_argument('--cold',action='store_true')
    ap.add_argument('--pinned',action='store_true',help='sensitivity only: admitted tags retain their rows')
    ap.add_argument('--scan-edges',type=int,choices=(2,3),default=2)
    a=ap.parse_args()
    PortLink.scan_edges=a.scan_edges
    PortLink.pinned=a.pinned
    with patch.object(peer,'PeerLink',PortLink),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        tag='914pin' if a.pinned else '914bport'
        peer.compare(a.temp,a.phase,a.cold,True,edition=907,work_arm=work('idle'),run_id=tag+str(a.scan_edges))
