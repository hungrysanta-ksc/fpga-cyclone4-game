"""Join 2580 section admissions, packet heads and physical PPU transfers."""
import csv
import json
from pathlib import Path

from analyze_nes_map830 import packets, point, window
from analyze_nes_seal831 import contents
from analyze_nes_window837 import opening
from nes_section841 import ARM, OUT, REFERENCE, admission, raw, sha

TEMP=Path.home()/"AppData/Local/Temp"
TILES={(0,0):16,(1,1760):32,(1,1824):64,(1,1920):32,(1,1984):32}


def folder(phase,tag,opening_clip=False):
    clip="earlyB" if opening_clip else "demoB"
    return TEMP/f"nes-tile821-{clip}-jointmirror-p{phase}-{tag}"


def csv_rows(f):
    with f.open() as stream:
        return list(csv.DictReader(stream))


def beam_start(f,number):
    starts=set()
    rows=window(f)
    for b in csv_rows(f/"budget685.csv"):
        if b["generation"]!="910":continue
        clock=int(b["clock"])
        dma,=[r for r in rows if r["event"]=="ppu_dma" and r["g"]==910 and
              r["value"]==int(b["bytes"]) and 0<=r["clock"]-clock<1000]
        if dma["frame"]==number:
            starts.add(int(b["latch_clock"])-(int(b["line"])-225)*1364-int(b["h"]))
    assert len(starts)==1
    return starts.pop()


