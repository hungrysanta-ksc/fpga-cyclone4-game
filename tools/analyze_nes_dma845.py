"""Account for shared SPI by actual occupancy and measure final physical PPU writes."""
import csv
import json
from collections import defaultdict
from pathlib import Path

from analyze_nes_tail844 import contents, decode_oam, folder, opening, packets, read, timing, window
from nes_dma845 import ARM, BASE, OUT, base


def tail(f, ref, cutoff):
    d = timing(f, ref, cutoff)
    joint = read(f / "joint.json")
    assert joint["passed"] and joint["commits"] == 6 and joint["last_status"] == 1
    assert contents(f) == contents(ref)
    pk = packets(f)
    assert decode_oam([b for b in pk if b[8:10] == bytes((142, 3))]) == (ref / "colors636-910.bin").read_bytes()[512:1056]
    bus = [e for e in read(f / "events.json") if e["event"] == "SPI"]
    offers = [e for e in bus if e["opcode"] == "0xe1"]
    assert len(offers) == len(pk)
    seal = offers[d["packets"][-1]["index"]-1]
    start, end = d["last_OBJ_ACK"][0], d["packets"][-1]["head"][0]
    busy = defaultdict(float)
    counts = defaultdict(int)
    previous = 0
    for e in bus:
        assert e["start"] >= previous - 0.01
        previous = e["clock"]
        length = min(end, previous) - max(start, e["start"])
        if length > 0:
            name = "SEAL_E1" if e is seal else e["opcode"]
            busy[name] += length
            counts[name] += 1
    occupied = sum(busy.values())
    assert 0 <= occupied <= end-start
    rows = window(f)
    last = next(r for r in rows if r["event"] == "ack" and r["index"] == d["packets"][-1]["index"]-1)
    calls = [json.loads(s) for s in (f/"oam840.jsonl").read_text().splitlines()]
    call = next(r for r in calls if r["event"] == "wire" and r["op"] == 3)
    wait = next(r for r in rows if r["g"] == 910 and r["event"] == "wait169")
    assert seal["start"] >= call["clock"] and end >= max(last["clock"], seal["clock"])
    d["tail_clocks"] = dict(total=end-start, SPI={k:round(v) for k,v in busy.items()},
                            transactions=dict(counts), off_bus=round(end-start-occupied),
                            SEAL_call=round(call["clock"]), SEAL_start=round(seal["start"]),
                            SEAL_end=round(seal["clock"]), prior_palette_ACK=last["clock"],
                            SEAL_end_to_head=round(end-seal["clock"]), wait169=wait["clock"])
    d["ARM_SHA256"] = joint["firmware_SHA256"]
    return d


def transfers(f):
    with (f/"seal528.csv").open() as stream:
        return [r for r in csv.DictReader(stream) if r["g"] == "910" and r["event"] == "dma"]


def jobs(rows):
    return [(r["port"],r["src"],r["dst"] if r["port"]=="24" else None,r["bytes"]) for r in rows]


def receiver(f, ref, cutoff):
    run = read(f/"result.json")
    assert run["passed"] and run["last_status"] == 1 and run["commits"] == 6
    assert not any((f/n).exists() for n in ("callback-error.txt","map-error.txt"))
    d = timing(f, ref, cutoff)
    end = transfers(f)[-1]
    assert end["port"] == "4" and d["last_DMA"][1] == 53
    start = int(end["clock"]) - (int(end["line"])-225)*1364 - int(end["h"])
    wait = next(r for r in window(f) if r["g"] == 910 and r["event"] == "wait169")
    return dict(last_write_minus_line246_end=d["last_DMA"][0]-(start+22*1364),
                wait_after_VB52_start=wait["clock"]-(cutoff-22*1364),display=d["display2580"],ACK=d["ACK"])


