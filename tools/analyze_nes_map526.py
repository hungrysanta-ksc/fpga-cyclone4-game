# SPDX-License-Identifier: MIT
"""Compare accepted map rows, fresh waits, displayed VBlanks and the last ACK on matched clocks."""
import argparse
import json
from pathlib import Path

from analyze_nes_dense519 import ROOT, consumed_tiles, interval, measure, ms, read, seal_waits
from analyze_nes_idle524 import head_delays, idle_transfers
from analyze_nes_prefix523 import packet_trace, verified_visible_dma
from analyze_nes_transfer512 import fpga
from prepare_nes_dense519 import tiles
from run_nes_scroll229 import sha
from test_nes_service509_schedule import Calendar


def run_cost(folder, key, reference, plans, calendar, oracle):
    rows,res=measure(folder,plans,reference["firmware"],calendar)
    assert res["parameters"]==reference["parameters"] and res["last_status"]==1
    assert not (folder/"map-error.txt").exists() and res["max_bulk_banks"]<=2
    assert consumed_tiles(folder)==oracle
    events,packets,keys,_=packet_trace(folder)
    assert [(r["event"],r["value"]) for r in events if r["g"]=="0"]==[("ppu_dma","2048")]*2
    events=[r for r in events if int(r["g"])>=905]
    idle=idle_transfers(events,packets,map_rows=key!="524")
    details=[]
    previous_frame=None
    for f in rows:
        g=f["generation"]
        trace=[r for r in events if int(r["g"])==g and r["op"]=="3"]
        ack,=[r for r in trace if r["event"]=="ack"]
        reveal,=[r for r in trace if r["event"]=="reveal"]
        assert ack["frame"]==reveal["frame"] and int(reveal["line"])>=225 and ack["value"]=="1"
        waits=seal_waits(trace)
        final_start,=[int(r["clock"]) for r in trace if r["event"]=="final212"]
        final_waits=sum(r["event"]=="wait169" and int(r["clock"])>=final_start for r in trace)
        upload_B=sum(int(r["value"]) for r in trace if r["event"]=="ppu_dma" and int(r["clock"])<final_start)
        frame=int(reveal["frame"])
        granted=idle[g]
        map_acks=[r for r in events if int(r["g"])==g and r["section"]=="2" and r["event"]=="ack"]
        first_map=int(map_acks[0]["clock"]) if map_acks else None
        first_map_push=packets[int(map_acks[0]["index"])-1][1] if map_acks else None
        details.append(dict(g=g,ack=f["display_ack"],gap_ms=f["gap_ms"],reveal_frame=frame,
            display_VBlanks=frame-previous_frame if previous_frame is not None else None,
            seal_waits=len(waits),final_waits=final_waits,pre_final_PPU_B=upload_B,wait_ms=sum(w["ms"] for w in waits),
            final_branch=[(r["event"],int(r["line"])) for r in trace if r["event"] in ("borrow516","fresh516","final212")],
            early_B=sum(r["bytes"] for r in granted),map_offsets=[r["cursor"]-65536 for r in granted if r["cursor"]>=65536],
            first_map_ACK=first_map,grants_before_first_map=sum(first_map is None or r["grant"]<first_map for r in granted),
            first_map_push=first_map_push,grants_before_map_push=sum(first_map_push is None or r["grant"]<first_map_push for r in granted),
            overlap_ms=sum(r["overlapping_next_ready_ms"] for r in granted)))
        previous_frame=frame
    summary=dict(warm_ms=interval(rows,907,957),dense_ms=interval(rows,951,955),final_ack=rows[-1]["display_ack"],
                 instructions=res["ARM_instructions"],irqs=res["SysTick_calls"],SPI_B=res["wire_B"],
                 ROM_reads=res["ROM_read_allocations"],max_banks=res["max_bulk_banks"],stack_B=res["observed_stack_B"],
                 dma_B=res["vram_DMA_B"],visible_DMA=verified_visible_dma(events),head_delays_ms=head_delays(events,packets),
                 client=res["client_SHA256"],packets=len(packets),tiles=len(oracle),frames=details,
                 pins={n:sha(folder/n) for n in ("joint.json","window.csv","events.json","obj-phases.json","packets.jsonl")})
    return summary,set(keys)


