# SPDX-License-Identifier: MIT
"""Partition the measured MMC520 receipt-to-display tail without adding nested timers."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_nes_dense519 import ms
from nes_raw506 import sha

ROOT = Path(__file__).resolve().parents[1]


def one(rows, event):
    hits=[r for r in rows if r["event"]==event]
    assert len(hits)==1, event
    return hits[0]


def values(rows, event):
    return [r["value"] for r in rows if r["event"]==event]


def frame(trace, arrivals):
    seal=[r for r in trace if r["op"]==3]
    receipts=[r for r in trace if r["event"]=="receipt522" and r["section"]==1]
    if not receipts:
        return None
    receipt=receipts[-1]
    by_index=defaultdict(list)
    for row in trace:
        by_index[row["index"]].append(row)
    bulk=one(by_index[receipt["index"]],"ack")
    assert bulk["value"]==0 and bulk["clock"]>=receipt["clock"]
    entry=one(seal,"seal")["clock"]
    upload=one(seal,"upload165_entry")["clock"]
    final=one(seal,"final212")["clock"]
    ack=one(seal,"ack")["clock"]
    # Disjoint wall-clock ledger. Arrival is the PUSH target on the recorded
    # ARM timeline. An already queued head contributes no producer gap.
    parts=Counter(receipt_to_packet_ack=bulk["clock"]-receipt["clock"])
    cursor=bulk["clock"]
    packet_cost=Counter()
    for i in range(bulk["index"]+1,seal[0]["index"]+1):
        rows=by_index[i]
        loaded=one(rows,"load")
        at=loaded["clock"]
        available=max(cursor,arrivals[i])
        assert cursor<=available<=at
        parts["await_packet"]+=available-cursor
        parts["dispatch"]+=at-available
        if loaded["op"]==3:
            parts["seal_header"]=entry-at
        else:
            cursor=one(rows,"ack")["clock"]
            elapsed=cursor-at
            parts["packet_service"]+=elapsed
            packet_cost[f'{loaded["op"]}/{loaded["section"]}']+=elapsed
    parts["seal_checks"]=upload-entry
    waits=[]
    wait=None
    dma=None
    dmas=[]
    for row in seal:
        event,tick=row["event"],row["clock"]
        if event=="wait169":
            assert wait is None and dma is None
            wait=row
        elif wait and (event.startswith("wait_return_") or event=="final_upload212_same_blank212"):
            waits.append(dict(stage="upload" if wait["clock"]<final else "final",clocks=tick-wait["clock"],
                              enter_line=wait["line"],resume_line=row["line"],resume_clock=tick))
            wait=None
        elif event=="ppu_dma":
            assert dma is None and wait is None
            dma=dict(start=tick,bytes=row["value"])
        elif event=="dma_bbus522":
            assert dma is not None
            dma["bbus"]=row["value"]
        elif event=="ppu_last":
            assert dma is not None and wait is None
            stage="upload" if dma["start"]<final else "final"
            assert dma["bbus"] in ((0x18,) if stage=="upload" else (0x22,4))
            dmas.append(dict(stage=stage,clocks=tick-dma["start"],bytes=dma["bytes"],bbus=dma["bbus"]))
            dma=None
    assert wait is None and dma is None
    for stage,elapsed in (("upload",final-upload),("final",ack-final)):
        parts[stage+"_wait"]=sum(w["clocks"] for w in waits if w["stage"]==stage)
        parts[stage+"_dma_to_last_write"]=sum(d["clocks"] for d in dmas if d["stage"]==stage)
        parts[stage+"_other"]=elapsed-parts[stage+"_wait"]-parts[stage+"_dma_to_last_write"]
    assert min(parts.values())>=0 and sum(parts.values())==ack-receipt["clock"]
    assert [d["bytes"] for d in dmas if d["stage"]=="final"]==[512,544]

    # Audit the actual 65816 conservative byte-credit ledger, including the
    # raw setup charge. Never substitute DMA payload bytes for command charge.
    credit=0
    grants=[]
    cmds=[]
    charges=values(seal,"issue_charge522")
    indices=values(seal,"issue_index522")
    dsts=values(seal,"issue_dst522")
    credits=values(seal,"issue_credit522")
    assert len(charges)==len(indices)==len(dsts)==len(credits)
    for j,(idx,dest,charge,observed) in enumerate(zip(indices,dsts,charges,credits)):
        assert idx==j*8 and 0<charge<=4192
        if credit<charge:
            grants.append((idx,credit,charge))
            credit=4192
        assert credit==observed
        credit-=charge
        cmds.append(dict(index=j,dest=dest,charge=charge))
    prefinal=[r for r in seal if r["clock"]<final]
    assert grants==list(zip(values(prefinal,"command522"),values(prefinal,"credit522"),values(prefinal,"charge522")))
    assert len(grants)==sum(w["stage"]=="upload" for w in waits)

    # Sufficient remaining credit for ALL work including the fixed final
    # transaction in a single fresh blank. This is not a speedup prediction.
    needed=max(0,sum(charges)+1568-4192)
    moved=0
    prefix=0
    for cmd in cmds:
        if moved>=needed or cmd["dest"] in (0x5000,0x9000):break
        moved+=cmd["charge"]
        prefix+=1
    candidate=dict(upload_only_shortfall=max(0,sum(charges)-4192),needed_charge=needed,prefix_commands=prefix,prefix_charge=moved,
                   final_credit=credit,sufficient=moved>=needed)
    if needed and moved>=needed:
        # append212 may still extend the final entry. Insist on a subsequent
        # entry and an accepted packet before treating this prefix as closed.
        ready=next((r for r in trace if r["op"]!=3 and r["event"]=="list_end522" and r["value"]>=8*(prefix+1)),None)
        candidate["closed_before_seal"]=ready is not None
        if ready:
            candidate["ready_to_seal_clocks"]=entry-ready["clock"]
            candidate["ready_relative_to_receipt_clocks"]=ready["clock"]-receipt["clock"]
    # Inspect accepted data as it stood in the last observed VBlank before
    # SEAL. A still-growing map entry cannot earn its setup credit twice.
    seal_event=one(seal,"seal")
    blank=[r for r in trace if r["clock"]<entry and r["frame"]==seal_event["frame"] and r["line"]>=225]
    if blank and seal_event["line"]<225:
        first,last=blank[0]["clock"],blank[-1]["clock"]
        snapshots=[r for r in trace if r["event"]=="list_end522" and r["clock"]<=last and r["op"]!=3]
        if snapshots and snapshots[-1]["value"]>=8:
            snap=snapshots[-1]
            tail=snap["value"]//8-1
            rr=by_index[snap["index"]]
            dest=one(rr,"tail_dst522")["value"]
            size=one(rr,"tail_len522")["value"]
            assert dest==cmds[tail]["dest"]
            closed=sum(charges[:tail])
            is_map=any(base<=dest<base+4096 for base in (0x6000,0xa000))
            if is_map:
                assert size%64==0 and size+96<=charges[tail]
            short=max(0,needed-closed)
            previous=[r for r in snapshots if r["clock"]<first]
            opening=None
            if previous and previous[-1]["value"]>=8:
                edge=previous[-1]
                pos=edge["value"]//8-1
                group=by_index[edge["index"]]
                opening=dict(closed_charge=sum(charges[:pos]),tail_dst=one(group,"tail_dst522")["value"],
                             tail_bytes=one(group,"tail_len522")["value"])
            span=last-first
            busy=sum(max(0,min(one(group,"ack")["clock"],last)-max(one(group,"load")["clock"],first))
                     for group in by_index.values())
            assert busy<=span
            candidate["preceding_blank"]=dict(frame=blank[0]["frame"],
                closed_charge=closed,open_dst=dest,open_observed_bytes=size,is_map=is_map,
                split_map_bytes_if_all_closed_moved=64*((short+63)//64) if is_map else None,
                before_first_sample=opening,sampled_clocks=span,packet_owned_clocks=busy)
    return dict(g=receipt["g"],receipt=receipt["clock"],obj_ack=bulk["clock"],seal=entry,display_ack=ack,
                total_ms=ms(ack-receipt["clock"]),clocks=dict(parts),packet_service_clocks=dict(packet_cost),
                waits=waits,ppu_dma=dmas,commands=cmds,prefix_budget=candidate)


def run(source,replay):
    joint=json.loads((source/"joint.json").read_text())
    known=json.loads((ROOT/"analysis/order520-verification.json").read_text())
    phase=next(p for p in known["phases"] if p["start_clock"]==joint["parameters"]["start"])
    for name,digest in phase["builds"]["candidate"]["pins"].items():
        assert sha(source/name)==digest
    result=json.loads((replay/"result.json").read_text())
    assert result["passed"] and result["frames"]==joint["frames"] and result["commits"]==53
    arrivals={i:json.loads(line)[1] for i,line in enumerate((source/"packets.jsonl").read_text().splitlines(),1)}
    frames=defaultdict(list)
    with (source/"window.csv").open() as ref,(replay/"window.csv").open() as new:
        original=csv.DictReader(ref)
        for r in csv.DictReader(new):
            if not r["event"].endswith("522"):assert r==next(original)
            parsed={k:int(v) if k!="event" else v for k,v in r.items()}
            frames[parsed["g"]].append(parsed)
        assert next(original,None) is None
    for g in range(905,958):
        assert sha(replay/f"frame-{g}.rgb")==sha(source/f"frame-{g}.rgb")
    measured=[f for g in range(907,958) if (f:=frame(frames[g],arrivals))]
    return dict(start=phase["start_clock"],matched_RGB_and_ACK=53,warm_frames_with_OBJ_receipt=len(measured),
                heavy=[f for f in measured if 951<=f["g"]<=955],
                replay_trace_sha256=sha(replay/"window.csv"),reference_sha256=sha(source/"window.csv"),
                packet_arrival_sha256=sha(source/"packets.jsonl"))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("first","first_replay","second","second_replay","out"):
        parser.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    a=parser.parse_args()
    phases=[run(a.first,a.first_replay),run(a.second,a.second_replay)]
    assert [p["start"] for p in phases]==[3000000,3178684]
    a.out.write_text(json.dumps(dict(scope="MMC520 replay at original ARM enqueue times; not new hardware timing.",
                                    phases=phases),indent=2)+"\n",encoding="utf8",newline="\n")
