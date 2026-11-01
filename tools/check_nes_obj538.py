# SPDX-License-Identifier: MIT
"""Check the new eighth-record boundary in the linked M4 and fail closed on a fault."""
import argparse
import json
from pathlib import Path

from check_nes_order520 import ARM, Endpoint, exercise, record, wire_plan
from prepare_nes_obj538 import expected


def check(src):
    lead=[record(2,0,0),record(0,1,1)]
    obj=[record(1,32-i,i) for i in range(16)]
    prefix=[record(0,2,2),record(0,3,3)]
    cases={}
    for name,tail,counts in [('mixed',prefix+obj,[2,8,11]),('OBJ_only',obj,[2,15,2]),
                             ('BG_to_first_OBJ',[record(0,i,i) for i in range(2,10)]+obj[:1],[2,8,2]),
                             ('END_at_eight',prefix+obj[:6],[2,9]),
                             ('full_barrier',prefix+obj[:6]+[record(1,8,8,True)],[2,10])]:
        records=lead+tail
        packets=exercise(src,records)
        sizes=[p[3] for p in packets]
        assert sizes==counts,(name,sizes)
        ordered=expected([[0,r.hex()] for r in records])
        assert b''.join(p[4:-4] for p in packets)==b''.join(wire_plan(bytes.fromhex(q)) for _,q in ordered)+wire_plan(record(3,0,0))
        cases[name]=sizes
    for fault in ('STOP_after_E9','corrupt_E8'):
        class Fault(Endpoint):
            def exchange(self,tx,clock):
                reply=super().exchange(tx,clock)
                if self.mode=='corrupt_E8' and tx[0]==0xe8:
                    return reply[:-1]+bytes([reply[-1]^1])
                return reply
        m=ARM(src,'normal')
        m.endpoint=Fault()
        m.setup()
        def emit(q):
            m.u.mem_write(m.q,q)
            return m.call('nes_plan200_emit',[m.p,m.q])
        assert all(emit(q) for q in lead+prefix+obj[:6])
        m.endpoint.mode=fault
        assert not emit(obj[6]) and not m.call('nes_plan200_end',[m.p])
        assert m.endpoint.accepted==1 and not m.endpoint.rearmed
        cases[fault]=m.endpoint.accepted
    return cases


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.arm),indent=2)+'\n')
