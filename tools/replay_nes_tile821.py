"""Time paired game geometry on the linked MMC820 ARM and its production 65816.
The producer/ROM calendar, Cortex CPI and SPI duration are models, not board timestamps.
"""
import json
import re
import shutil
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_nes_raw506_joint as joint
from nes_transfer512_rpc import Pipe,PipeLink
from test_nes_service509_schedule import Calendar
from test_nes_banks557 import seal,decode,snapshot
from test_nes_progress680 import rpc_method
PROGRESS_RPC=rpc_method()
from test_nes_obj609 import lanes
from check_nes_game478 import crc,sha
from prepare_nes_mask820 import WORK

class GameLink(joint.Link):
    seal557=seal
    def decode557(self,q,arrived,now):
        start=decode(self,q,arrived,now)
        if start<=now:
            self.boundary_clock=start
            if self.open and q[6]!=3:
                size=32 if q[6]==1 else 16
                slot=int.from_bytes(q[2:4],"little")*size
                previous=self.open
                if previous["kind"]!=int(q[6]==1) or previous["slot"]+len(previous["data"])!=slot:
                    # bulk206 announces a discontinuity before this tile starts ROM reads.
                    self.publish()
        return start
    def snapshot557(self,tx,start):
        reply=snapshot(self,tx,start)
        if tx[0]==0xe8:
            quiet=self.previous_e8==reply and not reply[6] and self.generation>=907
            self.previous_e8=reply
            if self.a.mode=="poll":
                # Optimistic short reply only for unchanged descriptor-free snapshots.
                self.cpu.driver_extra[0xe8]=(2-20)*8*joint.MASTER/2625000 if quiet else self.e8_extra
        return reply

    def __init__(self,a):
        self.commands,self.replies=Pipe(True),Pipe(False)
        self.phases={}
        self.calendar=Calendar(a.calendar)
        self.pending=deque()
        self.line={}
        self.tag=-1
        self.cache=json.loads((a.data/"cache.json").read_text())
        self.folded=json.loads((a.data/"folded.json").read_text()) if a.mode=="fold" else {}
        self.progress680=False
        self.progress_events680=[]
        self.previous_e8=None
        self.packet_log=(a.out/"packets.jsonl").open("w")
        self.fp=(a.out/"producer.jsonl").open("w",buffering=1)
        def lua(args):
            s=a.template.read_text()
            if getattr(a, "adapt_template", None):
                s=a.adapt_template(s)
            s=re.sub('local ROOT=.*',lambda _: 'local ROOT='+json.dumps(a.out.as_posix()),s,count=1)
            for key,pipe in (("cmds",self.commands),("replies",self.replies)):
                s=re.sub('local '+key+r'=assert\(io.open\("[^"]+"',lambda _: 'local '+key+'=assert(io.open('+json.dumps(pipe.name),s,count=1)
            s=s.replace("and 66 or","and "+str(a.frames)+" or")
            for g in joint.frame_generations(a):
                for k in ("colors636","map"):
                    name=f"{k}-{g}.bin"
                    shutil.copyfile(a.data/name,a.out/name)
            (a.out/"capture.lua").write_text(s,encoding="utf8")
        with patch.object(joint,"lua_rpc",lua):
            super().__init__(a)
    def exchange(self,seq,target,op,args):
        return PipeLink.exchange(self,seq,target,op,args)
    def response(self,tx):
        r=bytearray(super().response(tx))
        if tx[0]==0xe0:
            if self.progress680 and self.sent==self.retired and self.retired:r[2]|=8
            r[19]=crc(r[1:19],8,7,0)
        return bytes(r)
    def rpc(self,t,*args):
        self.now=t
        return PROGRESS_RPC(self,t,*args)
    def accept(self,tx,t):
        if tx[0]==0xe1:self.progress680=False
        if tx[0]==0xe9:
            # The staging callback can reorder a burst. Verify every emitted record
            # against one remaining independent planner record, including slot and mask.
            plans=self.plansets[self.generation]
            body=tx[4:-4]
            offset=0
            for pos in range(self.plan_at,min(len(plans),self.plan_at+tx[3])):
                index=next((j for j in range(pos,len(plans)) if body.startswith(joint.wire_plan(plans[j]),offset)),None)
                assert index is not None,(self.generation,pos,body[offset:].hex())
                plans.insert(pos,plans.pop(index))
                offset+=len(joint.wire_plan(plans[pos]))
            for q in plans[self.plan_at:self.plan_at+tx[3]]:
                k=q[6]
                if k<2:
                    self.pending.extend((k,addr) for j,addr in lanes(q))
        return super().accept(tx,t)
    def next_rom(self,t):
        k,addr=self.pending.popleft()
        if k==0:
            if self.tag==addr//16 and (addr&15) in self.line:return t+1
        else:
            tag=addr//16
            use_fold=self.a.mode=="fold" and self.generation>=907
            index=(tag^(tag>>7) if use_fold else tag)&127
            row=(self.folded if use_fold else self.cache)[str(self.generation)].get(str(index))
            if row and row[0]==addr//16 and str(addr%16) in row[1]:return t+8
        request=t+(1 if not k else 8)
        grant,response=self.calendar.select(request-self.a.rom_phase)
        # Ideal supply bound: preserve transfer latency and payload; remove grant wait only.
        wait=grant+self.a.rom_phase-request
        if k==0:
            self.tag=addr//16
            self.line={addr&15,addr%16^8}
        if self.a.mode=="supply" and self.generation>=907:
            response-=wait
        return response+self.a.rom_phase
    def publish(self):
        super().publish()
        d=self.jobs[-1]
        # A descriptor publishes on a non-contiguous next tile or decoded END.
        # Bound availability by the event clock that caused the publication and
        # the first joint clock at which the port model exposes it.
        self.fp.write(json.dumps(dict(generation=self.generation,token=d["token"],kind=d["kind"],bytes=len(d["data"]),
            producer=max(self.producer_clock,self.flight[2] if self.flight else self.boundary_clock),observed=self.now))+"\n")
    def advance(self,now):
        self.now=now
        return super().advance(now)

