"""Inject STOP after the first borrowed descriptor, or corrupt SEAL coverage."""
import argparse
import json
from pathlib import Path

from analyze_nes_map830 import window
from nes_group835 import OUT, PROBES
from nes_raw506 import once
from replay_nes_seal831 import after_display2572
from replay_nes_section832 import run


def guard(phase,temp,budget,fault):
    client=OUT/"client-warm"
    labels=json.loads((client/"labels.json").read_bytes())
    tag="835warmguard"+fault
    def adapt(s):
        s=after_display2572(s,client)
        hook="""
local armed835=false
local stopped835=false
local function seal835() return packet and pb(0)==3 and pw(8)==909 end
"""
        if fault=="stop":
            hook+=f"""
checkedMem527(function() if seal835() then armed835=true end end,emu.callbackType.exec,{labels['early835']})
checkedMem527(function() if armed835 and seal835() and not stopped835 then
 stopped835=true
 local f=assert(io.open(ROOT..'/injected835.txt','w'))
 f:write(emu.getState().masterClock);f:close()
end end,emu.callbackType.exec,{labels['service835']})
"""
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if stopped835 then return 128 end")
        else:
            hook+=f"checkedMem527(function() if seal835() then emu.write(0x1320+word(0x1254),0,emu.memType.snesWorkRam) end end,emu.callbackType.exec,{labels['coverage212']})\n"
        s=once(s,"local MODE='normal'",f"local MODE='835{fault}'")
        s=once(s,"local FAULT=905","local FAULT=909")
        return once(s,"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")
    try:
        run("progress",phase,temp,budget,True,overlay_root=OUT,tag=tag,adapt=adapt)
    except (AssertionError,BrokenPipeError):
        folder=temp/f"nes-tile821-demoB-jointmirror-p{phase}-{tag}"
        events=window(folder)
        assert [r["g"] for r in events if r["event"]=="reveal"]==list(range(905,909))
        assert [(r["g"],r["op"],r["value"]) for r in events if r["event"]=="ack" and r["value"]>=224]==[(909,3,228 if fault=="stop" else 224)]
        if fault=="stop":
            clk=int((folder/"injected835.txt").read_text())
            assert not any(r["event"] in ("ppu_dma","ppu_last") and r["clock"]>=clk for r in events)
        print("PASS",fault)
    else:
        raise AssertionError("fault was not rejected")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("fault",choices=("stop","coverage"))
    guard(**vars(p.parse_args()))
