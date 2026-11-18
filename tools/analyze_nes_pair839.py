"""Audit accepted ranges, actual DMA writes, SPI polling and whole-frame deadlines."""
import csv
import json
from pathlib import Path

from analyze_nes_map830 import packets, point, window
from analyze_nes_seal831 import measure
from analyze_nes_window837 import opening
from nes_pair839 import ARM, BASE, CLIENT, OUT, REFERENCE
from nes_raw506 import sha
from replay_nes_repeat833 import verify_rejection


def demo(folder, control):
    common = measure(folder, control)
    rows = [r for r in window(folder) if r["g"]==910]
    wire = packets(folder)
    events = json.loads((folder/"events.json").read_bytes())
    sends = [e for e in events if e.get("opcode")=="0xe1"]
    assert len(sends)==len(wire)
    def head(section, offset):
        return next(r for r in rows if r["event"]=="load" and r["section"]==section
                    and int.from_bytes(wire[r["index"]-1][10:12],"little")==offset)
    table=head(5,1505)
    tail=head(5,1745)
    seal=next(r for r in rows if r["event"]=="load" and r["op"]==3)
    gaps=[]
    for r in rows:
        if r["event"]!="load" or r["op"]==1 or r["index"]<2:continue
        i=r["index"]-1
        prev=sends[i-1]["clock"]
        cur=sends[i]["start"]
        gaps.append(dict(before=r["index"],section=r["section"],op=r["op"],
                         clocks=round(cur-prev),polls=sum(1 for e in events if
                         e.get("opcode")=="0xe0" and prev<=e["start"]<cur)))
    transfers=[]
    for a,b in zip([r for r in rows if r["event"]=="ppu_dma"],
                   [r for r in rows if r["event"]=="ppu_last"],strict=True):
        transfers.append(dict(size=a["value"],start=point(a),end=point(b)))
    # Confirm the identity by descriptor source/destination, not just length:
    # OAM also transfers 544 bytes through a different port in this screen.
    with (folder/"tile532.csv").open() as f:
        prefix=[int(r["clock"]) for r in csv.DictReader(f) if r["g"]=="910" and
                r["event"]=="tile" and (int(r["src"]),int(r["dst"]),int(r["n"]))==(51296,34912,544)]
    with (folder/"seal528.csv").open() as f:
        sealed=[int(r["clock"]) for r in csv.DictReader(f) if r["g"]=="910" and
                r["event"]=="dma" and r["port"]=="24" and int(r["src"])==51296 and int(r["bytes"])==544]
    obj,=[t for t in transfers if t["size"]==544 and
          (any(0<=t["start"][0]-tick<1500 for tick in prefix) or t["start"][0] in sealed)]
    mp,=[t for t in transfers if t["size"]==704]
    assert any(size==704 and clk==mp["start"][0] for size,clk,_,_ in common["map2580"])
    with (folder/"budget685.csv").open() as f:
        beam,=[r for r in csv.DictReader(f) if r["generation"]=="910" and r["bytes"]=="704"]
    assert mp["start"][1]==52
    deadline=int(beam["latch_clock"])+(247-int(beam["line"]))*1364-int(beam["h"])
    remaining=[t for t in transfers if t["start"][0]>seal["clock"]]
    return dict(residual_DMA_bytes=[t["size"] for t in remaining],
                residual_elapsed=remaining[-1]["end"][0]-remaining[0]["start"][0],
                intervals=common["intervals"],last_ACK=common["last_ACK"],
                reveal2576=common["reveals"][-2],reveal2580=common["reveals"][-1],
                prefix_through2576=common["reveals"][:-1],map704=mp,obj544=obj,
                table240=point(table),tail9=point(tail),head_OAM=point(head(4,0)),
                gap_before_OAM=next(g for g in gaps if g["before"]==head(4,0)["index"]),
                seal=point(seal),last_DMA=transfers[-1],deadline_upper=deadline,
                seal_minus_deadline=seal["clock"]-deadline,worst_SPI_gap=max(gaps,key=lambda v:v["clocks"]),
                image=common["boot_ROM"],arm=common["ARM"])


