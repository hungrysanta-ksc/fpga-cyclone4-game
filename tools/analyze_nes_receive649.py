"""Join input/credit/END timestamps to checked scanout on MMC643, 648 and 649."""
import argparse
import json
from pathlib import Path
from analyze_nes_export636 import run as verify
from analyze_nes_oam618 import work
from analyze_nes_output615 import ROOT, csv_groups, ms, one, read, sha

MODES=("credit","stream","sealed")


def measure(folder,golden):
    v=verify(folder,golden)
    assert work(folder)==work(golden)
    events=read(folder/"events.json")
    window=csv_groups(folder/"window.csv")
    ev=[e for e in events if e["generation"]==954]
    inputs=[e for e in events if e.get("input_generation")==955]
    oldack=one([r for r in window[954] if r["op"]==3],"ack")["clock"]
    rel=lambda t:ms(t-oldack)
    d1=[e for e in inputs if e.get("opcode")=="0xd1"][:7]
    d2=[e for e in inputs if e.get("opcode")=="0xd2"][:7]
    confirms=[next(e for e in inputs if e.get("opcode")=="0xd0" and e["start"]>=pop["clock"]) for pop in d2]
    assert all(read_["clock"]<=pop["start"]<confirm["clock"] for read_,pop,confirm in zip(d1,d2,confirms,strict=True))
    source=one([e for e in events if e["generation"]==955],"source_begin")
    capture=source["capture_ready"]
    bulk=max(r["clock"] for r in window[954] if r["event"]=="ack" and r["op"]==7)
    closed=[e for e in ev if e.get("opcode")=="0xe8" and bytes.fromhex(e["reply"])[3]&2]
    end=closed[0]["clock"]
    clean=next(e["clock"] for e in closed if not bytes.fromhex(e["reply"])[6])
    spi=[e for e in ev if e["event"]=="SPI"]
    seal=next(e for e in spi if e.get("packet_opcode")==3)
    first=d1[0]["start"]
    assert first>=max(capture,end) or first>=bulk and first>=capture
    if source.get("held_tokens649"):
        assert closed[0]["clock"]<=source["clock"]<=first and capture<=source["clock"]
    # Charge only actual intersections, leaving CPU work and callback gaps in
    # the remainder. The earliest observed closed END is a conservative mark.
    begin=max(capture,end)
    busy={}
    for e in spi:
        duration=min(first,e["clock"])-max(begin,e["start"])
        if duration>0:busy[e["opcode"]]=busy.get(e["opcode"],0)+ms(duration)
    noninput=sum(max(0,min(e["clock"],oldack)-max(e["start"],begin)) for e in spi
                 if e["opcode"] not in ("0xd0","0xd1","0xd2","0xd3"))
    first_status=max((e for e in inputs if e.get("opcode")=="0xd0" and e["clock"]<=first),key=lambda e:e["clock"])
    seven_input=[e for e in inputs if e.get("opcode") in ("0xd0","0xd1","0xd2")
                 and first_status["start"]<=e["start"]<confirms[-1]["clock"]]
    last_status=[e for e in spi if e.get("opcode")=="0xe0" and e["clock"]<=first][-1]
    data=bytes.fromhex(last_status["reply"])
    status_out=int.from_bytes(data[3:5],"big")-int.from_bytes(data[5:7],"big")
    # Logical queue ownership at the D1 instant, independent of cached E0.
    heads=sum(e["clock"]<=first and e.get("opcode")=="0xe1" for e in events)
    acks=sum(r["clock"]<=first and r["event"]=="ack" for rows in window.values() for r in rows)
    assert 0<=heads-acks<=4
    # The model allowing held slots can differ from the conservative control
    # only on D0 after a positive E8 END+descriptor for a ready capture and
    # before the last old chunk is consumed. Tail ACK bounds that consume.
    changed_probes=[]
    for g in range(905,957):
        old=[e for e in events if e["generation"]==g]
        last=max([r["clock"] for r in window[g] if r["op"]==7 and r["event"]=="ack"] or [0])
        nxt=one([e for e in events if e["generation"]==g+1],"source_begin")
        snapshots=[e for e in old if e.get("opcode")=="0xe8" and
                   (b:=bytes.fromhex(e["reply"]))[3]==2 and b[6]==1]
        if snapshots:
            lo=max(nxt["capture_ready"],snapshots[0]["clock"])
            changed_probes.extend(g for e in old if e.get("opcode")=="0xd0" and lo<=e["start"]<last)
    rows=v["rows"]
    display={}
    for g in (954,955):
        previous=one(window[g-1],"reveal")["clock"]
        seal_rows=[r for r in window[g] if r["op"]==3]
        push=next(e for e in events if e["generation"]==g and e.get("packet_opcode")==3)
        display[g]=dict(SEAL_SPI_start_ms=ms(push["start"]-previous),SEAL_load_ms=ms(one(seal_rows,"load")["clock"]-previous),
                        SEAL_line=one(seal_rows,"load")["line"],upload_line=one(seal_rows,"upload165_entry")["line"])
    return dict(input955=dict(capture=rel(capture),END_with_or_without_slot=rel(end),last_tile_ACK=rel(bulk),
        clean_END=rel(clean),old_SEAL_SPI_end=rel(seal["clock"]),first_D1=rel(first),absolute_D1=first,
        capture_to_D1_ms=ms(first-capture),from_953_display_ms=ms(first-one(window[953],"reveal")["clock"]),
        old_ACK_from_953_display_ms=ms(oldack-one(window[953],"reveal")["clock"]),
        end_to_first_D1_bus_ms=busy,
        closed_to_ACK_ms=ms(oldack-begin),other_SPI_to_ACK_ms=ms(noninput),
        seven_input_SPI_ms=ms(sum(e["clock"]-e["start"] for e in seven_input)),
        # Excludes inter-transaction ARM restore, scheduling, CRC and guards.
        frozen_schedule_bus_margin_ms=ms(oldack-begin-noninput-sum(e["clock"]-e["start"] for e in seven_input)),
        unoccupied_ms=ms(first-begin)-sum(busy.values()) if first>=begin else None,
        last_E0_clock=rel(last_status["clock"]),last_E0_outstanding=status_out,outstanding_at_first_D1=heads-acks,
        pops_before_ACK=sum(e["clock"]<=oldack for e in d2),confirmed_before_ACK=sum(e["clock"]<=oldack for e in confirms),
        first_seven_D1=[rel(e["start"]) for e in d1],first_seven_D2=[rel(e["clock"]) for e in d2],
        seventh_confirm=rel(confirms[-1]["clock"]),D3=rel(next(e["clock"] for e in inputs if e.get("opcode")=="0xd3")),
        held_tokens=source.get("held_tokens649",[])),first_D0_opportunities_with_held_slot=changed_probes,
        held_export_generations=[e["generation"] for e in events if e.get("held_tokens649")],
        display=display,intervals=[rows[g]["interval_VB"] for g in range(951,956)],line951=rows[951]["line"],wait957=rows[957]["final_waits"],
        dense_VB=v["dense_VB"],dense_ms=v["dense_mean_ms"],last_ACK=v["last_ACK"],
        absolute954=one(window[954],"reveal")["frame"],absolute955=one(window[955],"reveal")["frame"],
        schedule=v["measured"],pins={k:sha(folder/k) for k in ("events.json","joint.json","window.csv","packets.jsonl","seal528.csv")})


