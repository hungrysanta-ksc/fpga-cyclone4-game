"""Reconcile END phases, ROM/bank availability and actual display/ACK gates."""
import argparse
from collections import Counter
import json
from pathlib import Path
from analyze_nes_export636 import run as verify
from analyze_nes_geometry650 import split
from analyze_nes_oam618 import work
from analyze_nes_output615 import ROOT, csv_groups, ms, one, packets, read, sha
from nes_geometry650 import encode
from test_nes_banks557 import handoff,host_after,MASTER

MODES=("bg8","short","handoff","grant")


def canonical(folder):
    ordinary,raw,tiles=work(folder)
    # The short-map candidate may partition the same consecutive bytes at
    # different head boundaries. Verify every destination and reject overlap.
    maps={}
    for g,cmds in packets(folder).items():
        for h,_,_ in cmds:
            if h[1]!=2:continue
            off=int.from_bytes(h[10:12],"little");body=h[16:]
            if h[0]==4:
                length=int.from_bytes(h[14:16],"little")
                assert len(body)==2 and length%2==0
                body=body*(length//2)
            else:assert h[0]==2
            for i,v in enumerate(body):
                key=(g,off+i)
                assert key not in maps
                maps[key]=v
    return {k:v for k,v in ordinary.items() if k[0][1]!=2},raw,tiles,maps


def profile(folder):
    events=[r for r in read(folder/"events.json") if r["generation"]==955]
    obj=read(folder/"obj-phases.json")["955"]
    cpu=csv_groups(folder/"window.csv")
    lo=one(events,"end_enter")["clock"];hi=one(events,"output_enter531")["clock"]
    spi=[r for r in events if r["event"]=="SPI"]
    clocks=Counter();counts=Counter()
    for r in spi:
        if not lo<=r["start"]<hi:continue
        assert r["clock"]<=hi
        key=r["opcode"]+("/"+str(r["packet_opcode"]) if r["opcode"]=="0xe1" else "")
        counts[key]+=1;clocks[key]+=r["clock"]-r["start"]
    clocks["other_ARM_IRQ_wait"]=hi-lo-sum(clocks.values())
    assert min(clocks.values())>=0
    batches=obj["banks557"]
    batch=batches[-1]
    rom=[r for r in obj["cache611"] if r[5]=="ROM"]
    hits=[r for r in obj["cache611"] if r[0]==1]
    assert rom and hits and all(r[5]=="OBJ_capture" for r in hits)
    bursts=[r for r in spi if r["opcode"]=="0xe9"]
    assert len(bursts)==len(batches)
    assert abs(batch["seal"]-bursts[-1]["clock"])<=1
    status=[r for r in spi if r["opcode"]=="0xe8" and r["clock"]<bursts[-1]["start"]]
    positive=[r for r in status if bytes.fromhex(r["reply"])[3]==1]
    grant=positive[-1]
    reply=bytes.fromhex(grant["reply"])
    issued=handoff(batches,len(batches)-2) if len(batches)>1 else None
    def rel(t):return ms(t-lo)
    def sampled(r):return host_after(r["start"]+7.5*MASTER/2625000,3)
    if issued is not None:assert sampled(grant)>=issued
    commands=packets(folder)[955]
    pubs=[r for r in spi if r["opcode"]=="0xe1"]
    loads=[r for r in cpu[955] if r["event"]=="load"]
    tiles=[];outstanding=[]
    for (h,data,push),e,load in zip(commands,pubs,loads,strict=True):
        assert abs(e["clock"]-push)<=1 and h[0]==load["op"]
        ack=one([r for r in cpu[955] if r["index"]==load["index"]],"ack")
        queued=sum(t>e["start"] for t in outstanding)
        outstanding.append(ack["clock"])
        if h[0]!=7:continue
        observed=next(r for r in events if r["event"]=="credit_observed648" and r["new_retired"]>=load["index"])
        assert observed["clock"]>=ack["clock"]
        tiles.append(dict(kind=h[1],size=len(data),offset=int.from_bytes(h[10:12],"little"),
            token=int.from_bytes(h[16:20],"little"),prior_queue_heads=queued,start=e["start"],
            push=push,load=load["clock"],ack=ack["clock"],ARM_credit=observed["clock"]))
    seals=[r for r in cpu[955] if r["op"]==3]
    prev=one(cpu[954],"reveal")["clock"]
    first_BG=next((r for r in obj["boundaries561"] if r["prior_B"]==144 and r["kind"]==1),None)
    return dict(END=lo,output=hi,END_to_output_ms=rel(hi),END_E9_ms=rel(batch["seal"]),
        output_to_END_E9_ms=ms(batch["seal"]-hi),end_counts=[b["count"] for b in batches],
        END_plan_bank_ready_ms=None if issued is None else rel(issued),END_E8_sample_ms=rel(sampled(grant)),
        END_E8_also_held_tile=bool(reply[6]),end_E8_to_E9_ms=ms(batch["seal"]-sampled(grant)),
        END_to_output_counts=counts,END_to_output_ms_by_owner={k:ms(v) for k,v in clocks.items()},
        BG_reads=len(rom),BG_grants=[r[3] for r in rom],BG_last_response_ms=rel(rom[-1][4]),
        OBJ_capture_reads=len(hits),last_OBJ_response_ms=rel(hits[-1][4]),
        BG144_ready_ms=rel(first_BG["ready"]) if first_BG else None,tiles=tiles,
        E8=[dict(ms=rel(sampled(r)),flags=bytes.fromhex(r["reply"])[3],descriptor=bytes.fromhex(r["reply"])[6],
                 token=int.from_bytes(bytes.fromhex(r["reply"])[14:18],"little"))
            for r in spi if r["opcode"]=="0xe8" and lo<=r["start"]<max(hi,batch["seal"])],
        output_from_954_display_ms=ms(hi-prev),SEAL_load_from_954_display_ms=ms(one(seals,"load")["clock"]-prev),
        SEAL_line=one(seals,"load")["line"],upload_line=one(seals,"upload165_entry")["line"],
        first_upload_wait_line=next((r["line"] for r in seals if r["event"]=="wait169"),None))


def analyze(a):
    old=read(ROOT/"analysis/geometry650-verification.json")
    g=(a.data/"frame955.geometry").read_bytes();raw=(a.data/"frame955.raw").read_bytes()
    inputs=encode(g,raw,955)[0]
    phases={}
    for n in (1,2):
        golden=a.traces/f"nes-front638-both{n}h"
        src=a.traces/f"nes-geometry650-packed{n}wire"
        expected=canonical(src)
        legacy=old["phases"][str(n)]
        limit=legacy["cases"]["base"]["cost"]
        mmc=legacy["MMC643"]
        cases={}
        for mode in ("650",*MODES):
            folder=src if mode=="650" else a.traces/f"nes-end651-{mode}{n}"
            v=verify(folder,golden)
            assert canonical(folder)==expected and v["measured"]["wire_B"]["0xd1"]==read(src/"joint.json")["wire_B"]["0xd1"]
            assert v["measured"]["parameters"]==read(src/"joint.json")["parameters"]
            assert v["measured"]["client_SHA256"]==read(src/"joint.json")["client_SHA256"]
            costs=profile(folder)
            inp=split(folder,inputs)
            assert inp["wire_payload_B"]==495
            rows=v["rows"]
            intervals=[rows[g]["interval_VB"] for g in range(951,956)]
            end=costs["END_to_output_ms"]
            gaps=dict(absolute=ms(inp["SEAL_start"]-limit["SEAL_start"]),
                      relative=inp["SEAL_from_953_ms"]-limit["SEAL_from_953_ms"])
            gates=dict(deadline=max(gaps.values())<=0,interval=intervals[3:]==[3,3],
                public_line=rows[951]["line"]<=246,final_wait=rows[957]["final_waits"]==0,
                dense=v["dense_VB"]<mmc["dense_VB"] and v["dense_mean_ms"]<mmc["dense_ms"],
                last_ACK=v["last_ACK"]<mmc["last_ACK"])
            frames={g:one([r for r in commands if r["op"]==3],"reveal")["frame"]
                    for g,commands in csv_groups(folder/"window.csv").items() if 905<=g<=957}
            all_intervals={g:frames[g]-frames[g-1] for g in range(906,958)}
            if mode=="650":
                assert v["last_ACK"]==legacy["cases"]["packed"]["last"] and intervals==legacy["cases"]["packed"]["intervals"]
                base_intervals=all_intervals
            else:assert v["measured"]["firmware_SHA256"]==sha(a.build/mode/"src/obj-nes-100/firmware.stm")
            shifts={g:[base_intervals[g],vb] for g,vb in all_intervals.items() if base_intervals[g]!=vb}
            cases[mode]=dict(end=costs,intervals=intervals,deadline_delta_ms=gaps,dense_ms=v["dense_mean_ms"],
                interval_changes_vs_650=shifts,last_vs_650_ms=ms(v["last_ACK"]-legacy["cases"]["packed"]["last"]),
                dense_VB=v["dense_VB"],last_ACK=v["last_ACK"],last_vs_MMC643_ms=ms(v["last_ACK"]-mmc["last_ACK"]),
                line951=rows[951]["line"],wait957=rows[957]["final_waits"],wait955=rows[955]["final_waits"],
                before_954_ACK=inp["confirmed_pre_ACK"],firmware=v["measured"]["firmware_SHA256"],
                gates=gates,time_pass=all(gates.values()),pins={k:sha(folder/k) for k in ("events.json","window.csv","obj-phases.json","joint.json","packets.jsonl","seal528.csv")})
        phases[n]=cases
    a1,a2=(phases[n]["650"]["end"] for n in (1,2))
    assert a1["BG_grants"]==a2["BG_grants"] and a1["OBJ_capture_reads"]==a2["OBJ_capture_reads"]
    owners=a1["END_to_output_ms_by_owner"]
    ledger={k:a2["END_to_output_ms_by_owner"][k]-v for k,v in owners.items()}
    assert abs(sum(ledger.values())-(a2["END_to_output_ms"]-a1["END_to_output_ms"]))<1e-9
    # Alternate partition of the same elapsed time. Do not add the concurrent
    # ROM/queue boundaries to the SPI/ARM ownership ledger above.
    pieces=[]
    for phase in (a1,a2):
        bg,=[t for t in phase["tiles"] if t["kind"]==0 and t["size"]==144]
        first=next(r for r in phase["E8"] if r["descriptor"] and r["token"]==bg["token"])
        marks=[0,phase["BG144_ready_ms"],first["ms"],ms(bg["push"]-phase["END"]),
               ms(bg["ack"]-phase["END"]),phase["last_OBJ_response_ms"],phase["END_to_output_ms"]]
        assert marks==sorted(marks)
        pieces.append(dict(zip(("to_BG_ready","ready_to_E8","E8_to_BG_push","BG_push_to_ACK",
                                "BG_ACK_to_last_OBJ","last_OBJ_to_output"),
                               [b-x for x,b in zip(marks,marks[1:])],strict=True)))
    guards={}
    for mode in MODES:
        folder=a.build/mode;fw=phases[1][mode]["firmware"]
        pins={}
        for name in ("end","geometry","menu","seal","queue"):
            f=folder/(name+".json");assert read(f)["firmware"]==fw;pins[name]=sha(f)
        for fault in ("none","busy","program","done","token"):
            f=folder/f"base-{fault}/result.json";r=read(f)
            assert r["passed"] and r["safe_return"]==r["base_restored"]==int(fault=="none") and r["firmware_sha256"]==fw
            pins[fault]=sha(f)
        guards[mode]=dict(flash_B=(folder/"src/obj-nes-100/firmware.stm").stat().st_size,pins=pins)
    timing_pass=[mode for mode in MODES if all(p[mode]["time_pass"] for p in phases.values())]
    board=read(a.rtl/"result.json")
    assert board["plan_ready_with_tile"] and board["receipts"]==2 and board["STOP"]
    return dict(phases=phases,baseline_phase_delta_ms=ledger,baseline_milestones_ms=pieces,
        guards=guards,board=board,timing_pass=timing_pass,flash_limit_B=212992,
        MMC643={n:old["phases"][str(n)]["MMC643"] for n in phases},
        scope="Eight new linked ARM/Mesen schedules. Same 650 compression producer reference, CPI2, modeled ROM and SPI; actual MCU code, two slots, independent CPU display. Separate fitted RTL E8/END/receipt test. No physical candidate or new FIT/STA.")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("traces","build","rtl","data","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
