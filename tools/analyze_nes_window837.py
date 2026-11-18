"""Measure the 2580 validation budget after the observed prefix DMA last write."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_group835 import read
from analyze_nes_map830 import point, window
from analyze_nes_repeat833 import inspect
from analyze_nes_seal831 import contents, measure
from nes_raw506 import sha
from nes_window837 import BASE, OUT, PROBES
from replay_nes_repeat833 import verify_rejection


FINAL = "837client-stickypalette"


def demo(folder, ref):
    row = read(folder, ref, measure(ref, ref))
    assert inspect(folder)[0] == inspect(ref)[0]
    events = [e for e in window(folder) if e["g"] == 910]
    obj = next(e for e in reversed(events) if e["event"] == "ack" and e["op"] == 7 and e["section"] == 1)
    palette = next(e for e in events if e["event"] == "load" and e["section"] == 3)
    seal = next(e for e in events if e["event"] == "load" and e["op"] == 3)
    upload = next(e for e in events if e["event"] == "upload165_entry")
    result = {k:row[k] for k in ("intervals","delta_ACK","last_ACK","reveal2576","map2580","raw_B")}
    result.update(last_OBJ=point(obj), first_palette=point(palette), palette_minus_OBJ=palette["clock"]-obj["clock"],
                  SEAL=point(seal), upload=point(upload), SEAL_to_upload=upload["clock"]-seal["clock"])
    if folder.name.endswith(FINAL):
        with (folder/"budget685.csv").open() as f:
            beam, = [r for r in csv.DictReader(f) if r["generation"]=="910" and r["bytes"]=="704"]
        dma = next(e for e in events if e["event"]=="ppu_dma" and e["value"]==704)
        last = next(e for e in events if e["event"]=="ppu_last" and e["clock"]>dma["clock"])
        assert int(beam["latch_clock"]) < int(beam["clock"]) < dma["clock"] < last["clock"] < seal["clock"]
        assert dma["frame"]==last["frame"]==52 and last["line"]==231
        # Use full-length scanlines and ignore DMA return, polling, all
        # further uploads and latch overhead. This favors the candidate.
        limit = int(beam["latch_clock"])+(247-int(beam["line"]))*1364-int(beam["h"])
        available = limit-last["clock"]
        result.update(map704_last=point(last), clocks_to_end246_at_most=available,
                      validation_shortfall_at_least=result["SEAL_to_upload"]-available)
    return result


def opening(folder, ref):
    run=json.loads((folder/"joint.json").read_bytes())
    assert run["passed"] and run["commits"]==6 and run["last_status"]==1
    assert contents(ref)==contents(folder)
    for g in range(905,911):
        name=f"frame-{g}.rgb"
        assert (folder/name).read_bytes()==(ref/name).read_bytes()
    rows=window(folder)
    visible=[r["frame"] for r in rows if r["event"]=="reveal"]
    with (folder/"seal528.csv").open() as f:
        latch=[r for r in csv.DictReader(f) if r["g"]=="908" and r["event"]=="latch"][-1]
    return dict(intervals=[b-a for a,b in zip(visible[1:],visible[2:])], latch=[int(latch[k]) for k in ("line","h")],
                last_ACK=run["frames"][-1]["ACK_masterclock"])


def analyze(temp):
    phases={}
    for p in (1,2):
        prefix=f"nes-tile821-demoB-jointmirror-p{p}-"
        ref=temp/(prefix+"832base")
        variants=("832base","836v2banksplit","837client-stickysplit","837bankpalette",FINAL,"837client-stickyseal")
        demos={name:demo(temp/(prefix+name),ref) for name in variants}
        prefix=f"nes-tile821-earlyB-jointmirror-p{p}-"
        ref=temp/(prefix+"823826")
        openings={name:opening(temp/(prefix+name),ref) for name in ("823826","836v2banksplit","837client-stickysplit",FINAL)}
        phases[p]=dict(demo=demos,opening=openings)
    prefix=f"nes-tile821-demoB-jointmirror-p1-{FINAL}"
    verify_rejection(temp/(prefix+"damage"),"damage")
    for fault,value in (("coverage",224),("pulse",228)):
        folder=temp/(prefix+fault)
        events=window(folder)
        assert [(e["g"],e["op"],e["value"]) for e in events if e["event"]=="ack" and e["value"]>=224]==[(909,3,value)]
        assert [e["g"] for e in events if e["event"]=="reveal"]==list(range(905,909))
        if fault=="pulse":
            stop=int((folder/"stop837.txt").read_text())
            assert not any(e["event"] in ("ppu_dma","ppu_last") and e["clock"]>=stop for e in events)
    arm=PROBES/"nes-output823/link-837palette/src/obj-nes-100/firmware.stm"
    menu=json.loads((OUT/"menu-palette.json").read_bytes())
    base=json.loads((OUT/"base-palette/result.json").read_bytes())
    assert menu["firmware"]==base["firmware_sha256"]==sha(arm)
    assert menu["rows"]["normal"]["released"] and base["base_restored"] and base["safe_return"]
    client=OUT/"client-sticky"
    build=json.loads((client/"build.json").read_bytes())
    flash={name:(BASE.parent/("link-837"+name)/"src/obj-nes-100/firmware.stm").stat().st_size for name in ("palette","seal","prefix","shared")}
    for p in (1,2):
        for group in ("earlyB","demoB"):
            run=json.loads((temp/f"nes-tile821-{group}-jointmirror-p{p}-{FINAL}"/"joint.json").read_bytes())
            assert run["firmware_SHA256"]==sha(arm) and run["client_SHA256"]==sha(client/"sink165.sfc")
    return dict(phases=phases,ARM_SHA256=sha(arm),flash_B=flash,ROM_SHA256=sha(client/"sink165.sfc"),
                ROM_free_B=build["physical_free_B"],STOP_clock=stop,coverage_and_WRAM_status=224,
                STOP_status=228,menu_release=True,base_restore=True,
                scope="Six consecutive captures per clip; linked ARM and 65816 with modeled SPI, interrupts and ROM contention.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("temp",type=Path)
    parser.add_argument("out",type=Path)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp),indent=2)+"\n")
