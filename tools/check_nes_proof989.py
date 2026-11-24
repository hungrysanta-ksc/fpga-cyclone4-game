"""Compare phase-matched full links and rejected writes using the original capture clock."""
import argparse
import csv
import json
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_menu533 import check as menu
from check_nes_oam988 import streams
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_tile985 import transfers
from nes_proof989 import PACKED, ROM
from nes_scroll989 import ROM as SCROLL
from nes_tile985 import work
from test_nes_raw506_joint import PERIOD

TAGS=("978returned","985after","985between","989v2after","989v2between","989prefixafter",
      "989scroll","989scrollprefix","989scrollbetween")


def marks(folder):
    with (folder/"proof989.csv").open() as f:
        return {k:(int(at),int(flag)) for k,at,flag in csv.reader(f)}


def measure(temp,phase,tag,ref):
    d=directory(temp,phase,tag,"cold")
    m=transfers(d)
    c,ledger=packet_path(d,911)
    assert streams(c)==streams(packet_path(ref,911)[0])
    assert map_payloads(d)==map_payloads(ref)
    assert [e["records"] for e in read(d/"e9931.json")]==[e["records"] for e in read(ref/"e9931.json")]
    assert all(sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb") for g in range(905,913))
    rom=PACKED if not tag.startswith("989") or "prefix" in tag else SCROLL if "scroll" in tag else ROM
    assert sha(d/"client.sfc")==sha(rom/"sink165.sfc")
    events=read(d/"events.json")
    joint=read(d/"joint.json")
    origin=next(e["capture_ready"] for e in events if e["event"]=="source_begin" and e["generation"]==911)-240*1364
    previous=next(f["ACK_masterclock"] for f in joint["frames"] if f["generation"]==909)
    last_d2=max(e["clock"] for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    cap=origin+round((previous-origin)/PERIOD)*PERIOD
    reveal912=int(next(x["frame"] for x in rows(d/"window.csv") if x["g"]=="912" and x["event"]=="reveal"))
    ack=joint["frames"][-1]["ACK_masterclock"]
    cutoff=read(Path("analysis/tile985-results.json"))["phases"][str(phase)]["bound"]["cutoff_exclusive"]
    cutoff+=(m["target"]-44)*PERIOD
    result=dict(boot_rom=sha(d/"client.sfc"),arm=joint["firmware_SHA256"],display908=m["reveals"][908],
                dma909_B=m["early909_B"],capture910_ms=ms(cap-last_d2),target=m["target"],
                tile_start=m["dma"][0]["start"],tile_end=m["dma"][2]["end"],early_B=m["early_B"],
                last_table_ACK=ledger[-2]["ack"],seal=m["seal"],upload=m["validated"],
                seal_to_upload_ms=ms(m["validated"][0]-m["seal"][0]),display911=m["reveals"][911],
                interval911=m["interval911"],dense6=reveal912-m["reveals"][906][1],ACK912=ack,
                delta_ACK912_ms=ms(ack-read(ref/"joint.json")["frames"][-1]["ACK_masterclock"]),
                tile_end_to_cutoff_ms=ms(cutoff-m["dma"][2]["end"][0]))
    if tag.startswith("989"):
        hit=marks(d)
        assert hit["early989"][0]<hit["record989"][0] and hit["seal989"][1]==1
        assert "damage989" not in hit and "full989" not in hit
        result.update(early_check_to_saved_ms=ms(hit["record989"][0]-hit["early989"][0]),
                      seal_recheck_ms=ms(hit["reuse989"][0]-hit["seal989"][0]),
                      saved_to_tile_start_ms=ms(m["dma"][0]["start"][0]-hit["record989"][0]),proof=hit)
    return result


def analyze(t):
    data={"phases":{},"budgets":{},"menu":{}}
    for kind,rom in (("section",ROM),("scroll",SCROLL)):
        b=read(rom/"build.json")
        data["budgets"][kind]={"physical_ROM_B":64+b["encoded_B"]+b["loader_B"],
            "scratch_B":96 if kind=="section" else 23,"ROM_SHA256":sha(rom/"sink165.sfc")}
    for mode in ("after","between"):
        link=work(mode)/"link"
        data["budgets"][mode]={"ARM_flash_B":next(link.rglob("firmware.stm")).stat().st_size}
        data["menu"][mode]={k:v["released"] for k,v in menu(link/"src","966")["rows"].items()}
    for p in (1,2):
        ref=directory(t,p,"978returned","cold")
        cases={tag:measure(t,p,tag,ref) for tag in TAGS}
        s=cases["989scroll"]
        assert s["display908"][1:]==[38,245] and s["dma909_B"]==624 and s["capture910_ms"]>0
        assert s["early_B"]==432 and s["saved_to_tile_start_ms"]>0
        for tag in ("989prefixafter","989scrollprefix"):
            m=cases[tag];parent=cases["985after"]
            assert m["display908"]==parent["display908"] and m["capture910_ms"]==parent["capture910_ms"]
        guards={}
        for kind,faults in (("proof",("scroll","table","length","append","stoplatched","bad_seal")),
                            ("scroll",("scroll","overlap","stoplatched"))):
            for fault in faults:
                d=t/f"nes-{kind}989-fixed-p{p}-{fault}"
                r=read(d/"result.json")
                assert r["passed"] and r["commits"]==6 and r["last_status"]==(228 if fault=="stoplatched" else 224)
                assert sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
                log=marks(d)
                assert "record989" in log
                # A corrupted generation is outside the 911-only event filter.
                # The receiver-side rollback assertion still checks the flag.
                if fault!="bad_seal":assert "invalidate989" in log
                if fault in ("scroll","table","length"):assert "damage989" in log
                guards[kind+"-"+fault]={"last_status":r["last_status"],"marks":log}
        data["phases"][p]={"cases":cases,"guards":guards}
    return data


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8")