def analyze(temp):
    variants=("837client-stickypalette","839xpair","839tail","839xboth","839xgated","839fixed")
    result={}
    for p in (1,2):
        def folder(v,group="demoB"):
            return temp/f"nes-tile821-{group}-jointmirror-p{p}-{v}"
        control=folder("832base")
        original=json.loads((control/"joint.json").read_bytes())["frames"][-1]["ACK_masterclock"]
        cases={}
        for tag in variants:
            r=demo(folder(tag),control)
            r["delta_ACK_MMC826"]=r["last_ACK"]-original
            expected_arm=(BASE if tag in (variants[0],"839xpair","839fixed") else
                          ARM.parent/"link-839gated" if tag=="839xgated" else ARM)
            expected_rom=REFERENCE if tag in (variants[0],"839tail","839fixed") else CLIENT
            assert r["arm"]==sha(expected_arm/"src/obj-nes-100/firmware.stm")
            assert r["image"]==sha(expected_rom/"sink165.sfc")
            r["all_DMA_by_52_line246"]=r["last_DMA"]["end"][0]<r["deadline_upper"]
            if tag!="839fixed":
                r["opening"]=opening(folder(tag,"earlyB"),folder("823826","earlyB"))
            else:
                assert r["prefix_through2576"]==cases[variants[0]]["prefix_through2576"]
            if tag in ("839fixed","839xpair"):
                assert r["map704"]["end"][1]==r["obj544"]["end"][1]==52
            cases[tag]=r
        result[p]=cases
    firmware={}
    for key,arm in (("pair",BASE),("tail",ARM),("gated",ARM.parent/"link-839gated")):
        fw=arm/"src/obj-nes-100/firmware.stm"
        folder=OUT if key!="pair" else REFERENCE.parent
        menu=json.loads((folder/(f"menu-{key}.json" if key!="pair" else "menu-palette.json")).read_bytes())
        base=json.loads((folder/(f"base-{key}" if key!="pair" else "base-palette")/"result.json").read_bytes())
        assert sha(fw)==menu["firmware"]==base["firmware_sha256"]
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        firmware[key]=dict(bytes=fw.stat().st_size,sha=sha(fw),menu_and_base=True)
    verify_rejection(folder_fault(temp,"839xbothdamage"),"damage")
    for name in ("839xbothcoverage","839xbothpulse","839stopReturn"):
        f=folder_fault(temp,name)
        rows=window(f)
        if name.endswith("Return"):
            assert (f/"stop-return839.txt").is_file()
            assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
        else:
            assert [e["value"] for e in rows if e["event"]=="ack" and e["value"]>=224]==[224 if name.endswith("coverage") else 228]
        if name.endswith(("pulse","Return")):
            stop=int((f/("stop839.txt" if name.endswith("Return") else "stop837.txt")).read_text())
            assert not any(r["event"] in ("ppu_dma","ppu_last") and r["clock"]>=stop for r in rows)
    return dict(phases=result,firmware=firmware,ROM_bytes=json.loads((CLIENT/"build.json").read_bytes())["program_bytes"],
                stop_before_OBJ=True,stop_between_sealed_DMA=True,damaged_WRAM_and_coverage_rejected=True,
                scope="Emulated ARM and 65816 with modeled shared SPI/ROM. Fixed pair swaps only executable WRAM after 2576 final ACK.")


def folder_fault(temp,name):
    return temp/f"nes-tile821-demoB-jointmirror-p1-{name}"


if __name__=="__main__":
    result=analyze(Path.home()/"AppData/Local/Temp")
    Path("analysis/pair839-results.json").write_text(json.dumps(result,indent=2)+"\n")
