"""Compare palette final stores, SPI occupancy, receiver admission and VBlank."""
import json
from pathlib import Path
from analyze_nes_dma845 import tail
from analyze_nes_tail844 import read
from analyze_nes_section841 import folder, opening, packets, window
from nes_palette846 import BASE, OUT, link, base


def measure(mode,phase,test):
    tag = f"846{mode}{test}" + ("02" if mode=="control" and test=="boot" else "")
    f = folder(phase,tag)
    ref = folder(phase,"832base")
    cutoff = read(Path("analysis/section841-results.json"))["phases"][str(phase)]["VB52_start"]+22*1364
    d = tail(f,ref,cutoff)
    assert d["ARM_SHA256"] == base.section.sha(link(mode)/"src/obj-nes-100/firmware.stm")
    log = [json.loads(x) for x in (f/"palette846.jsonl").read_text().splitlines()]
    wire = [e for e in read(f/"events.json") if e["event"]=="SPI" and e["opcode"]=="0xe1"]
    pk = packets(f)
    rows = window(f)
    detailed = []
    for g in (909,910):
        stores = set()
        calls = [r for r in log if r["event"]=="wire" and r["section"]==3 and r["g"]==g]
        for r in calls:
            assert bytes.fromhex(r["cgram"]) == (f/f"colors636-{g}.bin").read_bytes()[:512]
            assert r["last_store"] <= r["clock"]
            stores.add(r["last_store"])
        assert len(stores)==1
        hits = [(i,q) for i,q in enumerate(pk) if int.from_bytes(q[8:10],"little")==g and q[1]==3]
        assert len(hits)==len(calls)
        times = []
        for call,(i,q) in zip(calls,hits,strict=True):
            head = next(r for r in rows if r["index"]==i+1 and r["event"]=="load")
            ack = next(r for r in rows if r["index"]==i+1 and r["event"]=="ack")
            e = wire[i]
            assert call["offset"] == int.from_bytes(q[10:12],"little")
            assert call["clock"] <= e["start"] <= e["clock"] <= head["clock"] <= ack["clock"]
            times.append(dict(offset=call["offset"],call=round(call["clock"]),
                              SPI_start=round(e["start"]),SPI_end=round(e["clock"]),
                              head=[head[k] for k in ("clock","frame","line")],
                              ACK=[ack[k] for k in ("clock","frame","line")]))
        detailed.append(dict(g=g,last_store=round(stores.pop()),packets=times,
                             calls=[{k:v for k,v in r.items() if k!="cgram"} for r in log if r["g"]==g and r["event"]!="wire"]))
    d["palette"]=detailed
    j=read(f/"joint.json")
    d.update(ARM_stack_low=j["observed_stack_low"],wire=j["wire_B"])
    return d


def analyze():
    phases={}
    for p in (1,2):
        boot={m:measure(m,p,"boot") for m in ("control","compute","issue","first","safe","queued")}
        fixed={m:measure(m,p,"fixed") for m in ("compute","issue","first","safe","queued")}
        for comparison in (boot,fixed):
            assert comparison["safe"]["ACK"] == comparison["first"]["ACK"]
        phases[p]=dict(boot=boot,fixed=fixed,
                       opening={m:opening(folder(p,f"846{m}refopening",True),folder(p,"823826",True)) for m in ("issue","safe","queued")})
    ownership = read(OUT/"ownership.json")
    assert len(ownership["safe"]["cases"]) == 32
    assert not any(r["polls"] for r in ownership["safe"]["cases"] if not r["prepared"])
    guards = {}
    for m in ("issue","safe","queued"):
        for fault in ("pulse","coverage"):
            f=folder(1,f"846{m}{fault}")
            rows=window(f)
            assert [r["g"] for r in rows if r["event"]=="reveal"] == list(range(905,909))
            bad=[r for r in rows if r["event"]=="ack" and r["value"]>=224]
            assert [(r["g"],r["op"],r["value"]) for r in bad] == [(909,3,228 if fault=="pulse" else 224)]
            if fault=="pulse":
                tick=int((f/"stop837.txt").read_text())
                assert not any(r["clock"]>=tick and r["event"] in ("ppu_dma","ppu_last","reveal") for r in rows)
            guards[m+"_"+fault]=bad[0]["value"]
    for mode,suffix in (("safe",""),("queued","-queued")):
        fw=base.section.sha(link(mode)/"src/obj-nes-100/firmware.stm")
        menu,recovery=read(OUT/f"menu{suffix}.json"),read(OUT/f"base{suffix}/result.json")
        assert fw == menu["firmware"] == recovery["firmware_sha256"] == ownership[mode]["firmware"]
        assert menu["rows"]["normal"]["released"] and recovery["base_restored"] and recovery["safe_return"]
    q=(OUT/"queue.log").read_text()
    assert "PASS846 OAM" in q and "Errors: 0, Warnings: 0" in q
    rtl={}
    for name in ("nes_sink_bridge165.sv","nes_sink_bus165.sv","nes_domain_reset124.sv","nes_sink_spi165.sv"):
        original=base.TEMP/"nes-trial816-board822held"/name
        tested=base.TEMP/"nes-queue846"/name
        rtl[name]=base.section.sha(original)
        assert rtl[name]==base.section.sha(tested)
    return dict(phases=phases,ownership=ownership,guards=guards,menu_base=True,queue_RTL=True,queue_RTL_SHA256=rtl,
                board="Unchanged; no new Quartus FIT or STA",
                receiver_ROM_bytes=read(base.section.REFERENCE/"build.json")["physical_ROM_B"],
                cost={m:dict(Flash=(link(m)/"src/obj-nes-100/firmware.stm").stat().st_size,
                                         size=(link(m)/"size.log").read_text()) for m in ("control","compute","issue","first","safe","queued")},
                scope="Actual linked M4 and 65816 with modeled SPI/IRQ/ROM slots. Boot keeps 837 throughout. Fixed swaps receiver after 2576 ACK. Matching payload, colors and display checked against MMC826 clip. No physical measurement.")


if __name__=="__main__":
    Path("analysis/palette846-results.json").write_text(json.dumps(analyze(),indent=2)+"\n",newline="\n")