def main(source,group,mode,phase,temp,*,arm=None,link_class=GameLink,client=None,client_hash=None,adapt_template=None,packet_source=None,driver_extra_us=None):
    data=source/group
    start=7288416+(phase-1)*178684
    a=SimpleNamespace(arm=arm or WORK/"link820b/src",data=data,fixture=data,plans=data,
        client=client or WORK.parent/"nes-output815/client",adapt_template=adapt_template,mesen=temp/"nes-bonus698-mesen/Mesen.exe",
        out=temp/f"nes-tile821-{group}-{mode}-p{phase}-{sys.argv[6]}",mode=mode,rom_phase=0,
        start=start,cpi=2,candidate=True,frames=len(json.loads((data/"work.json").read_text())),
        calendar=temp/"nes-service509-rom03",trace_credit=True,capture_gate=True,early_export=True,commit_pop_bound=True,
        spi_us=0,rom_stride=48,driver503=None,template=temp/"nes-output809-mmc816-p1/capture.lua")
    assert sha(a.template).lower()=="7b4d48ae2bdb36f065b910dca7d8c379746126492a449a995e591e4b1d47445e"
    work=json.loads((data/"work.json").read_bytes())
    a.generations=[w["g"] for w in work]
    assert a.generations==sorted(set(a.generations)) and a.generations[0]==905
    a.next_generation=dict(zip(a.generations,a.generations[1:]))
    a.blank_frames_after={w["g"]:z["source_frame"]-w["source_frame"]-1 for w,z in zip(work,work[1:])
                          if z["g"]>w["g"]+1}
    assert sha(a.client/"sink165.sfc").lower()==(client_hash or "3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1")
    log=Path(sys.argv[7]) if len(sys.argv)>7 else Path.home()/"Downloads/nes-budget-mmc820.txt"
    if driver_extra_us is None:
        budget=dict(l.strip().split("=",1) for l in log.read_text().splitlines() if "=" in l)
    def setup(original):
        def init(self,args,link):
            original(self,args,link)
            self.link.cpu=self
            for i,op in enumerate((0xd0,0xd1,0xd2,0xd3,0xe0,0xe1,0xe8,0xe9,0xea)):
                if driver_extra_us is not None:
                    self.driver_extra[op]=driver_extra_us[hex(op)]*joint.MASTER/1e6
                    continue
                calls,n,hi,lo,_=map(int,budget[f"cost_op_{i:02}"].split(","))
                self.driver_extra[op]=max(0,((hi*2**32+lo)/84000000-n*8/2625000)/calls)*joint.MASTER
            self.link.e8_extra=self.driver_extra[0xe8]
        return init
    def encode(geo,raw,g):
        if packet_source is not None:
            return [bytes.fromhex(r["wire"]) for r in packet_source[str(g)]],None,None
        return [bytes.fromhex(x) for x in json.loads((data/f"frame{g}/packets.json").read_text())],None,None
    with patch.object(joint,"encode",encode),patch.object(joint,"Link",link_class),patch.object(joint.Runtime,"linked_runtime_storage",True,create=True),patch.object(joint.Runtime,"__init__",setup(joint.Runtime.__init__)):
        joint.run(a)

if __name__=="__main__":
    main(Path(sys.argv[1]).resolve(),sys.argv[2],sys.argv[3],int(sys.argv[4]),Path(sys.argv[5]).resolve())
