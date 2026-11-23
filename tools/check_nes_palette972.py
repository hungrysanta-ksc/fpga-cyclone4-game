"""Track actual ARM writes of the first 16 colours and verify candidate guards."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_MEM_WRITE
from analyze_nes_palette971 import commands, measure
from analyze_nes_output970 import deadline
from check_nes_blank959 import directory, read, rows, sha
from check_nes_output970 import counters, replay
from nes_page963 import simulate
from package_nes_trial966 import WORK as BASE
from replay_nes_supply905 import joint
from test_nes_banks557 import MASTER


def observe(temp, phase, prefix):
    mode = "972prefix" if prefix else "972end"
    folder = directory(temp,phase,mode,"cold")
    packets = commands(folder,911)
    expected, = (bytes.fromhex(w)[16:] for g,op,_,w,*_ in packets if g==911 and op==2 and
                 bytes.fromhex(w)[1]==3 and int.from_bytes(bytes.fromhex(w)[10:12],"little")==0)
    assert len(expected)==32
    original = joint.Runtime.__init__
    events = read(folder/"events.json")
    begin = next(e["start"] for e in events if e.get("generation")==911 and e.get("packet_opcode")==1)
    measure911 = measure(folder,directory(temp,phase,"971control","cold"))
    issue = next(p["issue"] for p in measure911["packets911"] if p["op"]==2 and p["section"]==3)
    writes = []
    def init(cpu,*args):
        original(cpu,*args)
        base = cpu.video+cpu.layout["nes_native_video165"]["cgram"]
        def write(u, access, address, size, value, _):
            if begin <= cpu.clock < issue:
                start,end=max(base,address),min(base+32,address+size)
                data=(value % (1<<(8*size))).to_bytes(size,"little")
                writes.append((round(cpu.clock),start-base,data[start-address:end-address].hex()))
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=base,end=base+31)
    work=BASE.with_name("nes-plan-palette972"+("-prefix" if prefix else ""))
    with patch.object(joint.Runtime,"__init__",init):
        simulate(temp,phase,"cold",True,work,True,tag=mode+"write",edition=966)
    observed=directory(temp,phase,mode+"write","cold")
    for name in ("window.csv","records.bin","events.json","producer.jsonl"):
        assert sha(folder/name)==sha(observed/name)
    image=[None]*32
    for tick,offset,raw in writes:
        image[offset:offset+len(raw)//2]=bytes.fromhex(raw)
    assert bytes(image)==expected
    return {"last_palette_store":writes[-1][0],"payload":expected.hex(),"write_count":len(writes)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("observe","bad_seal","stop_decode","report"))
    parser.add_argument("temp",type=Path)
    parser.add_argument("--phase",type=int,choices=(1,2),default=1)
    parser.add_argument("--prefix",action="store_true")
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    mode="972prefix" if a.prefix else "972end"
    folder=directory(a.temp,a.phase,mode,"cold")
    if a.action=="observe":
        result=observe(a.temp,a.phase,a.prefix)
        dest=directory(a.temp,a.phase,mode+"write","cold")/"stores972.json"
    elif a.action!="report":
        out=a.temp/f"nes-{mode}-{a.action}"
        result=replay(a.temp,folder,out,"control",commands(folder,911),911,a.action)
        dest=out/"guard972.json"
    else:
        if not a.out:
            parser.error("--out is required for report")
        dest=a.out
        result={"phases":{}, "guards":{}, "flash_bytes":{}}
        for phase in (1,2):
            items=result["phases"][phase]={}
            control=directory(a.temp,phase,"971control","cold")
            for name in ("971control","972end","972prefix"):
                directory972=directory(a.temp,phase,name,"cold")
                m=measure(directory972,control)
                events=read(directory972/"events.json")
                e9,=(e for e in events if e.get("opcode")=="0xe9" and e["generation"]==911)
                m["e9_completed"]=round(e9["clock"])
                m["chr_grants911"]={key:sum(row[0]==911 for row in log) for key,log in (
                    ("demand",read(directory972/"grants904.json")),
                    ("ahead",read(directory972/"ahead911.json")),
                    ("companion",read(directory972/"companion952.json")),
                    ("hint",read(directory972/"hint963.json")["fills"]))}
                consumer=[r for r in rows(directory972/"window.csv") if r["g"]=="911" and r["op"]=="7"]
                bulk=[p for p in m["packets911"] if p["op"]==7]
                for tile,packet,accepted,returned in zip(m["tiles911"],bulk,
                        (r for r in consumer if r["event"]=="load"),
                        (r for r in consumer if r["event"]=="ack"),strict=True):
                    assert tile["kind"]==packet["section"]==int(accepted["section"])
                    tile.update(issue=packet["issue"],load=int(accepted["clock"]),ack=int(returned["clock"]))
                m["seal"]=counters(directory972,911)
                m["prior_blank"]=deadline(directory972,911)
                m["seal_shortfall_ms"]=round((m["seal"]["load"][0]-m["prior_blank"]["latest_load_same_cost"])*1000/MASTER,3)
                m["ack_delay_ms"]=round((m["ack912"]-items.get("971control",m)["ack912"])*1000/MASTER,3)
                if name!="971control":
                    stores=read(directory(a.temp,phase,name+"write","cold")/"stores972.json")
                    m.update(stores)
                    m["store_after_e9_us"]=round((stores["last_palette_store"]-e9["clock"])*1e6/MASTER,2)
                items[name]=m
        for mode,work in (("971control",BASE),("972end",BASE.with_name("nes-plan-palette972")),
                          ("972prefix",BASE.with_name("nes-plan-palette972-prefix"))):
            binary,=(work/"link").rglob("firmware.stm")
            assert binary.stat().st_size<=212992
            result["flash_bytes"][mode]=binary.stat().st_size
            if mode!="971control":
                result["guards"][mode]={fault:read(a.temp/f"nes-{mode}-{fault}"/"guard972.json")
                                        for fault in ("bad_seal","stop_decode")}
    dest.write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":
    main()
