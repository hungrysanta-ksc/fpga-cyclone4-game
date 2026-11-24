"""Reconcile receiver service and bus-inclusive SEAL time against the 978 deadline."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from check_nes_raw991 import measure
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_blank959 import rows
from nes_color994 import BASE, PACKED, ROOT


def analyze(t):
    result={"phases":{},"guards":{},"stored_image_B":{}}
    for p in (1,2):
        ref=directory(t,p,"978returned","cold")
        cases=result["phases"][p]={}
        for mode in ("ref","scatter3","uniform3","both3","matched","ideal","split"):
            d=directory(t,p,"994"+mode,"cold")
            with patch("check_nes_raw991.directory",return_value=d):
                a=measure(t,p,"candidate",ref)
            _,ledger=packet_path(d,911)
            rr=rows(d/"window.csv")
            assert ledger[7]["op"]==7 and ledger[7]["section"]==1
            stage=[]
            colors=[q for q in ledger[8:] if q["section"] in (3,4)]
            assert len(colors)==5
            for q in colors:
                marks=[(r["event"],int(r["clock"])) for r in rr if int(r["index"])==q["index"]]
                def at(key):
                    value,=(clock for k,clock in marks if k==key)
                    return value
                lo,addr,done,hi=(q["load"],at("color994_checked"),at("color994_accepted"),q["ack"])
                ins=[clock for k,clock in marks if k=="color994_service_in" and addr<=clock<done]
                outs=[clock for k,clock in marks if k=="color994_service_out" and addr<=clock<done]
                assert lo<addr<done<hi and len(ins)==len(outs) and all(i<o for i,o in zip(ins,outs))
                stage.append(dict(op=q["op"],section=q["section"],index=q["index"],load=lo,checked_addr=addr,
                                  accepted=done,ack=hi,header_and_range=addr-lo,restore=done-addr,
                                  restore_service=sum(o-i for i,o in zip(ins,outs)),receipt=hi-done))
            orig=read(Path("analysis/overlap993-results.json"))["phases"][str(p)]["ref"]
            limit=orig["latest_SEAL"]
            service_end=ledger[7]["ack"]+sum(q["ack"]-q["load"] for q in ledger[8:-1])+a["seal"][0]-ledger[-1]["load"]
            clocks=lambda k:sum(s[k] for s in stage)
            case=cases[mode]=dict(stage=stage,stage_total_ms={k:ms(clocks(k)) for k in ("header_and_range","restore","restore_service","receipt")},
                OBJ_return=dict(read(d/"returns904.json"))[30],OBJ_ack=ledger[7]["ack"],receiver_only_late_ms=ms(service_end-limit),
                measured_SEAL_late_ms=ms(a["seal"][0]-limit),last_SPI_issue=ledger[-1]["issue"],last_SPI_end=ledger[-1]["arrive"],
                SEAL=a["seal"],DMAs=a["DMAs"],reveal911=a["reveal911"],interval=a["interval"],six=a["six"],ACK912=a["ACK912"],
                reveal908=a["reveal908"],early909_B=a["early909_B"],capture_margin910_ms=a["margin910_ms"],ACK910=a["ACK910"],
                delta_ACK912_ms=ms(a["ACK912"]-orig["ACK912"]),firmware=a["link"],rom=a["rom"])
            case["wire_and_head_gap"]=[
                dict(op=q["op"],section=q["section"],load_after_previous_ack_ms=ms(q["load"]-prev["ack"]),
                     wire_end_after_previous_ack_ms=ms(q["arrive"]-prev["ack"]))
                for prev,q in zip(ledger[7:-1],ledger[8:])]
            if mode!="split":assert case["reveal908"][1:]==[38,245] and case["capture_margin910_ms"]>0
            if mode=="ref":
                assert a["ACK912"]==orig["ACK912"] and a["seal"]==orig["seal"] and a["early909_B"]==624
                assert abs(case["receiver_only_late_ms"]-orig["service_only_late_ms"][0])<1e-5
            if mode in ("matched","ideal"):
                assert case["ACK910"]==cases["ref"]["ACK910"] and a["early909_B"]==624 and case["reveal908"]==cases["ref"]["reveal908"]
            if mode=="ideal":
                assert case["OBJ_return"]==cases["ref"]["OBJ_return"]
                assert sum(r["event"]=="instant994" for r in rr)==5
        for case in ("changed","span","stop","fallback"):
            d=t/f"nes-color994-guard-{case}-p{p}";data=read(d/"result.json")
            assert data["passed"] and data["commits"]==(7 if case=="changed" else 6)
            if case!="changed":
                assert data["last_status"]==(228 if case=="stop" else 224)
                assert sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
            result["guards"][f"{case}-p{p}"]=[data["commits"],data["last_status"]]
    for mode in ("ref","scatter3","uniform3","both3"):
        b=read((PACKED if mode=="ref" else ROOT/mode)/"build.json")
        result["stored_image_B"][mode]=64+b["loader_B"]+b["encoded_B"]
    result["ARM_flash_B"]=next((BASE/"link").rglob("firmware.stm")).stat().st_size
    from nes_overlap993 import ROOT as arm993
    result["split_ARM_flash_B"]=next((arm993/"split/link").rglob("firmware.stm")).stat().st_size
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf8",newline="\n")
