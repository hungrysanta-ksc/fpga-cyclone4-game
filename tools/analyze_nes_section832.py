"""Check the exact publication clock, physical DMA windows and last-OBJ overlap."""
import argparse
import csv
import json
import re
from pathlib import Path

from analyze_nes_map830 import packets, window
from analyze_nes_seal831 import measure
from analyze_nes_output822 import CLK_MS, sha
from prepare_nes_section832 import BASE, OUT, PROBES


def read(path):
    return json.loads(path.read_bytes())


def section(folder):
    heads = packets(folder)
    spi = [e for e in read(folder/"events.json") if e.get("opcode")=="0xe1"]
    expected = {}
    issue = []
    wire_counts = []
    last = None
    for b,e in zip(heads,spi,strict=True):
        if int.from_bytes(b[8:10],"little") != 909:
            continue
        offset = int.from_bytes(b[10:12],"little")
        size = int.from_bytes(b[14:16],"little")
        if b[:2] == bytes((7,1)):
            last = offset,size,int.from_bytes(b[16:20],"little")
        if b[1] != 5:
            continue
        payload = b[16:]
        if b[0] in (4,5):
            assert len(payload)==2 and size%2==0
            payload *= size//2
        else:
            assert b[0]==2
        for i,v in enumerate(payload,offset):
            assert i not in expected
            expected[i]=v
        issue.append((offset,len(payload),e["start"],e["clock"]))
        wire_counts.append(len(b)-16)
    slot,n,token=last
    # A descriptor can span multiple discontinuous ROM grant windows.
    # Count intersections with individual service intervals, never the gap between them.
    reads=[(a,b) for pos,_,a,b in read(folder/"obj-reads832.json") if slot<=pos<slot+n]
    assert reads and all(a<b for a,b in reads)
    ready=next(json.loads(l)["producer"] for l in (folder/"producer.jsonl").read_text().splitlines()
               if json.loads(l)["token"]==token and json.loads(l)["generation"]==909)
    confirmed=float((folder/"section-ready832.txt").read_text())
    overlap=[]
    preparation=[]
    payload_overlap=[]
    ticks_per_byte=8*21_477_272/2_625_000
    for (offset,n,start,end), wire_n in zip(issue,wire_counts,strict=True):
        clocks=sum(max(0,min(end,b)-max(start,a)) for a,b in reads)
        if clocks:
            overlap.append([offset,n,round(clocks)])
        overlap_with_job=max(0,min(end,ready)-max(start,reads[0][0]))
        if overlap_with_job:
            preparation.append([offset,n,round(overlap_with_job)])
        # Place all charged driver/RPC time before or after the burst.
        # Only the common interior of both payload windows is unambiguous.
        lo=end-(wire_n+2)*ticks_per_byte
        hi=start+(17+wire_n)*ticks_per_byte
        ticks=sum(max(0,min(hi,b)-max(lo,a)) for a,b in reads)
        if ticks:
            payload_overlap.append([offset,wire_n,round(ticks)])
    return expected,dict(seal_function_entry=confirmed,final_OBJ_slot=slot,final_OBJ_token=token,
                         final_OBJ_read_span=[reads[0][0],reads[-1][1]],final_OBJ_ready=ready,
                         section5_packets=issue,section5_E1_wire_B=sum(wire_counts)+19*len(issue),
                         section5_read_overlaps=overlap,
                         section5_payload_read_overlaps=payload_overlap,section5_job_overlaps=preparation)


