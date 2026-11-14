# SPDX-License-Identifier: MIT
"""Execute the linked firmware's ACK, recovery, and sealed input wait guards."""
import argparse
import json
from pathlib import Path

from check_nes_credit752 import Handoff, menu, seal_receipts, sha
from check_nes_receive682 import Burst, burst


def sealed_wait(src, case):
    m=Burst(src, "normal")
    assert m.call("wait634",[m.rt,m.check|1,2,0]) and m.index==7
    m.layout["nes_sink_window184"]=Handoff(src,"normal").layout["nes_sink_window184"]
    window=m.rt+m.layout["nes_native_runtime165"]["transport"]
    # The first seven READ/POP pairs left the receiver in RECEIVING. Leave
    # one additional valid block, keeping the same incrementing token chain.
    assert len(m.packets)==8 and m.get(m.state,"nes_native165","ready183")==1
    m.u.mem_write(window+m.layout["nes_sink_window184"]["last"], bytes([2 if case=="ordinary" else 3]))
    m.put(window,"nes_sink_window184","sent",11,2)
    m.put(window,"nes_sink_window184","retired",11 if case=="returned" else 10,2)
    if case=="STOP":
        m.case="STOP_before"
    m.ops.clear()
    ok=m.call("wait634",[m.rt,m.check|1,2,int(case=="progress")])
    assert bool(ok)==(case!="STOP")
    assert m.index==7+int(case=="waiting"),(case,m.index,m.ops)
    assert m.ops==([0xd1,0xd2,0xd0] if case=="waiting" else []),(case,m.ops)
    assert m.state_value()!=4
    return dict(case=case,success=bool(ok),extra=m.index-7,operations=m.ops)


def owned_wait(src, stop):
    m=Burst(src, "normal")
    r=0x20008000
    # The compiled resident layout varies by candidate; read it from DWARF.
    from elftools.elf.elffile import ELFFile
    from test_nes_raw506_joint import member_offset
    with (src/"obj-nes-100/sd2snes.elf").open("rb") as f:
        structures=(d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
                    if d.tag=="DW_TAG_structure_type" and "DW_AT_byte_size" in d.attributes and
                    "DW_AT_name" in d.attributes and d.attributes["DW_AT_name"].value==b"nes_resident211")
        m.layout["nes_resident211"]={c.attributes["DW_AT_name"].value.decode():member_offset(c)
                                     for c in next(structures).iter_children() if c.tag=="DW_TAG_member"}
    m.put(m.rt,"nes_native_runtime165","resident",r,4)
    m.put(r,"nes_resident211","tile_boundary",1,4)
    m.put(r,"nes_resident211","prepared",0,1)
    if stop:
        m.case="STOP_before"
    ok=m.call("wait634",[m.rt,m.check|1,4,0])
    assert bool(ok)==(not stop) and not m.ops and m.state_value()==4
    return dict(stop=stop,success=bool(ok),operations=m.ops,remains_committed=True)


def check(src, extra, owner):
    result=dict(firmware=sha(src/"obj-nes-100/firmware.stm"),menu=menu(src,"763"),
                ACK=seal_receipts(src),
                input=[burst(src,c) for c in ("STOP_after3","CRC_third","cache_token")])
    if owner:
        result["owned"]=[owned_wait(src,s) for s in (False,True)]
    if extra:
        result["sealed"]=[sealed_wait(src,c) for c in ("waiting","progress","returned","ordinary","STOP")]
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("arm",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--refill",action="store_true")
    p.add_argument("--owner",action="store_true")
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.arm,a.refill,a.owner),indent=2)+"\n",newline="\n")
