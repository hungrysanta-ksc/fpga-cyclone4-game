"""Decompose the timed ARM output phase using the matching 65816 and SPI clocks."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_output822 import CLIENT, CLK_MS, sha, trace
from analyze_nes_output823 import map_tail
from prepare_nes_trial802 import PROBES


def load(folder, name):
    return json.loads((folder/name).read_text())


def phase_cost(folder):
    phases=load(folder,"output-phase.json")
    assert len(phases)==6
    spi=[r for r in load(folder,"events.json") if r["event"]=="SPI"]
    issues=[r for r in spi if r["opcode"]=="0xe1"]
    packets=[bytes.fromhex(json.loads(line)[2]) for line in (folder/"packets.jsonl").read_text().splitlines()]
    assert len(issues)==len(packets)
    with (folder/"window.csv").open() as f:
        events=[{k:v if k=="event" else int(v) for k,v in row.items()} for row in csv.DictReader(f)]
    records={}
    for g in (907,908,909,910):
        start,end=(phases[g-905][k] for k in ("start","end"))
        seal=[r for r in events if r["g"]==g and r["op"]==3]
        head=next(r for r in seal if r["event"]=="load")
        ack=next(r for r in seal if r["event"]=="ack" and r["value"]==1)
        packet=issues[head["index"]-1]
        assert packet["packet_opcode"]==3
        issued=packet["clock"]
        # RPC ends at the SPI transfer boundary. Transfers driving other heads
        # and status/credit polls can run concurrently with their SNES handlers.
        assert start<issued<=head["clock"]<ack["clock"]<=end
        by_op=Counter()
        for r in spi:
            clocks=min(issued,r["clock"])-max(start,r["start"])
            if clocks>0:
                by_op[r["opcode"]]+=clocks
        pre_wire=sum(by_op.values())
        dma_starts=[r for r in seal if r["event"]=="ppu_dma"]
        lasts=[r for r in seal if r["event"]=="ppu_last"]
        waits=[r for r in seal if r["event"]=="wait169"]
        wakes=[r for r in seal if r["event"]=="wait_return_5781"]
        assert len(dma_starts)==len(lasts) and len(waits)==len(wakes)
        dma=sum(b["clock"]-a["clock"] for a,b in zip(dma_starts,lasts))
        wait=sum(b["clock"]-a["clock"] for a,b in zip(waits,wakes))
        pieces=dict(spi_to_seal=pre_wire,other_before_seal=issued-start-pre_wire,
                    seal_queue_to_load=head["clock"]-issued,
                    snes_checks_setup_publish=ack["clock"]-head["clock"]-dma-wait,
                    dma_first_to_last=dma,vblank_wait=wait,arm_ack_tail=end-ack["clock"])
        assert min(pieces.values())>=0 and abs(sum(pieces.values())-(end-start))<0.01
        data=[p for p in packets if int.from_bytes(p[8:10],"little")==g]
        map_b=sum(int.from_bytes(p[14:16] if p[0]!=2 else p[12:14],"little")
                  for p in data if p[1]==2)
        obj_b=sum(int.from_bytes(p[14:16],"little") for p in data if p[:2]==bytes((7,1)))
        records[2560+4*(g-905)]=dict(map_B=map_b,obj_B=obj_b,seal_line=head["line"],
              final_dma_B=sum(r["value"] for r in dma_starts),total_ms=round((end-start)/CLK_MS,4),
              parts_ms={k:round(v/CLK_MS,4) for k,v in pieces.items()},
              pre_seal_spi_by_opcode_ms={k:round(v/CLK_MS,4) for k,v in by_op.items()})
    return records


def changed_words(folder,g):
    old=(folder/f"map-{g-2}.bin").read_bytes()
    new=(folder/f"map-{g}.bin").read_bytes()
    assert len(old)==len(new)==4096
    changed=[i for i in range(0,len(old),2) if old[i:i+2]!=new[i:i+2]]
    return dict(words=len(changed),rows=sorted({i//64 for i in changed}),columns=sorted({i%64//2 for i in changed}),
                different_bytes=sum(x!=y for x,y in zip(old,new)))


def obj_to_seal(folder):
    with (folder/"window.csv").open() as stream:
        rows=[r for r in csv.DictReader(stream) if r["g"]=="910"]
    start=max(int(r["clock"]) for r in rows if (r["op"],r["section"],r["event"])==("7","1","ack"))
    end=next(int(r["clock"]) for r in rows if r["op"]=="3" and r["event"]=="load")
    polls=sum(1 for r in load(folder,"events.json") if r.get("opcode")=="0xe0" and start<=r["start"]<end)
    return dict(ms=round((end-start)/CLK_MS,4),E0=polls)


def compare(temp, budget, variants):
    fields=dict(line.split("=",1) for line in budget.read_text().splitlines() if "=" in line)
    assert fields["cost_scene_crc32_hex"]=="a58fe808" and fields["display_1_30_60"]=="508,484"
    bins=[[int(n,16) for n in fields[f"b{i:02d}"].split(",")] for i in range(6,12)]
    frames=sum(b[0] for b in bins)
    result=dict(physical=dict(log=sha(budget),frames=frames,output_ms=sum(b[3] for b in bins)*10/frames),
                breakdown={},runs={})
    result["scope"]=("Physical mean uses frame-start bins 30–60 s. Individual output phases come from "
                     "linked ARM and 65816 replays with MMC826 per-op SPI times, CPI=2 and the recorded ROM calendar. "
                     "Before-SEAL SPI includes status and input transactions. DMA already overlapping that prefix "
                     "is not charged twice. Reveal and client ACK are separate 65816 events.")
    for v in ("baseline","overlap","inherited"):
        for phase in (1,2):
            result["breakdown"][f"{v}-{phase}"]=phase_cost(temp/f"nes-tile821-demoB-jointmirror-p{phase}-827-mark-{v}")
    for group in ("earlyB","demoB"):
        for phase in (1,2):
            baseline=temp/f"nes-tile821-{group}-jointmirror-p{phase}-827control"
            if group=="demoB" and phase==1:
                result["target_bank_delta"]={2560+4*(g-905):changed_words(baseline,g) for g in (909,910)}
            for v in ["baseline"]+variants:
                d=baseline if v=="baseline" else temp/f"nes-tile821-{group}-jointmirror-p{phase}-823827{v}"
                link="826" if v=="baseline" else "827"+v
                fw=PROBES/f"nes-output823/link-{link}/src/obj-nes-100/firmware.stm"
                row=trace(d,sha(fw))
                with (d/"window.csv").open() as stream:
                    reveal=[int(r["clock"]) for r in csv.DictReader(stream)
                            if r["event"]=="reveal" and int(r["g"])>=906]
                assert len(reveal)==5
                # RGB is generated by the client. The map/expected files are
                # the oracle inputs copied into each run, not rendered output.
                for g in range(905,911):
                    for name in (f"frame-{g}.rgb",f"map-{g}.bin",f"expected-{g}.bin",f"colors636-{g}.bin"):
                        assert (d/name).read_bytes()==(baseline/name).read_bytes(), (d,name)
                result["runs"].setdefault(v,{})[f"{group}-{phase}"]={
                    "intervals":row["interval_vblanks"],"warm_ms":row["warm_ms"],
                    "last_ack":row["final_clock"],"flash_B":fw.stat().st_size,"firmware":sha(fw),
                    "display_interval_clocks":[b-a for a,b in zip(reveal,reveal[1:])]}
                if group=="demoB" and v in ("baseline","overlap","inherited"):
                    result["runs"][v][f"{group}-{phase}"]["map_before_ordinary_B"]=[
                        map_tail(d,g)["before_ordinary_issue"] for g in (909,910)]
                if group=="demoB" and v in ("baseline","credit","inherited"):
                    result["runs"][v][f"{group}-{phase}"]["last_obj_to_seal"]=obj_to_seal(d)
    for v in ("overlap","inherited"):
        result[v+"_checks"]=guards(temp,v,result["runs"][v]["demoB-1"]["firmware"])
    result["holdout"]={}
    for clip in ("late","demoD"):
        for phase in (1,2):
            control=temp/f"nes-tile821-{clip}-jointmirror-p{phase}-827-mark-baseline"
            for v in ("baseline","inherited"):
                d=temp/f"nes-tile821-{clip}-jointmirror-p{phase}-827-mark-{v}"
                run=load(d,"joint.json")
                assert run["passed"] and run["commits"]==6 and run["last_status"]==1
                assert run["firmware_SHA256"]==result["runs"][v]["demoB-1"]["firmware"] and run["client_SHA256"]==CLIENT
                for g in range(905,911):
                    assert (d/f"frame-{g}.rgb").read_bytes()==(control/f"frame-{g}.rgb").read_bytes()
                with (d/"window.csv").open() as stream:
                    displays=[(int(r["clock"]),int(r["frame"])) for r in csv.DictReader(stream)
                              if r["event"]=="reveal" and int(r["g"])>=906]
                assert len(displays)==5
                result["holdout"][f"{clip}-{phase}-{v}"]=dict(
                    intervals=[b[1]-a[1] for a,b in zip(displays,displays[1:])],
                    warm_clocks=displays[-1][0]-displays[0][0],last_ack=run["frames"][-1]["ACK_masterclock"])
    for phase in (1,2):
        runs=result["runs"]
        early=f"earlyB-{phase}"
        demo=f"demoB-{phase}"
        control=runs["baseline"][demo]
        candidate=runs["inherited"][demo]
        for metric in ("intervals","last_ack","display_interval_clocks"):
            assert runs["baseline"][early][metric]==runs["inherited"][early][metric]
        assert control["map_before_ordinary_B"]==candidate["map_before_ordinary_B"]==[1280,1280]
        assert candidate["last_ack"]<control["last_ack"] and candidate["flash_B"]<=212992
        assert sum(candidate["display_interval_clocks"])<sum(control["display_interval_clocks"])
        assert candidate["intervals"]==control["intervals"]==[4,3,5,4]
        for frame in (2576,2580):
            base=result["breakdown"][f"baseline-{phase}"][frame]
            trial=result["breakdown"][f"inherited-{phase}"][frame]
            assert (base["map_B"],base["obj_B"])==(trial["map_B"],trial["obj_B"])
    return result


def guards(temp, variant, arm):
    work=PROBES/"nes-demo827"
    prefix="" if variant=="overlap" else variant+"-"
    safety={k:load(work,prefix+f) for k,f in (("menu","menu.json"),("base","base/result.json"),
                                        ("windows","windows.json"),("timer","timer.json"))}
    assert safety["menu"]["firmware"]==safety["base"]["firmware_sha256"]==arm
    assert safety["menu"]["rows"]["normal"]["released"] and safety["base"]["passed"] and safety["base"]["base_restored"] and safety["base"]["safe_return"]
    assert safety["timer"]["passed"] and safety["timer"]["firmware"]==arm
    assert safety["windows"]["layout"]=="demo" and safety["windows"]["firmware_SHA256"]==arm
    for fault in ("stop","crc","identity"):
        safety[fault]=load(temp/f"nes-tile821-demoB-jointmirror-p1-823827{variant}-{fault}-fence","rejection.json")
        assert safety[fault]["arm"]==arm and safety[fault]["case"]==fault and not safety[fault]["seal_submitted"]
    for phase in (1,2):
        d=temp/f"nes-tile821-change-jointmirror-p{phase}-827-mark-{variant}"
        control=temp/f"nes-tile821-change-jointmirror-p{phase}-827-mark-baseline"
        actual=load(d,"joint.json")
        assert actual["passed"] and actual["commits"]==6 and actual["last_status"]==1
        assert actual["firmware_SHA256"]==arm and actual["client_SHA256"]==CLIENT
        for g in range(905,911):
            assert (d/f"frame-{g}.rgb").read_bytes()==(control/f"frame-{g}.rgb").read_bytes()
        reference=load(control,"joint.json")
        safety[f"transition-{phase}"]=dict(commits=6,last_ack=actual["frames"][-1]["ACK_masterclock"],
           baseline_last_ack=reference["frames"][-1]["ACK_masterclock"])
    return safety


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("temp","budget","out"):
        p.add_argument(arg,type=Path)
    p.add_argument("variants",nargs="*")
    a=p.parse_args()
    a.out.write_text(json.dumps(compare(a.temp,a.budget,a.variants),indent=2)+"\n")
