"""Inject faults inside the enlarged post-SEAL receive batch on the linked CPUs."""
import argparse
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

from replay_nes_tile821 import joint
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2


def check(args):
    data = args.temp / "nes-work848"
    tag = "849fault-" + args.fault
    run = args.temp / ("nes-tile821-demo-jointmirror-p1-" + tag)
    original = joint.Runtime.hook
    state = {}

    def hook(cpu,u,pc,size,user):
        if not cpu.live:
            return original(cpu,u,pc,size,user)
        if state.get("armed") and args.fault == "stop" and pc == cpu.syms["nes_cf86_check094"]:
            state["fired"] = True
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        if pc != cpu.spi:
            return original(cpu,u,pc,size,user)
        op = u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]
        rx = u.reg_read(UC_ARM_REG_R2)
        before = len(cpu.events)
        original(cpu,u,pc,size,user)
        if before == len(cpu.events):
            return
        if op == 0xd1 and cpu.input_generation == cpu.generation+1 and cpu.index == 11:
            assert next(e for e in reversed(cpu.events) if e.get("opcode")=="0xe1")["packet_opcode"] == 3
            state.update(armed=True, generation=cpu.generation, clock=cpu.clock, index=cpu.index)
            if args.fault == "crc":
                pos = rx + cpu.events[-1]["bytes"] - 1
                u.mem_write(pos,bytes([u.mem_read(pos,1)[0]^1]))
                state["fired"] = True
        if state.get("armed") and args.fault == "identity" and op == 0xe0:
            b = bytearray(u.mem_read(rx,20))
            if b[3:5] == b[5:7] and b[7:9] == bytes((1,3)):
                b[9] ^= 1
                b[19] = joint.crc(b[1:19],8,7,0)
                u.mem_write(rx,bytes(b))
                state["fired"] = True

    replay = Path(__file__).with_name("replay_nes_input848.py")
    argv = [str(replay),str(data/"demo/demo"),str(data/"sender-demo"),str(data/"hits-demo/hits.json"),
            str(args.budget),str(args.temp),"1",tag,"--arm",str(args.arm)]
    with patch.object(sys,"argv",argv), patch.object(joint.Runtime,"hook",hook):
        try:
            runpy.run_path(str(replay),run_name="__main__")
        except AssertionError as exc:
            failure = exc.args[0]
            assert state.get("fired") and failure[:2] == ("runtime fault",state["generation"]), failure
        else:
            raise AssertionError("injected fault was accepted")
    g = state["generation"]
    events = json.loads((run/"events.json").read_bytes())
    tail = [e for e in events if e.get("clock",-1) > state["clock"] and "opcode" in e]
    assert not any(e["opcode"] in ("0xea","0xd3") for e in tail)
    assert failure[2] == {"stop":2, "crc":4, "identity":5}[args.fault]
    if args.fault != "identity":
        assert not any(e["opcode"] == "0xd2" for e in tail)
    else:
        fault = json.loads((run/"fault.json").read_bytes())["transport"]
        assert bytes.fromhex(fault["bytes"])[fault["layout"]["error"]] == 8
    result = dict(case=args.fault, generation=g, input_generation=g+1, zero_based_D1=state["index"],
                  fault=failure, after_injection_EA=0, after_injection_D3=0)
    (run/"guard849.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("temp","budget","arm"):
        p.add_argument(name,type=Path)
    p.add_argument("fault",choices=("stop","crc","identity"))
    check(p.parse_args())
