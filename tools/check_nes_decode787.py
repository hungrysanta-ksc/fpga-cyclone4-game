# SPDX-License-Identifier: MIT
"""Exercise linked decoder success, truncation and semantic rejection against 786M."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from check_nes_game478 import Machine, sha

def evaluate(src):
    cpu = Machine(src, bytes(128))
    layout = cpu.layout["nes_native165"]
    data = 0x20006000
    results = {}
    for name,kind,index,count,start,value,ok in (
        ("raw10",7,0x1000,256,0,(10<<60)|0x123456789abcdef,True),
        ("raw6",7,0x10fa,256,250,(6<<60)|0x123456789,True),
        ("raw_padding",7,0x10fa,256,250,(6<<60)|(1<<36),False),
        ("raw_offset",7,0x10fa,256,249,6<<60,False),
        ("raster224",4,0x1cdf,224,0,0x73a0,True),
        ("raster_wrap",4,0x1c07,224,216,(1<<44)|0x73e0,True),
        ("raster_limit",4,0x1c08,224,216,0,False),
        ("raster_palette",4,0x1c01,224,0,2<<44,False),
        ("raster_flags",4,0x1c01,224,0,1<<49,False),
        ("rows8",1,0x1907,224,0,0x0102030405060708,True),
        ("palette3",5,0x1d02,64,61,0x12343f,True),
        ("palette_overflow",5,0x1d02,64,61,0x12403f,False),
        ("palette_padding",5,0x1d02,64,61,0x4012343f,False)):
        cpu.call("nes_native165_reset",[cpu.state])
        def put(field,v,width,index=0):
            cpu.u.mem_write(cpu.state+layout[field]+index*width,v.to_bytes(width,"little"))
        put("generation",953,2)
        put("state",1,1)
        put("next_kind",kind,1)
        put("patch_count",1,1)
        put("counts",1056,2,0)
        put("counts",64,2,5)
        if kind==7:
            put("last_tile",start,2)
        else:
            put("counts",count,2,kind)
            put("at",start,2,kind)
        packet=struct.pack(">HHQ",0xe000|index,953,value)
        cpu.u.mem_write(data,packet)
        result=cpu.call("nes_native165_packet",[cpu.state,65535,data,len(packet)])
        assert bool(result)==ok,(name,result)
        state=bytes(cpu.u.mem_read(cpu.state,layout["size"]))
        results[name]=dict(ok=bool(result),state=hashlib.sha256(state).hexdigest())
    return results


def profile953(src, sender):
    cpu=Machine(src, bytes(128))
    parts=[bytes.fromhex(row["wire"]) for row in json.loads(sender.read_bytes())["953"]]
    assert len(parts)==17 and parts[-1][:2]==bytes.fromhex("e003")
    results=[]
    for i,block in enumerate(parts[:-1]):
        addr=0x20006000
        cpu.u.mem_write(addr,block)
        start=cpu.instructions
        assert cpu.call("nes_native165_packet",[cpu.state,i,addr,len(block)])
        results.append(cpu.instructions-start)
    assert cpu.state_value()==2
    state=bytes(cpu.u.mem_read(cpu.state,cpu.layout["nes_native165"]["size"]))
    return dict(instructions=results,bytes=[len(p) for p in parts[:-1]],state=hashlib.sha256(state).hexdigest())


def sealed_budgets(src):
    from check_nes_receive682 import Burst
    from check_nes_credit752 import Handoff
    window_layout = Handoff(src, "normal").layout["nes_sink_window184"]
    results = {}
    for case in ("empty_geometry", "sealed_geometry", "sealed_raw"):
        m = Burst(src, "empty_after3" if case == "empty_geometry" else "normal")
        assert m.call("wait634", [m.rt, m.check|1, 2, 0])
        if case == "empty_geometry":
            assert m.index==3 and m.state_value()==1
            results[case] = m.get(m.rt, "nes_native_runtime165", "prefetch_left")
            continue
        assert m.index==7
        m.layout["nes_sink_window184"]=window_layout
        win=m.rt+m.layout["nes_native_runtime165"]["transport"]
        m.u.mem_write(win+window_layout["last"],bytes([3]))
        m.put(win,"nes_sink_window184","sent",11,2)
        m.put(win,"nes_sink_window184","retired",10,2)
        if case=="sealed_raw":
            m.put(m.state,"nes_native165","next_kind",7,1)
            m.put(m.state,"nes_native165","last_tile",0,2)
            m.put(m.state,"nes_native165","patch_count",1,1)
            m.packets[7:]=[struct.pack(">HHQ",0xf000+10*i,953,10<<60) for i in range(4)]
            # Setup just returned a positive D0. Refresh its length for the
            # selected raw packet, retaining its actual token and CRC.
            m.u.mem_write(m.state+m.layout["nes_native165"]["status183"],bytes(m.status()))
        else:
            m.packets.extend(struct.pack(">HHH",i,953,i) for i in (7,8,9))
        m.ops.clear()
        assert m.call("wait634",[m.rt,m.check|1,2,0]) and m.state_value()==1
        group=m.index-7
        assert group in (1,3) and m.ops==[0xd1,0xd2,0xd0]*group
        results[case]=group
    return results


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("base","src","out"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    states=evaluate(a.src)
    assert states==evaluate(a.base)
    a.out.write_text(json.dumps(dict(firmware=sha(a.src/"obj-nes-100/firmware.stm"),cases=states,budget=sealed_budgets(a.src)),indent=2)+"\n",newline="\n")
