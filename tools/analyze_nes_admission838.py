"""Compare the acceptance proof with 837, keeping a separate identical-boot control."""
import csv
import json
from pathlib import Path

from analyze_nes_map830 import point, window
from analyze_nes_seal831 import contents
from analyze_nes_window837 import opening
from nes_admission838 import ARM, BASE, CLIENT, OUT
from nes_raw506 import sha
from replay_nes_repeat833 import verify_rejection


def read(folder, reference):
    run=json.loads((folder/"joint.json").read_bytes())
    rows=window(folder)
    assert run["passed"] and run["commits"]==6 and run["last_status"]==1
    assert contents(folder)==contents(reference)
    for gen in range(905,911):
        rgb=f"frame-{gen}.rgb"
        assert (folder/rgb).read_bytes()==(reference/rgb).read_bytes()
    reveals=[point(r) for r in rows if r["event"]=="reveal"]
    events=[r for r in rows if r["g"]==910]
    def event(name):
        return next(r for r in events if r["event"]==name and r["op"]==3)
    seal=event("load")
    coverage=event("coverage212")
    upload=event("upload165_entry")
    last_map=next(r for r in events if r["event"]=="ppu_dma" and r["value"]==704)
    end_map=next(r for r in events if r["event"]=="ppu_last" and r["clock"]>last_map["clock"])
    with (folder/"budget685.csv").open() as f:
        beam,=[r for r in csv.DictReader(f) if r["generation"]=="910" and int(r["bytes"])==704]
    assert int(beam["clock"])<=last_map["clock"]<end_map["clock"]
    end246=int(beam["latch_clock"])+(247-int(beam["line"]))*1364-int(beam["h"])
    obj=next(r for r in reversed(events) if r["event"]=="ack" and r["op"]==7 and r["section"]==1)
    section=[r for r in events if r["section"]==5 and r["event"]=="load"][-1]
    starts=[r for r in events if r["event"]=="ppu_dma" and r["clock"]>seal["clock"]]
    ends=[r for r in events if r["event"]=="ppu_last" and r["clock"]>seal["clock"]]
    assert [v["value"] for v in starts]==[544,64,64,64,512,544] and len(ends)==6
    clocks=[r["clock"] for r in [seal,coverage,upload,starts[0],ends[-1]]]
    intervals=[b[1]-a[1] for a,b in zip(reveals[1:],reveals[2:])]
    return dict(reveals=reveals,intervals=intervals,interval_sum=sum(intervals),
                last_ACK=run["frames"][-1]["ACK_masterclock"],map704_end=point(end_map),
                last_OBJ_ack=point(obj),section_tail=point(section),seal=point(seal),seal_to_coverage=clocks[1]-clocks[0],
                coverage_to_upload=clocks[2]-clocks[1],seal_to_upload=clocks[2]-clocks[0],
                blank52_line247_start_upper=end246,map_end_to_deadline=end246-end_map["clock"],
                section_tail_late=section["clock"]-end246,seal_late=seal["clock"]-end246,
                residual_DMA=[v["value"] for v in starts],residual_first=point(starts[0]),
                residual_last=point(ends[-1]),residual_elapsed=clocks[-1]-clocks[-2])


def analyze(temp):
    phases={}
    for phase in (1,2):
        def folder(tag,group="demoB"):
            return temp/f"nes-tile821-{group}-jointmirror-p{phase}-{tag}"
        reference=folder("832base")
        base=read(folder("837client-stickypalette"),reference)
        cases={}
        for tag in ("838admit","838admitfixed"):
            path=folder(tag)
            data=read(path,reference)
            meta=json.loads((path/"joint.json").read_bytes())
            client=BASE/"client-sticky" if tag.endswith("fixed") else CLIENT
            assert meta["client_SHA256"]==sha(client/"sink165.sfc")
            assert meta["firmware_SHA256"]==sha(ARM/"src/obj-nes-100/firmware.stm")
            audit=(path/"admission838.txt").read_text().splitlines()
            evidence=[r.split()[1] for r in audit if r.startswith("910 ")]
            assert evidence==["record838","reuse838","coverage212"],evidence
            if tag.endswith("fixed"):
                assert data["reveals"][:-1]==base["reveals"][:-1]
            data["delta_ACK_vs_MMC826"]=data["last_ACK"]-json.loads((reference/"joint.json").read_bytes())["frames"][-1]["ACK_masterclock"]
            data["delta_ACK_vs_837"]=data["last_ACK"]-base["last_ACK"]
            cases[tag]=data
        phases[phase]=dict(r837=base,**cases,opening=opening(folder("838admit","earlyB"),folder("823826","earlyB")))
    def fault(name):
        return temp/f"nes-tile821-demoB-jointmirror-p1-838admit{name}"
    verify_rejection(fault("damage"),"damage")
    guards={}
    for name in ("coverage","pulse","metadata","table","identity"):
        gen=909 if name in ("coverage","pulse") else 910
        events=window(fault(name))
        assert [r["g"] for r in events if r["event"]=="reveal"]==list(range(905,gen))
        codes=[r["value"] for r in events if r["event"]=="ack" and r["value"]>=224]
        assert codes==[228 if name=="pulse" else 224],(name,codes)
        if name in ("metadata","identity","table"):
            entries=(fault(name)/"admission838.txt").read_text().splitlines()
            actions=[r.split()[1] for r in entries if r.startswith("910 ")]
            assert actions=={"table":["full838"],"identity":["record838"],
                             "metadata":["record838","full838"]}[name]
        if name=="pulse":
            stop=int((fault(name)/"stop837.txt").read_text())
            assert not any(r["event"] in ("ppu_dma","ppu_last") and r["clock"]>=stop for r in events)
        guards[name]=codes[0]
    menu=json.loads((OUT/"menu.json").read_bytes())
    recovery=json.loads((OUT/"base/result.json").read_bytes())
    assert menu["rows"]["normal"]["released"] and recovery["base_restored"] and recovery["safe_return"]
    assert menu["firmware"]==recovery["firmware_sha256"]==sha(ARM/"src/obj-nes-100/firmware.stm")
    info=json.loads((CLIENT/"build.json").read_bytes())
    return dict(phases=phases,guards=guards,raw_damage=224,menu=True,base_restore=True,
                diagnostic_ROM_B=info["program_bytes"],limit_B=5120,proof_WRAM_B=2,
                client=sha(CLIENT/"sink165.sfc"),ARM=menu["firmware"],
                scope="Emulated linked ARM/65816 with modeled bus and IRQ timing. Fixed runs install the alternate consumer after 2576 ACK.")


if __name__=="__main__":
    result=analyze(Path.home()/"AppData/Local/Temp")
    Path("analysis/admission838-results.json").write_text(json.dumps(result,indent=2)+"\n")
