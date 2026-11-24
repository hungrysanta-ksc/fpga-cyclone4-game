"""Correlate OAM, section 5 and checked tile DMA with the actual release deadline."""
import argparse
import json
from pathlib import Path

from check_nes_blank959 import rows
from check_nes_bg976 import map_payloads
from check_nes_menu533 import check as menu
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_tile985 import transfers
from nes_oam988 import FAST, MODES, ROM, work
from test_nes_raw506_joint import PERIOD


def streams(commands):
    content={}
    for g,op,_,wire,bulk,*_ in commands:
        b=bytes.fromhex(wire)
        data=b[16:]
        if b[1]==4 and op==4 and int.from_bytes(b[10:12],"little")==512:
            n=int.from_bytes(b[14:16],"little")
            assert len(data)==2 and n==32
            b=bytes([2])+b[1:2]+b[2:12]+bytes((32,0,0,0))+data*16
        content.setdefault((g,b[1]),[]).append((b[:2]+b[4:],bulk))
    return content


def measure(t,p,tag,base):
    d=directory(t,p,tag,"cold")
    trace=rows(d/"window.csv")
    cmds,ledger=packet_path(d,911)
    assert streams(cmds)==streams(packet_path(base,911)[0])
    assert map_payloads(d)==map_payloads(base)
    assert all(sha(d/f"frame-{g}.rgb")==sha(base/f"frame-{g}.rgb") for g in range(905,913))
    assert [e["records"] for e in read(d/"e9931.json")]==[e["records"] for e in read(base/"e9931.json")]
    expected_rom = ROM/"sink165.sfc" if tag.endswith("wram") else base/"client.sfc"
    assert sha(d/"client.sfc")==sha(expected_rom)
    def packet(section,offset):
        item,=(q for a,q in zip(cmds[-len(ledger):],ledger,strict=True) if q["section"]==section
               and int.from_bytes(bytes.fromhex(a[3])[10:12],"little")==offset)
        return item
    m=transfers(d)
    cold=read(d/"joint.json")
    events=read(d/"events.json")
    origin=next(e["capture_ready"] for e in events if e["event"]=="source_begin" and e["generation"]==911)-240*341*4
    ack909=next(f["ACK_masterclock"] for f in cold["frames"] if f["generation"]==909)
    d2=max(e["clock"] for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    reveal912=int(next(r["frame"] for r in trace if r["event"]=="reveal" and r["g"]=="912"))
    limit=read(Path("analysis/tile985-results.json"))["phases"][str(p)]["bound"]["cutoff_exclusive"]
    # A missed earlier generation shifts the target VBlank as well.
    limit+=(m["target"]-44)*PERIOD
    oam=packet(4,512)
    fill=[r for r in trace if r["g"]=="911" and r["event"]=="zero_dma" and int(r["index"])==oam["index"]]
    assert [int(r["value"]) for r in fill]==([32] if tag.endswith("wram") else [])
    return dict(oam_prefix=packet(4,0),oam=oam,table=packet(5,1322),seal=m["seal"],upload=m["validated"],
                tile_dma=m["dma"][:3],residual_dma=m["dma"][3:],pre_B=m["early_B"],pre_by246_B=m["completed_transfers_by_246_B"],
                target=m["target"],cutoff=limit,shows=m["reveals"],interval=m["interval911"],early909=m["early909_B"],
                capture910_ms=ms(origin+round((ack909-origin)/PERIOD)*PERIOD-d2),six=reveal912-m["reveals"][906][1],
                ACK912=cold["frames"][-1]["ACK_masterclock"],flash_hash=cold["firmware_SHA256"])


def analyze(t):
    out={"phases":{},"flash_B":{},"menu":{}}
    tags=["978returned","985after"]+["988"+m for m in MODES]+["988"+m+"wram" for m in FAST]
    for mode in (*MODES,*FAST):
        link=(FAST[mode] if mode in FAST else work(mode))/"link"
        out["flash_B"][mode]=next(link.rglob("firmware.stm")).stat().st_size
        out["menu"][mode]={k:v["released"] for k,v in menu(link/"src","966")["rows"].items()}
    info=read(ROM/"build.json")
    out["program_with_vectors_B"]=64+info["loader_B"]+info["encoded_B"]
    for p in (1,2):
        base=directory(t,p,tags[0],"cold")
        cases={tag:measure(t,p,tag,base) for tag in tags}
        r=cases[tags[0]]
        for v in cases.values():
            v["delta_ms"]={k:ms(v[k]["ack"]-r[k]["ack"]) for k in ("oam_prefix","oam","table")}
            v["delta_ms"].update(seal=ms(v["seal"][0]-r["seal"][0]),ACK912=ms(v["ACK912"]-r["ACK912"]))
        protected=cases["988fastidlewram"]
        assert protected["shows"][908][1:]==r["shows"][908][1:]
        assert protected["early909"]==624 and protected["capture910_ms"]>0
        assert protected["pre_B"]==protected["pre_by246_B"]==432
        verify=r["upload"][0]-r["seal"][0]
        # All three tile DMAs complete before SEAL starts on the idle path.
        # Assume zero setup and no gaps. Baseline SEAL cost is measured.
        budget=22*1364
        lower=8*(432+192+512+544)+verify
        guards={}
        for mode in ("between","fastidle"):
            tag="988"+mode+("wram" if mode in FAST else "")
            for fault,status in (("bad_seal",224),("stop_decode",228)):
                d=t/f"nes-{tag}-p{p}-{fault}"
                report=read(d/"result.json")
                assert report["passed"] and report["last_status"]==status and report["commits"]==6
                assert sha(d/"retained.rgb")==sha(base/"frame-910.rgb")
                dma=[int(r["value"]) for r in rows(d/"window.csv") if r["g"]=="911" and r["event"]=="ppu_dma"]
                guards[f"{mode}-{fault}"]=dict(ACK=status,DMA=dma)
        out["phases"][p]=dict(cases=cases,guards=guards,available_ms=ms(budget),checks_ms=ms(verify),
                              dma_min_ms=ms(1680*8),minimum_excess_ms=ms(lower-budget))
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8")
