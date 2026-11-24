"""Verify protected events and intersect actual physical OAM writes with retained ranges."""
import argparse
import json
from pathlib import Path
from build_nes_oam996 import WORK, ROM, BASE, PACKED
from check_nes_blank959 import rows
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_output970 import counters
from test_nes_raw506_joint import PERIOD


def writes(path):
    events=rows(path/"oam996.csv")
    copies=lambda kind,op: {int(r["address"]):int(r["value"]) for r in events
                            if r["event"]==kind and (op is None or int(r["op"])==op)}
    old=copies("history",3);before=copies("load",8);final=copies("final",None)
    assert len(old)==len(before)==len(final)==368
    assert old==before
    io=[r for r in events if r["event"] in ("direct","port")]
    assert not any(int(r["clock"])<next(int(r["clock"]) for r in events
                   if r["event"]=="load" and r["op"]=="8") for r in io)
    addresses=sorted({int(r["address"]) for r in io})
    return dict(unique_write_B=len(addresses),min_offset=min(addresses,default=None),max_offset=max(addresses,default=None),
                direct=sum(r["event"]=="direct" for r in io),port=sum(r["event"]=="port" for r in io),
                changed_B=sum(old[k]!=final[k] for k in old),unchanged_until_repeat=True)


def joint(t,p,tag,ref):
    d=directory(t,p,tag,"cold")
    _,ledger=packet_path(d,911,expected_shape=(16 if tag=="978returned" else 15,3))
    j=read(d/"joint.json");w=rows(d/"window.csv");e=read(d/"events.json")
    assert j["passed"] and j["commits"]==8
    for g in range(905,913):
        assert sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb")
    displays={int(r["g"]):[int(r[k]) for k in ("clock","frame","line")] for r in w if r["event"]=="reveal"}
    early=sum(int(r["value"]) for r in w if r["g"]=="909" and r["event"]=="ppu_dma" and int(r["frame"])<displays[909][1])
    source=next(r["capture_ready"] for r in e if r["generation"]==911 and r["event"]=="source_begin")-240*1364
    lastD2=max(r["clock"] for r in e if r.get("input_generation")==910 and r.get("opcode")=="0xd2")
    edge=source+round((j["frames"][4]["ACK_masterclock"]-source)/PERIOD)*PERIOD
    tail=ledger[next(i for i,r in enumerate(ledger) if r["op"]==8):]
    finalOAM=next(r for r in reversed(tail) if r["section"]==4)
    return dict(displays=displays,early909_B=early,capture_margin910_ms=ms(edge-lastD2),
                six=displays[912][1]-displays[906][1],interval911=displays[911][1]-displays[910][1],
                ACK912=j["frames"][-1]["ACK_masterclock"],events911=counters(d,911),tail=tail,
                oam_ms=ms(finalOAM["ack"]-tail[0]["load"]),
                dma911=[[int(r[k]) for k in ("clock","frame","line","value")] for r in w if r["g"]=="911" and r["event"]=="ppu_dma"],
                frames_ACK=[f["ACK_masterclock"] for f in j["frames"]])


def analyze(t):
    r={"arm_flash_B":{},"stored_65816_B":{},"phases":{}}
    for name,w in (("978",BASE),("996",WORK)):
        r["arm_flash_B"][name]=next((w/"link").rglob("firmware.stm")).stat().st_size
    for name,w in (("978",PACKED),("scalar",ROM),("grouped",WORK/"grouped")):
        b=read(w/"build.json");r["stored_65816_B"][name]=64+b["loader_B"]+b["encoded_B"]
    for p in (1,2):
        ref=directory(t,p,"978returned","cold")
        a=r["phases"][p]={tag:joint(t,p,tag,ref) for tag in ("978returned","996tail","996grouped","996ideal","996groupwire","996idealwire")}
        for tag in ("996tail","996grouped","996ideal","996groupwire","996idealwire"):
            a[tag]["delta_ACK912_ms"]=ms(a[tag]["ACK912"]-a["978returned"]["ACK912"])
            a[tag]["delta_SEAL_ms"]=ms(a[tag]["events911"]["seal"][0]-a["978returned"]["events911"]["seal"][0])
        assert a["996tail"]["frames_ACK"][:6]==a["996ideal"]["frames_ACK"][:6]
        for paid,wire in (("996grouped","996groupwire"),("996ideal","996idealwire")):
            assert a[paid]["frames_ACK"][:6]==a[wire]["frames_ACK"][:6]
            charges=read(directory(t,p,wire,"cold")/"transport995.json")
            a[wire]["wire_charges"]=charges
            assert sum(v["logical_B"]-v["charged_B"] for v in charges)==371
        a["907_baseline"]=dict(events=counters(ref,907),DMA=[[int(r[k]) for k in ("clock","frame","line","value")]
                for r in rows(ref/"window.csv") if r["g"]=="907" and r["event"]=="ppu_dma"])
        a["fixed"]={}
        for case in ("trace","matched","partial","damaged","highbits","span","noprior","group-partial",
                     "group-damaged" if p==1 else "group-highbits"):
            d=t/f"nes-oam996-{case}-p{p}";j=read(d/"result.json");w=writes(d)
            assert j["passed"]
            if case in ("trace","matched"):
                assert j["commits"]==7 and j["last_status"]==1
                assert sha(d/"frame-911.rgb")==sha(ref/"frame-911.rgb")
                assert w["unique_write_B"]==(368 if case=="trace" else 36) and w["changed_B"]==36
                w["SEAL"]=counters(d,911)["seal"]
            else:
                assert j["commits"]==6 and sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
                assert j["last_status"]==(228 if case.endswith("partial") else 224)
                assert w["unique_write_B"]==(20 if case.endswith("partial") else 0)
            w.update(commits=j["commits"],status=j["last_status"]);a["fixed"][case]=w
        cold=t/f"nes-oam996-cold-p{p}";cj=read(cold/"result.json")
        assert cj["passed"] and cj["commits"]==2 and cj["last_status"]==1
        for g in (905,906):assert sha(cold/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb")
        a["reset_cold_commits"]=cj["commits"]
    return r


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf8",newline="\n")
