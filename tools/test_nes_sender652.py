"""Gate the real ARM's D0 sample by measured 84 MHz sender RAM ownership."""
import argparse
import json
import runpy
import sys
from pathlib import Path
from unittest.mock import patch
import test_nes_raw506_joint as joint
from test_nes_banks557 import MASTER
from check_nes_game478 import crc


def gates(rows,board_owner):
    begin=joint.Runtime.begin_input
    status=joint.Runtime.status
    def load(cpu,generation=None):
        start=cpu.clock
        begin(cpu,generation)
        g=cpu.input_generation
        if str(g) not in rows:return
        packets=[bytes.fromhex(r["wire"]) for r in rows[str(g)]]
        assert cpu.packets==packets
        cpu.packets=packets
        cpu.start652=max(start,cpu.source_ready)
        if board_owner and g>905:
            # The FPGA starts from the owned capture, closed preceding plan
            # and drained ROM reader, even while the ARM serves other work.
            # Use a positive E8 observation as a conservative close witness.
            closed=next(e["clock"] for e in cpu.events if e["generation"]==g-1
                        and e.get("opcode")=="0xe8" and bytes.fromhex(e["reply"])[3]==2)
            service=cpu.link.phases[g-1].get("cache611",[])
            drained=max((r[4] for r in service),default=closed)
            cpu.start652=max(cpu.source_ready,closed,drained+4)
            assert cpu.start652<=max(cpu.source_ready,cpu.clock)
        cpu.key652=None
    def checked(cpu):
        result=bytearray(status(cpu))
        if not cpu.live or str(cpu.input_generation) not in rows or cpu.index>=len(cpu.packets):return bytes(result)
        if not result[2]&1:return bytes(result)
        key=(cpu.input_generation,cpu.index)
        if cpu.key652!=key:
            if cpu.index:
                # D3 releases the last COMMIT record. Every other new head
                # starts after D2's SS rise, not at the later ARM callback.
                op="0xd3" if cpu.index==len(cpu.packets)-1 else "0xd2"
                e=next(r for r in reversed(cpu.events) if r.get("opcode")==op and r.get("input_generation")==cpu.input_generation)
                origin=e["start"]+8*8*MASTER/2625000+3*MASTER/84000000
            else:origin=cpu.start652
            ticks=rows[str(cpu.input_generation)][cpu.index]["ready_cycles"]
            assert ticks>0
            cpu.deadline652=origin+ticks*MASTER/84000000
            cpu.events.append(dict(event="sender652_ready",generation=cpu.generation,input_generation=cpu.input_generation,index=cpu.index,origin=origin,ready=cpu.deadline652))
            cpu.key652=key
        if cpu.clock+7.5*MASTER/2625000<cpu.deadline652:
            cpu.events.append(dict(event="sender652_busy",generation=cpu.generation,
                                   input_generation=cpu.input_generation,index=cpu.index,clock=cpu.clock))
            result[2]&=254
            result[5:7]=b"\0\0"
            result[7]=crc(result[1:7],8,7,0)
        return bytes(result)
    return patch.multiple(joint.Runtime,begin_input=load,status=checked)


if __name__=="__main__":
    p=argparse.ArgumentParser(add_help=False);p.add_argument("--sender652",type=Path)
    p.add_argument("--board-owner",action="store_true")
    a,rest=p.parse_known_args();sys.argv[1:]=rest
    if a.sender652:
        with gates(json.loads(a.sender652.read_text()),a.board_owner):runpy.run_module("test_nes_geometry650",run_name="__main__")
    else:runpy.run_module("test_nes_geometry650",run_name="__main__")
