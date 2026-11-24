"""Compare the 912 VRAM jobs, physical packing budget and protected prefix."""
import argparse
import csv
import json
from pathlib import Path

from check_nes_blank959 import directory, sha
from check_nes_output970 import counters
from nes_dma1000 import ORIGIN, PACKED, join_body
from pack_nes_column854 import encode
from test_nes_banks557 import MASTER


def records(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def phase_result(temp, phase):
    src = temp / f"nes-ready999-bank-0-p{phase}"
    original = directory(temp, phase, "978returned", "cold")
    prefix = [r for r in records(original/"window.csv") if int(r["g"])<912]
    result = {"linked_978": counters(original,912)}
    for kind in ("control","join","priority","rawfirst","control-begin","fresh","freshjoin","guardjoin"):
        mode, _, suffix = kind.partition("-")
        d=temp/(f"nes-dma1000-{mode}-p{phase}"+("-"+suffix if suffix else ""))
        success=json.loads((d/"result.json").read_bytes())
        assert success["passed"] and success["commits"]==8
        assert all(sha(d/f"frame-{g}.rgb")==sha(original/f"frame-{g}.rgb") for g in range(905,913))
        window=records(d/"window.csv")
        assert [r for r in window if int(r["g"])<912]==prefix
        c=counters(d,912)
        if kind=="control":
            assert c==counters(src,912)
        tail=[r for r in window if r["op"]=="3" and r["g"]=="912"]
        dma=[r for r in tail if r["event"]=="ppu_dma"]
        assert sum(int(r["value"]) for r in dma)==1904
        io=[r for r in records(d/"seal528.csv") if r["g"]=="912" and r["event"]=="dma"]
        assert [int(r["bytes"]) for r in io]==[int(r["value"]) for r in dma]
        # Each row associates the actual MDMAEN with this packet, port, lengths
        # and latched beam. dst is in VRAM bytes only for port $18.
        c["dma"]=[dict(size=int(r["bytes"]),port=int(r["port"]),source=int(r["src"]),
                       last_VRAM_address_register=int(r["dst"]),clock=int(r["clock"]),
                       vb=int(a["frame"]),line=int(r["line"])) for r,a in zip(io,dma,strict=True)]
        c["post_validation_descriptors"]=[list(map(int,s.split())) for s in (d/"descriptors.txt").read_text().splitlines()]
        c["accepted"]=[[int(r[k]) for k in ("index","op","section","clock","frame","line")]
                       for r in window if r["g"]=="912" and r["event"]=="ack"]
        last=io[-1]
        end=int(last["clock"])+(247-int(last["line"]))*1364-int(last["h"])
        c["reveal_minus_end246_same_vblank"]=c["reveal"][0]-end
        c["early_bytes"]=sum(int(r["value"]) for r in dma if r["frame"]=="46")
        c["delta_ACK_vs_same_schedule_us"]=round((c["ack"][0]-counters(src,912)["ack"][0])*1e6/MASTER,3)
        if kind=="control":
            latch=next(r for r in records(d/"seal528.csv") if r["event"]=="latch" and r["g"]=="912")
            end=int(latch["clock"])+(247-int(latch["line"]))*1364-int(latch["h"])
            remaining=end-c["upload165_entry"][0]
            c["until_line_247"]=remaining
            c["data_only_excess"]=1904*8-remaining
            assert c["data_only_excess"]>0
        result[kind]=c
    archived=temp/f"nes-dma1000-join-p{phase}-recorded"
    assert all(sha(archived/f"frame-{g}.rgb")==sha(original/f"frame-{g}.rgb") for g in range(905,913))
    result["recorded_join"] = counters(archived,912)
    result["recorded_join"]["descriptors"] = (archived/"descriptors.txt").read_text().splitlines()
    guards={}
    for fault, status in (("bad_seal",224),("stop_raw",228),("stop_join",228)):
        d=temp/f"nes-dma1000-join-p{phase}-{fault}"
        value=json.loads((d/"result.json").read_bytes())
        assert value["passed"] and value["commits"]==7 and value["last_status"]==status
        assert sha(d/"retained.rgb")==sha(src/"frame-911.rgb")
        dma=[int(r["bytes"]) for r in records(d/"seal528.csv") if r["g"]=="912" and r["event"]=="dma"]
        if fault=="stop_join":
            assert dma[-3:]==[416,32,32]
        guards[fault]=dict(status=status,commits=7,retained_generation=911,dma=dma)
    d=temp/f"nes-dma1000-guardjoin-p{phase}-stop_join"
    value=json.loads((d/"result.json").read_bytes())
    assert value["passed"] and (value["commits"],value["last_status"])==(7,228)
    assert sha(d/"retained.rgb")==sha(src/"frame-911.rgb")
    dma=[int(r["bytes"]) for r in records(d/"seal528.csv") if r["g"]=="912" and r["event"]=="dma"]
    assert dma[-1]==416
    guards["guarded_stop_join"]=dict(status=228,commits=7,retained_generation=911,dma=dma)
    result["guards"]=guards
    return result


def packing():
    pc,target,extra=join_body()
    old=(PACKED/"body.bin").read_bytes()
    data=bytearray(old)
    data[pc-ORIGIN:pc-ORIGIN+3]=bytes((0x20,target&255,target>>8&255))
    data.extend(extra)
    build=json.loads((PACKED/"build.json").read_bytes())
    packed=len(encode(bytes(data),0,2,short_pairs=True))
    assert len(encode(old,0,2,short_pairs=True))==build["encoded_B"]
    return dict(additional_WRAM_code=len(extra),original_encoded=build["encoded_B"],new_encoded=packed,
                loader=build["loader_B"],physical_free=build["physical_free_B"]-(packed-build["encoded_B"]))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    data=dict(packing=packing(), phases={i:phase_result(a.temp,i) for i in (1,2)})
    a.output.write_text(json.dumps(data,indent=2)+"\n",encoding="utf8",newline="\n")
