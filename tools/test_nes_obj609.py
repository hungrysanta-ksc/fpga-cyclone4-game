"""Replay a generation-owned OBJ capture bank on the 608 palette-only schedule."""
import argparse
from collections import deque
import json
from pathlib import Path
import runpy
import struct
import sys
from unittest.mock import patch

from check_nes_wire600 import ROOT, pin, read
from test_nes_service509_schedule import TraceLink
from trace_nes_obj518 import ObjLink


def capture(fixture):
    pin(fixture,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
    frames={}; generation=904
    with fixture.open() as stream:
        for line in stream:
            op,kind,address,value,_=line.split()
            if op=='0':
                generation+=1
                lines=frames[generation]={}
            elif op=='1' and kind=='1':
                addr=int(address,16);tag=addr//16;index=tag%128
                if index not in lines or lines[index][0]!=tag:
                    lines[index]=(tag,{})
                lines[index][1][addr%16]=int(value,16)
    assert list(frames)==list(range(905,958))
    return frames


def lanes(q):
    for j in range(16):
        if q[7]>>(j//2)&1:
            tag=int.from_bytes(q[4:6],'little')
            alt=struct.unpack_from('<H',q,24+2*(j//2))[0]
            if j%2==0 and alt!=65535:tag=alt
            yield j,16*tag+8*(j%2)+q[8+j]


if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--samples',required=True,type=Path)
    p.add_argument('--bg-dispatch-clocks',type=int,choices=(0,1),default=0)
    args,rest=p.parse_known_args()
    sys.argv[1:]=rest
    frames=capture(args.samples)
    pending=deque()
    accept=ObjLink.accept
    qualified=TraceLink.next_rom

    def enqueue(link,tx,t):
        if tx[0]==0xe9:
            for q in link.plansets[link.generation][link.plan_at:link.plan_at+tx[3]]:
                if q[6]!=1:continue
                g,slot=struct.unpack_from('<HH',q)
                assert g==link.generation
                tile=link.tilebytes[g,1,32*slot]
                pending.extend((g,slot,address,tile[j]) for j,address in lanes(q))
        if tx[0]==0xea:assert not pending
        return accept(link,tx,t)

    def supply(link,t):
        # ObjLink consumed the request owner immediately before this callback.
        # BG passes through without a cache penalty, OBJ pays two PPU dots even on a miss.
        if not link.obj_request609:return qualified(link,t)
        g,slot,addr,expected=pending.popleft()
        assert g==link.generation
        line=frames[g].get((addr//16)%128)
        hit=line is not None and line[0]==addr//16 and addr%16 in line[1]
        ready=t+8
        if hit:
            assert line[1][addr%16]==expected
            link.allocations.append(dict(requested=t,grant=t,response=ready))
            response=ready
        else:
            response=qualified(link,ready)
        link.phases[g].setdefault('OBJ609',[]).append([slot,addr,t,response,int(hit)])
        return response

    actual=ObjLink.next_rom
    def owner(link,t):
        g,kind=link.owners[0]
        link.obj_request609=kind==1
        if kind==0 and args.bg_dispatch_clocks:
            if link.phases[g].get('first_BG561')==t:
                link.phases[g]['first_BG561']=t+args.bg_dispatch_clocks
            t+=args.bg_dispatch_clocks
        return actual(link,t)

    with patch.object(ObjLink,'accept',enqueue),patch.object(ObjLink,'next_rom',owner),patch.object(TraceLink,'next_rom',supply):
        runpy.run_module('test_nes_quiet608',run_name='__main__')
