"""Account for the last required return, receiver work and occupied precheck time."""
import argparse
import json
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_menu533 import check as menu
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_tile985 import transfers
from nes_tail986 import work
from test_nes_raw506_joint import PERIOD


def measure(temp,phase,tag,cutoff):
    d=directory(temp,phase,tag,"cold")
    ref=directory(temp,phase,"978returned","cold")
    obs=temp/f"nes-tail986-trace-{tag}-p{phase}"
    c,ledger=packet_path(d,911)
    prior,_=packet_path(ref,911)
    # Cross-section order and FIFO sequence can change. Verify each section's
    # original ordered stream, including all identities and tile payloads.
    def streams(cmds):
        groups={}
        for gen,op,_,wire,bulk,*_ in cmds:
            b=bytes.fromhex(wire)
            groups.setdefault((gen,b[1]),[]).append((b[:2]+b[4:],bulk))
        return groups
    assert streams(c)==streams(prior) and map_payloads(d)==map_payloads(ref)
    assert sha(d/"client.sfc")==sha(ref/"client.sfc")
    assert all(sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb") for g in range(905,913))
    m=transfers(d)
    assert m["target"]==44
    actual=rows(d/"window.csv")
    reveal912=next(int(x["frame"]) for x in actual if x["g"]=="912" and x["event"]=="reveal")
    ev=read(d/"events.json")
    frames=read(d/"joint.json")["frames"]
    origin=next(e["capture_ready"] for e in ev if e["event"]=="source_begin" and e["generation"]==911)-240*341*4
    ack909=next(x["ACK_masterclock"] for x in frames if x["generation"]==909)
    commit=max(e["clock"] for e in ev if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    r=rows(obs/"checks986.csv")
    def first(event):
        return int(next(x["clock"] for x in r if x["event"]==event))
    def seen(events):
        return {int(x["offset"]):int(x["value"]) for x in r if x["event"] in events}
    scroll=seen(["read_validate181"])
    table=seen(["read_table181","read_table_end181","read_length181"])
    literals={}
    for cmd,q in zip(c[-len(ledger):],ledger,strict=True):
        b=bytes.fromhex(cmd[3])
        if b[:2]==bytes((2,5)):
            offset=int.from_bytes(b[10:12],"little")
            literals[offset]=q
            for pos,v in (scroll if offset==0 else table).items():
                if 0<=pos-offset<len(b)-16:assert v==b[16+pos-offset]
    assert list(scroll)==[0,5,10,15,20] and sum(scroll.values())==224
    assert len(table)==69 and sum(i<1322 for i in table)==9
    assert first("seal")==m["seal"][0] and first("upload165_entry")==m["validated"][0]
    last=literals[1322]
    all_done=ledger[-2]["ack"]
    validate=first("upload165_entry")-first("seal")
    scroll_time=first("scroll_end181")-first("validate181")
    table_time=first("coverage212")-first("table181")
    color=m["reveals"][911][0]-m["dma"][-2]["start"][0]
    polls=[]
    for x in r:
        idx=int(x["index"])-1
        at=int(x["clock"])
        if x["event"]!="empty" or idx>=len(c) or at>=cutoff:continue
        end=min(cutoff,c[idx][2])
        if end<=at:continue
        dma=sum(max(0,min(end,v["end"][0])-max(at,v["start"][0])) for v in m["dma"])
        polls.append(dict(index=idx+1,at=at,until=end,dma=dma))
    # Optimistic upper bound: exclude measured first-to-last DMA byte time,
    # but not setup, polling, STOP, dispatch or storage of a validation result.
    table_budget=sum(x["until"]-x["at"]-x["dma"] for x in polls if x["at"]>=last["ack"])
    first_scroll_gap=max((x["until"]-x["at"]-x["dma"] for x in polls
                          if literals[0]["ack"]<=x["at"]<literals[1121]["load"]),default=0)
    assert first_scroll_gap>=scroll_time
    return dict(literal_first=literals[1121],literal_last=last,last_ordinary=ledger[-2],seal_load=ledger[-1]["load"],
                seal=m["seal"],reveal908=m["reveals"][908],reveal911=m["reveals"][911],early909=m["early909_B"],
                early911=m["early_B"],complete_early911_by246=m["completed_transfers_by_246_B"],
                capture910_ms=ms(origin+round((ack909-origin)/PERIOD)*PERIOD-commit),
                interval911=m["interval911"],six=reveal912-m["reveals"][906][1],ACK912=frames[-1]["ACK_masterclock"],
                checks=dict(scroll_clocks=scroll_time,table_clocks=table_time,whole_clocks=validate,
                            scroll_offsets=sorted(scroll),table_offsets=sorted(table)),
                polls=polls,longest_early_scroll_window_ms=ms(first_scroll_gap),table_window_upper_ms=ms(table_budget),
                optimistic_margin_ms=ms(cutoff-all_done-(validate-scroll_time-table_time)-192*8-color),
                provenance={f:sha(d/f) for f in ("events.json","client.sfc","window.csv","packets.jsonl")},
                read_trace_sha256=sha(obs/"checks986.csv"))


def palette_lifetime(temp,phase):
    d=directory(temp,phase,"978returned","cold")
    commands,ledger=packet_path(d,911)
    images={}
    for g in (909,910,911):
        data=bytearray()
        for gen,_,_,wire,*_ in commands:
            b=bytes.fromhex(wire)
            if gen!=g or b[1]!=3:continue
            assert int.from_bytes(b[10:12],"little")==len(data)
            payload=b[16:]
            assert len(payload)==int.from_bytes(b[12:14],"little")
            if b[0]==4:
                run=int.from_bytes(b[14:16],"little")
                assert len(payload)==2 and not run%2
                payload*=run//2
            else:assert b[0]==2
            data.extend(payload)
        images[g]=(d/f"colors636-{g}.bin").read_bytes()
        assert len(data)==512 and data==images[g][:512]==images[909][:512]
    records=[]
    for cmd,q in zip(commands[-len(ledger):],ledger,strict=True):
        b=bytes.fromhex(cmd[3])
        if b[1]==3:records.append(dict(offset=int.from_bytes(b[10:12],"little"),
                                       wire_B=len(b)+3,spi=q["arrive"]-q["issue"],service=q["ack"]-q["load"]))
    obs=temp/f"nes-tail986-trace-978returned-p{phase}-palette"
    marks={x["event"]:[int(x[k]) for k in ("clock","offset","value")] for x in rows(obs/"checks986.csv")
           if x["event"] in ("ack909","ack910","begin911","before_palette")}
    assert list(marks)==["ack909","ack910","begin911","before_palette"]
    assert all(entry[1:]==[0,0] for entry in marks.values()) and read(obs/"result.json")["passed"]
    return dict(records=records,wire_B=sum(r["wire_B"] for r in records),
                spi_ms=ms(sum(r["spi"] for r in records)),service_ms=ms(sum(r["service"] for r in records)),
                clock_WRAM_mismatches_CGRAM_mismatches=marks,read_trace_sha256=sha(obs/"checks986.csv"),
                oam_tail_differences={g:sum(a!=b for a,b in zip(images[g][624:],images[911][624:],strict=True))
                                      for g in (909,910)})


def analyze(temp):
    out=dict(phases={},guards={},flash_B={})
    for p in (1,2):
        cutoff=read(Path("analysis/tile985-results.json"))["phases"][str(p)]["bound"]["cutoff_exclusive"]
        cases={tag:measure(temp,p,tag,cutoff) for tag in ("978returned","986high","986split","986fifo")}
        base=cases["978returned"]
        for v in cases.values():
            v["delta_ms"]={k:ms(v[k]["ack"]-base[k]["ack"]) for k in ("literal_last","last_ordinary")}
            v["delta_ms"].update(seal=ms(v["seal"][0]-base["seal"][0]),ACK912=ms(v["ACK912"]-base["ACK912"]))
        prior=read(Path("analysis/section983-results.json"))["phases"][str(p)]
        assert prior["cases"]["978returned"]["last"]==base["literal_last"]
        q=base["literal_last"]
        marks=prior["writes"]
        detail=dict(source_to_assembled=ms(marks["joined_last"]-max(marks["table_tail"],marks["lengths"])),
                    assembled_to_issue=ms(q["issue"]-marks["joined_last"]),spi=ms(q["arrive"]-q["issue"]),
                    queue=ms(q["load"]-q["arrive"]),service=ms(q["ack"]-q["load"]))
        out["phases"][p]=dict(baseline_breakdown_ms=detail,source_to_issue_SPI_ms=prior["preparation"]["last"]["SPI_ms"],
                              palette=palette_lifetime(temp,p),cases=cases)
    for mode in ("high","split","fifo"):
        d=work(mode)/"link"
        out["flash_B"][mode]=next(d.rglob("firmware.stm")).stat().st_size
        out.setdefault("menu",{})[mode]={k:v["released"] for k,v in menu(d/"src","966")["rows"].items()}
        for fault,status in (("bad_seal",224),("stop_decode",228)):
            guard=temp/f"nes-986{mode}-p1-{fault}"
            r=read(guard/"result.json")
            assert r["passed"] and r["last_status"]==status and r["commits"]==6
            assert sha(guard/"retained.rgb")==sha(directory(temp,1,"978returned","cold")/"frame-910.rgb")
            out["guards"][mode+"_"+fault]=status
    for p,fault in ((1,"scroll"),(2,"table")):
        d=temp/f"nes-tail986-trace-986high-p{p}-{fault}"
        r=read(d/"result.json")
        injection,=(x for x in rows(d/"checks986.csv") if x["event"]=="damaged")
        assert int(injection["offset"])==(0 if p==1 else 1475)
        assert r["passed"] and r["commits"]==6 and r["last_status"]==224
        assert sha(d/"retained.rgb")==sha(directory(temp,p,"978returned","cold")/"frame-910.rgb")
        out["guards"]["late_WRAM_"+fault]=dict(offset=int(injection["offset"]),status=224)
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8")
