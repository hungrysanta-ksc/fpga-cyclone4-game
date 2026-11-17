"""Read independently checked display ACKs and actual PPU DMA starts for the factorial comparison."""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

CLK_MS=21_477.272
BASE_ARM="47fd371a31eb78e0dd079c86347dbff483303bcb31c7a5dec55bfcc0863e2ea5"
CLIENT="3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def trace(folder,arm):
    run=json.loads((folder/"joint.json").read_text())
    assert run["passed"] and run["commits"]==6 and run["last_status"]==1
    assert run["firmware_SHA256"]==arm and run["client_SHA256"]==CLIENT
    with (folder/"window.csv").open() as f:
        window=[{k:v if k=="event" else int(v) for k,v in row.items()} for row in csv.DictReader(f)]
    packets=[bytes.fromhex(json.loads(line)[2]) for line in (folder/"packets.jsonl").read_text().splitlines()]
    with (folder/"seal528.csv").open() as f:
        dma=[r for r in csv.DictReader(f) if r["event"]=="dma" and r["port"]=="24"]
    with (folder/"tile532.csv").open() as f:
        dma.extend(dict(g=r["g"],dst=r["dst"],bytes=r["n"],clock=r["clock"]) for r in csv.DictReader(f) if r["event"]=="tile")
    frames=[]
    for g in range(906,911):
        seal=next(r for r in window if r["g"]==g and r["op"]==3 and r["event"]=="load")
        ack=next(r for r in window if r["g"]==g and r["op"]==3 and r["event"]=="ack" and r["value"]==1)
        frame=dict(g=g,seal_clock=seal["clock"],seal_line=seal["line"],seal_vb=seal["frame"],
                   ack_vb=ack["frame"],ack_clock=ack["clock"])
        if g>906:
            obj=[(i,p) for i,p in enumerate(packets,1) if p[:2]==bytes([7,1]) and int.from_bytes(p[8:10],"little")==g]
            if obj:
                i,p=obj[-1]
                dst=(0x4000 if g%2 else 0x8000)+int.from_bytes(p[10:12],"little")
                n=int.from_bytes(p[14:16],"little")
                accepted=next(r["clock"] for r in window if r["index"]==i and r["event"]=="ack" and r["value"]==0)
                c=min(int(r["clock"]) for r in dma if int(r["g"])==g and int(r["dst"])<=dst and
                      dst+n<=int(r["dst"])+int(r["bytes"]) and accepted<=int(r["clock"])<ack["clock"])
                event=next(r for r in window if r["clock"]==c and r["event"]=="ppu_dma")
                frame.update(last_obj_dma_clock=c,dma_vb=event["frame"],dma_line=event["line"])
        frames.append(frame)
    vbs=[b["ack_vb"]-a["ack_vb"] for a,b in zip(frames,frames[1:])]
    return dict(frames=frames[1:],interval_vblanks=vbs,warm_vblanks=sum(vbs),
                warm_ms=round((frames[-1]["ack_clock"]-frames[0]["ack_clock"])/CLK_MS,5),
                final_clock=frames[-1]["ack_clock"],window_sha256=sha(folder/"window.csv"))

def resources(temp,suffix):
    out=temp/f"nes-trial816-board{suffix}"/"output_files"
    fit=(out/"board.fit.rpt").read_text(errors="replace")
    totals={}
    for label,pattern in (("M9K",r"; M9Ks\s*;"),("LAB",r"; Total LABs:  partially or completely used\s*;"),
                          ("LE",r"; Total logic elements\s*;")):
        m=re.search(pattern+r"\s*([\d,]+)\s*/\s*([\d,]+)",fit)
        totals[label]=[int(x.replace(",","")) for x in m.groups()]
    totals["fit_sha256"]=sha(out/"board.fit.rpt")
    summary=out/"board.sta.summary"
    if summary.exists():
        minima={}
        for check,v in re.findall(r"Type\s*: [^\n]*? (Setup|Hold|Recovery|Removal|Minimum Pulse Width)(?: '[^\n]*')?\s*\nSlack\s*:\s*([-\d.]+)",summary.read_text()):
            minima[check]=min(minima.get(check,float("inf")),float(v))
        assert len(minima)==5
        totals["min_slack_ns"]=minima
    return totals

def main(temp,root,out):
    arms={}
    for label,name in (("a","link"),("b","link-b"),("c","link-c"),("d","link-d"),("e","link-e"),("f","link-f")):
        fw=root/name/"src/obj-nes-100/firmware.stm"
        arms[label]=dict(bytes=fw.stat().st_size,sha256=sha(fw))
    modes=[("base","04"),("word","822a"),("mirror","822b")]
    for label in arms:
        modes.extend((m,"822"+label) for m in (("ordinary","both") if label=="a" else ("ordinary","jointmirror")))
    results={}
    for group in ("earlyB","demoB"):
        runs={}
        for mode,edition in modes:
            for phase in (1,2):
                folder=temp/f"nes-tile821-{group}-{mode}-p{phase}-{edition}"
                arm=BASE_ARM if mode in ("base","word","mirror") else arms[edition[-1]]["sha256"]
                run=trace(folder,arm)
                first=708 if group=="earlyB" else 2568
                for index,frame in enumerate(run["frames"]):
                    frame["source_frame"]=first+4*index
                base=temp/f"nes-tile821-{group}-base-p{phase}-04"
                for pattern in ("frame-*.rgb","map-*.bin","expected-*.bin","colors*.bin"):
                    files=sorted(base.glob(pattern))
                    assert len(files)==6
                    for original in files:
                        assert original.read_bytes()==(folder/original.name).read_bytes(), (folder,original.name)
                run["matched_display_frames"]=6
                control=runs.get(f"base-04-p{phase}",run)
                run["final_delta_ms"]=round((run["final_clock"]-control["final_clock"])/CLK_MS,5)
                runs[f"{mode}-{edition}-p{phase}"]=run
        results[group]=runs
    counts={}
    groups=["demo","earlyB","lateB","demoA","demoB","demoC","demoD","early","late"]
    rtl=temp/"nes-output822-rtl-held"
    assert 'PASS MIRROR822' in (rtl/"vsim.log").read_text(errors="replace")
    assert sha(rtl/"hits.tsv")==sha(temp/"nes-output822-rtl/hits.tsv")
    for row in (rtl/"hits.tsv").read_text().splitlines():
        group,g,_,kind=map(int,row.split())
        counts.setdefault(groups[group],{}).setdefault(g,Counter())[("primary","mirror","ROM")[kind]]+=1
    out.write_text(json.dumps(dict(arms=arms,client_sha256=CLIENT,rtl_counts=counts,
        board={s:resources(temp,s) for s in ("820b","822","822m","822held")},timing=results,
        scope="Two cold frames then four warm frames, same six no-input pictures per clip and same initial clocks. Linked M4 and 65816; capture RTL byte strobes checked before joint replay, not simultaneous capture/producer simulation. CPI=2, measured MMC820 SPI averages, historical ROM grant calendar. No physical FPS measurement."),indent=2)+"\n")

if __name__=="__main__":main(*(Path(s) for s in sys.argv[1:]))
