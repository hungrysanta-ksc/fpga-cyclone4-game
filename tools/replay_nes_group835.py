"""Run the map publication and bounded tile group changes independently."""
import argparse
import json
from pathlib import Path

from nes_group835 import BASE, OUT
from nes_tail834 import OUT as OLD, PROBES
from replay_nes_repeat833 import replay
from replay_nes_tail834 import watch
from nes_raw506 import once


def trace_group(client):
    labels=json.loads((client/"labels.json").read_bytes())
    def inject(s):
        hooks="local groupLog835=assert(io.open(ROOT..'/group835.txt','w'))\n"
        for label in ("borrow835","early835","service835"):
            hooks+=f"""checkedMem527(function() if packet and pb(0)==3 and pw(8)==909 then
 groupLog835:write(string.format('%d {label} %d %d %d %d %d\\n',emu.getState().masterClock,
 word(0x125c),word(0x1240),word(0x1252),word(0x1250),word(0x103a)));groupLog835:flush()
 end end,emu.callbackType.exec,{labels[label]})
"""
        return once(s,"checkedMem527(function()rpc()end",hooks+"checkedMem527(function()rpc()end")
    return inject


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("bgdirty", "once", "progress"))
    p.add_argument("phase", type=int, choices=(1, 2))
    p.add_argument("temp", type=Path)
    p.add_argument("budget", type=Path)
    p.add_argument("--group", action="store_true")
    p.add_argument("--warm", action="store_true")
    p.add_argument("--fixed", action="store_true")
    a = p.parse_args()
    original = a.mode == "bgdirty"
    kind = "warm" if a.warm else ("group" if a.group else "inspect")
    tag = "835"+a.mode+kind+("fixed" if a.fixed else "")
    client=(OLD if kind=="inspect" else OUT)/("client-"+kind)
    replay(a.mode, a.phase, a.temp, a.budget, a.fixed, tag=tag,
           client=client,extra_trace=trace_group(client) if kind=="warm" else None,
           arm=BASE if original else PROBES/("nes-output823/link-835"+a.mode),
           overlay_root=OLD if original else OUT, on_attach=watch)
