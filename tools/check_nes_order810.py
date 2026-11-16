"""Exercise early prefix publication and failed publication on each linked ARM."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_game478 import Machine, encode, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from check_nes_reuse635_arm import Sender
from check_nes_receive682 import Burst
from check_nes_credit752 import Handoff
from check_nes_idle676 import caller


class PrefixReceiver(Sender):
    def hook(self, cpu, address, size, user):
        if address == self.callback and len(self.heads) == self.reject_at:
            cpu.reg_write(UC_ARM_REG_R0, 0)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        super().hook(cpu, address, size, user)


def case(src, scenario):
    m = PrefixReceiver(src, "normal")
    m.heads = []
    m.reject_at = {"first_error": 0, "padding_error": 1}.get(scenario, -1)
    sink, plan = 0x20015800, 0x20016300
    for key, value, width in (("serial", 5, 4), ("generation", 959, 2), ("state", 1, 1),
                              ("plan", plan, 4), ("enqueue", m.callback | 1, 4),
                              ("exchange", m.callback | 1, 4), ("ack635", 3 | (4 << 32), 8)):
        m.put(sink, "nes_native_sink165", key, value, width)
    m.put(plan, "nes_plan200", "bank_history", 0 if scenario == "cold" else 2, 1)
    m.put(m.video, "nes_native_video165", "patch_count", int(scenario != "no_patch"), 1)
    size = {"unfinished": 0, "even": 16, "large": 241}.get(scenario, 21)
    m.put(m.video, "nes_native_video165", "hdma_size", size, 2)
    scroll = bytes(range(21))
    m.u.mem_write(m.video + m.layout["nes_native_video165"]["hdma"], scroll)
    high_mask = 0x7ffff if scenario == "long_map" else 0
    ok = m.call("nes_scroll810", [sink, m.video, 0, high_mask])
    accepted = scenario == "normal"
    assert bool(ok) == (m.reject_at < 0)
    assert m.get(m.video, "nes_native_video165", "scroll_issued", 1) == accepted
    assert len(m.heads) == (2 if accepted else int(scenario == "padding_error"))
    assert m.get(sink, "nes_native_sink165", "ack635", 8) == 3 | (4 << 32)
    if m.heads:
        assert m.heads[0][:2] == bytes((2,5)) and m.heads[0][16:] == scroll
    if accepted:
        pad = m.heads[1]
        assert pad[:2] == bytes((5,5)) and pad[10:] == bytes.fromhex("150002004c040000")
    return dict(case=scenario,success=bool(ok),packets=len(m.heads),prefix_published=accepted)


def input_borrow(src, policy):
    rows = []
    cases=["normal", "empty_after3", "CRC_third", "STOP_after3", "cache_token"]
    if policy=="object":
        cases.extend(("two_bg","small_obj"))
        sink_layout=Handoff(src,"normal").layout["nes_native_sink165"]
    for mode in cases:
        m=Burst(src,"normal" if mode in ("two_bg","small_obj") else mode)
        if policy=="object":
            sink=m.rt+m.layout["nes_native_runtime165"]["sink"]
            m.layout["nes_native_sink165"]=sink_layout
            m.put(sink,"nes_native_sink165","bg_next",2 if mode=="two_bg" else 1,2)
            m.put(sink,"nes_native_sink165","obj_next",7 if mode=="small_obj" else 8,2)
        if mode!="empty_after3":
            m.packets.extend(struct.pack(">HHH",i,953,i) for i in range(7,12))
        ok = m.call("wait634",[m.rt,m.check|1,3,0])
        assert bool(ok)==(mode in ("normal","empty_after3","two_bg","small_obj"))
        first=m.index
        if mode=="normal":
            assert first==(7 if policy=="idle" else 11),(policy,first)
            if policy=="idle":
                assert m.call("wait634",[m.rt,m.check|1,2,1]) and m.index==first
                assert m.call("wait634",[m.rt,m.check|1,2,0]) and m.index==first+1
        elif mode in ("two_bg","small_obj"):
            assert first==7
        else:
            assert first=={"empty_after3":3,"STOP_after3":3,"CRC_third":2,"cache_token":1}[mode]
        assert not set(m.ops).intersection((0xd3,0xe1,0xea)) and m.state_value()!=4
        rows.append(dict(case=mode,at_seal=first,after_status=m.index,no_commit=True))
    return rows


def unfinished_planner(src, stop):
    m=Burst(src,"normal")
    m.layout["nes_resident211"]=Handoff(src,"normal").layout["nes_resident211"]
    resident=0x20008000
    m.put(m.rt,"nes_native_runtime165","resident",resident,4)
    m.put(resident,"nes_resident211","open",1,1)
    m.put(resident,"nes_resident211","prepared",0,1)
    if stop:
        m.case="STOP_before"
    ok=m.call("wait634",[m.rt,m.check|1,4,0])
    assert bool(ok)!=stop and not m.ops and m.state_value()==4 and m.index==0
    return dict(stop=stop,receiver_still_committed=True,operations=m.ops)


def planar(src, geometry_file):
    m=Machine(src,bytes(128))
    geometry=geometry_file.read_bytes()
    rows=geometry[5740]
    assert 1<=rows<=7
    raw=bytes((i*37+i//8+i//256)&63 for i in range(256*rows))
    packets,_,_=encode(geometry,raw,959)
    packets[0]=packets[0][:4]+bytes.fromhex("2233")+packets[0][6:]
    m.frame(packets,geometry,raw,959,1)
    expected=bytearray(2048)
    for i,color in enumerate(raw):
        y,x=divmod(i,256)
        for plane in range(8):
            if (64+color)&(1<<plane):
                expected[(x//8)*64+(plane//2)*16+y*2+plane%2]|=1<<(7-x%8)
    assert m.u.mem_read(m.video,2048)==expected
    return dict(raw_rows=rows,colors=len(set(raw)),verified_bytes=len(expected))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--credit",choices=("batch","idle","object"))
    parser.add_argument("--geometry",type=Path)
    parser.add_argument("--grant-polls",type=int,choices=(24,32,56))
    args = parser.parse_args()
    scenarios = ("normal","cold","long_map","unfinished","no_patch","even","large","first_error","padding_error")
    result={"prefix":[case(args.arm,s) for s in scenarios]}
    if args.credit:
        result["receive"]=input_borrow(args.arm,args.credit)
        result["unfinished_planner"]=[unfinished_planner(args.arm,s) for s in (False,True)]
    if args.geometry:
        result["planar"]=planar(args.arm,args.geometry)
    if args.grant_polls:
        rows=[caller(args.arm,s) for s in ("under_threshold","bad_credit","STOP","bad_final")]
        assert rows[0]["drains"]==args.grant_polls+1
        rows.append(caller(args.arm,"bad_progress",fail_drain=args.grant_polls+1))
        result["map_grant"]=rows
    args.output.write_text(json.dumps(result,indent=2)+"\n",newline="\n")
