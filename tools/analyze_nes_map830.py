"""Compare target head retirement, actual PPU transfers, reveal, and the final receipt."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_output822 import CLIENT, CLK_MS, sha
from prepare_nes_map828 import PROBES

MODES=("control","prefix","page","flight","grant","grantfill","complete","completefill","completeraw","joined","joinedfill","rawfill","rawfirst","free")


def load(path):
    return json.loads(path.read_bytes())


def window(folder):
    with (folder/"window.csv").open() as f:
        return [{k:(v if k=="event" else int(v)) for k,v in row.items()} for row in csv.DictReader(f)]


def packets(folder):
    return [bytes.fromhex(json.loads(l)[2]) for l in (folder/"packets.jsonl").read_text().splitlines()]


def point(row):
    return [row["clock"],row["frame"],row["line"]]


def measure(folder,baseline):
    run=load(folder/"joint.json")
    assert run["passed"] and run["commits"]==6 and run["last_status"]==1 and run["client_SHA256"]==CLIENT
    for g in range(905,911):
        assert (folder/f"frame-{g}.rgb").read_bytes()==(baseline/f"frame-{g}.rgb").read_bytes()
    w=window(folder)
    target=[r for r in w if r["g"]==909]
    pk=packets(folder)
    refs={i:b for i,b in enumerate(pk,1) if int.from_bytes(b[8:10],"little")==909 and b[1]==2}
    canonical=(baseline/"map-909.bin").read_bytes()
    covered=[]
    for b in refs.values():
        assert b[0]==2
        at=int.from_bytes(b[10:12],"little")
        assert b[16:]==canonical[at:at+len(b)-16]
        covered.extend(range(at,at+len(b)-16))
    assert sorted(covered)==list(range(2048,2048+1472))
    final_map=max(refs)
    ack=next(r for r in target if r["index"]==final_map and r["event"]=="ack")
    assert ack["value"]==0
    spi=[s for s in load(folder/"events.json") if s["event"]=="SPI"]
    credit=next(s for s in spi if s["opcode"]=="0xe0" and s["start"]>=ack["clock"] and
                int.from_bytes(bytes.fromhex(s["reply"])[5:7],"big")>=final_map)
    assert len(pk)==sum(e["opcode"]=="0xe1" for e in spi)
    all_e1=[s for s in spi if s["opcode"]=="0xe1"]
    issue=all_e1[final_map-1]
    begins=[r for r in target if r["event"]=="ppu_dma"]
    ends=[r for r in target if r["event"]=="ppu_last"]
    assert len(begins)==len(ends)
    dma=[]
    for a,b in zip(begins,ends):
        assert a["clock"]<b["clock"]
        dma.append([a["value"],*point(a),*point(b)])
    reveal=[r for r in w if r["g"]>=906 and r["event"]=="reveal"]
    assert len(reveal)==5
    frames=[r["frame"] for r in reveal]
    credit_gate=next(r for r in csv.DictReader((folder/"seal528.csv").read_text().splitlines())
                     if r["g"]=="909" and r["event"]=="final_credit")
    return dict(arm=run["firmware_SHA256"],map_packets=len(refs),map_SPI_end=round(issue["clock"]),
                map_SPI_duration=sum(all_e1[i-1]["clock"]-all_e1[i-1]["start"] for i in refs),
                map_ACK=point(ack),ARM_credit=round(credit["clock"]),PPU_DMA=dma,
                last_OBJ_ack=point(next(r for r in reversed(target) if r["event"]=="ack" and r["op"]==7 and r["section"]==1)),
                seal=point(next(r for r in target if r["event"]=="load" and r["op"]==3)),
                upload=point(next(r for r in target if r["event"]=="upload165_entry")),
                final_credit=[int(credit_gate[k]) for k in ("clock","line","h")],
                reveal=[point(r) for r in reveal],intervals=[b-a for a,b in zip(frames,frames[1:])],
                last_ACK=run["frames"][-1]["ACK_masterclock"])


def analyze(temp):
    results={}
    for phase in (1,2):
        prefix=f"nes-tile821-demoB-jointmirror-p{phase}-"
        ref=temp/(prefix+"827control")
        baseline=measure(ref,ref)
        runs={"MMC826":baseline}
        for mode in MODES:
            folder=temp/(prefix+"830"+mode)
            row=measure(folder,ref)
            fw=PROBES/"nes-output823"/("link-826" if mode=="free" else "link-830"+mode)/"src/obj-nes-100/firmware.stm"
            assert row["arm"]==sha(fw)
            row["flash_B"]=fw.stat().st_size
            row["delta_ms"]={k:round((new-old)/CLK_MS,6) for k,new,old in (
                ("map_ACK",row["map_ACK"][0],baseline["map_ACK"][0]),
                ("credit",row["ARM_credit"],baseline["ARM_credit"]),
                ("2572",row["reveal"][2][0],baseline["reveal"][2][0]),
                ("2576",row["reveal"][3][0],baseline["reveal"][3][0]),("last_ACK",row["last_ACK"],baseline["last_ACK"]))}
            if mode=="free":
                assert row["reveal"][:3]==baseline["reveal"][:3]
                def map_wire(d):
                    return [b for b in packets(d) if b[1]==2 and int.from_bytes(b[8:10],"little")==909]
                assert map_wire(folder)==map_wire(ref)
                removed=baseline["map_SPI_duration"]-row["map_SPI_duration"]
                assert abs(removed-1472*8*21_477_272/2_625_000)<3
            row["gates"]=dict(same_2572_clock=row["reveal"][2]==baseline["reveal"][2],same_2572_vblank=row["reveal"][2][1]==baseline["reveal"][2][1],
                              map_single_1472=any(r[0]==1472 for r in row["PPU_DMA"]),
                              all_DMA_by_previous_VBlank=all(r[5]<baseline["reveal"][3][1] for r in row["PPU_DMA"]),
                              below_16=sum(row["intervals"])<16,earlier_2580_ACK=row["last_ACK"]<baseline["last_ACK"],
                              within_Flash=row["flash_B"]<=212992,measured_SPI_cost=mode!="free")
            runs[mode]=row
        for mode in ("wide","widefill","wideend"):
            folder=temp/(prefix+"830"+mode)
            w=window(folder)
            reject=next(r for r in w if r["g"]==909 and r["event"]=="ack" and r["value"]!=0)
            b=packets(folder)[reject["index"]-1]
            assert reject["value"]==0xe0 and b[:2]==bytes((2,2)) and len(b)==256
            assert not any(r["event"]=="reveal" and r["g"]>=909 for r in w)
            runs[mode]=dict(rejected=point(reject),status=reject["value"],offset=int.from_bytes(b[10:12],"little"))
        results[phase]=runs
    guards={}
    for mode in ("complete","completefill"):
        checks=PROBES/"nes-map830"/("checks-"+mode)
        identity=results[1][mode]["arm"]
        menu=load(checks/"menu.json")
        base=load(checks/"base/result.json")
        assert menu["firmware"]==base["firmware_sha256"]==identity
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        cases={}
        for fault in ("stop","identity","crc"):
            r=load(temp/f"nes-tile821-demoB-jointmirror-p1-823830{mode}-{fault}/rejection.json")
            assert r["arm"]==identity and not r["seal_submitted"]
            cases[fault]=r
        guards[mode]=dict(base_restored=True,menu_released=True,rejection=cases)
    return dict(scope="Six MMC826 pictures, original 815R client. SPI costs from hardware; modeled ROM calendar, Cortex CPI and IRQ dispatch. free discounts only 2576 map data bits; it is not a physical sender. Points are master clock, VBlank counter, scanline. PPU DMA rows contain length and both endpoints.",runs=results,guards=guards)


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("temp",type=Path);cli.add_argument("out",type=Path)
    a=cli.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n")
