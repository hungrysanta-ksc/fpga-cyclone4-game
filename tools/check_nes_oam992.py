"""Compare complete ARM/Mesen schedules with equal packets, plan, map and pixels."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from check_nes_raw991 import measure
from check_nes_plan975 import directory, milliseconds, packet_path, read, sha
from nes_oam992 import BASE, PACKED, ROOT


def analyze(temp):
    result={"phases":{}, "ARM_flash_B":{}, "stored_ROM_B":{}, "guards":{}}
    for p in (1,2):
        ref=directory(temp,p,"978returned","cold")
        cases=result["phases"][p]={}
        for mode in ("ref","beforepal","prefix","store","joint"):
            folder=directory(temp,p,"992"+mode,"cold")
            with patch("check_nes_raw991.directory",return_value=folder):
                a=measure(temp,p,"trial",ref)
            marks=read(temp/f"nes-oam992-{mode}-{p}.json")
            _,ledger=packet_path(folder,911)
            last=a["last_oam"]
            a["oam_ARM_last_writes"]=marks
            a["OAM_final_to_last_issue_ms"]=milliseconds(last["issue"]-marks["full_final"])
            start=marks["full_final"]
            end=last["issue"]
            busy={}
            for e in read(folder/"events.json"):
                if e["event"]!="SPI":continue
                clocks=min(e["clock"],end)-max(e["start"],start)
                if clocks>0:busy[e["opcode"]]=busy.get(e["opcode"],0)+clocks
            assert sum(busy.values())<=end-start
            a["SPI_before_last_OAM_ms"]={k:milliseconds(v) for k,v in busy.items()}
            a["outside_SPI_before_last_OAM_ms"]=milliseconds(end-start-sum(busy.values()))
            a["OAM_SPI_ms"]=milliseconds(last["arrive"]-last["issue"])
            a["OAM_queue_ms"]=milliseconds(last["load"]-last["arrive"])
            a["OAM_receiver_ms"]=milliseconds(last["ack"]-last["load"])
            a["return_to_SEAL_entry_ms"]=milliseconds(a["seal"][0]-last["ack"])
            a["packets911"]=ledger
            a["delta_ACK912_ms"]=milliseconds(a["ACK912"]-cases.get("ref",a)["ACK912"])
            if mode=="ref":
                assert a["ACK912"]==read(ref/"joint.json")["frames"][-1]["ACK_masterclock"]
                assert sha(folder/"window.csv")==sha(ref/"window.csv")
            cases[mode]=a
        for mode,a in cases.items():
            base=cases["ref"]
            a["OAM_return_gain_ms"]=milliseconds(base["last_oam"]["ack"]-a["last_oam"]["ack"])
            a["SEAL_gain_ms"]=milliseconds(base["seal"][0]-a["seal"][0])
            a["OAM_margin_to_978_seal_limit_ms"]=milliseconds(base["latest_seal_if_only_validation_and_color_remain"]-a["last_oam"]["ack"])
        for fault in ("stop","span"):
            out=temp/f"nes-oam992-guard-{fault}-p{p}"
            data=read(out/"result.json")
            assert data["passed"] and data["commits"]==6 and data["last_status"]==(228 if fault=="stop" else 224)
            assert sha(out/"retained.rgb")==sha(ref/"frame-910.rgb")
            result["guards"][f"{p}-{fault}"]={"commits":6,"status":data["last_status"],"retained_910":True}
    for name,root in (("978",BASE),("beforepal",ROOT/"beforepal"),("prefix",ROOT/"prefix")):
        result["ARM_flash_B"][name]=next((root/"link").rglob("firmware.stm")).stat().st_size
    for name,root in (("978",PACKED),("store",ROOT/"store")):
        b=read(root/"build.json");result["stored_ROM_B"][name]=64+b["loader_B"]+b["encoded_B"]
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("out",type=Path)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp),indent=2)+"\n",encoding="utf-8")
