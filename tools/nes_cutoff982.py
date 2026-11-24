"""Trace 911 SEAL checks and test the queue collision with a 909 tile DMA."""
import argparse
import json
import math
from pathlib import Path

from check_nes_gap981 import baseline
from check_nes_plan975 import directory, packet_path, read, replay, sha
from nes_raw506 import once


def observer(trace):
    client = baseline("returned").parent / "nes-blank960/retry"
    assert sha(client/"sink165.sfc") == sha(trace/"client.sfc")
    labels = read(client/"labels.json")
    names = ("seal", "validate181", "scroll_validate181", "scroll_end181", "table181",
             "table_end181", "coverage212", "coverage_loop212", "map_coverage212",
             "local165_entry", "upload165_entry", "wait169", "priority524", "ready524", "grant524")
    def apply(lua):
        body = """local out982=assert(io.open(ROOT..'/clocks982.csv','w'))
out982:write('event,clock,line,h,index,retired,sent\\n')
local function mark982(key)
 local s=emu.getState()
 local c=s.masterClock
 if not ((c>=14271000 and c<=14285000) or (packet and pw(8)==911 and pb(0)==3)) then return end
 out982:write(string.format('%s,%d,%d,%d,%d,%d,%d\\n',key,c,s['ppu.scanline'],s['memoryManager.hClock'],index,retired,sent))
 out982:flush()
end
"""
        for key in names:
            body += f"checkedMem527(function()mark982('{key}')end,emu.callbackType.exec,{labels[key]})\n"
        return once(lua,"checkedMem527(function()rpc()end",body+"checkedMem527(function()rpc()end")
    return apply


def run(temp, phase, mode, fault=None):
    tag = "978returned" if mode == "ref" else "981pair"
    trace = directory(temp,phase,tag,"cold")
    commands,_ = packet_path(trace,911)
    changes = []
    if mode == "defer":
        # Delay issue of token 22 only. Serialize all following transactions,
        # including E0, until the first recorded bus idle gap absorbs the delay.
        requests = [e for e in read(trace/"events.json") if e.get("event") == "SPI"]
        index = 134  # packet 135 in the one-based 65816 trace
        packet = bytes.fromhex(commands[index][3])
        assert packet[:2] == bytes((7,1)) and int.from_bytes(packet[16:20],"little")==22
        e1 = -1
        free = 0
        for e in requests:
            if e["opcode"]=="0xe1":
                e1 += 1
            start = max(free, e["start"])
            if e["opcode"]=="0xe1" and e1==index:
                start += 1800
            free = start + (e["clock"]-e["start"])
            shift = free-e["clock"]
            if shift > 0.01:
                changes.append([e["opcode"],start,free,shift])
                if e["opcode"]=="0xe1":
                    cmd=list(commands[e1])
                    assert abs(cmd[2]-e["clock"])<1
                    cmd[2]=math.ceil(free)
                    commands[e1]=tuple(cmd)
            elif changes:
                break
        assert [x[0] for x in changes]==["0xe1","0xe1","0xe0"]
    suffix = f"-{fault}" if fault else ""
    out=temp/f"nes-cutoff982-{mode}-p{phase}{suffix}"
    replay(temp,trace,out,"fixed" if changes else "control",commands,911,fault,observe=observer(trace))
    (out/"retimed982.json").write_text(json.dumps(changes))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("ref","pair","defer"))
    p.add_argument("--fault",choices=("bad_seal","stop_decode"))
    a=p.parse_args()
    run(a.temp,a.phase,a.mode,a.fault)
