"""Two-slot lower-envelope schedule through SEAL-to-upload, excluding group setup."""
from itertools import product

from test_nes_banks557 import MASTER


def earliest(phase, permille):
    jobs=phase['jobs']
    work={j['index']:j for j in phase['service']['work']}
    queues=[[j for j in jobs[1:-1] if (j['op']==7 and group=='tile')
             or (j['op']!=7 and j['section']==group)] for group in ('tile',3,4,5)]
    assert sum(map(len,queues))+2==len(jobs)

    def step(times,j):
        bus,previous,receiver=times
        w=work[j['index']]
        selected=j.get('token',0)>=34 or (j['section']==5 and j['offset']>=1121)
        cpu=w['floor']*permille//1000 if selected else w['floor']
        # Relax admission: two packets may be stored, while another transfer
        # is on the wire. Enforce room only at the actual enqueue edge.
        wire=int(j['wire_B']*8*MASTER//2625000)
        arrive=max(max(bus,w['independent_release'])+wire,previous)
        return (arrive,receiver,max(arrive,receiver)+cpu)

    def retain(states,new):
        if any(all(a<=b for a,b in zip(old,new)) for old in states):
            return
        states[:]=[old for old in states if not all(a<=b for a,b in zip(new,old))]
        states.append(new)

    initial=(0,)*len(queues)
    states={initial:[step((0,0,0),jobs[0])]}
    for pos in product(*(range(len(q)+1) for q in queues)):
        front=states.pop(pos)
        if all(n==len(q) for n,q in zip(pos,queues)):
            return min(step(t,jobs[-1])[-1] for t in front)
        for k,(n,q) in enumerate(zip(pos,queues)):
            if n==len(q):
                continue
            nxt=pos[:k]+(n+1,)+pos[k+1:]
            target=states.setdefault(nxt,[])
            for times in front:
                retain(target,step(times,q[n]))
    raise AssertionError('missing terminal state')


def budget(phase):
    start=phase['vblank46_start']
    lo,hi=0,1000
    empty,stock=earliest(phase,lo),earliest(phase,hi)
    if empty>=start or stock<start:
        boundary=None
    else:
        while hi-lo>1:
            mid=(lo+hi)//2
            if earliest(phase,mid)<start:
                lo=mid
            else:
                hi=mid
        boundary=lo
    return dict(zero_late_clocks=empty-start,stock_late_clocks=stock-start,
                max_remaining_permille=boundary)
