"""Check both 978 prefixes and reconcile E1 wire time with actual queue service."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from build_nes_sparse995 import WORK
from check_nes_blank959 import rows
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_raw991 import measure
from nes_hdma990 import BASE
from nes_receiver995 import receiver
from nes_sparse995 import MODES, SPI_HZ
from test_nes_raw506_joint import PERIOD


def analyze(temp):
    result = {"spi_Hz": SPI_HZ, "decoder_code_B":len(receiver()[0]), "flash_B":{}, "phases":{}}
    for name, work in (("978",BASE),("995",WORK)):
        image, = (work/"link").rglob("firmware.stm")
        result["flash_B"][name] = image.stat().st_size
    limits = read(Path("analysis/overlap993-results.json"))["phases"]
    for p in (1,2):
        ref = directory(temp,p,"978returned","cold")
        cases = result["phases"][p] = {}
        for mode in ("ref",*MODES,"linked"):
            tag = "995linked" if mode=="linked" else "995wire"+mode
            d = ref if mode=="ref" else directory(temp,p,tag,"cold")
            with patch("check_nes_raw991.directory",return_value=d):
                a = measure(temp,p,"candidate",ref)
            _, q = packet_path(d,911)
            tbl,seal = q[-2:]
            j = read(d/"joint.json")
            points = {k:a[k] for k in ("seal","upload","reveal908","early909_B","margin910_ms",
                                        "reveal910","reveal911","interval","six","ACK912","link","rom")}
            points["frame_ACKs"] = [f["ACK_masterclock"] for f in j["frames"]]
            points["tail"] = [{k:r[k] for k in ("op","section","index","issue","arrive","load","ack")} for r in q[-9:]]
            points["DMA"] = a["DMAs"]
            points["table_queued_ms"] = ms(tbl["load"]-tbl["arrive"])
            points["SEAL_queued_ms"] = ms(seal["load"]-seal["arrive"])
            points["SEAL_after_table_ACK_ms"] = ms(a["seal"][0]-tbl["ack"])
            points["SEAL_late_ms"] = ms(a["seal"][0]-limits[str(p)]["ref"]["latest_SEAL"]
                                        -(a["reveal910"][1]-43)*PERIOD)
            cases[mode] = points
            if mode == "ref":
                continue
            base=cases["ref"]
            points["ACK912_delta_ms"] = ms(a["ACK912"]-base["ACK912"])
            if mode != "linked":
                assert points["frame_ACKs"][:6] == base["frame_ACKs"][:6]
                assert a["reveal908"][1:] == [38,245] and a["early909_B"] == 624 and a["margin910_ms"]>0
                wire = read(d/"transport995.json")
                points["wire"] = wire
                points["wire_saved_ms"] = round(sum(x["logical_B"]-x["charged_B"] for x in wire)*8000/SPI_HZ,6)
                points["SEAL_gain_ms"] = ms(base["seal"][0]-a["seal"][0])
                assert tbl["load"] == base["tail"][-2]["load"] and tbl["ack"] == base["tail"][-2]["ack"]
            else:
                w = read(d/"wire995.json")
                points["actual_wire"] = w
                timing = [r for r in rows(d/"window.csv") if r["event"] in ("decode995","restored995")]
                assert len(timing)==2*len(w)
                elapsed=[]
                for z,(begin,end) in zip(w,zip(timing[::2],timing[1::2],strict=True),strict=True):
                    assert begin["index"]==end["index"] and int(begin["g"])==int(end["g"])==z[0]
                    assert begin["event"]=="decode995" and end["event"]=="restored995"
                    if z[0]==911:
                        elapsed.append(ms(int(end["clock"])-int(begin["clock"])))
                assert [(x[2],x[3]) for x in w if x[0]==911]==[(240,55),(168,57)]
                points["decode911_ms"] = elapsed
        # Compare logical OAM from the last final ACK of the same bank.
        commands, _ = packet_path(ref,911)
        def oam(generation):
            out=bytearray()
            for gen,op,_,wire,*_ in commands:
                b=bytes.fromhex(wire)
                if gen!=generation or b[1]!=4:
                    continue
                assert len(out)==int.from_bytes(b[10:12],"little") and op in (2,4,8)
                data=b[16:]
                span=len(data) if op==2 else int.from_bytes(b[14:16],"little")
                assert span%len(data)==0
                out.extend(data*(span//len(data)))
            assert len(out)==544
            return out
        old,new=oam(909),oam(911)
        cases["OAM_909_to_911"]=[[start,end,sum(x!=y for x,y in zip(old[start:end],new[start:end],strict=True))]
                                 for start,end in ((0,176),(176,212),(212,512),(512,544))]
        guards=cases["guards"]={}
        for case,status in (("stop",228),("truncated",224),("semantic",224)):
            d=temp/f"nes-sparse995-guard-{case}-p{p}"
            if case=="stop":
                d=d.with_name(d.name+"-bounded")
                marks=[r for r in rows(d/"window.csv") if r["event"]=="partial_stop995"]
                assert len(marks)==1 and int(marks[0]["value"])==64
            j=read(d/"result.json")
            assert j["passed"] and j["commits"]==6 and j["last_status"]==status
            assert sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
            guards[case]={"commits":j["commits"],"status":status,"retained_rgb":sha(d/"retained.rgb")}
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf8",newline="\n")
