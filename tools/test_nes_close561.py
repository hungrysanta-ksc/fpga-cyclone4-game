# SPDX-License-Identifier: MIT
"""Hold a nonadjacent plan until a close marker returns through the tile mailbox."""
import math
import runpy
from unittest.mock import patch
from test_nes_banks557 import ObjLink, decode, host_after, seal, snapshot


def boundary(link,q,arrived,now):
    pending=getattr(link,'boundary561',None)
    if pending is None:
        check=decode(link,q,arrived,now)
        if check>now or q[6]==3 or not link.open:
            return check
        kind=int(q[6]==1)
        slot=int.from_bytes(q[2:4],'little')*(32 if kind else 16)
        last=link.open
        if last['kind']==kind and last['slot']+len(last['data'])==slot:
            return check
        # Source has completed its preceding tile on this model timeline.
        # Include previous tile mailbox ACK synchronization before marker launch.
        launch=max(check,math.ceil(link.producer_clock)+4)
        close=host_after(launch,8)
        ready=math.ceil(host_after(launch,10))+4
        pending=link.boundary561=dict(q=q,close=close,ready=ready,published=False)
        link.phases[link.generation].setdefault('boundaries561',[]).append(dict(
            slot=slot,kind=kind,prior_slot=last['slot'],prior_B=len(last['data']),
            check=check,launch=launch,close=close,ready=ready))
    assert q==pending['q']
    if now>=pending['close'] and not pending['published']:
        link.publish()
        pending['published']=True
    if now>=pending['ready']:
        link.boundary561=None
    return pending['ready']


if __name__=='__main__':
    base_rom=ObjLink.next_rom
    def rom(link,request):
        g,kind=link.owners[0]
        if kind==0:
            link.phases[g].setdefault('first_BG561',request)
        return base_rom(link,request)
    with patch.object(ObjLink,'next_rom',rom),patch.object(ObjLink,'seal557',seal,create=True),patch.object(ObjLink,'decode557',boundary,create=True),patch.object(ObjLink,'snapshot557',snapshot,create=True):
        runpy.run_module('test_nes_prelude554',run_name='__main__')
