"""Time the actual 610 ARM and 65816 with matched old/new CHR cache service."""
import argparse,json,runpy,struct,sys
from collections import deque
from unittest.mock import patch
from pathlib import Path
from test_nes_obj609 import capture,lanes
from test_nes_service509_schedule import TraceLink
from trace_nes_obj518 import ObjLink

if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--samples',type=Path,required=True)
    p.add_argument('--reference-cache',action='store_true')
    a,rest=p.parse_known_args();sys.argv[1:]=rest
    frames=capture(a.samples);pending=deque();line={};tag=None
    accept=ObjLink.accept;qualified=TraceLink.next_rom

    def enqueue(link,tx,t):
        if tx[0]==0xe9:
            for q in link.plansets[link.generation][link.plan_at:link.plan_at+tx[3]]:
                kind=q[6]
                if kind not in (0,1):continue
                g,slot=struct.unpack_from('<HH',q)
                tile=link.tilebytes[g,kind,(32 if kind else 16)*slot]
                pending.extend((g,kind,slot,addr,tile[j]) for j,addr in lanes(q))
        if tx[0]==0xea:assert not pending
        return accept(link,tx,t)

    def supply(link,t):
        global tag,line
        g,kind,slot,addr,expected=pending.popleft()
        assert g==link.generation
        hit=False;mode='ROM';delay=0
        if a.reference_cache or kind==0:
            hit=tag==addr//16 and addr%16 in line
            if hit:assert line[addr%16]==expected;mode='BG_hit' if kind==0 else 'OBJ_line_hit'
            else:
                if tag!=addr//16:tag=addr//16;line={}
                line[addr%16]=expected
            delay=1 if not a.reference_cache else 0
        else:
            row=frames[g].get((addr//16)%128)
            hit=row is not None and row[0]==addr//16 and addr%16 in row[1]
            if hit:assert row[1][addr%16]==expected;mode='OBJ_capture'
            delay=8
        if hit:
            response=t+(8 if mode=='OBJ_capture' else 1)
            link.allocations.append(dict(requested=t,grant=t,response=response))
        else:response=qualified(link,t+delay)
        grant=link.allocations[-1]['grant']
        link.phases[g].setdefault('cache611',[]).append([kind,addr,t,grant,response,mode])
        return response

    with patch.object(ObjLink,'accept',enqueue),patch.object(TraceLink,'next_rom',supply):
        runpy.run_module('test_nes_quiet608',run_name='__main__')
