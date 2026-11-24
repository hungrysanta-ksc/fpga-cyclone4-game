"""Compare matched full-link runs and bound raw preupload on observed idle polls."""
import argparse
import json
from collections import Counter
from pathlib import Path

from check_nes_bg976 import map_payloads, same_trace
from check_nes_blank959 import rows
from check_nes_menu533 import check as check_menu
from check_nes_plan975 import directory, milliseconds, packet_path, read, sha
from check_nes_tail979 import display
from nes_section983 import work
from test_nes_raw506_joint import PERIOD


def compare(temp,phase,tag,cutoff):
    trace=directory(temp,phase,tag,"cold")
    ref=directory(temp,phase,"978returned","cold")
    assert map_payloads(trace)==map_payloads(ref)
    for g in range(905,913):
        assert sha(trace/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb")
    def records(d):
        return [(b["g"],b["records"]) for b in read(d/"e9931.json")]
    assert records(trace)==records(ref)
    marks=display(trace)
    cmds,ledger=packet_path(trace,911)
    whole=cmds[-len(ledger):]
    sections={int.from_bytes(b[10:12],"little"):q for c,q in zip(whole,ledger,strict=True)
              for b in [bytes.fromhex(c[3])] if b[:2]==bytes((2,5))}
    first,last=sections[1121],sections[1322]
    body=b"".join(bytes.fromhex(c[3])[16:] for c in whole if bytes.fromhex(c[3])[:2]==bytes((2,5))
                  and int.from_bytes(bytes.fromhex(c[3])[10:12],"little")>=1121)
    assert len(body)==441 and all(len(set(body[i+j:i+64:2]))==1 for i in (0,64,128) for j in (0,1))
    sizes=[int.from_bytes(body[i:i+2],"little") for i in (435,437,439)]
    assert sizes==[21]*3
    for i,n in enumerate(sizes):
        assert not any(body[192+81*i+n:192+81*(i+1)])
    # Cost a separate future format using the observed row widths and table
    # lengths. Round-trip all three padded tables, including their terminators.
    packed=body[435:]+b"".join(body[i:i+2] for i in (0,64,128))
    packed+=b"".join(body[192+i*81:192+i*81+n] for i,n in enumerate(sizes))
    at=12
    decoded=b"".join(packed[i:i+2]*32 for i in (6,8,10))
    for i in (0,2,4):
        n=int.from_bytes(packed[i:i+2],"little")
        decoded+=packed[at:at+n].ljust(81,b"\0")
        at+=n
    assert at==len(packed) and decoded+packed[:6]==body
    obs=temp/f"nes-983observer-{tag}-p{phase}"
    log=rows(obs/"raw983.csv")
    assert [(x["event"],int(x["clock"])) for x in log if x["event"]!="empty"]==[
        ("first",first["ack"]),("last",last["ack"])]
    assert all(x["visible"]!=x["target"] for x in log)
    # At the target blank, each empty-queue 0x6000 read is a possible first
    # grant. Stop a row chain at the next E1 arrival. One 64B row already
    # started may complete after that arrival, before the public deadline.
    windows={}
    for x in log:
        at=int(x["clock"])
        if x["event"]!="empty" or not 225<=int(x["line"])<=246 or at>=cutoff:
            continue
        idx=int(x["index"])
        if idx not in windows:
            end=cmds[idx-1][2]
            assert end>at
            count=min(3,(end-at+511)//512,(cutoff-at)//512)
            windows[idx]=dict(poll=at,until_next_E1=end-at,line=int(x["line"]),ideal_rows=count)
    ev=read(trace/"events.json")
    ready,=(e["capture_ready"] for e in ev if e["event"]=="source_begin" and e["generation"]==911)
    ack909=next(e["ACK_masterclock"] for e in read(trace/"joint.json")["frames"] if e["generation"]==909)
    commit=max(e["clock"] for e in ev if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    origin=ready-240*341*4
    target=origin+round((ack909-origin)/PERIOD)*PERIOD
    frames=read(trace/"joint.json")["frames"]
    beam=rows(trace/"window.csv")
    reveals=[int(x["frame"]) for x in beam if x["event"]=="reveal"]
    return dict(first=first,last=last,seal=marks["seal"],upload=marks["upload"],reveal=marks["reveal911"],
                reveal908=marks["reveal908"],early909=marks["early909_B"],margin910_ms=milliseconds(target-commit),
                cutoff_clock=cutoff,interval911=reveals[-2]-reveals[-3],dense6=reveals[-1]-reveals[1],
                ACK912=frames[-1]["ACK_masterclock"],windows=windows,
                optimistic_raw_B=64*min(3,sum(w["ideal_rows"] for w in windows.values())),
                dma911=marks["dma"],sizes=sizes,raw_words=[body[i:i+2].hex() for i in (0,64,128)],
                compact_projection=dict(payload_B=len(packed),wire_B=19+len(packed),
                    wire_only_saving_ms=(441+2*19-19-len(packed))*8/2625),
                hashes={"cpu":sha(trace/"client.sfc"),"observed":sha(obs/"raw983.csv"),
                        "arm":read(trace/"joint.json")["firmware_SHA256"]})


def main(temp):
    result=dict(phases={},guards={},flash={})
    for phase in (1,2):
        d=directory(temp,phase,"978returned","cold")
        prof=directory(temp,phase,"983profile","cold")
        same_trace(prof,d)
        times=read(prof/"writes983.json")
        # 982's neutral callbacks recorded the absolute end of line 246.
        cutoff=read(Path("analysis/cutoff982-results.json"))["phases"][str(phase)]["ref"]["cutoff_exclusive_clock"]
        cases={tag:compare(temp,phase,tag,cutoff) for tag in ("978returned","983raw","983tables")}
        ref=cases["978returned"]
        ev=read(d/"events.json")
        stages={}
        for name,ready in (("first",max(times["raw"],times["table_head"])),
                            ("last",max(times["table_tail"],times["lengths"]))):
            issue=ref[name]["issue"]
            spi=Counter()
            for e in ev:
                if e.get("event")=="SPI":
                    overlap=min(issue,e["clock"])-max(ready,e["start"])
                    if overlap>0:
                        spi[e["opcode"]]+=overlap
            total=issue-ready
            stages[name]=dict(source_ready_to_issue_ms=milliseconds(total),
                assembled_to_issue_ms=milliseconds(issue-times["joined_"+name]),
                SPI_ms={k:milliseconds(v) for k,v in spi.items()},outside_SPI_ms=milliseconds(total-sum(spi.values())))
        for c in cases.values():
            c["relative_ms"]={k:milliseconds(c[k]["ack"]-ref[k]["ack"]) for k in ("first","last")}
            c["relative_ms"].update(seal=milliseconds(c["seal"][0]-ref["seal"][0]),
                                    ACK912=milliseconds(c["ACK912"]-ref["ACK912"]))
        result["phases"][phase]=dict(writes=times,preparation=stages,cases=cases)
    for mode in ("raw","tables"):
        image,=(work(mode)/"link").rglob("firmware.stm")
        result["flash"][mode]=image.stat().st_size
        assert sha(image)==result["phases"][1]["cases"]["983"+mode]["hashes"]["arm"]
        menu=check_menu(work(mode)/"link/src","966")
        result["guards"][mode+"_menu"]={k:v["released"] for k,v in menu["rows"].items()}
        for fault,status in (("bad_seal",224),("stop_decode",228)):
            d=temp/f"nes-983observer-983{mode}-p1-{fault}"
            r=read(d/"result.json")
            assert r["passed"] and r["commits"]==6 and r["last_status"]==status
            assert sha(d/"retained.rgb")==sha(directory(temp,1,"983"+mode,"cold")/"frame-910.rgb")
            result["guards"][mode+"_"+fault]=status
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(main(a.temp),indent=2)+"\n")
