"""Replay production map828 endpoints. Extend the independent DMA receipt monitor only."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

from nes_raw506 import once
from prepare_nes_map828 import PROBES, OUT
from replay_nes_tile821 import main
from replay_nes_output822 import MirrorLink

CLIENT_HASH = "abef2831efa5919cb3d31b1d81a0bc154e32c94be13a144d76190b5528f75f21"
FAST_HASH = "09bfaa014a8541ac72608c2c14df4adc70cd206a452d3065ef6fd3ec61e56440"
def monitor(s, fault, client, seed=None):
    if seed:
        assert seed.stat().st_size==8192
        load=f"""
local seed828=assert(io.open({json.dumps(seed.as_posix())},'rb'))
local mem828=seed828:read('*a');seed828:close()
for bank=0,1 do for i=0,4095 do
 emu.write(0x15000+bank*32768+i,mem828:byte(bank*4096+i+1),emu.memType.snesWorkRam)
end end
"""
        s=once(s,"local reads,token",load+"local reads,token")
    if fault:
        s=once(s,"local MODE='normal'","local MODE='map828"+fault+"'")
        s=once(s,"local FAULT=905","local FAULT=909")
        save="""
  if rejected then
   assert(word(0x1248)==4 and word(0x124a)==0,'canceled identity published')
   local mem=assert(io.open(ROOT..'/canceled-map.bin','wb'))
   for bank=0,1 do for i=0,4095 do mem:write(string.char(rd(0x15000+bank*32768+i))) end end;mem:close()
  end
"""
        s=once(s,"  assert(captured==commits)",save+"  assert(captured==commits)")
    labels=json.loads((client/"labels.json").read_bytes())
    # Poison only the inactive packet destination before its first write. Host
    # memory callbacks have no emulated CPU cost and cannot restore bytes.
    hooks="""
local injected828=false
local stop828=false
local trace828=assert(io.open(ROOT..'/codec828.csv','w'))
local function codec828(name)
 trace828:write(string.format('%d,%d,%d,%s,%d\\n',pw(8),pw(10),pw(12),name,emu.getState().masterClock));trace828:flush()
end
checkedMem527(function()
 codec828('begin')
 local dst=0x10000+word(0x7a)
 for i=0,pw(12)/18*64-1 do emu.write(dst+i,0xa5,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,RESTORE)
checkedMem527(function()
 if packet and pb(0)==9 and pb(1)==2 then codec828('verified') end
end,emu.callbackType.exec,ACCEPTED)
"""
    if fault:
        assert fault in ("damage","stop")
        hooks += """
checkedMem527(function()
 if not injected828 and pw(8)==909 then
  injected828=true;codec828('injected')
  ACTION
 end
end,emu.callbackType.exec,CHECK)
"""
        hooks=hooks.replace("ACTION","emu.write(0x10000+word(0x7a)+63,0x81,emu.memType.snesWorkRam)" if fault=="damage" else "stop828=true")
        s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if stop828 then return 128 end")
    for name,label in (("RESTORE","restore828"),("ACCEPTED","accepted"),("CHECK","check_tail828")):
        hooks=hooks.replace(name,str(labels[label]))
    anchor="checkedMem527(function()rpc()end"
    s=once(s,anchor,hooks+anchor)
    s = once(s,"(pb(0)==2 or pb(0)==4) then","(pb(0)==2 or pb(0)==4 or pb(0)==9) then")
    return once(s,"local n=pb(0)==2 and pw(12) or pw(14)",
        "local n=pb(0)==9 and (pw(12)/18)*64 or pb(0)==2 and pw(12) or pw(14)")

def run(a):
    src={"demoB":"demo-extra01","earlyB":"extra01","late":"data02","demoD":"demo-extra01"}
    data=PROBES/"nes-trial825/data" if a.group=="change" else PROBES/"nes-tile821"/src[a.group]
    lookup=a.temp/"nes-demo825-cache/hits.json" if a.group=="change" else MirrorLink.lookup_file
    client=OUT/("client-fast" if a.fast else "client-b")
    with patch.object(sys,"argv",["replay","","","","","",a.tag,str(a.budget)]), patch.object(MirrorLink,"lookup_file",lookup):
        main(data,a.group,"jointmirror",a.phase,a.temp,arm=OUT/a.link/"src",client=client,
             client_hash=FAST_HASH if a.fast else CLIENT_HASH,link_class=MirrorLink,adapt_template=lambda s:monitor(s,a.fault,client,a.seed))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("group");p.add_argument("phase",type=int);p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path);p.add_argument("--tag",default="828b");p.add_argument("--link",default="link-c")
    p.add_argument("--fault",choices=("stop","damage"))
    p.add_argument("--fast",action="store_true")
    p.add_argument("--seed",type=Path)
    args=p.parse_args()
    try:
        run(args)
    except (AssertionError, BrokenPipeError):
        if not args.fault:
            raise
        out=args.temp/f"nes-tile821-{args.group}-jointmirror-p{args.phase}-{args.tag}"
        r=json.loads((out/"result.json").read_bytes())
        assert r["passed"] and r["commits"]==4 and r["last_status"]=={"stop":228,"damage":224}[args.fault]
        assert (out/"canceled-map.bin").stat().st_size==8192
        assert (out/"retained.rgb").read_bytes()==(out/"frame-908.rgb").read_bytes()
    else:
        assert not args.fault
