"""Boot the same consumer and full ARM link for opening and demo comparisons."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from nes_window837 import BASE, LAST, OUT, PROBES
from nes_raw506 import once, sha
from analyze_nes_map830 import window
from replay_nes_section832 import run
from replay_nes_charge836 import trace
from replay_nes_output822 import MirrorLink
from replay_nes_repeat833 import replay
from replay_nes_tile821 import main


def reject(a,client,arm,tag):
    label=json.loads((client/"labels.json").read_bytes())
    fault=a.fault
    def inject(s):
        hook=""
        # One positive register read only. A second status read observes
        # normal operation, even though the CPU must retain the first STOP.
        if fault=="pulse":
            hook=f"""local armed837=false
local sent837=false
checkedMem527(function()
 if packet and pb(0)==3 and pw(8)==909 and not sent837 then armed837=true end
end,emu.callbackType.exec,{label["test837"]})
"""
            s=once(s," if a==0x6001 then",""" if a==0x6001 then
  if armed837 then
   armed837=false;sent837=true
   local f=assert(io.open(ROOT..'/stop837.txt','w'));f:write(emu.getState().masterClock);f:close()
   return 128
  end""")
        else:
            hook=f"""checkedMem527(function()
 if packet and pb(0)==3 and pw(8)==909 then emu.write(0x1320+word(0x1254),0,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{label["coverage212"]})
"""
        s=once(s,"local MODE='normal'",f"local MODE='837{fault}'")
        s=once(s,"local FAULT=905","local FAULT=909")
        return once(s,"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")
    folder=a.temp/f"nes-tile821-demoB-jointmirror-p{a.phase}-{tag}"
    try:
        run(a.arm,a.phase,a.temp,a.budget,arm=arm,client=client,tag=tag,adapt=inject)
    except (AssertionError,BrokenPipeError):
        rows=window(folder)
        assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,909))
        assert [(r["g"],r["op"],r["value"]) for r in rows if r["event"]=="ack" and r["value"]>=224]==[(909,3,228 if fault=="pulse" else 224)]
        if fault=="pulse":
            stop=int((folder/"stop837.txt").read_text())
            assert not any(r["event"] in ("ppu_dma","ppu_last") and r["clock"]>=stop for r in rows)
    else:
        raise AssertionError("injected fault was accepted")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("phase", type=int, choices=(1,2))
    parser.add_argument("temp", type=Path)
    parser.add_argument("budget", type=Path)
    parser.add_argument("--arm", choices=("split","palette","prefix","shared","seal"), default="palette")
    parser.add_argument("--receiver",choices=("bank","client-sticky"),default="client-sticky")
    parser.add_argument("--opening",action="store_true")
    parser.add_argument("--fault",choices=("pulse","coverage","damage"))
    a=parser.parse_args()
    client=LAST/"final-bank" if a.receiver=="bank" else OUT/a.receiver
    arm=BASE if a.arm=="split" else PROBES/("nes-output823/link-837"+a.arm)
    tag="837"+a.receiver+a.arm+(a.fault or "")
    if a.fault in ("pulse","coverage"):
        reject(a,client,arm,tag)
        raise SystemExit
    if a.opening:
        with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]):
            main(PROBES/"nes-tile821/extra01","earlyB","jointmirror",a.phase,a.temp,
                 arm=arm/"src",link_class=MirrorLink,client=client,client_hash=sha(client/"sink165.sfc"))
    else:
        replay(a.arm,a.phase,a.temp,a.budget,tag=tag,client=client,arm=arm,fault=a.fault,extra_trace=trace(client,False))
