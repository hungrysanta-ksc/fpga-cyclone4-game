"""Replay the same early OAM/SEAL arrivals with the optimized sealed-list loop."""
import argparse
import json
from unittest.mock import patch

import replay_nes_tail844 as timeline
import replay_nes_handoff843 as recorder
from analyze_nes_section841 import window
from nes_dma845 import OUT, base, once


def run(phase, stop=False, retire=False, repair=False):
    client=OUT/("client-bg-retire" if retire else "client-bg")
    folder=base.TEMP/f"nes-dma845{'-retire' if retire else ''}-{'repair' if repair else 'stop' if stop else 'ready'}-p{phase}"
    original=timeline.run
    def replay(*args,adapt,**kwargs):
        def attach(lua):
            lua=adapt(lua)
            if repair:
                assert retire and not stop
                labels=json.loads((client/"labels.json").read_bytes())
                return once(lua,"local function loaded()",f"""checkedMem527(function()
 if packet and pw(8)==910 and not lost845 then
  local done=word(0x1506);assert(done~=0)
  lost845=true;emu.write(0x1506,0,emu.memType.snesWorkRam);emu.write(0x1507,0,emu.memType.snesWorkRam)
  local f=assert(io.open(ROOT..'/lost845.txt','w'));f:write(done);f:close()
 end
end,emu.callbackType.exec,{labels['history845']})
local function loaded()""")
            if not stop:
                return lua
            labels=json.loads((client/"labels.json").read_bytes())
            # After MDMAEN returns, X points at the next sealed entry, while
            # the committed WRAM cursor is still from before this run.
            addr=labels["stop845"]
            start=labels["normal845"]
            body=(client/"body.bin").read_bytes()
            at=body.index(bytes.fromhex("ad016030"),start-0x7e2000,addr-0x7e2000)+0x7e2000
            anchor="local function loaded()"
            lua=once(lua,anchor,f"""checkedMem527(function()
 if packet and pb(0)==3 and pw(8)==910 then
  local x=emu.getState()['cpu.x']
  if word(0x4004+x-8)==32 and x>word(0x1252) then pending845=x end
 end
end,emu.callbackType.exec,{at})
"""+anchor)
            lua=once(lua,"if a==0x6001 then observe843(a);","""if a==0x6001 then observe843(a);
 if pending845 and not pulse845 then pulse845=emu.getState().masterClock;return 128 end""")
            lua=once(lua,"lastStatus=ack[1];sample516", """if pulse845 and not logged845 then
 assert(pb(0)==3 and pw(8)==910 and ack[1]==0xe4 and commits==5 and word(0x1236)~=0)
 assert(word(0x1252)==pending845 and word(0x1248)==5)
 for j=0x14d0,0x14d8,2 do assert(word(j)==0) end
 local f=assert(io.open(ROOT..'/stop845.txt','w'));f:write(pulse845..' '..pending845..' '..emu.getState().masterClock);f:close()
 logged845=true;trace516:flush();emu.stop(0)
 end
 lastStatus=ack[1];sample516""")
            # The stopped transaction is terminal. Prevent a later host-frame
            # callback from running the six-success postcondition on teardown.
            lua=once(lua,"if (rejected or index>TOTAL)","if not logged845 and (rejected or index>TOTAL)")
            return lua
        return original(*args,**(kwargs|dict(dst=folder,adapt=attach)))
    with patch.object(timeline,"run",replay),patch.object(recorder.handoff,"CLIENT",client):
        if not stop:
            timeline.simulate(phase,"ready")
            return
        try:
            timeline.simulate(phase,"ready")
        except FileNotFoundError as e:
            if e.filename is None or (folder/"result.json")!=type(folder)(e.filename):
                raise
        assert not (folder/"callback-error.txt").exists() and not (folder/"map-error.txt").exists()
        tick,cursor,end=map(int,(folder/"stop845.txt").read_text().split())
        rows=window(folder)
        assert tick<end and cursor%8==0
        assert not any(r["clock"]>=tick and r["event"] in ("ppu_dma","ppu_last","reveal") for r in rows)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("--stop",action="store_true")
    p.add_argument("--retire",action="store_true")
    p.add_argument("--repair",action="store_true")
    a=p.parse_args()
    run(a.phase,a.stop,a.retire,a.repair)
