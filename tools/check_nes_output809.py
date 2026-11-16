"""Compare the linked CRC routines with the wire oracle and run the existing guards."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import Machine, crc, sha
from check_nes_obj807 import check as obj_check
from check_nes_supply781 import check as protocol_check


def check(parent, src, edition):
    before, after = (Machine(folder, bytes(128)) for folder in (parent,src))
    samples = [bytes([b]) for b in range(256)]
    lengths = (0,2,5,6,18,32,96,240,246)
    samples.extend(bytes((37*i+91)&255 for i in range(n)) for n in lengths)
    costs = {}
    for pos,data in enumerate(samples):
        counts = []
        for m in (before, after):
            ptr = 0x20012000
            if data:
                m.u.mem_write(ptr, data)
            mark = m.instructions
            observed = m.call("nes_wire_crc807",[ptr,len(data)])
            assert observed == crc(data,8,7,0)
            counts.append(m.instructions-mark)
        if pos>=256:
            costs[len(data)] = counts
    # For any prior CRC and any next byte, both production functions first
    # XOR those two bytes. The 256 single-byte inputs cover that entire domain.
    assert costs[18][1] < costs[18][0]
    guard = protocol_check(src,False,False,trial=str(edition))
    assert guard["ACK"]["corrupt_bits"] == 152
    obj = obj_check(src,limit=0 if edition in (808,812,814) else 6000)
    assert obj["service_stop_pending"] and obj["runtime_consecutive_skips"] == 2
    result = {}
    for name,root in (("parent",parent),("candidate",src)):
        fw=root/"obj-nes-100/firmware.stm"
        result[name]=dict(bytes=fw.stat().st_size,firmware=sha(fw))
        assert fw.stat().st_size<=212992
    return dict(**result,linked_crc_inputs=len(samples),arm_instructions=costs,
                guards=guard,object_recovery=obj)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("parent",type=Path)
    p.add_argument("src",type=Path)
    p.add_argument("edition",type=int,choices=(807,808,811,812,813,814))
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.parent,a.src,a.edition),indent=2)+"\n",newline="\n")