def analyze(a):
    prior=read(ROOT/"analysis/tail648-verification.json")
    phases={}
    for n in (1,2):
        golden=a.traces/f"nes-front638-both{n}h"
        controls=[measure(a.traces/f"nes-tail648-{tag}",golden) for tag in (f"base{n}a",f"packed{n}")]
        base,packed=controls
        for c,label in zip(controls,("base","candidate")):
            reference=prior["phases"][str(n)][label]
            assert c["last_ACK"]==reference["last_ACK"] and not c["first_D0_opportunities_with_held_slot"]
        cases={"MMC643":base,"648":packed}
        for mode in MODES:
            x=measure(a.traces/f"nes-receive649-{mode}{n}",golden)
            assert x["schedule"]["parameters"]==packed["schedule"]["parameters"]
            assert x["schedule"]["client_SHA256"]==packed["schedule"]["client_SHA256"]
            assert x["schedule"]["firmware_SHA256"]==sha(a.build/mode/"src/obj-nes-100/firmware.stm")
            assert x["input955"]["pops_before_ACK"]<=7
            # Elapsed-budget comparison only. Use the 648 three-VBlank
            # duration without shifting any SPI, DMA or ACK in either run.
            q=x["input955"]
            x["seventh_confirm_vs_648_three_VB_duration_ms"]=(
                q["old_ACK_from_953_display_ms"]+q["seventh_confirm"]-packed["input955"]["old_ACK_from_953_display_ms"])
            x["gates"]=dict(first=x["input955"]["capture_to_D1_ms"]<packed["input955"]["capture_to_D1_ms"],
                recovered=x["input955"]["confirmed_before_ACK"]==7,control954=x["intervals"][3]==3,
                target955=x["intervals"][4]==3,protected=x["line951"]<=246 and x["wait957"]==0 and x["intervals"][1]<=4,
                dense=x["dense_VB"]<base["dense_VB"] and x["dense_ms"]<base["dense_ms"],last=x["last_ACK"]<base["last_ACK"])
            x["time_pass"]=all(x["gates"].values())
            x["last_ACK_delta_ms"]=ms(x["last_ACK"]-base["last_ACK"])
            cases[mode]=x
        phases[n]=cases
    guards={}
    for mode in MODES:
        folder=a.build/mode
        firmware=folder/"src/obj-nes-100/firmware.stm";fw=sha(firmware)
        pins={}
        for name in ("receive","menu","queue","seal"):
            path=folder/(name+".json")
            assert read(path)["firmware"]==fw
            pins[name]=sha(path)
        for fault in ("none","program","done","busy","token"):
            path=folder/f"base-{fault}/result.json"
            r=read(path)
            assert r["passed"] and r["firmware_sha256"]==fw and r["safe_return"]==r["base_restored"]==int(fault=="none")
            pins[fault]=sha(path)
        guards[mode]=dict(flash_B=firmware.stat().st_size,firmware=fw,pins=pins)
    return dict(phases=phases,guards=guards,RTL=read(a.rtl/"result.json"),
        scope="53 accepted generations; linked ARM CPI2, measured driver overhead, modeled SPI/ROM and Mesen CPU. Sealed mode uses a witnessed closed END with staged token, no early prepare/COMMIT. Hardware FPS unmeasured.")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("traces","rtl","build","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
