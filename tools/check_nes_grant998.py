"""Check address provenance, prefix causality, downstream deadlines and STOP."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from check_nes_blank959 import rows
from check_nes_output970 import counters, packet_path
from check_nes_plan975 import directory, milliseconds as ms, read, sha
from nes_objhint998 import hint, obj_rows, Rows952
from prepare_nes_tile821 import ADVENTURE_SHA, FETCH, records, samples
from test_nes_raw506_joint import PERIOD


def stop_cases():
    class Port:
        def __init__(self,args):
            self.owner=self.generation=906
            self.stopped=False
            self.chr=bytes(range(256))*512
            self.store=self.ready_rows=Rows952()
            self.free=0
            # Single checked OBJ record (tag 1, row 0).
            self.cpu=SimpleNamespace(input_generation=907,index=0,packets=[bytes.fromhex("4000038b00004000000001")])
        def cancel_supply(self):
            self.stopped=True
            self.store=self.ready_rows=Rows952()
        def begin(self):
            if self.owner!=self.generation:
                self.owner=self.generation
                self.store=self.ready_rows=Rows952()
        def accept(self,tx,now):return now
        def original_select(self,at):return max(at,100),max(at,100)+5
        def rpc(self,now,*a):return now
    for when in (104,106):
        x=hint(Port)(None)
        x.accept(bytes([0xe1,3]),10)
        x.rpc(20)
        assert not x.known998
        x.cpu.index=1
        x.rpc(25)
        assert 16 in x.known998 and not x.store
        x.rpc(when)
        assert bool(x.store)==(when>105)
        x.cancel_supply()
        x.generation=907
        x.begin()
        x.rpc(120)
        assert x.stopped and not x.store and not x.todo998 and x.lease998 is None
    return ["before_reply","after_fill"]


def inspect(d,ref):
    j=read(d/"joint.json")
    assert j["passed"] and j["commits"]==8
    for g in range(905,913):
        assert sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb")
    w=rows(d/"window.csv")
    show={int(r["g"]):[int(r[k]) for k in ("clock","frame","line")] for r in w if r["event"]=="reveal"}
    events=read(d/"events.json")
    def d2(g):
        return [v["clock"] for v in events if v.get("input_generation")==g and v.get("opcode")=="0xd2"]
    ready=next(v["capture_ready"] for v in events if v["event"]=="source_begin" and v["generation"]==911)-240*1364
    edge=ready+round((j["frames"][4]["ACK_masterclock"]-ready)/PERIOD)*PERIOD
    latch=next(r for r in rows(d/"budget685.csv") if r["generation"]=="907")
    cutoff=int(latch["latch_clock"])+(247-int(latch["line"]))*1364-int(latch["h"])
    tiles=[json.loads(line) for line in (d/"producer.jsonl").read_text().splitlines()]
    obj,=(v for v in tiles if v["generation"]==907 and v["kind"]==1)
    cmds,ledger=packet_path(d,907)
    tail=[]
    for cmd,r in zip(cmds[-len(ledger):],ledger,strict=True):
        b=bytes.fromhex(cmd[3])
        tail.append(dict(section=r["section"],op=r["op"],offset=int.from_bytes(b[10:12],"little"),issue=r["issue"],load=r["load"],ack=r["ack"]))
    grants=read(d/"grants904.json")
    path=d/"demand998.jsonl"
    selected=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    assert len(selected)==sum(v[0]==907 for v in grants)
    early=sum(int(r["value"]) for r in w if r["g"]=="909" and r["event"]=="ppu_dma" and int(r["frame"])<show[909][1])
    return dict(commits=8,RGB_match=8,shows=show,six=show[912][1]-show[906][1],ACK912=j["frames"][-1]["ACK_masterclock"],
                early909_B=early,capture910_margin_ms=ms(edge-d2(910)[-1]),cutoff907=cutoff,blocks907_D2=d2(907),
                obj907=obj,seal907=counters(d,907),packets907=tail,demand907=selected,
                DMA907=[[int(r[k]) for k in ("clock","frame","line","value")] for r in w if r["g"]=="907" and r["event"]=="ppu_dma"],
                grants908=[v[2:] for v in grants if v[0]==908],tiles908=[v for v in tiles if v["generation"]==908])


def analyze(t,rom):
    assert sha(rom).lower()==ADVENTURE_SHA.lower()
    work=t/"nes-gap904"
    f=next(v["source_frame"] for v in read(work/"data-obj/obj/work.json") if v["g"]==907)
    observed,_=samples(records(work/"fetch"/str(f)/"ppu-fetch.bin",FETCH),work/"rtl"/f"frame{f}.hex",rom.read_bytes()[-131072:])
    physical={a for kind,a,_ in observed if kind==1}
    wire=read(work/"sender-obj/sender.json")["907"]
    blocks={}
    for i,record in enumerate(wire,1):
        for addr in obj_rows(bytes.fromhex(record["wire"]),907):
            blocks.setdefault(addr,i)
    out=dict(source_frame=f,ROM_SHA256=ADVENTURE_SHA,STOP_cache=stop_cases(),phases={})
    for p in (1,2):
        ref=directory(t,p,"978returned","cold")
        cases=out["phases"][p]={}
        baseline=directory(t,p,"998addr","cold")
        for filename in ("events.json","window.csv","producer.jsonl","grants904.json"):
            assert sha(ref/filename)==sha(baseline/filename)
        for tag in ("998addr","998now","998prefix","998pair"):
            d=directory(t,p,tag,"cold")
            a=cases[tag]=inspect(d,ref)
            b=cases["998addr"]
            if tag=="998addr":
                assert len(a["demand907"])==22
                for _,addr,*_ in a["demand907"]:
                    assert blocks[addr]==14 and addr in physical and addr+8 in physical
            a["delta_OBJ_ms"]=ms(a["obj907"]["producer"]-b["obj907"]["producer"])
            a["delta_ACK912_ms"]=ms(a["ACK912"]-b["ACK912"])
            a["SEAL_load_past_246_ms"]=ms(a["seal907"]["load"][0]-a["cutoff907"])
            if tag in ("998prefix","998pair"):
                h=read(d/"hint998.json")
                assert not a["demand907"] and a["blocks907_D2"]==b["blocks907_D2"]
                addrset={addr for addr,_,_ in h["rows"]}
                assert all(addr in addrset for _,addr,*_ in b["demand907"])
                for addr,grant,reply in h["rows"]:
                    i,seen=h["known"][str(addr)]
                    assert a["blocks907_D2"][i-1]<=seen<grant<reply<a["shows"][906][0]
                a["prefix"]=dict(rows=len(h["rows"]),first_grant=h["rows"][0][1],last_reply=h["rows"][-1][2],
                                 base_demand_rows_covered=22,blocks=sorted(set(i for i,_ in h["known"].values())))
        cases["guards"]={}
        for fault,status in (("stop_decode",228),("bad_seal",224)):
            d=t/f"nes-998prefix-{fault}-p{p}"
            j=read(d/"result.json")
            assert j["passed"] and j["commits"]==2 and j["last_status"]==status
            assert sha(d/"retained.rgb")==sha(ref/"frame-906.rgb")
            cases["guards"][fault]=dict(status=status,previous_RGB_retained=True)
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("rom",type=Path);p.add_argument("out",type=Path)
    args=p.parse_args()
    result=analyze(args.temp,args.rom)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
