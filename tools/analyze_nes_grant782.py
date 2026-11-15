# SPDX-License-Identifier: MIT
"""Compare capture eligibility, checked refill, map receipt and destination DMA."""
import argparse
import json
from pathlib import Path

from analyze_nes_first780 import RANGES, coverage
from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_prefix777 import ms
from analyze_nes_supply781 import measure
from analyze_nes_tail779 import examine


def transitions(folder):
    w=csv_groups(folder/"window.csv")
    ev=read(folder/"events.json")
    out={}
    for g in (960,969):
        previous=[r for r in w[g-1] if r["op"]==3]
        ack=one(previous,"ack")["clock"]
        before=lambda c:ms(ack-c)
        rows=[e for e in ev if e.get("generation")==g]
        release=one(rows,"source_begin")
        begin=one(rows,"planner_enter")["clock"]
        source=[e for e in ev if e.get("opcode")=="0xd1" and release["clock"]<=e["clock"]<=begin]
        assert len(source)==17
        pres=[e for e in source if e["clock"]<=ack]
        crc_pop=[e for e in ev if e.get("opcode")=="0xd2" and release["clock"]<=e["clock"]<=begin]
        assert len(crc_pop)==17
        confirms=[]
        io=[e for e in ev if e.get("event")=="SPI" and release["clock"]<=e["clock"]<=begin]
        for pos,e in enumerate(io):
            if e.get("opcode")=="0xd2":
                # Before next token, the real receiver must validate D0.
                confirm=next(x for x in io[pos+1:] if x["opcode"] in ("0xd0","0xd1"))
                assert confirm["opcode"]=="0xd0"
                confirms.append(confirm["clock"])
        out[g]=dict(capture_ready_lead=before(release["capture_ready"]),source_begin_lead=before(release["clock"]),
                    first_D1_lead=before(source[0]["start"]),last_pre_D1_lead=before(pres[-1]["clock"]) if pres else None,
                    received_before_ACK=len(pres),confirmed_before_ACK=sum(c<=ack for c in confirms),D1_total=len(source),
                    previous_SEAL_lead=before(one(previous,"load")["clock"]),planner_after_ACK=ms(begin-ack))
    return out


def report(temp,work):
    builds={}
    for name,i in (("credit",5),("gap",6),("rows",8),("map",9),("paired",10)):
        arm=work/f"arm{i:02d}/src/obj-nes-100"
        proof=read(work/f"g{i}/guards.json")
        padding=read(work/f"g{i}/padding.json")
        assert sha(arm/"firmware.stm")==proof["guards"]["firmware"]==padding["firmware"]
        builds[name]=dict(firmware=sha(arm/"firmware.stm"),elf=sha(arm/"sd2snes.elf"),
                          flash=(arm/"firmware.stm").stat().st_size,guards=proof,padding_cases=padding["exact_short_lengths"])
    phases={}
    for p in (1,2):
        base=temp/f"nes-range778-763-p{p}"
        prior=temp/f"nes-supply781-refill3-p{p}"
        phase=phases[p]={}
        for n,d in (("763",base),("781C",prior),("credit",temp/f"nes-grant782-credit-p{p}"),("gap",temp/f"nes-grant782-gap-p{p}"),
                    ("rows",temp/f"nes-grant782-rows-p{p}"),("map",temp/f"nes-grant782-map-p{p}"),("paired",temp/f"nes-grant782-paired-p{p}")):
            r=phase[n]=measure(d,base)
            r["transitions"]=transitions(d)
            a=phase["763"]
            r["dense_delta_ms"]=round(r["dense_ms"]-a["dense_ms"],6)
            r["final970_delta_ms"]=ms(r["final970"]-a["final970"])
            r["local970_delta_ms"]=round(r["ACK968_to_970"]-a["ACK968_to_970"],6)
            heads={h["offset"]:h for h in r["map_heads"]}
            r["map2496_ACK_to_3072_wire_ms"]=round(heads[3072]["wire"]-heads[2496]["ACK"],6)
            r["map2496_return_vs_first_blank_end_ms"]=round(heads[2496]["ACK"]-r["first_blank_end"],6)
            r["deadline_909_763"]=r["intervals"][909]<=a["intervals"][909]
            if n in builds:
                assert builds[n]["firmware"]==r["firmware"]
                r["passed_all"]=(r["deadline_909_763"] and r["intervals"][960]<=3 and r["intervals"][969]==2 and
                                 sum(r["first"])==496 and r["dense_delta_ms"]<0 and r["final970_delta_ms"]<0 and
                                 builds[n]["flash"]<=212992)
        obs=temp/f"nes-grant782-hold-p{p}"
        m=examine(prior,obs,prior,fixed=True)
        assert read(obs/"audit.json")["frames"]==66
        phase["receiver_hold"]=dict(first=coverage(m["transfers"],-1),transfers=m["transfers"],intervals=m["intervals"],
                                    measured_970=False)
    stop=read(temp/"nes-grant782-stop/proof.json")
    assert stop["retained"]==sha(temp/"nes-grant782-map-p1/frame-968.rgb") and stop["blanks_after_STOP"]>=3
    returned=read(temp/"nes-grant782-stop2496/proof.json")
    assert returned["retained"]==sha(temp/"nes-grant782-gap-p1/frame-968.rgb")
    assert returned["map_offset"]==2496 and returned["after_return"] and returned["blanks_after_STOP"]>=3
    return dict(phases=phases,builds=builds,receiver_STOP=stop,returned_map_STOP=returned,ranges=RANGES,baselines="Physical MMC763, linked 781C. "
                "Linked M4 and original 65816 with modeled bus and ROM. Dense is 951 reveal to 957 reveal divided by six.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","work","out"):
        p.add_argument(k,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.work),indent=2)+"\n",newline="\n")
