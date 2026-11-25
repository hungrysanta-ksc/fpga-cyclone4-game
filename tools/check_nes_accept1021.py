"""Isolate the client change with recorded MMC1012 packet arrivals and boot timing."""
import argparse
import csv
import json
from pathlib import Path

import replay_nes_split1020 as split
from check_nes_output970 import packet_path, replay
from nes_accept1021 import OUT, PACKED, PROOF, once, observe


def test(temp,phase,mode):
    trace=temp/f"nes-tile821-late-jointmirror-p{phase}-1018wire-control"
    out=temp/"nes-accept1021-fixed"/f"p{phase}-{mode}"
    with (trace/"window.csv").open() as stream:
        loads=[r for r in csv.DictReader(stream) if r["g"]=="908" and r["event"]=="load"]
    commands,_=packet_path(trace,908,expected_shape=(len(loads),sum(r["op"]=="7" for r in loads)))
    old=(PACKED/"body.bin").read_bytes()
    new=(OUT/"body.bin").read_bytes()
    labels=json.loads((OUT/"labels.json").read_bytes())
    def instrument(lua):
        if mode=="profile":
            return observe(lua,json.loads((PACKED/"labels.json").read_bytes()))
        edits=[f"emu.write({8192+i},{v},emu.memType.snesWorkRam)" for i,v in enumerate(new)
               if i>=len(old) or old[i]!=v]
        lua=once(lua,"  lastStatus=ack[1];","  if pw(8)==907 and pb(0)==3 and ack[1]==1 then\n"+
                 "\n".join(edits)+"\nend\n  lastStatus=ack[1];")
        if mode=="stop_after":
            lua=once(lua,"MODE=='stop_decode'and decodeStart","MODE=='stop_decode' and pb(0)==3")
        if mode in ("stop_after","late_damage","bad_seal","coverage"):
            lua=once(lua,'assert(captured==commits)','assert(captured==commits);assert(word('+str(PROOF)+')==0)')
        return observe(lua,labels,mode=="late_damage")

    faults={"stop_after":"stop_decode","bad_seal":"bad_seal","late_damage":"bad_seal","coverage":"bad_seal"}
    if mode in ("late_damage","coverage"):
        # The common fixture flips the generation. Cancel that injection so
        # only the indicated WRAM byte or required coverage bit is damaged.
        g,op,t,wire,*tail=commands[-1]
        b=bytearray.fromhex(wire); b[8]^=1
        if mode=="coverage":
            assert op==3 and len(b)==184
            # Pick an absent BG slot; the independently collected receipt
            # must disagree with the new required bit.
            index=next(i for i in range(40,168) if b[i]!=255)
            absent=(~b[index])&255
            b[index]|=absent&-absent
        commands[-1]=(g,op,t,b.hex(),*tail)
    if mode=="trigger":
        def timed(t,source,dest,kind,order,g,*,observe,schedule_after):
            return replay(t,source,out,kind,order,g,observe=lambda lua:instrument(observe(lua)),
                          schedule_after=schedule_after)
        result=split.compare(temp,phase,dest=out,sender=timed)
    else:
        result=replay(temp,trace,out,mode,commands,908,faults.get(mode),observe=instrument)
    (out/"checks1021.json").write_text(json.dumps(result,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path); p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("profile","fixed","bad_seal","late_damage","coverage","stop_after","trigger"))
    a=p.parse_args(); test(a.temp,a.phase,a.mode)
