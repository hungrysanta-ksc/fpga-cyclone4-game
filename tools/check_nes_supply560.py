# SPDX-License-Identifier: MIT
"""Verify exact E9 bytes and STOP on both sides of the deferred ARM flush."""
import argparse
import json
from pathlib import Path
from check_nes_supply549 import StopARM, Endpoint, record, wire_plan, sha, run


def check(src, slots, groups, stop_after=None):
    arm = StopARM(src, 'normal')
    arm.endpoint = Endpoint()
    arm.setup()
    records = [record(1, slot, 100+i) for i, slot in enumerate(slots)]
    for i, q in enumerate(records):
        if i == stop_after:
            arm.stopped = True
        arm.u.mem_write(arm.q, q)
        if not arm.call('nes_plan200_emit', [arm.p, arm.q]):
            assert arm.stopped
            break
    if stop_after == len(slots):
        arm.stopped = True
    assert bool(arm.call('nes_plan200_end', [arm.p])) == (stop_after is None)
    if stop_after is None:
        assert arm.call('nes_plan200_progress', [arm.p, 1])
    else:
        assert not arm.endpoint.rearmed
    sent = [bytes.fromhex(t) for t in arm.endpoint.calls if t.startswith('e9')]
    assert len(sent) == len(groups)
    for tx, group in zip(sent, groups):
        plans = [record(3, 0, 0) if i is None else records[i] for i in group]
        assert tx[3] == len(group) and tx[4:-4] == b''.join(map(wire_plan, plans))
    return dict(slots=slots, stop_after=stop_after, counts=[tx[3] for tx in sent])


def main(arm):
    slots = [39,40,27,41,42,43,29,44,31,45,46,34,47,48,49,50]
    ordered = sorted(range(15), key=slots.__getitem__)
    long = ordered[4:]+[15]
    rows = [check(arm, slots, [long, ordered[:4]+[None]]),
            check(arm, slots, [], 15), check(arm, slots, [long], 16),
            check(arm, slots[:15], [ordered, [None]]),
            check(arm, slots[:15]+[60], [ordered, [15,None]])]
    for cut in (1,7):
        test = list(range(cut))+list(range(50,66-cut))
        rows.append(check(arm, test, [list(range(cut,16)),list(range(cut))+[None]]))
    # Equal slots across the cut must keep both distinct tags in input order.
    rows.append(check(arm,[39,*range(39,54)], [list(range(15)),[15,None]]))
    return dict(firmware=sha(arm/'obj-nes-100/firmware.stm'), cases=rows,
                BG=[run(arm,True,k,False) for k in (1,2,3)]+[run(arm,True,2,True)])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(main(a.arm),indent=2)+'\n')
