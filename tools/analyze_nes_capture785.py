# SPDX-License-Identifier: MIT
"""Check both the absolute 783G capture edge and the edge following the candidate's own 952 ACK."""
import argparse
import json
from pathlib import Path

from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_prefix777 import ms
from analyze_nes_rows783 import analyze
from analyze_nes_first780 import RANGES
from test_nes_raw506_joint import PERIOD

MODES={1:"crc",2:"handoff",3:"poll",4:"cache",5:"cache_poll",6:"cache_crc",7:"cache_fit",
       8:"cache_poll_fit",9:"cache_crc_fit",10:"handoff_fit",11:"poll_fit",12:"fused",
       13:"compact",14:"retire",15:"retire_cache",16:"retire_full",17:"owned",18:"sealed",19:"sealed_poll",20:"sealed_fit",21:"sealed_compact",22:"sealed_history"}
RUNS={1:"crc",9:"cache",10:"checked",11:"poll",12:"fused",14:"retire",15:"retirecache",16:"retirefull",22:"sealed"}


def frame(folder, baseline):
    schedule=analyze(folder,baseline)
    windows=csv_groups(folder/"window.csv")
    def mark(g,event):
        return one([r for r in windows[g] if r["op"]==3],event)["clock"]
    ack=mark(952,"ack")
    ev=read(folder/"events.json")
    source=one([e for e in ev if e.get("generation")==954],"source_begin")
    wire=[e for e in ev if e["event"]=="SPI"]
    d2=[e for e in wire if e.get("input_generation")==953 and e["opcode"]=="0xd2"][-1]["clock"]
    origin=read(folder/"joint.json")["parameters"]["ROM_phase"]
    edge=((ack-origin)//PERIOD+1)*PERIOD+origin
    captured=(int((d2-origin)//PERIOD)+1)*PERIOD+origin
    assert source["capture_ready"]==captured+240*341*4
    post=[]
    for e in wire:
        if ack<=e["clock"]<=d2:
            txn=dict(op=e["opcode"],start_ms=ms(e["start"]-ack),end_ms=ms(e["clock"]-ack))
            if e["opcode"]=="0xe0":
                reply=bytes.fromhex(e["reply"])
                txn.update(sent=int.from_bytes(reply[3:5],"big"),retired=int.from_bytes(reply[5:7],"big"),
                           flags=reply[2],ACK_status=reply[7],ACK_op=reply[8])
            post.append(txn)
    starts=[x[-1] for x in schedule["transfers"] if x[0]=="map" and x[4]==-1 and
            any(k=="map" and max(o,x[1])<min(o+n,x[1]+x[2]) for k,o,n in RANGES)]
    dependencies={}
    for g in (953,954,959,960,968,969):
        previous=mark(g-1,"reveal")
        timeline=[e for e in ev if e.get("generation")==g]
        head=one(timeline,"source_begin")
        pops=[e for e in wire if e.get("input_generation")==g and e["opcode"]=="0xd2"]
        dependencies[g]=dict(capture_ready_from_display_ms=ms(head["capture_ready"]-previous),
            first_input_from_display_ms=ms(head["clock"]-previous),
            planner_from_display_ms=ms(one(timeline,"planner_enter")["clock"]-previous),
            SEAL_from_display_ms=ms(mark(g,"load")-previous),
            data_complete_pop_from_ACK_ms=ms(pops[-2]["clock"]-mark(g-1,"ack")),
            commit_pop_from_ACK_ms=ms(pops[-1]["clock"]-mark(g-1,"ack")))
    return dict(dependencies=dependencies,ACK952_clock=ack,D2_clock=d2,edge_after_ACK=edge,captured_edge=captured,lead_ms=ms(edge-d2),
                ACK_to_D2_ms=ms(d2-ack),wire_after_ACK=post,intervals=schedule["intervals"],dense=schedule["dense_VBlanks"],
                dense_ms=schedule["dense_ms"],reveal954=mark(954,"reveal"),final970=schedule["final970"],
                first969=schedule["first"],map_start_lines=starts,matched_frames=schedule["verified"],
                firmware=schedule["firmware"])


def collect(temp,work):
    results={"scope":"905–970, linked M4 and original 65816; modeled SPI/IRQ and recorded ROM calendar. Prior edge is the first allowed capture start after 952 ACK for each boot. Positive lead means the final D2 finished before that edge.",
             "builds":{},"phases":{}}
    # CRC-8 advances are affine in (old CRC XOR next byte). Exhaust this
    # entire input domain, including nonzero seed states.
    from prepare_nes_capture785 import crc8
    for x in range(256):
        folded=x^(x>>6)^(x>>7)
        assert ((folded^(folded<<1)^(folded<<2))&255)==crc8(bytes([x]))
    results["CRC8_transitions"]=256
    for i,mode in MODES.items():
        src=work/f"arm{i}/src/obj-nes-100"
        report=results["builds"][i]=dict(mode=mode,flash=(src/"firmware.stm").stat().st_size,firmware=sha(src/"firmware.stm"),elf=sha(src/"sd2snes.elf"))
        if i in RUNS:
            guards=read(work/f"g{i}/guards.json")
            assert guards["guards"]["firmware"]==report["firmware"]==read(work/f"g{i}/padding.json")["firmware"]
            report["guards"]=guards
            c=work/f"cache{i}.json"
            if i in (9,12,14,15,16,22):
                report["cache_guards"]=read(c)
                assert report["cache_guards"]["firmware"]==report["firmware"]
    for phase in (1,2):
        base=temp/f"nes-range778-763-p{phase}"
        ph=results["phases"][phase]={}
        # 763 lacks 783's extra row hooks; use its original 66-screen comparison.
        ref=read(Path(__file__).resolve().parents[1]/"analysis/grant782.json")["phases"][str(phase)]["763"]
        ph["763"]={k:ref[k] for k in ("dense_ms","final970")}
        g=ph["783G"]=frame(temp/f"nes-grant783-window-p{phase}",base)
        for i,name in RUNS.items():
            folder=temp/f"nes-capture785-{name}-p{phase}"
            r=ph[name]=frame(folder,base)
            assert r["firmware"]==results["builds"][i]["firmware"] and r["matched_frames"]==66
            r["tail_saving_vs_G_ms"]=round(g["ACK_to_D2_ms"]-r["ACK_to_D2_ms"],6)
            # Arithmetic only: this does not assume the candidate would issue
            # the same transactions if its ACK were forcibly moved in time.
            r["G_ACK_budget_minus_candidate_tail_ms"]=round(ms(g["edge_after_ACK"]-g["ACK952_clock"])-r["ACK_to_D2_ms"],6)
            r["D2_to_G_target_ms"]=ms(g["edge_after_ACK"]-r["D2_clock"])
            r["dense_vs_G_ms"]=round(r["dense_ms"]-g["dense_ms"],6)
            r["ACK970_vs_G_ms"]=ms(r["final970"]-g["final970"])
            r["dense_vs_763_ms"]=round(r["dense_ms"]-ref["dense_ms"],6)
            r["ACK970_vs_763_ms"]=ms(r["final970"]-ref["final970"])
            pp=temp/f"nes-capture785-stop-{name}-p{phase}"/"proof.json"
            if pp.exists():
                proof=read(pp)
                assert proof["map_offset"]==2496 and proof["after_return"] and proof["commits"]==64 and proof["blanks_after_STOP"]>=3 and proof["last_packet_status"]==0
                assert proof["retained"]==sha(folder/"frame-968.rgb") and proof["client"]==sha(folder/"client.sfc")
                r["STOP"]=proof
            checks={
                "display_953_954":r["dense"][1:3]==[2,3],
                "first_969_destinations":r["first969"]==[n for _,_,n in RANGES],
                "map_starts_by_252":bool(r["map_start_lines"]) and max(r["map_start_lines"])<=252,
                "protected_display":all(r["intervals"][k]<=2 for k in (909,960,969)),
                "dense_and_final":max(r["dense_vs_G_ms"],r["ACK970_vs_G_ms"],r["dense_vs_763_ms"],r["ACK970_vs_763_ms"])<0,
                "flash":results["builds"][i]["flash"]<=212992}
            if phase==2:
                checks["captures_prior_edge"]=r["lead_ms"]>0 and r["D2_to_G_target_ms"]>0
            r["missed"]=[k for k,ok in checks.items() if not ok]
            r["pass_schedule"]=all(checks.values())
    results["passing_both"]=[name for name in RUNS.values() if all(
        results["phases"][phase][name]["pass_schedule"] for phase in (1,2))]
    return results


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("temp","work","out"):p.add_argument(key,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(collect(a.temp,a.work),indent=2)+"\n",newline="\n")
