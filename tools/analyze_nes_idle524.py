# SPDX-License-Identifier: MIT
"""Compare three consumers on two continuous schedules, including head delay during idle DMA."""
import argparse
import json
from collections import defaultdict
from math import ceil
from pathlib import Path

from analyze_nes_dense519 import ROOT, consumed_tiles, interval, measure, ms, read, seal_waits
from analyze_nes_prefix523 import firmware_checks, packet_trace, verified_visible_dma
from analyze_nes_transfer512 import fpga
from prepare_nes_dense519 import tiles
from run_nes_scroll229 import sha
from test_nes_service509_schedule import Calendar


def head_delays(events,packets):
    """From both arrival and predecessor retirement to the first ready observation."""
    loaded={int(r["index"]):int(r["clock"]) for r in events if r["event"]=="load"}
    retired={int(r["index"]):int(r["clock"]) for r in events if r["event"]=="ack"}
    delays=sorted(ms(loaded[i]-max(arrival,retired.get(i-1,0)))
                  for i,(_,arrival,_,_) in enumerate(packets,1))
    assert delays[0]>=0
    return dict(mean=sum(delays)/len(delays),p99=delays[ceil(len(delays)*.99)-1],max=delays[-1])


def map_offsets(rows):
    return [r['cursor']-65536+j for r in rows if r['cursor']>=65536 for j in range(0,r['bytes'],64)]


def idle_transfers(events, packets, *, map_rows=False,map_chunk=64):
    by_generation = defaultdict(list)
    loads = {int(r["index"]):int(r["clock"]) for r in events if r["event"]=="load"}
    for pos, r in enumerate(events):
        if r["event"] != "idle524":
            continue
        start, end = events[pos+1:pos+3]
        assert [start["event"],end["event"]] == ["ppu_dma","ppu_last"]
        assert all(q["index"]==r["index"] and q["g"]==r["g"] and q["op"]=="-1" for q in (r,start,end))
        assert r["frame"]==start["frame"]==end["frame"]
        ticks, finish = int(r["clock"]), int(end["clock"])
        assert 225 <= int(start["line"]) <= int(end["line"]) < 262
        n = int(start["value"])
        assert 0 < n <= 2048
        # index names the waiting head, which is not owned by the CPU yet.
        index = int(r["index"])
        arrival = packets[index-1][1]
        assert loads[index] > finish
        by_generation[int(r["g"])].append(dict(cursor=int(r["value"]),bytes=n,grant=ticks,
            last_write=finish,first_line=int(start["line"]),last_line=int(end["line"]),
            next_index=index,next_arrival=arrival,next_load=loads[index],
            overlapping_next_ready_ms=ms(max(0,finish-max(ticks,arrival)))))
    for rs in by_generation.values():
        if map_rows:
            offsets=map_offsets(rs)
            assert len(offsets)==len(set(offsets))
            assert all(0<=offset<4096 and offset%64==0 for offset in offsets)
            assert all(0<r["bytes"]<=map_chunk and r["bytes"]%64==0 for r in rs if r["cursor"]>=65536)
        else:
            assert [r["cursor"] for r in rs]==list(range(0,8*len(rs),8))
    count = sum(map(len,by_generation.values()))
    for event in ("ppu_dma","ppu_last"):
        assert sum(r["event"]==event and r["op"]=="-1" and int(r["g"])>=905 for r in events)==count
    return by_generation


