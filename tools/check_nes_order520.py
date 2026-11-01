# SPDX-License-Identifier: MIT
"""Exercise order, duplicate slots, barriers, packet limits and faults on the linked ARM."""
import argparse
import json
import struct
from itertools import groupby
from pathlib import Path

from check_nes_dense519 import run as guard
from check_nes_supply485_arm import ARM, sha
from test_nes_bulk497_arm import Endpoint
from test_nes_raw506_joint import wire_plan


def record(kind, slot, tag, full=False):
    rows=bytearray(i//2 for i in range(16)) if kind<2 else bytearray(16)
    if full:
        rows[0]=1
    mask=(255,3,0,0)[kind]
    alt=[tag]*8 if kind==0 and full else [65535]*8
    return struct.pack("<HHHBB",907,slot,tag,kind,mask)+rows+struct.pack("<8H",*alt)


def exercise(src,records):
    m=ARM(src,"normal")
    m.endpoint=Endpoint()
    m.setup()
    for q in records:
        m.u.mem_write(m.q,q)
        assert m.call("nes_plan200_emit",[m.p,m.q])
    assert m.call("nes_plan200_end",[m.p]) and m.call("nes_plan200_progress",[m.p,1])
    assert not m.call("nes_plan200_retire",[m.p]) and not m.endpoint.rearmed
    return [bytes.fromhex(tx) for tx in m.endpoint.calls if tx.startswith("e9")]


def check(a):
    # Interleave short/full OBJ, equal destinations with distinct tags, a BG
    # record, a zero barrier, full 32-byte records and a count-limited batch.
    records=[record(2,0,0),record(0,1,1)]
    records += [record(1,s,i,full=i==3) for i,s in enumerate((7,4,4,9,3,2,127))]
    records += [record(2,0,0),record(1,0,18),record(0,2,19)]
    records += [record(0,i,i,True) for i in range(3,13)]
    records += [record(1,36-i,i) for i in range(32)]
    ref=exercise(a.baseline,records)
    new=exercise(a.candidate,records)
    assert len(ref)==len(new)
    stream=records+[record(3,0,0)]
    at=0
    reordered=0
    for before,after in zip(ref,new):
        count=before[3]
        chunk=stream[at:at+count]
        at+=count
        assert before[:4]==after[:4] and before[4:-4]==b"".join(map(wire_plan,chunk))
        ordered=[]
        for sortable,run in groupby(chunk,lambda q:q[6]==1 and (not a.compact or wire_plan(q)[0]==0x81)):
            items=list(run)
            if sortable:
                items.sort(key=lambda q:int.from_bytes(q[2:4],"little"))
            ordered.extend(items)
        assert after[4:-4]==b"".join(map(wire_plan,ordered))
        reordered+=ordered!=chunk
    assert at==len(stream) and reordered
    assert any(tx[3]==15 for tx in ref) and any(len(tx)-8==240 for tx in ref)
    for invalid in (record(1,128,1),record(1,4,8192)):
        m=ARM(a.candidate,"normal")
        m.setup()
        assert m.emit(2,0,0) and m.emit(1,3,4)
        before=bytes(m.u.mem_read(m.p+m.layout["nes_plan200"]["buffer"],248))
        calls=len(m.endpoint.calls)
        m.u.mem_write(m.q,invalid)
        assert not m.call("nes_plan200_emit",[m.p,m.q]) and len(m.endpoint.calls)==calls
        assert bytes(m.u.mem_read(m.p+m.layout["nes_plan200"]["buffer"],248))==before
        assert not m.endpoint.rearmed
    blobs={}
    for name,src in (("baseline",a.baseline),("candidate",a.candidate)):
        blob=src/"obj-nes-100/firmware.stm"
        fields=(src.parent/"size.log").read_text().splitlines()[-1].split()
        blobs[name]=dict(sha256=sha(blob),firmware_B=blob.stat().st_size,flash_free_B=0x34000-blob.stat().st_size,
                         text_B=int(fields[0]),data_B=int(fields[1]),bss_B=int(fields[2]))
    cases=[guard(a.candidate,False,mode) for mode in ("normal","bad_E8_CRC","STOP_after_E9","STOP_after_bulk",
                                                        "wrong_generation","bad_accepted","bad_ACK")]
    return dict(blobs=blobs,record_count=at,counts=[tx[3] for tx in ref],payload_lengths=[len(tx)-8 for tx in ref],
                changed_packets=reordered,invalid_slot_and_tag_preserved_buffer=True,cases=cases)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("baseline","candidate","out"):
        p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--compact",action="store_true")
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a),indent=2)+"\n",encoding="utf8",newline="\n")
