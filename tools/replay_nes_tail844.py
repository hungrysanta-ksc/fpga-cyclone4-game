"""Replay moved OAM with original wire spacing and an optional earliest legal SEAL."""
import argparse
import json
import math
from analyze_nes_section841 import folder, window
from nes_pair839 import once
from nes_tile842 import TEMP
from replay_nes_handoff843 import run


def simulate(phase, mode):
    ref=folder(phase,"842controlfixed")
    baseline=window(TEMP/f"nes-handoff843-tail-p{phase}")
    spi=json.loads((ref/"events.json").read_bytes())
    wire=[e for e in spi if e.get("opcode")=="0xe1"]
    seal_clocks=math.ceil(wire[-1]["clock"]-wire[-1]["start"])
    ready = [json.loads(line) for line in (folder(phase,"844controlfixed")/"oam840.jsonl").read_text().splitlines()]
    last_store = next(r["last_store"] for r in ready if r["event"]=="wire" and r["section"]==4)
    def retime(records, first):
        # Keep the four right map returns intact, then use the idle interval
        # before the first OBJ. The independent receiver checks the moved OAM.
        oam=[r for r in records[first:] if bytes.fromhex(r[2])[1]==4]
        assert len(oam)==3
        maps=[r for r in baseline if r["g"]==910 and r["event"]=="ack" and r["section"]==2]
        assert len(maps)==8
        first_oam=wire[-4]
        assert first_oam["packet_opcode"]==2
        start=maps[-1]["clock"]+math.ceil(first_oam["clock"]-first_oam["start"])
        if mode=="ready":
            start=max(start,math.ceil(last_store+first_oam["clock"]-first_oam["start"]))
        shift=oam[0][1]-start
        for r in oam:
            r[1]-=shift
        if mode in ("both","ready"):
            # Timer is armed by the actual final OBJ return in this replay.
            # Keep the record behind all ordinary/tile arrivals.
            seal,=[r for r in records[first:] if bytes.fromhex(r[2])[0]==3]
            seal[1] = max(r[1] for r in records[first:] if bytes.fromhex(r[2])[0]!=3)+1
    def adapt(lua):
        if mode=="oam":
            return lua
        return once(lua," while tick and now>=tick do",f""" if tick and bytes:sub(1,2)=='03' and bytes:sub(17,20)=='8e03' then
  if retired<sent then return end
  if not seal_start844 then
   seal_start844=now;tick=now+{seal_clocks}
  end
 end
 while tick and now>=tick do
  if bytes:sub(1,2)=='03' and bytes:sub(17,20)=='8e03' and not seal_start844 then break end""")
    run(phase,"tail",dst=TEMP/f"nes-tail844-checked-{mode}-p{phase}",retime=retime,adapt=adapt)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("oam","both","ready"))
    p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args()
    simulate(a.phase,a.mode)
