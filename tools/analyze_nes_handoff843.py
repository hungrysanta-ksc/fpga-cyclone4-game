"""Compare the coupled sender to a controlled one-packet arrival on the same 65816."""
import csv
import json
from pathlib import Path

from analyze_nes_section841 import folder, opening, point, window
from analyze_nes_tile842 import measure, read
from nes_handoff843 import CLIENT, OUT, arm
from nes_section841 import sha
from nes_tile842 import TEMP


def capture(phase, case):
    suffix = "-v3" if case in ("stop", "tailstop", "preempt") else ""
    return TEMP / f"nes-handoff843-{case}{suffix}-p{phase}"


def replay(phase, case, end51, end246, ref):
    f = capture(phase, case)
    rows = window(f)
    assert not (f/"map-error.txt").exists() and not (f/"callback-error.txt").exists()
    if case in ("stop", "tailstop"):
        trigger, canceled = map(int, (f/"cancel843.txt").read_text().split())
        assert canceled >= trigger and len([r for r in rows if r["event"]=="reveal"]) == 5
        assert not any(r["clock"]>=trigger and r["event"] in ("ppu_dma","ppu_last","reveal","ack") for r in rows)
        return dict(stop=trigger, canceled=canceled)
    joint = read(f/"result.json")
    assert joint["passed"] and joint["commits"]==6 and joint["last_status"]==1
    for g in range(905,911):
        assert (f/f"frame-{g}.rgb").read_bytes()==(ref/f"frame-{g}.rgb").read_bytes()
    if case=="original":
        assert (f/"window.csv").read_bytes()==(ref/"window.csv").read_bytes()
    shown=[point(r) for r in rows if r["event"]=="reveal"]
    gaps=[b[1]-a[1] for a,b in zip(shown[1:],shown[2:])]
    rows=[r for r in rows if r["g"]==910]
    head=next(r for r in rows if r["event"]=="load" and r["op"]==7 and r["section"]==0)
    ack=next(r for r in rows if r["event"]=="ack" and r["index"]==head["index"])
    first=[r for r in rows if r["event"]=="ppu_dma"]
    last=[r for r in rows if r["event"]=="ppu_last"]
    transfers=list(zip(first,last,strict=True))
    map_end,=[b for a,b in transfers if a["value"]==768 and b["frame"]==51]
    ranges=[(a["value"],point(b)) for a,b in transfers if a["frame"]==b["frame"]==51]
    bg=next((b for a,b in transfers if a["value"]==16 and a["frame"]==51),None)
    if case=="tail":
        assert [n for n,_ in ranges]==[64,64,64,768,16]
        assert len((f/"rows841.csv").read_text().splitlines())==3
        with (f/"tile532.csv").open() as stream:
            tile=next(r for r in csv.DictReader(stream) if r["src"]=="32768" and r["n"]=="16")
        assert map_end["clock"]<int(tile["clock"])<bg["clock"]<end51
        with (f/"io843.csv").open() as stream:
            guards=[int(row[2]) for row in csv.reader(stream) if map_end["clock"]<int(row[0])<int(tile["clock"])]
        assert guards[-2:]==[0x6001,0x6000]
    if case=="preempt":
        at=int((f/"preempt843.txt").read_text())
        taken=next(r for r in rows if r["clock"]>=at and r["event"]=="load")
        assert taken["section"]==2 and taken["op"]!=7 and bg is None
    arrivals=(f/"arrivals.txt").read_text().splitlines()
    late_heads=[]
    for r in rows:
        if r["event"]=="load" and (r["section"]==4 or r["op"]==3):
            offer=int(arrivals[r["index"]-1].split()[0])
            late_heads.append(dict(op=r["op"],arrival=offer,head=point(r),arrival_minus_deadline=offer-end246))
    return dict(late_OAM_and_SEAL=late_heads,head=point(head),BG_packet_ACK=point(ack),last_map_write=point(map_end),
                remaining_after_map=end51-map_end["clock"],head_to_ACK=ack["clock"]-head["clock"],
                remaining_after_packet_ACK=end51-ack["clock"],DMA51=ranges,intervals=gaps,total=sum(gaps),
                SEAL=point(next(r for r in rows if r["event"]=="load" and r["op"]==3)),
                last_DMA=point(last[-1]),late_for_52_246=last[-1]["clock"]-end246,
                ACK=joint["frames"][-1]["ACK_masterclock"],display=shown[-1],RGB_match=True)


def analyze():
    phases={}
    values=read(Path("analysis/section841-results.json"))["phases"]
    for phase in (1,2):
        beam=values[str(phase)]
        end51=beam["VB51_start"]+37*1364
        ref=folder(phase,"842controlfixed")
        offline={case:replay(phase,case,end51,beam["VB52_start"]+22*1364,ref)
                 for case in ("original","return","inflight","before","tail","preempt","stop","tailstop")}
        arms={}
        for mode in ("before","after"):
            cases={}
            for receiver in ("fixed","tail"):
                data=measure(phase,mode,receiver,tag=f"843{mode}{receiver}")
                cases[receiver]={k:data[k] for k in ("BG","raw_DMA_in_51","tile_DMA_in_51","DMA_in_51",
                        "SEAL","final_DMA","clocks_past_52_246","reveals","total","intervals","ACK","ACK_delta_826")}
            cases["opening"]=opening(folder(phase,f"843{mode}opening",True),folder(phase,"823826",True))
            arms[mode]=cases
        ref_ack=read(folder(phase,"832base")/"joint.json")["frames"][-1]["ACK_masterclock"]
        phases[phase]=dict(end51=end51,end52_line246=beam["VB52_start"]+22*1364,MMC826_ACK=ref_ack,
                           ideal_arrival=offline,linked_ARM=arms)
    costs={}
    for mode in ("before","after"):
        file=arm(mode)/"src/obj-nes-100/firmware.stm"
        menu=read(OUT/f"menu-{mode}.json")
        base=read(OUT/f"base-{mode}/result.json")
        assert sha(file)==menu["firmware"]==base["firmware_sha256"]
        assert base["safe_return"] and base["base_restored"] and menu["rows"]["normal"]["released"]
        costs[mode]=dict(
            flash_bytes=file.stat().st_size,menu_and_base=True,sha256=sha(file))
    return dict(phases=phases,ARM=costs,ROM=read(CLIENT/"cost.json"),
                scope="Recorded queue arrivals for isolation; linked M4 for sender costs. Mesen real 65816; experimental receiver substituted after 2576 ACK. FPGA timing modeled, no physical trial.")


if __name__=="__main__":
    Path("analysis/handoff843-results.json").write_text(json.dumps(analyze(),indent=2)+"\n", newline="\n")
