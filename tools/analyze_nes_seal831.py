"""Reconcile the 2576 SEAL critical path with the four visible intervals."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map830 import packets, point, window
from analyze_nes_output822 import CLK_MS
from nes_raw506 import sha
from nes_seal831 import OUT, PROBES


def contents(folder):
    seals=[]
    for b in packets(folder):
        if b[0]!=3:
            continue
        data=b[16:]
        assert len(data)==int.from_bytes(b[12:14],"little")
        assert len(data) in (56,168)
        if len(data)==56:
            data=data[:40]+bytes(112)+data[40:]
        seals.append(data)
    return seals


def measure(folder, ref):
    run=json.loads((folder/"joint.json").read_bytes())
    assert run["passed"] and run["commits"]==6 and run["last_status"]==1
    assert len(contents(folder))==6 and contents(folder)==contents(ref)
    for i in range(905,911):
        assert (folder/f"frame-{i}.rgb").read_bytes()==(ref/f"frame-{i}.rgb").read_bytes()
    rows=window(folder)
    visible=[point(r) for r in rows if r["event"]=="reveal"]
    assert len(visible)==6
    target=[r for r in rows if r["g"]==909]
    obj=next(r for r in reversed(target) if r["event"]=="ack" and r["op"]==7 and r["section"]==1)
    seal={r["event"]:r for r in target if r["op"]==3}
    points=[obj]+[seal[k] for k in ("load","validate181","coverage212","upload165_entry")]
    def last(event):
        return [r for r in target if r["event"]==event]
    transfers=list(zip(last("ppu_dma"),last("ppu_last"),strict=True))
    assert [a["value"] for a,b in transfers[-2:]]==[512,544]
    assert all(a["clock"]<b["clock"] for a,b in transfers)
    def by48(r):
        return r["frame"]<48 or (r["frame"]==48 and r["line"]>=225)
    single_map=[point(b) for a,b in transfers if a["value"]==1472]
    # If the map were split, a length-only filter would miscount it as tile.
    tile48=(sum(a["value"] for a,b in transfers[:-2] if a["value"]!=1472 and b["frame"]==48 and by48(b))
            if len(single_map)==1 else None)
    seallens=[len(b)-16 for b in packets(folder) if b[0]==3]
    idle=list(csv.DictReader((folder/"budget685.csv").read_text().splitlines()))
    idle_ranges=[(int(v["clock"]),int(v["bytes"])) for v in idle if v["generation"]=="910"]
    ppumap={int(v["clock"]) for v in csv.DictReader((folder/"seal528.csv").read_text().splitlines())
            if v["g"]=="910" and v["event"]=="dma" and v["port"]=="24"
            and 0xd000<=int(v["src"])<0xe000 and 0xa000<=int(v["dst"])<0xb000}
    map2580=[]
    for r in rows:
        if r["g"]==910 and r["event"]=="ppu_dma":
            if r["clock"] in ppumap or any(n==r["value"] and 0<=r["clock"]-t<2500 for t,n in idle_ranges):
                map2580.append([r["value"],*point(r)])
    return dict(ARM=run["firmware_SHA256"],boot_ROM=run["client_SHA256"],
                reveals=visible,intervals=[b[1]-a[1] for a,b in zip(visible[1:],visible[2:])],
                OBJ_to_SEAL_ms=round((points[1]["clock"]-obj["clock"])/CLK_MS,6),
                SEAL_to_upload_ms=round((points[-1]["clock"]-points[1]["clock"])/CLK_MS,6),
                milestones=dict(zip(("OBJ_return","SEAL_accept","validate","coverage","upload"),map(point,points))),
                tile_B_in_VB48=tile48,SEAL_lengths=seallens,
                map1472_complete=single_map,ACK2572=run["frames"][3]["ACK_masterclock"],
                palette_complete=point(transfers[-2][1]),OAM_complete=point(transfers[-1][1]),
                map2580=map2580,all_DMA_by_VB48=all(by48(b) for a,b in transfers),last_ACK=run["frames"][-1]["ACK_masterclock"])


def analyze(temp):
    checks={}
    for arm in ("830joined","831early","831short","831split","831lateoam","831splitshort"):
        src=PROBES/f"nes-output823/link-{arm}/src/obj-nes-100/firmware.stm"
        menu=json.loads((OUT/f"menu-{arm}.json").read_bytes())
        base=json.loads((OUT/f"base-{arm}/result.json").read_bytes())
        assert menu["firmware"]==base["firmware_sha256"]==sha(src)
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        checks[arm]=dict(Flash_B=src.stat().st_size,menu_and_base=True,arm=sha(src))
    guards={}
    for sender in ("joined","short"):
        guards[sender]={}
        faults=("table","coverage","stop") if sender=="joined" else ("table","coverage","stop","high","width")
        for fault in faults:
            folder=temp/f"nes-tile821-demoB-jointmirror-p1-831{sender}-guard-{fault}"
            ack=228 if fault=="stop" else 224
            assert (folder/"rejected831.txt").read_text()==f"4 {ack} 909"
            w=window(folder)
            assert [(r["g"],r["value"]) for r in w if r["event"]=="ack" and r["value"]>=224]==[(909,ack)]
            assert not any(r["event"]=="reveal" and r["g"]>=909 for r in w)
            guards[sender][fault]=ack
    report={}
    for phase in (1,2):
        prefix=f"nes-tile821-demoB-jointmirror-p{phase}-"
        ref=temp/(prefix+"827control")
        result={}
        for tag in ("827control","830joined","831earlystock","831original","831joined","831early",
                    "831originaltail","831joinedtail","831earlytail","831originaltailfixed",
                    "831originalpad","831joinedpad","831earlypad","831short","831shortwire","831split","831lateoam",
                    "831splitshort","831splitshortwire"):
            row=measure(temp/(prefix+tag),ref)
            baseline=result.get("827control",row)
            row["2572_delta_clocks"]=row["reveals"][3][0]-baseline["reveals"][3][0]
            row["2580_ACK_delta_ms"]=round((row["last_ACK"]-baseline["last_ACK"])/CLK_MS,6)
            row["pass"]=all((row["2572_delta_clocks"]==0,row["all_DMA_by_VB48"],row["reveals"][4][1]<=48,
                             sum(row["intervals"])<16,row["last_ACK"]<baseline["last_ACK"]))
            if tag.endswith("fixed"):
                assert row["reveals"][:4]==baseline["reveals"][:4]
                assert row["ACK2572"]==baseline["ACK2572"]
            if tag=="827control":
                assert [(n,vb) for n,_,vb,_ in row["map2580"]]==[(768,51),(704,52)]
            if tag=="831split":
                assert [(n,vb) for n,_,vb,_ in row["map2580"]]==[(1472,53)]
            result[tag]=row
        report[phase]=result
    return dict(clock_units="SNES master clocks. Points give clock, VBlank counter and scanline. fixed installs changed instructions at 2572 final ACK on an authentic baseline boot; static runs boot the indicated ROM.",checks=checks,guards=guards,phases=report)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n")
