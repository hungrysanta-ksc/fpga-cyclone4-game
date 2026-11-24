"""Check generation 907's real DMA order, ROM grant deadlines and canceled publication."""
import argparse
import json
from pathlib import Path
from check_nes_blank959 import rows
from check_nes_output970 import counters, packet_path, replay
from check_nes_plan975 import directory, milliseconds as ms, read, sha
from nes_map997 import PACKED, ROM
from test_nes_raw506_joint import PERIOD


def guard(temp, phase, fault):
    d = directory(temp, phase, "997static", "cold")
    commands, _ = packet_path(d, 907)
    return replay(temp, d, temp/f"nes-map997-{fault}-p{phase}", "fixed", commands, 907, fault)


def inspect(d, ref, calendar):
    from bisect import bisect_left
    j = read(d/"joint.json")
    assert j["passed"] and j["commits"] == 8
    for g in range(905, 913):
        assert sha(d/f"frame-{g}.rgb") == sha(ref/f"frame-{g}.rgb")
    w = rows(d/"window.csv")
    reveals = {int(r["g"]): [int(r[k]) for k in ("clock","frame","line")] for r in w if r["event"]=="reveal"}
    e = read(d/"events.json")
    ready = next(r["capture_ready"] for r in e if r["generation"]==911 and r["event"]=="source_begin")-240*1364
    last_d2 = max(r["clock"] for r in e if r.get("input_generation")==910 and r.get("opcode")=="0xd2")
    edge = ready+round((j["frames"][4]["ACK_masterclock"]-ready)/PERIOD)*PERIOD
    commands, ledger = packet_path(d, 907)
    dma = [[int(r[k]) for k in ("clock","frame","line","value")] for r in w if r["g"]=="907" and r["event"]=="ppu_dma"]
    latch = next(r for r in rows(d/"budget685.csv") if r["generation"]=="907")
    cutoff = int(latch["latch_clock"])+(247-int(latch["line"]))*1364-int(latch["h"])
    c = counters(d,907)
    tiles = [json.loads(line) for line in (d/"producer.jsonl").read_text().splitlines()]
    obj, = (r for r in tiles if r["generation"]==907 and r["kind"]==1)
    assert obj["bytes"]==448
    grants = [r for r in read(d/"grants904.json") if r[0]==907]
    request, first, reply = grants[0][2:]
    assert calendar.select(request)==(first,reply)
    period, offset = divmod(request,calendar.period)
    pos = bisect_left(calendar.starts,offset)
    previous = (period-int(pos==0))*calendar.period+calendar.starts[pos-1]
    planner = next(r["clock"] for r in e if r["event"]=="planner_enter" and r["generation"]==907)
    e9 = next(r for r in e if r.get("opcode")=="0xe9" and r["generation"]==907)
    maps = []
    for cmd, item in zip(commands[-len(ledger):],ledger,strict=True):
        b = bytes.fromhex(cmd[3])
        if item["section"]==2 and item["op"]==2:
            maps.append(dict(offset=int.from_bytes(b[10:12],"little"),returned=item["ack"],
                             relative_first_dma_ms=ms(item["ack"]-dma[0][0])))
    assert [r["offset"] for r in maps]==list(range(0,1345,192))
    return dict(reveals=reveals,interval907=reveals[907][1]-reveals[906][1],
                six=reveals[912][1]-reveals[906][1],ACK912=j["frames"][-1]["ACK_masterclock"],
                early909_B=sum(int(r["value"]) for r in w if r["g"]=="909" and r["event"]=="ppu_dma" and int(r["frame"])<reveals[909][1]),
                capture910_ms=ms(edge-last_d2),dma907=dma,map_returns=maps,section_clock=c,cutoff_exclusive=cutoff,
                OBJ=dict(token=obj["token"],planner=planner,E9_issue=e9["start"],E9_accepted=e9["clock"],
                         prior_calendar_grant=previous,prior_grant_to_planner_ms=ms(planner-previous),
                         first_request=request,first_grant=first,last_reply=grants[-1][-1],requests=len(grants),
                         first_grant_wait_ms=ms(first-request),ready=obj["producer"],valid_E8=obj["observed"],
                         past_cutoff_ms=ms(obj["producer"]-cutoff),packet=next(r for r in ledger if r["op"]==7 and r["section"]==1)),
                cross_sizes=[int(r["value"]) for r in w if r["event"]=="cross997" and r["g"]=="907"])


def analyze(t):
    from test_nes_service509_schedule import Calendar
    calendar = Calendar(t/"nes-service509-rom03")
    result = dict(stored_65816_B={},phases={})
    for name, root in (("978",PACKED),("997",ROM)):
        info=read(root/"build.json")
        result["stored_65816_B"][name]=64+info["loader_B"]+info["encoded_B"]
    for p in (1,2):
        ref=directory(t,p,"978returned","cold")
        cases=result["phases"][p]={}
        for tag in ("978returned","997matched","997static"):
            d=directory(t,p,tag,"cold")
            a=cases[tag]=inspect(d,ref,calendar)
            assert a["six"]==13 and a["interval907"]==2 and a["capture910_ms"]>0
            base=cases["978returned"]
            a["delta_ACK912_ms"]=ms(a["ACK912"]-base["ACK912"])
            assert a["dma907"][0][3]==(768 if tag=="978returned" else 1152)
            assert sum(v[3] for v in a["dma907"])==sum(v[3] for v in base["dma907"])
            if tag!="978returned":assert a["cross_sizes"]==[960,1152]
        faults=cases["guards"]={}
        for mode,status in (("stop_decode",228),("bad_seal",224)):
            d=t/f"nes-map997-{mode}-p{p}"
            j=read(d/"result.json")
            assert j["passed"] and j["commits"]==2 and j["last_status"]==status
            assert sha(d/"retained.rgb")==sha(ref/"frame-906.rgb")
            assert any(r["g"]=="907" and r["event"]=="ppu_dma" and r["value"]=="1152" for r in rows(d/"window.csv"))
            faults[mode]=dict(commits=2,status=status,previous_RGB_retained=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--guard",choices=("stop_decode","bad_seal"))
    p.add_argument("--phase",type=int,choices=(1,2))
    a=p.parse_args()
    if a.guard and a.phase:
        guard(a.temp,a.phase,a.guard)
    elif a.out:
        a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf8",newline="\n")
    else:
        p.error("supply --out or --guard with --phase")