def compare(folders, previous, plans, calendar, oracle):
    variants, traces, packet_sets, generations = {}, {}, {}, {}
    for name, folder in folders.items():
        result=read(folder/"joint.json")
        rows,result=measure(folder,plans,previous["candidate"]["firmware"],calendar)
        assert consumed_tiles(folder)==oracle and result["parameters"]==previous["candidate"]["parameters"]
        assert result["last_status"]==1 and result["max_bulk_banks"]<=2
        events, packets, keys, _=packet_trace(folder)
        # The idle observer also sees the two force-blank startup clears,
        # before the first packet. Older observers record only packet owners.
        boot=[r for r in events if int(r["g"])<905]
        if name=="524":
            assert [(r["g"],r["event"],r["value"]) for r in boot]==[("0","ppu_dma","2048")]*2
            assert int(boot[-1]["clock"])<int(next(r for r in events if r["event"]=="load")["clock"])
        else:
            assert not boot
        events=[r for r in events if int(r["g"])>=905]
        traces[name]=(events,packets)
        packet_sets[name]=set(keys)
        generations[name]=rows
        variants[name]=dict(warm_ms=interval(rows,907,957),dense_ms=interval(rows,951,955),
            final_ack=rows[-1]["display_ack"],ROM_reads=result["ROM_read_allocations"],
            SPI_B=result["wire_B"],irqs=result["SysTick_calls"],instructions=result["ARM_instructions"],
            max_banks=result["max_bulk_banks"],VRAM_DMA_B=result["vram_DMA_B"],stack=result["observed_stack_B"],
            visible_DMA=verified_visible_dma(events),head_ready_to_load_ms=head_delays(events,packets),
            client=result["client_SHA256"],
            pins={f:sha(folder/f) for f in ("joint.json","window.csv","events.json","obj-phases.json","packets.jsonl")})
    for name, key in (("520","baseline"),("523","candidate")):
        assert variants[name]["pins"]==previous[key]["pins"]
    assert packet_sets["520"]==packet_sets["523"]==packet_sets["524"]
    assert len({v["VRAM_DMA_B"] for v in variants.values()})==1
    assert len({v["ROM_reads"] for v in variants.values()})==1
    idle=idle_transfers(*traces["524"])
    out=[]
    for i,g in enumerate(range(905,958)):
        assert len({sha(folder/f"frame-{g}.rgb") for folder in folders.values()})==1
        samples={}
        for name,rows in generations.items():
            frame=rows[i]
            trace=[r for r in traces[name][0] if int(r["g"])==g]
            waits=seal_waits(trace)
            samples[name]=dict(gap_ms=frame["gap_ms"],ack=frame["display_ack"],seal_ms=frame["seal_to_ack_ms"],
                               waits=len(waits),wait_ms=sum(w["ms"] for w in waits),
                               final_gate=[(r["event"],int(r["line"])) for r in trace
                                           if r["event"] in ("borrow516","fresh516")])
        out.append(dict(g=g,samples=samples,early=idle[g]))
    c=variants["524"]
    return dict(start=previous["start"],variants=variants,frames=out,RGB_frames=len(out),tiles=len(oracle),
                packets=len(packet_sets["524"]),issued_in_952_and_954=all(idle[g] for g in (952,954)),
                delta_vs={k:dict(dense_ms=c["dense_ms"]-variants[k]["dense_ms"],
                                 final_ms=ms(c["final_ack"]-variants[k]["final_ack"])) for k in ("520","523")})


def analyze(a):
    previous=read(ROOT/"analysis/prefix523-verification.json")
    calendar=Calendar(a.calendar)
    oracle=tiles(a.fixture,957)
    plans={r["generation"]:r for r in read(ROOT/"analysis/obj518-verification.json")["plans"]["frames"]}
    phases=[compare(dict(zip(("520","523","524"),dirs)),ref,plans,calendar,oracle)
            for dirs,ref in zip(zip(a.mmc520,a.prefix523,a.idle524),previous["phases"])]
    assert [p["start"] for p in phases]==[3000000,3178684]
    for p in phases:
        assert p["variants"]["524"]["client"]==sha(a.client/"sink165.sfc")
    pins=list(read(a.pins)["board_inputs"])+["board.qpf","nominal204.sdc","timing506.tcl"]
    assert [n for n in pins if sha(a.board/n)!=sha(a.reference_board/n)]==["sink-program.hex"]
    assert sha(a.reference_board/"output_files/board.sof")==previous["boards"]["prefix523"]["SOF_SHA256"]
    assert sha(a.board/"sink-program.hex")==sha(a.client/"sink-program.hex")
    board=fpga(a.board)
    board["SOF_SHA256"]=sha(a.board/"output_files/board.sof")
    guards=read(a.priority)
    assert {(r["generation"],r["case"]) for r in guards}=={
        (g,c) for g in (906,907) for c in ("head","stop","both","late_head","late_stop","bad_manifest","cold")} | {(906,"max_late_stop")}
    return dict(scope="Two matched starts with the same linked ARM firmware, a CPI model, calibrated shared SPI and boot ROM grant replay. No physical FPS measurement.",
                phases=phases,priority=guards,paced_maximum_DMA=read(a.priority.with_name("line232.json")),whole_board=board,board_inputs=len(pins),
                body_B=read(a.client/"build.json")["body_bytes"],WRAM_added_B=0,
                targets_met=all(p["issued_in_952_and_954"] and all(d["dense_ms"]<0 and d["final_ms"]<0
                                for d in p["delta_vs"].values()) for p in phases))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("mmc520","prefix523","idle524"):
        p.add_argument("--"+k,type=Path,nargs=2,required=True)
    for k in ("calendar","fixture","priority","board","reference-board","client","pins","out"):
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--label-validation",type=Path,nargs=3,metavar=("OLD_SRC","NEW_SRC","CHECKS"))
    a=p.parse_args()
    report=analyze(a)
    if a.label_validation:
        report["labeled_firmware"]=firmware_checks(*a.label_validation,label=b"524")
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8",newline="\n")
