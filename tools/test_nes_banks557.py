# SPDX-License-Identifier: MIT
"""Retimed host-bank admission and ordered short-plan decoding on the existing tile/ROM model."""
import math
import runpy
from unittest.mock import patch

from trace_nes_obj518 import ObjLink
from test_nes_raw506_joint import MASTER,crc,wire_plan

HOST=MASTER/84_000_000


def host_after(t,n):
    return (math.floor(t/HOST)+n)*HOST


def batches(link):
    return link.phases.setdefault(link.generation,{}).setdefault('banks557',[])


def handoff(rows,k):
    # Seal is sampled on a host edge; pending can enter the mailbox on the
    # next edge. Prior CHECK acknowledges its mailbox, across two host flops.
    prior=0 if k==0 else rows[k-1].get('release',math.inf)
    return max(host_after(rows[k]['seal'],2),host_after(prior,3) if math.isfinite(prior) else prior)


def idle(rows,t):
    return not rows or t>=handoff(rows,len(rows)-1)


def snapshot(link,tx,start):
    # Separate driver overhead is still charged by the joint harness. Place
    # the first bit of the command at start; sample at its eighth rising edge.
    sample=host_after(start+7.5*MASTER/2_625_000,3)
    link.rpc(sample)
    rows=batches(link)
    ready=idle(rows,sample) and not link.end and link.accepted<65535
    reply=bytearray(link.response(tx))
    if tx[0]==0xe8:
        reply[3]=2 if link.end else int(ready)
        reply[19]=crc(reply[1:19],8,7,0)
    else:
        assert ready,('E9 began before writable bank',link.generation,rows)
        link.e9_snapshot557=sample
    return bytes(reply)


def seal(link,tx,t):
    rows=batches(link)
    assert idle(rows,link.e9_snapshot557)
    rows.append(dict(seal=t,sample=link.e9_snapshot557,count=tx[3],first=link.plan_at))
    assert len(rows)==link.accepted+1


def decode(link,q,arrived,now):
    rows=batches(link)
    # Link.accept stored the same seal clock on every record in this burst.
    k=next(i for i in range(len(rows)-1,-1,-1) if rows[i]['seal']==arrived)
    row=rows[k]
    # Handoff may wait for a previously executing tile. Once its last
    # descriptor passed CHECK that tile no longer owns the mailbox/bank.
    box=handoff(rows,k)
    if not math.isfinite(box):return math.inf
    at=row.get('decoded',0)
    body=wire_plan(q)
    assert body[0] in (0x80,0x81,0x82,0x83),'full-form decoder timing is not calibrated'
    # WAIT consumes the mailbox after its synchronized request and capture.
    # Next descriptors instead enter READ on the preceding RUN/tile_done.
    before_read=(max(math.floor(box)+5,math.ceil(link.producer_clock)+1) if at==0
                 else math.ceil(link.producer_clock))
    check=before_read+1+2*len(body)
    if check+1>now:
        # The admission edge must be visible even when plan_ready is not yet sampled.
        if check<=now and at+1==row['count']:row['release']=check
        return check+1
    row['decoded']=at+1
    if at+1==row['count']:row['release']=check
    if at==0:row['first_check']=check
    return check+1


if __name__=='__main__':
    with patch.object(ObjLink,'seal557',seal,create=True),patch.object(ObjLink,'decode557',decode,create=True),patch.object(ObjLink,'snapshot557',snapshot,create=True):
        runpy.run_module('test_nes_prelude554',run_name='__main__')
