"""Replay the two receiver changes against the same ARM map-progress link."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch
from nes_charge836 import LIVE, OUT, PROBES, BASE
from nes_raw506 import once
from replay_nes_repeat833 import replay
from replay_nes_tail834 import watch
from check_nes_group835 import guard
from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import main as replay_clip
from nes_raw506 import sha


def trace(client,fixed):
    labels=json.loads((client/"labels.json").read_bytes())
    def instrument(s):
        hook="local trace836=assert(io.open(ROOT..'/charge836.txt','w'))\n"
        for key in ("borrow835","charge836","early835","raw_dma489","raw836","prepare547","expand833","done833","wait_final516"):
            if key not in labels:continue
            hook+=f"""checkedMem527(function()
 if packet and pw(8)==909 then
 local cursor,finish=word(0x1252),word(0x1250)
 local sum=0
 if pb(0)==3 then for i=cursor,finish-1,8 do sum=sum+word(0x4004+i) end end
 trace836:write(string.format('%d {key} %d %d %d %d %d %d\\n',emu.getState().masterClock,
 cursor,finish,word({LIVE}),sum,word(0x78),pb(0)));trace836:flush()
 end end,emu.callbackType.exec,{labels[key]})
"""
        if "read836" in labels:
            hook+=f"""checkedMem527(function()
 assert(regs[0x4300]==1 and regs[0x4301]==0x18 and regs[0x4304]==0x7f,'raw channel ownership')
 end,emu.callbackType.exec,{labels['raw836']})
"""
        if "charge836" in labels:
            hook+=f"""local totals836=assert(io.open(ROOT..'/totals836.txt','w'))
checkedMem527(function() if packet and pb(0)==3 and pw(8)>={909 if fixed else 905} then
 local total=0
 for i=word(0x1252),word(0x1250)-1,8 do total=total+word(0x4004+i) end
 assert(total==word({LIVE}),'live descriptors differ from incremental bytes')
 totals836:write(string.format('%d %d %d\\n',pw(8),total,word(0x1250)-word(0x1252)));totals836:flush()
 end end,emu.callbackType.exec,{labels['prepare547']})
"""
        return once(s,"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")
    return instrument


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("charge","raw","both","bank","control"))
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("--fixed",action="store_true")
    p.add_argument("--opening",action="store_true")
    p.add_argument("--arm",choices=("progress","direct","early","split"),default="progress")
    p.add_argument("--fault",choices=("stop","coverage","damage"))
    a=p.parse_args()
    client=BASE/"client-warm" if a.mode=="control" else OUT/("final-"+a.mode)
    inherited=a.arm=="progress"
    tag="836v2"+a.mode+("" if inherited else a.arm)+("fixed" if a.fixed else "")
    if a.opening:
        assert not a.fixed and not a.fault and a.arm=="split" and a.mode=="bank"
        with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]):
            replay_clip(PROBES/"nes-tile821/extra01","earlyB","jointmirror",a.phase,a.temp,
                        arm=PROBES/"nes-output823/link-836split/src",link_class=MirrorLink,
                        client=client,client_hash=sha(client/"sink165.sfc"))
        raise SystemExit
    if a.fault in ("stop","coverage"):
        assert a.fixed and a.mode in ("both","bank")
        guard(a.phase,a.temp,a.budget,a.fault,client=client,tag_prefix=tag+"guard",mode=a.arm,
              overlays=BASE if inherited else OUT,raw_row=True)
        raise SystemExit
    replay(a.arm,a.phase,a.temp,a.budget,a.fixed,fault=a.fault,tag=tag+(a.fault or ""),
           client=client,extra_trace=trace(client,a.fixed),arm=PROBES/("nes-output823/link-"+("835" if inherited else "836")+a.arm),
           overlay_root=BASE if inherited else OUT,on_attach=watch)
