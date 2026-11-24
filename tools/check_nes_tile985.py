"""Compare full ARM schedules with fixed-arrival, zero-notification-cost controls."""
import argparse
import json
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_menu533 import check as menu
from check_nes_plan975 import directory, milliseconds, packet_path, read, sha
from nes_tile985 import work
from test_nes_raw506_joint import PERIOD


def transfers(folder):
    r=rows(folder/"window.csv")
    def gen(g,event):
        return [x for x in r if x["g"]==str(g) and x["event"]==event]
    def beam(x):
        return [int(x[k]) for k in ("clock","frame","line")]
    reveals={g:beam(gen(g,"reveal")[0]) for g in range(905,912)}
    target=reveals[910][1]+1
    starts=gen(911,"ppu_dma")
    ends=gen(911,"ppu_last")
    sizes=[int(x["value"]) for x in starts]
    assert sizes==[16,32,384,64,64,64,512,544]
    dma=[dict(size=n,start=beam(a),end=beam(b)) for n,a,b in zip(sizes,starts,ends,strict=True)]
    assert all(a["start"][0]<a["end"][0] for a in dma)
    ports=rows(folder/"seal528.csv")
    assert [(int(x["port"]),int(x["bytes"])) for x in ports if x["g"]=="911" and
            x["event"]=="dma" and x["port"] in ("34","4")]==[(34,512),(4,544)]
    early=[a for a in dma if a["start"][1]==target and a["end"][1]==target]
    assert all(225<=a["start"][2]<=a["end"][2]<=261 for a in early)
    return dict(target=target,tile_accept=[beam(x) for x in gen(911,"ack") if x["op"]=="7"],
                early_B=sum(a["size"] for a in early),
                completed_transfers_by_246_B=sum(a["size"] for a in early if a["end"][2]<=246),dma=dma,reveals=reveals,
                seal=beam(gen(911,"seal")[0]),validated=beam(gen(911,"upload165_entry")[0]),
                interval911=reveals[911][1]-reveals[910][1],ACK911=beam(gen(911,"ack")[-1])[0],
                early909_B=sum(int(x["value"]) for x in gen(909,"ppu_dma") if int(x["frame"])<reveals[909][1]))


def full(folder,ref):
    m=transfers(folder)
    events=read(folder/"events.json")
    joint=read(folder/"joint.json")
    c,ledger=packet_path(folder,911)
    old,_=packet_path(ref,911)
    assert [(v[3],v[4]) for v in c]==[(v[3],v[4]) for v in old]
    assert map_payloads(folder)==map_payloads(ref)
    assert sha(folder/"client.sfc")==sha(ref/"client.sfc")
    assert all(sha(folder/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb") for g in range(905,913))
    tiles=lambda d:[(x["g"],x["records"]) for x in read(d/"e9931.json")]
    assert tiles(folder)==tiles(ref)
    origin=next(e["capture_ready"] for e in events if e["event"]=="source_begin" and e["generation"]==911)-240*341*4
    ack=next(x["ACK_masterclock"] for x in joint["frames"] if x["generation"]==909)
    capture=origin+round((ack-origin)/PERIOD)*PERIOD
    commit=max(e["clock"] for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
    reveal912=next(x for x in rows(folder/"window.csv") if x["g"]=="912" and x["event"]=="reveal")
    tail=ledger[-3:]
    assert [(x["op"],x["section"]) for x in tail]==[(2,5),(2,5),(3,0)]
    return dict(**m,literal_and_seal=tail,margin910_ms=milliseconds(capture-commit),
                six=int(reveal912["frame"])-m["reveals"][906][1],ACK912=joint["frames"][-1]["ACK_masterclock"],
                arm_sha256=joint["firmware_SHA256"],client_sha256=sha(folder/"client.sfc"))


def analyze(temp):
    result=dict(phases={},guards={},flash_B={},menu={})
    for phase in (1,2):
        src=directory(temp,phase,"978returned","cold")
        ref=full(src,src)
        data=result["phases"][phase]=dict(ref=ref,full={},fixed={})
        # Charge the full original SEAL check and the observed palette/OAM
        # service. Give the three raw transfers zero setup time, charging only
        # 8 clocks per byte. This optimistic bound is not an executable trace.
        limit=read(Path("analysis/cutoff982-results.json"))["phases"][str(phase)]["ref"]["cutoff_exclusive_clock"]
        assert ref["target"]==44 and ref["seal"][1:]==[44,240+phase-1]
        validate=ref["validated"][0]-ref["seal"][0]
        color=ref["reveals"][911][0]-ref["dma"][-2]["start"][0]
        latest=limit-validate-color-192*8
        last=ref["literal_and_seal"][-2]["ack"]
        data["bound"]=dict(cutoff_exclusive=limit,latest_seal=latest,
                latest_line=247+(latest-limit)/1364,
                last_literal_to_cutoff_ms=milliseconds(limit-last),
                validation_ms=milliseconds(validate),raw_min_ms=milliseconds(192*8),color_to_reveal_ms=milliseconds(color),
                late_if_SEAL_at_literal_return_ms=milliseconds(last-latest),
                margin_with_free_checks_and_all_tiles_done_ms=milliseconds(limit-last-color-192*8))
        for where in ("between","after"):
            tag="985"+where
            folder=directory(temp,phase,tag,"cold")
            actual=full(folder,src)
            actual["delta_ACK912_ms"]=milliseconds(actual["ACK912"]-ref["ACK912"])
            data["full"][where]=actual
            fixed=temp/f"nes-tile985-fixed-{where}-p{phase}"
            data["fixed"][where]=transfers(fixed)
            assert sha(fixed/"frame-911.rgb")==sha(src/"frame-911.rgb")
            assert actual["target"]==44 and actual["reveals"][908][1:]==ref["reveals"][908][1:]
            assert actual["margin910_ms"]>0 and actual["early909_B"]==624
            assert actual["early_B"]==data["fixed"][where]["early_B"]==432
            assert actual["completed_transfers_by_246_B"]==432
            assert max(x[0] for x in actual["tile_accept"])<actual["dma"][0]["start"][0]
            assert actual["dma"][2]["end"][0]<actual["seal"][0]
            for fault,status in (("bad_seal",224),("stop_decode",228)):
                d=temp/f"nes-{tag}-p{phase}-{fault}"
                stop=read(d/"result.json")
                assert stop["passed"] and stop["last_status"]==status and stop["commits"]==6
                assert sha(d/"retained.rgb")==sha(src/"frame-910.rgb")
                dma=[int(x["value"]) for x in rows(d/"window.csv") if x["event"]=="ppu_dma" and x["g"]=="911"]
                assert dma==[16,32,384]
                result["guards"][f"{where}-p{phase}-{fault}"]=dict(ack=status,early_B=sum(dma),commits=6)
    for where in ("after","between"):
        link=work(where)/"link"
        image,=link.rglob("firmware.stm")
        result["flash_B"][where]=image.stat().st_size
        check=menu(link/"src","966")
        assert check["firmware"]==result["phases"][1]["full"][where]["arm_sha256"]
        result["menu"][where]={k:v["released"] for k,v in check["rows"].items()}
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8")
