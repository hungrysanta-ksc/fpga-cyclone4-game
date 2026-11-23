"""Partition OBJ latency at the physical bank release and the matching E8 response."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_output970 import deadline
from analyze_nes_palette971 import commands, measure
from check_nes_blank959 import directory, read, sha
from check_nes_output970 import counters, packet_path, replay
from nes_token973 import source
from test_nes_banks557 import MASTER, crc

MODES=("control","prefix","before96","before232")


def ms(ticks):
    return round(ticks*1000/MASTER,4)


def inspect(temp,phase,mode):
    folder=directory(temp,phase,"973"+mode,"cold")
    reference=directory(temp,phase,"971control","cold")
    m=measure(folder,reference)
    if mode in ("control","prefix"):
        previous=directory(temp,phase,"971control" if mode=="control" else "972prefix","cold")
        for name in ("events.json","producer.jsonl","window.csv","records.bin"):
            assert sha(folder/name)==sha(previous/name)
    events=read(folder/"events.json")
    e8={e["start"]:e for e in events if e.get("opcode")=="0xe8"}
    matching=[]
    for raw in (folder/"e8-973.jsonl").read_text().splitlines():
        start,wire=json.loads(raw)
        data=bytes.fromhex(wire)
        assert len(data)==20 and data[1:3]==b"\xd7\x04" and crc(data[1:19],8,7,0)==data[19]
        if data[6] and int.from_bytes(data[12:14],"little")==911 and int.from_bytes(data[14:18],"little")==30:
            matching.append((e8[start],data))
    first,reply=matching[0]
    assert reply[3]==2 and int.from_bytes(reply[4:6],"big")==1 and reply[6]==1 and reply[18]==0
    wires=[bytes.fromhex(p[3]) for p in commands(folder,911) if p[:2]==(911,7)]
    assert [int.from_bytes(w[16:20],"little") for w in wires]==[28,29,30]
    packet=wires[-1]
    assert (reply[7],reply[8:10],reply[10:12],reply[12:14],reply[14:18])==(
        packet[1],packet[14:16],packet[10:12],packet[8:10],packet[16:20])
    last=m["tiles911"][-1]
    assert last["token"]==30 and last["bytes"]==384
    issue=[p for p in m["packets911"] if p["op"]==7][-1]["issue"]
    released=dict(read(folder/"returns904.json"))[29]
    marks=[last["observed"],released,first["start"],first["clock"],issue]
    assert marks==sorted(marks)
    labels=("published_to_previous_release","release_to_query","query_wire","valid_reply_to_issue")
    stages={k:ms(y-x) for k,x,y in zip(labels,marks,marks[1:])}
    occupied=Counter()
    for e in events:
        if "start" in e:
            clipped=min(e["clock"],first["start"])-max(e["start"],released)
            if clipped>0:
                key=e["opcode"] if e["opcode"]!="0xe1" else f"E1 op{e['packet_opcode']}"
                occupied[key]+=clipped
    remaining=first["start"]-released-sum(occupied.values())
    assert remaining>=-1
    occupied["outside_SPI"]=remaining
    seal=counters(folder,911)
    d=deadline(folder,911)
    _,ledger=packet_path(folder,911)
    last_obj=max(i for i,row in enumerate(ledger) if row["op"]==7)
    previous=ledger[last_obj]["ack"]
    tail=Counter()
    for row in ledger[last_obj+1:]:
        assert previous<=row["load"]<=row["ack"]
        tail["between_packets"]+=row["load"]-previous
        if row["op"]==3:
            break
        tail[f"section{row['section']}_op{row['op']}"]+=row["ack"]-row["load"]
        previous=row["ack"]
    assert sum(tail.values())==seal["load"][0]-ledger[last_obj]["ack"]
    return dict(clocks=marks,stages_ms=stages,response=reply.hex(),
                obj_ack_to_seal_load_ms={key:ms(v) for key,v in tail.items()},
                seal_load=seal["load"], published911=seal["reveal"],final_ack911=seal["ack"],
                release_to_query_spi_ms={k:ms(v) for k,v in occupied.items()},
                visible_to_issue_ms=ms(marks[-1]-marks[0]),
                seal_shortfall_ms=ms(seal["load"][0]-d["latest_load_same_cost"]),
                reveal_vblank=m["reveal_vblank"],ack912=m["ack912"],rgb_matches=m["rgb_matches"],
                ack_delay_us=round((m["ack912"]-read(reference/"joint.json")["frames"][-1]["ACK_masterclock"])*1e6/MASTER,2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--guard",choices=("bad_seal","stop_decode"))
    p.add_argument("--tail-phase",type=int,choices=(1,2))
    p.add_argument("--mode",choices=MODES)
    a=p.parse_args()
    if a.tail_phase:
        folder=directory(a.temp,a.tail_phase,"973before232","cold")
        packets,_=packet_path(folder,911)
        result=replay(a.temp,folder,a.out,"tail",packets,911)
        target=a.out/"tail973.json"
    elif a.guard:
        if not a.mode: p.error("--mode required with --guard")
        folder=directory(a.temp,1,"973"+a.mode,"cold")
        result=replay(a.temp,folder,a.out,"control",commands(folder,911),911,a.guard)
        target=a.out/"guard973.json"
    else:
        result={"phases":{},"flash":{},"guards":{},"fixed_tile_tail":{}}
        for phase in (1,2):
            result["phases"][phase]={mode:inspect(a.temp,phase,mode) for mode in MODES}
            result["fixed_tile_tail"][phase]=read(a.temp/f"nes-973-tail-p{phase}"/"tail973.json")
        for mode in MODES:
            binary,=(source(mode)/"link").rglob("firmware.stm")
            result["flash"][mode]=binary.stat().st_size
            assert binary.stat().st_size<=212992
            if mode.startswith("before"):
                result["guards"][mode]={fault:read(a.temp/f"nes-973-{mode}-{fault}"/"guard973.json")
                                        for fault in ("bad_seal","stop_decode")}
        target=a.out
    target.write_text(json.dumps(result,indent=2)+"\n")