def demo(p,tag,start51,start52,arm,rom):
    f=folder(p,tag)
    ref=folder(p,"832base")
    joint=json.loads((f/"joint.json").read_bytes())
    assert joint["passed"] and joint["commits"]==6 and joint["last_status"]==1
    assert contents(f)==contents(ref) and len(contents(f))==6
    for g in range(905,911):
        assert (f/f"frame-{g}.rgb").read_bytes()==(ref/f"frame-{g}.rgb").read_bytes()
    assert joint["firmware_SHA256"]==sha(arm/"src/obj-nes-100/firmware.stm")
    assert joint["client_SHA256"]==sha(rom/"sink165.sfc")
    all_rows=window(f)
    shown=[point(r) for r in all_rows if r["event"]=="reveal"]
    assert len(shown)==6
    gaps=[b[1]-a[1] for a,b in zip(shown[1:],shown[2:])]
    ack=joint["frames"][-1]["ACK_masterclock"]
    w=[r for r in all_rows if r["g"]==910]
    pk=packets(f)
    heads=[r for r in w if r["event"]=="load"]
    def head(section,offset):
        return next(r for r in heads if r["section"]==section and int.from_bytes(pk[r["index"]-1][10:12],"little")==offset)
    accept=head(5,1745)
    log=(f/"admission838.txt").read_text().splitlines()
    entries=[(v.split()[1],int(v.split()[-1])) for v in log if v.startswith("910 ")]
    finish=next(c for label,c in entries if label=="record838")
    receipt=next(r for r in w if r["event"]=="ack" and r["index"]==accept["index"])
    assert accept["clock"]<finish<receipt["clock"]
    seal=next(r for r in heads if r["op"]==3)
    dma=list(zip((r for r in w if r["event"]=="ppu_dma"),(r for r in w if r["event"]=="ppu_last"),strict=True))
    # OAM also has length 544. Require the OBJ aperture and the VRAM port.
    starts=[int(r["clock"]) for r in csv_rows(f/"tile532.csv") if r["g"]=="910" and r["event"]=="tile" and
            (int(r["src"]),int(r["dst"]),int(r["n"]))==(51296,34912,544)]
    sealed=[int(r["clock"]) for r in csv_rows(f/"seal528.csv") if r["g"]=="910" and r["event"]=="dma" and
            (int(r["port"]),int(r["src"]),int(r["dst"]),int(r["bytes"]))==(24,51296,34912,544)]
    obj,=[point(b) for a,b in dma if a["value"]==544 and (a["clock"] in sealed or any(0<=a["clock"]-i<1500 for i in starts))]
    prior=[]
    if (f/"rows841.csv").exists():
        for row in csv.reader((f/"rows841.csv").read_text().splitlines()):
            g,bank,i,dest,grant,vb,line,verified=map(int,row)
            if g!=910:continue
            a,b=next((a,b) for a,b in dma if grant<=a["clock"]<b["clock"]<=verified)
            assert a["value"]==64 and a["frame"]==b["frame"]==vb and 225<=a["line"]<=b["line"]<=246
            assert bank==1 and dest==0x9000+16*(i//2)+2*(i%2)
            prior.append(dict(row=i,start=point(a),end=point(b)))
    tile_heads=[]
    for (section,off),count in TILES.items():
        h=next(r for r in heads if r["op"]==7 and r["section"]==section and int.from_bytes(pk[r["index"]-1][10:12],"little")==off)
        assert int.from_bytes(pk[h["index"]-1][14:16],"little")==count
        tile_heads.append(dict(section=section,offset=off,bytes=count,head=point(h)))
    ack826=json.loads((ref/"joint.json").read_bytes())["frames"][-1]["ACK_masterclock"]
    return dict(section5_head=point(accept),section5_check=finish,section5_ACK=point(receipt),
                independent_check_margin_to_52=start52-finish,proof_at_SEAL=entries,
                SEAL=point(seal),SEAL_margin_to_52=start52-seal["clock"],
                map=[dict(bytes=a["value"],start=point(a),end=point(b)) for a,b in dma if a["value"] in (704,768)],
                first_OAM=point(head(4,0)),OBJ544_end=obj,early_raw=prior,tile_acceptance=tile_heads,
                tile_bytes_available_by_end_51=sum(v["bytes"] for v in tile_heads if v["head"][0]<start51+37*1364),
                raw_bytes_in_51=64*sum(v["end"][1]==51 for v in prior),
                residual_after_SEAL=[a["value"] for a,b in dma if a["clock"]>=seal["clock"]],
                last_DMA=point(dma[-1][1]),DMA_margin_to_52_line246=start52+22*1364-dma[-1][1]["clock"],
                display2576=shown[-2],display2580=shown[-1],intervals=gaps,
                sum=sum(gaps),ACK=ack,ACK_delta_826=ack-ack826,
                ARM_SHA256=joint["firmware_SHA256"],boot_ROM_SHA256=joint["client_SHA256"])


def analyze():
    result={}
    release=ARM.parent/"link-841release"
    for p in (1,2):
        control=folder(p,"840objendfixed")
        start51,start52=[beam_start(control,n) for n in (51,52)]
        cases={}
        for tag,arm,client in (("section",ARM,admission.CLIENT),("checkedC",ARM,raw.SCOPED),("releaseC",release,raw.SCOPED),
                               ("paircheckedC",ARM,OUT/"client-paired-stop")):
            for mode in ("demo","fixed"):
                run=demo(p,"841"+tag+mode,start51,start52,arm,REFERENCE if mode=="fixed" else client)
                cases[tag+mode]=run
            cases[tag+"opening"]=opening(folder(p,"841"+tag+"opening",True),folder(p,"823826",True))
        cases["pairreleaseCfixed"]=demo(p,"841pairreleaseCfixed",start51,start52,release,REFERENCE)
        paired=cases["paircheckedCfixed"]
        assert (paired["display2576"][1],paired["OBJ544_end"][1],paired["raw_bytes_in_51"])==(48,52,192)
        assert sorted(row["row"] for row in paired["early_raw"])==[0,1,4]
        assert paired["tile_bytes_available_by_end_51"]==0
        assert paired["map"][-1]["bytes"]==704 and paired["map"][-1]["end"][1]==52
        assert paired["residual_after_SEAL"]==[32,512,544]
        assert any(label=="reuse838" for label,tick in paired["proof_at_SEAL"])
        # The fixed-ARM opening uses the original 837 receiver throughout.
        for tag,arm in (("checkedC",ARM),("releaseC",release)):
            f=folder(p,"841"+tag+"refopening",True)
            j=json.loads((f/"joint.json").read_bytes())
            assert j["firmware_SHA256"]==sha(arm/"src/obj-nes-100/firmware.stm") and j["client_SHA256"]==sha(REFERENCE/"sink165.sfc")
            cases[tag+"refopening"]=opening(f,folder(p,"823826",True))
        result[p]=dict(VB51_start=start51,VB52_start=start52,cases=cases)
    costs={}
    for key,arm,suffix in (("checked",ARM,""),("release",release,"-release")):
        fw=arm/"src/obj-nes-100/firmware.stm"
        menu=json.loads((OUT/f"menu{suffix}.json").read_bytes())
        base=json.loads((OUT/f"base{suffix}/result.json").read_bytes())
        assert menu["firmware"]==base["firmware_sha256"]==sha(fw)
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        costs[key]=dict(ARM_bytes=fw.stat().st_size,menu_base=True)
    for p,suffix in ((1,"stop"),(2,"damage")):
        f=folder(p,"841checkedCfixed"+suffix)
        tick=int((f/"stop841.txt").read_text())
        assert int((f/"cancel841.txt").read_text())>=tick
        assert not any(r["event"] in ("ppu_dma","ppu_last","reveal") and r["clock"]>=tick for r in window(f))
    for fault,status,g in (("table",224,910),("identity",224,910),("coverage",224,909),("pulse",228,909)):
        rows=window(folder(1,"841checkedC"+fault))
        rejected_generation=g^1 if fault=="identity" else g
        assert [(r["g"],r["op"],r["value"]) for r in rows if r["event"]=="ack" and r["value"]>=224]==[(rejected_generation,3,status)]
        assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,g))
    return dict(phases=result,costs=costs,receiver_bytes=json.loads((raw.SCOPED/"build.json").read_bytes())["program_bytes"],
                paired_receiver_bytes=json.loads((OUT/"client-paired-stop/build.json").read_bytes())["program_bytes"],
                receiver_sha=sha(raw.SCOPED/"sink165.sfc"),STOP_damage_and_independent_checks=True,
                scope="Linked ARM and 65816 with measured MMC826 SPI costs and modeled IRQ/ROM; fixed swaps receiver WRAM after 2576 ACK.")


if __name__=="__main__":
    Path("analysis/section841-results.json").write_text(json.dumps(analyze(),indent=2)+"\n")