def analyze():
    beam = read(Path("analysis/section841-results.json"))["phases"]
    phases = {}
    for p in (1,2):
        ref = folder(p,"832base")
        cutoff = beam[str(p)]["VB52_start"] + 22*1364
        tags = ["844objdonefixed","845armfixed","845dmafixed","845bothfixed","845retirefixed"]
        fixed = {tag:tail(folder(p,tag),ref,cutoff) for tag in tags}
        for tag,d in fixed.items():
            link = BASE if tag in ("844objdonefixed","845dmafixed") else ARM
            assert d["ARM_SHA256"] == base.section.sha(link/"src/obj-nes-100/firmware.stm")
            assert [j[0] for j in d["DMA"][51]] == [64,64,64,768]
            assert [j[0] for j in d["DMA"][52]] == [704,544]
        reference = base.TEMP/f"nes-tail844-checked-ready-p{p}"
        replay = {}
        for suffix in ("ready","retire-ready","retire-repair"):
            f = base.TEMP/f"nes-dma845-{suffix}-p{p}"
            assert (f/"arrivals.txt").read_bytes() == (reference/"arrivals.txt").read_bytes()
            replay[suffix] = receiver(f,ref,cutoff)
            physical = jobs(transfers(f))
            original = jobs(transfers(reference))
            if suffix == "retire-repair":
                assert int((f/"lost845.txt").read_text()) == 0x13
                assert physical[:-5] == original[:-2] and physical[-2:] == original[-2:]
                assert [(int(x[2]),int(x[3])) for x in physical[-5:-2]] == [(36864,64),(36866,64),(36896,64)]
            else:
                assert physical == original
        replay["baseline"] = receiver(reference,ref,cutoff)
        stopped = {}
        for kind in ("stop","retire-stop"):
            f = base.TEMP/f"nes-dma845-{kind}-p{p}"
            tick,cursor,end = map(int,(f/"stop845.txt").read_text().split())
            assert tick < end and not any(r["clock"] >= tick and r["event"] in ("ppu_dma","ppu_last","reveal") for r in window(f))
            stopped[kind] = [tick,cursor,end]
        phases[p] = dict(fixed=fixed,receiver_same_arrivals=replay,stop=stopped,
                         opening_reference=opening(folder(p,"845armrefopening",True),folder(p,"823826",True)),
                         opening_static=opening(folder(p,"845retireopening",True),folder(p,"823826",True)),
                         static=tail(folder(p,"845retirestatic"),ref,cutoff))
    guards = {}
    for tag in ("both","retire"):
        for fault in ("stop","damage"):
            f = folder(1,"845"+tag+fault)
            tick = int((f/"stop841.txt").read_text())
            end = int((f/"cancel841.txt").read_text())
            rows = window(f)
            assert tick <= end and [r["g"] for r in rows if r["event"]=="reveal"] == list(range(905,910))
            assert not any(r["event"] in ("ppu_dma","ppu_last","reveal") and r["clock"] >= tick for r in rows)
            guards[tag+"_"+fault] = [tick,end]
    fw = ARM/"src/obj-nes-100/firmware.stm"
    menu, recovery = read(OUT/"menu.json"),read(OUT/"base/result.json")
    assert menu["firmware"] == recovery["firmware_sha256"] == base.section.sha(fw)
    assert menu["rows"]["normal"]["released"] and recovery["safe_return"] and recovery["base_restored"]
    q = (OUT/"queue.log").read_text()
    assert "PASS845 queued palette" in q and "Errors: 0, Warnings: 0" in q
    return dict(phases=phases,guards=guards,menu_base=True,queue_RTL=True,
                ARM_bytes=fw.stat().st_size,ARM_limit=212992,
                ROM={s:read(OUT/s/"cost.json") for s in ("client","client-retire","client-bg-retire")},
                scope="Linked ARM/65816; modeled shared SPI, ROM and IRQ. Fixed swaps receiver after 2576. Static uses new receiver from boot. Same-arrival replay isolates service in the next full blank; it does not move work to VB52. SPI occupancy clipped to last OBJ ACK through SEAL head, off-bus includes unclassified CPU and scheduling gaps.")


if __name__ == "__main__":
    Path("analysis/dma845-results.json").write_text(json.dumps(analyze(),indent=2)+"\n",newline="\n")