def analyze(phase,mode,temp):
    prefix=f"nes-tile821-demoB-jointmirror-p{phase}-"
    control=temp/(prefix+"827control")
    run=temp/(prefix+"832"+mode)
    base=measure(control,control)
    observed=measure(run,control)
    image,details=section(run)
    canonical,_=section(temp/(prefix+"832base"))
    assert image==canonical
    with (run/"seal528.csv").open() as f:
        raw_dma=[int(e["bytes"]) for e in csv.DictReader(f) if e["g"]=="909" and
                 e["event"]=="dma" and e["port"]=="24" and 0x5000<=int(e["dst"])<0x5100]
    assert raw_dma and all(n==64 for n in raw_dma)
    details["raw_CHR_DMA_B"]=sum(raw_dma)
    implementation=mode.removesuffix("fixed").removesuffix("tail")
    link=BASE if implementation=="base" else PROBES/"nes-output823"/("link-832"+implementation)
    fw=link/"src/obj-nes-100/firmware.stm"
    fixed=mode.endswith("fixed")
    if fixed:
        entry=read(run/"fixed832.json")
        assert entry["parent"].lower()==observed["ARM"].lower()
        assert entry["object"]==sha(fw.parent/"nes_native_sink165.o")
        assert observed["reveals"][:4]==base["reveals"][:4] and observed["ACK2572"]==base["ACK2572"]
        details["diagnostic_overlay"]=entry
        if mode.endswith("tailfixed"):
            details["receiver_after2572"]=sha(PROBES/"nes-seal831/client-tail/body.bin")
    else:
        assert sha(fw).lower()==observed["ARM"].lower()
    map_slots=[(n,vb) for n,_,vb,_ in observed["map2580"]]
    reveal_delta=observed["reveals"][3][0]-base["reveals"][3][0]
    delta=observed["last_ACK"]-base["last_ACK"]
    checks=dict(fixed2572=reveal_delta==0,section5_during_OBJ=bool(details["section5_job_overlaps"]),
                tail_by48=observed["all_DMA_by_VB48"],reveal2576=observed["reveals"][4][1]<=48,
                map2580=map_slots==[(768,51),(704,52)],intervals=sum(observed["intervals"])<16,
                faster_ACK=delta<0,flash=fw.stat().st_size<=212992)
    if mode in ("base","basefixed"):
        assert observed==base
    return dict(**observed, **details, static_Flash_B=fw.stat().st_size,delta2572=reveal_delta,
                delta_ACK_ms=round(delta/CLK_MS,6),checks=checks,passed=all(checks.values()))


def guards(temp):
    data={}
    for mode in ("plane","stream","streammid","streamburst"):
        fw=PROBES/"nes-output823"/("link-832"+mode)/"src/obj-nes-100/firmware.stm"
        menu=read(OUT/("menu-"+mode+".json"))
        base=read(OUT/("base-"+mode)/"result.json")
        assert sha(fw)==menu["firmware"]==base["firmware_sha256"]
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        data[mode]=dict(menu_released=True,base_restored=True,ARM=sha(fw))
    prefix="nes-tile821-demoB-jointmirror-p1-"
    for fault in ("stop","crc","identity"):
        res=read(temp/(prefix+"823832stream-"+fault+"-section5")/"rejection.json")
        assert not res["seal_submitted"] and res["arm"]==data["stream"]["ARM"]
        data["stream"][fault]=res
    for arm,tag in (("streammid","streammid"),("streamburst","streambursttail")):
        for fault,ack in (("stop",228),("coverage",224),("table",224)):
            run=temp/(prefix+"832"+tag+"-guard-"+fault)
            assert (run/"rejected831.txt").read_text()==f"4 {ack} 909"
            assert not any(r["g"]>=909 and r["event"]=="reveal" for r in window(run))
            data[arm][fault]=dict(last_committed=4,error_ACK=ack)
    rejected={}
    for phase in (1,2):
        rejected[phase]={}
        for mode in ("table","tableplane","tableoam"):
            run=temp/f"nes-tile821-demoB-jointmirror-p{phase}-832{mode}"
            w=window(run)
            a=next(r for r in w if r["g"]==909 and r["event"]=="ack" and r["value"]>=224)
            b=packets(run)[a["index"]-1]
            assert a["value"]==224 and b[:2]==bytes((2,5)) and int.from_bytes(b[10:12],"little")==1505
            assert not any(r["g"]>=909 and r["event"]=="reveal" for r in w)
            rejected[phase][mode]=dict(failing_offset=1505,ACK=224,last_committed=4)
    return dict(recovery=data,out_of_order=rejected)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("modes",nargs="+")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    report={}
    for phase in (1,2):
        report[phase]={}
        for mode in a.modes:
            r=analyze(phase,mode,a.temp)
            print(phase,mode,r["delta2572"],r["tile_B_in_VB48"],r["palette_complete"][1:],
                  r["OAM_complete"][1:],r["map2580"],r["intervals"],r["delta_ACK_ms"],
                  r["section5_read_overlaps"],r["passed"])
            report[phase][mode]=r
    if a.out:
        record=dict(scope="Linked ARM and 65816. CPI 2, MMC826 SPI driver means and modeled producer/ROM grants. fixed switches one BL after 2572; tailfixed also switches the checked 831-tail instructions. Flash counts describe static full builds.",phases=report,guards=guards(a.temp))
        formatted=json.dumps(record,indent=2)
        # Keep each timestamp tuple or packet record on one line for review.
        formatted=re.sub(r"\[[\d.,\s-]+\]",lambda m:json.dumps(json.loads(m[0])),formatted)
        assert json.loads(formatted)==json.loads(json.dumps(record))
        a.out.write_text(formatted+"\n",newline="\n")