def analyze(a):
    profiles=("524","row232","row254")
    old=read(ROOT/"analysis/idle524-verification.json")
    inputs=read(ROOT/"analysis/prefix523-verification.json")
    plans={f["generation"]:f for f in read(ROOT/"analysis/obj518-verification.json")["plans"]["frames"]}
    calendar=Calendar(a.calendar)
    oracle=tiles(a.fixture,957)
    phases=[]
    for i,folders in enumerate(zip(a.baseline,a.row232,a.row254)):
        costs={};results={}
        for name,folder in zip(profiles,folders):
            cost,keys=run_cost(folder,name,inputs["phases"][i]["candidate"],plans,calendar,oracle)
            costs[name]=cost
            if name=="524":
                assert cost["pins"]==old["phases"][i]["variants"]["524"]["pins"]
                baseline_keys=keys
                continue
            base=costs["524"]
            assert keys==baseline_keys and base["dma_B"]==cost["dma_B"] and base["ROM_reads"]==cost["ROM_reads"]
            assert all(sha(folders[0]/f"frame-{g}.rgb")==sha(folder/f"frame-{g}.rgb") for g in range(905,958))
            results[name]=dict(final_delta_ms=ms(cost["final_ack"]-base["final_ack"]),
                               dense_delta_ms=cost["dense_ms"]-base["dense_ms"],targets={})
            for g in (952,954):
                new,prior=[v["frames"][g-905] for v in (cost,base)]
                results[name]["targets"][str(g)]=dict(map_B=64*len(new["map_offsets"]),
                    fewer_SEAL_waits=prior["seal_waits"]-new["seal_waits"],
                    fewer_final_waits=prior["final_waits"]-new["final_waits"],
                    fewer_display_VBlanks=prior["display_VBlanks"]-new["display_VBlanks"],
                    gap_delta_ms=new["gap_ms"]-prior["gap_ms"])
        phases.append(dict(start=old["phases"][i]["start"],variants=costs,results=results))
    assert [p["start"] for p in phases]==[3000000,3178684]
    pins=list(read(a.pins)["board_inputs"])+["board.qpf","nominal204.sdc","timing506.tcl"]
    assert sha(a.reference_board/"output_files/board.sof")==old["whole_board"]["SOF_SHA256"]
    builds={}
    for name,board,client,guards in zip(profiles[1:],a.boards,a.clients,a.guards):
        evidence=read(guards/"priority.json")
        assert {(r["generation"],r["case"]) for r in evidence}=={
            (g,k) for g in (906,907) for k in ("head","stop","both","late_head","late_stop","bad_manifest","cold","duplicate_map")}
        assert [n for n in pins if sha(a.reference_board/n)!=sha(board/n)]==["sink-program.hex"]
        assert all(p["variants"][name]["client"]==sha(client/"sink165.sfc") for p in phases)
        assert sha(board/"sink-program.hex")==sha(client/"sink-program.hex")
        empty=read(guards/"empty.json")
        assert empty["size"]==64 and empty["commits"]==2
        builds[name]=dict(board=fpga(board),SOF=sha(board/"output_files/board.sof"),
                          body_B=read(client/"build.json")["body_bytes"],priority=evidence,
                          empty_list_then_append=empty)
    edges=read(a.edges or (a.guards[1]/"edges.json"))
    assert [(r["command"],r["sample_line"],r["size"]) for r in edges]==[
        ("map",254,64),("map",255,0),("map",256,0),("tile",233,0)]
    builds["row254"]["edges"]=edges
    verdict={}
    for name in profiles[1:]:
        results=[p["results"][name] for p in phases]
        target=[frame for result in results for frame in result["targets"].values()]
        verdict[name]=dict(map_sent_at_all_targets=all(r["map_B"]>0 for r in target),
            fewer_final_waits_at_all_targets=all(r["fewer_final_waits"]>=1 for r in target),
            fewer_SEAL_waits_at_all_targets=all(r["fewer_SEAL_waits"]>=1 for r in target),
            shorter_display_gap_by_blank_at_all_targets=all(r["fewer_display_VBlanks"]>=1 for r in target),
            improved_dense_and_final_both_starts=all(r["dense_delta_ms"]<0 and r["final_delta_ms"]<0 for r in results))
    return dict(scope="Same linked MMC524 runtime code, CPI 2, calibrated SPI, SysTick, captured ROM grants and actual 65816 PPU DMA. Hardware baseline MMC524.",
                phases=phases,builds=builds,board_inputs=len(pins),verdict=verdict)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("baseline","row232","row254","boards","clients","guards"):
        p.add_argument("--"+n,type=Path,nargs=2,required=True)
    for n in ("fixture","calendar","pins","reference-board","out"):
        p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--edges",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",encoding="utf8",newline="\n")
