"""Join ARM OAM writes and credit receipts to SPI, 65816 head and PPU clocks."""
import csv
import json
from pathlib import Path

from analyze_nes_map830 import packets, point, window
from analyze_nes_seal831 import measure
from analyze_nes_window837 import opening
from nes_oam840 import CLIENT, MODES, OUT, REFERENCE, link, sha
from replay_nes_repeat833 import verify_rejection


def decode_oam(pk):
    data=bytearray()
    for b in pk:
        if b[1]!=4:continue
        offset=int.from_bytes(b[10:12],"little")
        assert offset==len(data)
        n=int.from_bytes(b[14:16],"little")
        unit=b[16:]
        if b[0]==2:
            assert not n
            data.extend(unit)
        else:
            assert b[0] in (4,5,8) and n and n%len(unit)==0
            data.extend(unit*(n//len(unit)))
    assert len(data)==544
    return data


def audit(folder,ref):
    common=measure(folder,ref)
    w=window(folder)
    rows=[r for r in w if r["g"]==910]
    pk=packets(folder)
    final=[b for b in pk if int.from_bytes(b[8:10],"little")==910]
    reference_oam=(ref/"colors636-910.bin").read_bytes()[512:1056]
    assert decode_oam(final)==(folder/"colors636-910.bin").read_bytes()[512:1056]==reference_oam
    spi=json.loads((folder/"events.json").read_bytes())
    sends=[e for e in spi if e.get("opcode")=="0xe1"]
    assert len(sends)==len(pk)
    def first(event,op=None,section=None):
        return next(r for r in rows if r["event"]==event and
                    (op is None or r["op"]==op) and (section is None or r["section"]==section))
    arm=[json.loads(s) for s in (folder/"oam840.jsonl").read_text().splitlines()]
    wire,=[e for e in arm if e["event"]=="wire" and e["section"]==4]
    sealed,=[e for e in arm if e["event"]=="wire" and e["op"]==3]
    assert wire["stores"]>0 and wire["stores"]==sealed["stores"] and sealed["last_store"]==wire["last_store"]
    head=first("load",section=4)
    i=head["index"]
    assert i==next(j for j,b in enumerate(pk,1) if b[8:10]==(910).to_bytes(2,"little") and b[1]==4)
    tx=sends[i-1]
    assert wire["clock"]<tx["start"]<tx["clock"]
    # At most four packets may be outstanding. The first legally usable
    # credit for index i is the observed return of i-4, also if delta>1.
    floor=i-4
    credit=next(e for e in arm if e["event"]=="credit" and e["new_retired"]>=floor)
    retire=next(r for r in w if r["event"]=="ack" and r["index"]==floor)
    assert retire["clock"]<=credit["clock"]<=tx["start"]
    seal=first("load",op=3)
    upload=first("upload165_entry",op=3)
    done=next(r for r in reversed(rows) if r["event"]=="ppu_last")
    transfers=list(zip((r for r in rows if r["event"]=="ppu_dma"),
                       (r for r in rows if r["event"]=="ppu_last"),strict=True))
    with (folder/"tile532.csv").open() as f:
        obs=[int(r["clock"]) for r in csv.DictReader(f) if r["g"]=="910" and r["event"]=="tile" and
             (int(r["src"]),int(r["dst"]),int(r["n"]))==(51296,34912,544)]
    with (folder/"seal528.csv").open() as f:
        late=[int(r["clock"]) for r in csv.DictReader(f) if r["g"]=="910" and r["event"]=="dma" and r["port"]=="24"
              and (int(r["src"]),int(r["dst"]),int(r["bytes"]))==(51296,34912,544)]
    obj=[(point(a),point(b)) for a,b in transfers if a["value"]==544 and
         (a["clock"] in late or any(0<=a["clock"]-v<1500 for v in obs))]
    assert len(obj)==1
    maps=common["map2580"]
    end_map=[point(b) for a,b in transfers if any(n==704 and clk==a["clock"] for n,clk,*_ in maps)]
    # Use the horizontal latch for this run's 704B DMA when it falls in VB52.
    deadline=None
    with (folder/"budget685.csv").open() as f:
        for r in csv.DictReader(f):
            if r["generation"]=="910" and r["bytes"]=="704" and end_map and end_map[0][1]==52:
                deadline=int(r["latch_clock"])+(247-int(r["line"]))*1364-int(r["h"])
    status_before=next((e for e in reversed(arm) if e["event"]=="credit" and e["clock"]<=tx["start"]),None)
    residue=[(a,b) for a,b in transfers if a["clock"]>seal["clock"]]
    section5=[point(r) for r in rows if r["event"]=="load" and r["section"]==5]
    assert section5 and residue
    return dict(last_store=round(wire["last_store"]),OAM_stores=wire["stores"],plan_END=[round(e["clock"]) for e in arm if e["event"]=="nes_plan200_end"],
                OAM_call=round(wire["clock"]),sent_at_call=wire["sent"],retired_at_call=wire["retired"],
                first_OAM_index=i,four_credit_threshold=floor,threshold_ACK=point(retire),
                max_queue_slots=4,
                threshold_seen=round(credit["clock"]),retired_at_E1=status_before["new_retired"],
                E1_start=round(tx["start"]),E1_end=round(tx["clock"]),OAM_head=point(head),
                OAM_ACK=point(first("ack",section=4)),SEAL=point(seal),upload=point(upload),
                seal_to_upload_clocks=upload["clock"]-seal["clock"],map_ranges=maps,
                end_map704=end_map,OBJ544=obj,section5_heads=section5,
                residual=[a["value"] for a,b in residue],residual_first_to_last=residue[-1][1]["clock"]-residue[0][0]["clock"],
                residual_min_bus_clocks=8*sum(a["value"] for a,b in residue),
                time_left_after_paired_OBJ=(deadline-obj[0][1][0] if obj[0][1][1]==52 and deadline is not None else None),
                last_DMA=point(done),deadline_upper=deadline,intervals=common["intervals"],
                reveal2576=common["reveals"][-2],reveal2580=common["reveals"][-1],ACK=common["last_ACK"],
                RGB_and_OAM=True,ARM_SHA256=common["ARM"],ROM_SHA256=common["boot_ROM"])


def analyze(temp):
    phases={}
    for p in (1,2):
        def folder(mode,group="demoB"):
            return temp/f"nes-tile821-{group}-jointmirror-p{p}-{mode}"
        ref=folder("832base")
        baseline=json.loads((ref/"joint.json").read_bytes())["frames"][-1]["ACK_masterclock"]
        result={}
        for mode in ("control","pair",*MODES):
            case=audit(folder("840"+mode),ref)
            early={"control":"837client-stickypalette","pair":"839xpair"}.get(mode,"840"+mode)
            case["opening"]=opening(folder(early,"earlyB"),folder("823826","earlyB"))
            assert case["ARM_SHA256"]==sha(link(mode)/"src/obj-nes-100/firmware.stm")
            assert case["ROM_SHA256"]==sha((REFERENCE if mode=="control" else CLIENT)/"sink165.sfc")
            case["ACK_delta_MMC826"]=case["ACK"]-baseline
            result[mode]=case
        fixed=audit(folder("840objendfixed"),ref)
        assert fixed["ROM_SHA256"]==result["control"]["ROM_SHA256"] and fixed["ARM_SHA256"]==result["objend"]["ARM_SHA256"]
        fixed["ACK_delta_MMC826"]=fixed["ACK"]-baseline
        fixed["opening"]=opening(folder("840objendfixed","earlyB"),folder("823826","earlyB"))
        result["objend_fixed_receiver"]=fixed
        phases[p]=result
    costs={}
    for mode in MODES:
        fw=link(mode)/"src/obj-nes-100/firmware.stm"
        menu=json.loads((OUT/f"menu-{mode}.json").read_bytes())
        recovery=json.loads((OUT/f"base-{mode}/result.json").read_bytes())
        assert sha(fw)==menu["firmware"]==recovery["firmware_sha256"]
        assert menu["rows"]["normal"]["released"] and recovery["safe_return"] and recovery["base_restored"]
        costs[mode]=fw.stat().st_size
    def fault_dir(name):
        return temp/f"nes-tile821-demoB-jointmirror-p1-840objend{name}"
    verify_rejection(fault_dir("damage"),"damage")
    for fault,status in (("coverage",224),("pulse",228),("pairstop",None)):
        f=fault_dir(fault)
        rows=window(f)
        assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910 if status is None else 909))
        if status is not None:
            assert [(r["g"],r["op"],r["value"]) for r in rows if r["event"]=="ack" and r["value"]>=224]==[(909,3,status)]
        if fault in ("pulse","pairstop"):
            stop=int((f/("stop839.txt" if status is None else "stop837.txt")).read_text())
            assert not any(r["event"] in ("ppu_dma","ppu_last") and r["clock"]>=stop for r in rows)
            if status is None:
                assert int((f/"stop-return839.txt").read_text())>stop
                assert not any(r["event"]=="ack" and r["clock"]>=stop for r in rows)
    return dict(phases=phases,ARM_bytes=costs,menu_and_base=True,ROM_bytes=json.loads((CLIENT/"build.json").read_bytes())["program_bytes"],
                objend_damage_coverage_sealed_STOP_and_pair_STOP=True,
                scope="Linked Cortex-M4 and 65816, measured MMC826 average SPI costs, modeled ROM competition and interrupts.")


if __name__=="__main__":
    Path("analysis/oam840-results.json").write_text(json.dumps(analyze(Path.home()/"AppData/Local/Temp"),indent=2)+"\n")
