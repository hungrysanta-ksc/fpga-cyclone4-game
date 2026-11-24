"""Account for bank release, first tile receipt, all eight PPU DMAs and final ACK."""
import argparse
import json
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from nes_raw991 import BASE, PACKED, ROOT, ROM, tile_work
from test_nes_raw506_joint import PERIOD


def point(row):
    return [int(row[k]) for k in ("clock","frame","line")]


def measure(temp,phase,mode,ref):
    d=ref if mode=="ref" else directory(temp,phase,"991"+mode,"cold")
    j=read(d/"joint.json")
    assert j["passed"] and j["commits"]==8
    assert map_payloads(d)==map_payloads(ref)
    assert all(sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb") for g in range(905,913))
    assert [r["records"] for r in read(d/"e9931.json")]==[r["records"] for r in read(ref/"e9931.json")]
    commands, ledger=packet_path(d,911)
    r=rows(d/"window.csv")
    def events(g,kind):
        return [x for x in r if x["event"]==kind and int(x["g"])==g]
    show={g:point(events(g,"reveal")[0]) for g in range(905,913)}
    # Compare actual packet payloads per section, preserving order in each.
    originals,_=packet_path(ref,911)
    def content(cmds):
        result={}
        for g,op,_,wire,bulk,*_ in cmds:
            b=bytes.fromhex(wire)
            result.setdefault((g,op,b[1]),[]).append((b[:2]+b[4:],bulk))
        return result
    assert content(commands)==content(originals)
    data=[(cmd,r) for cmd,r in zip(commands[-len(ledger):],ledger,strict=True)]
    raw,=(r for cmd,r in data if bytes.fromhex(cmd[3])[0:2]==bytes((2,5)) and
          int.from_bytes(bytes.fromhex(cmd[3])[10:12],"little")==1121)
    banks=[int.from_bytes(bytes.fromhex(c[3])[18:20],"little") for c in commands if c[0]>=909 and c[1]==1]
    assert banks==[0,1,0]
    spi=read(d/"events.json")
    d1=[e["clock"] for e in spi if e.get("input_generation")==911 and e.get("opcode")=="0xd1"]
    origin=next(e["capture_ready"] for e in spi if e["event"]=="source_begin" and e["generation"]==911)-240*1364
    ack909=j["frames"][4]["ACK_masterclock"]
    cap=origin+round((ack909-origin)/PERIOD)*PERIOD
    last_d2=max(e["clock"] for e in spi if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    transfers=[]
    for a,b in zip(events(911,"ppu_dma"),events(911,"ppu_last"),strict=True):
        n=int(a["value"]);start=point(a);end=point(b)
        assert start[0]<end[0] and start[1]==end[1] and 225<=start[2]<=end[2]<=261
        transfers.append(dict(size=n,start=start,end=end))
    assert sorted(x["size"] for x in transfers)==[16,32,64,64,64,384,512,544]
    early=sum(int(x["value"]) for x in events(909,"ppu_dma") if int(x["frame"])<show[909][1])
    cut=read(Path("analysis/tile985-results.json"))["phases"][str(phase)]["bound"]["cutoff_exclusive"]+(show[910][1]+1-44)*PERIOD
    seal=point(events(911,"seal")[0]);upload=point(events(911,"upload165_entry")[0])
    palette,=(x["start"][0] for x in transfers if x["size"]==512)
    # Lower bound with all tile/raw and setup up to the first palette DMA free.
    last_oam=next(x for x in reversed(ledger) if x["section"]==4)
    latest=cut-(upload[0]-seal[0])-(show[911][0]-palette)
    return dict(banks_909_to_911=banks,reveal908=show[908],early909_B=early,margin910_ms=ms(cap-last_d2),
                before_reveal910_D1=sum(k<show[910][0] for k in d1),total_D1=len(d1),reveal910=show[910],
                ACK910=j["frames"][5]["ACK_masterclock"],input911_D1_end=d1[-1],begin911=ledger[0],
                first_tile=next(x for x in ledger if x["op"]==7),raw201=raw,DMAs=transfers,
                last_data=ledger[-2],seal=seal,upload=upload,reveal911=show[911],interval=show[911][1]-show[910][1],
                early_raw_B=sum(a["size"] for a in transfers if a["size"]==64 and a["end"][1]==show[910][1]+1),
                early_tile_B=sum(a["size"] for a in transfers if a["size"] in (16,32,384) and a["end"][1]==show[910][1]+1),
                cutoff_exclusive=cut,latest_seal_if_only_validation_and_color_remain=latest,
                last_oam=last_oam,oam_over_ideal_seal_limit_ms=ms(last_oam["ack"]-latest),
                seal_over_that_limit_ms=ms(seal[0]-latest),six=show[912][1]-show[906][1],ACK912=j["frames"][-1]["ACK_masterclock"],
                link=j["firmware_SHA256"],rom=sha(d/"client.sfc"))


def analyze(t):
    result={"phases":{},"guards":{},"budgets":{}}
    for p in (1,2):
        ref=directory(t,p,"978returned","cold")
        modes=("ref","matched","static","first","both","drain")
        cases={m:measure(t,p,m,ref) for m in modes}
        base=cases["ref"]
        writes=read(Path("analysis/hdma990-results.json"))["phases"][str(p)]["ref"]["writes"]
        base["raw_pixels_final"]=writes["raw_pixels_final"]
        base["raw_packed"]=writes["packed_raw_final"]
        for c in cases.values():
            c["delta_ACK912_ms"]=ms(c["ACK912"]-base["ACK912"])
        for mode in ("ref","drain"):
            trace=t/f"nes-raw991-ownership-{mode}-p{p}"
            assert read(trace/"result.json")["passed"]
            rr=rows(trace/"ownership.csv")
            def at(k):
                return next(x for x in rr if x["event"]==k)
            c=cases[mode]
            assert int(at("public910")["clock"])==c["reveal910"][0]
            assert int(at("begin_valid")["active"])==1 and int(at("begin_valid")["target"])==0
            valid=int(at("raw201_valid")["clock"])
            assert c["raw201"]["load"]<=valid<c["raw201"]["ack"]
            folder=ref if mode=="ref" else directory(t,p,"991drain","cold")
            cmds,_=packet_path(folder,911)
            tile=next(bytes.fromhex(cmd[3]) for cmd in cmds if cmd[0]==911 and cmd[1]==7)
            token=int.from_bytes(tile[16:20],"little")
            returns=dict(tuple(map(int,line.split())) for line in (trace/"returns970.txt").read_text().splitlines())
            tvalid=returns[token]
            c["first_tile_token"]=token
            c["first_tile_consumption"]=tvalid
            assert c["first_tile"]["load"]<=tvalid<c["first_tile"]["ack"]
            onset=c["cutoff_exclusive"]-22*1364
            c["ownership_trace"]=rr
            c["earliest_after_contiguous_check_and_vblank"]=max(valid,onset)
            c["raw_check_after_first_tile_check_ms"]=ms(valid-tvalid)
            if mode=="drain":
                first=min(a["start"][0] for a in c["DMAs"] if a["size"]==64)
                assert first>=max(valid,onset)
                c["setup_after_first_legal_clock_ms"]=ms(first-max(valid,onset))
        for key in ("reveal908","early909_B","margin910_ms","reveal910","ACK910"):
            assert base[key]==cases["matched"][key]
        candidate=cases["drain"]
        assert candidate["reveal908"][1:]==base["reveal908"][1:]
        assert candidate["early909_B"]==base["early909_B"]==624 and candidate["margin910_ms"]>0
        assert candidate["early_raw_B"]==192 and candidate["early_tile_B"]==432
        first_raw=next(a for a in candidate["DMAs"] if a["size"]==64)
        assert first_raw["start"][1]==candidate["reveal910"][1]+1 and first_raw["start"][2]<=233
        result["phases"][p]=cases
        for case in ("changed","stop","damage"):
            d=t/f"nes-raw991-guard-{case}-p{p}"
            r=read(d/"result.json")
            count=7 if case=="changed" else 6
            assert r["passed"] and r["commits"]==count
            if count==6:
                assert r["last_status"]==(228 if case=="stop" else 224)
                assert sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
            marks=[point(x) for x in rows(d/"window.csv") if x["g"]=="911" and x["event"]=="raw991"]
            assert len(marks)==(1 if case=="stop" else 3)
            result["guards"][f"{case}-p{p}"]=dict(commits=count,status=r["last_status"],early_chunks=marks)
    for name,root in (("ref",BASE),("first",ROOT/"first"),("both",ROOT/"both"),("drain",tile_work("after"))):
        result["budgets"][name]=next((root/"link").rglob("firmware.stm")).stat().st_size
    for name,rom in (("ROM978",PACKED),("ROM991",ROM)):
        b=read(rom/"build.json");result["budgets"][name]=64+b["loader_B"]+b["encoded_B"]
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf8")
