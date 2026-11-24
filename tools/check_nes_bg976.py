"""Check 976 against 973, including RGB, map packets, profile equivalence and aborts."""
import argparse
import json
from pathlib import Path

from analyze_nes_output970 import deadline

from check_nes_plan975 import FAULTS, directory, inspect, milliseconds, packet_path, read, replay, sha
from nes_bg976 import BASE, EQUAL, ROWS, WORK


def same_trace(measured, original):
    for name in ("events.json","producer.jsonl","records.bin","window.csv"):
        assert sha(measured/name)==sha(original/name),name


def map_payloads(folder):
    result=[]
    for line in (folder/"packets.jsonl").read_text().splitlines():
        _,_,wire,_=json.loads(line)
        head=bytes.fromhex(wire)
        if head[1]==2 and head[0] in (2,4):
            result.append((head[:2]+head[8:]).hex())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--mode",choices=("976hint","976equal"))
    p.add_argument("--guard",choices=FAULTS)
    a=p.parse_args()
    if a.guard:
        if not a.mode:p.error("--mode required with --guard")
        folder=directory(a.temp,1,a.mode,"cold")
        packets,_=packet_path(folder,911)
        replay(a.temp,folder,a.out,"control",packets,911,a.guard)
        return
    result={"flash_B":{},"phases":{},"guards":{},"candidate_profile":{}}
    modes={"973before232":BASE,"976hint":WORK,"976equal":EQUAL}
    for name,work in {**modes,"976rows":ROWS}.items():
        binary,=(work/"link").rglob("firmware.stm")
        result["flash_B"][name]=binary.stat().st_size
        assert (result["flash_B"][name]<=212992)==(name in modes)
    for phase in (1,2):
        ref=directory(a.temp,phase,"973before232","cold")
        same_trace(directory(a.temp,phase,"976profile","cold"),ref)
        result["phases"][phase]=sample={}
        data=read(a.temp/f"nes-bg976-profile-p{phase}.json")
        marks,elapsed=data["marks"],data["elapsed"]
        row=marks["hdma"]-marks["zero"]
        sample["baseline_profile"]=dict(marks=marks,counts=data["counts"],unique_slots=len(set(slot for key,slot in data["calls"])),
            calls_ms={k:milliseconds(v) for k,v in elapsed.items()},
            other_BG_ms=milliseconds(row-sum(elapsed.values())),scroll_ms=milliseconds(marks["offer"]-marks["hdma"]))
        for tag in modes:
            folder=directory(a.temp,phase,tag,"cold")
            z=inspect(folder,ref)
            assert map_payloads(folder)==map_payloads(ref)
            assert [(r["g"],r["records"]) for r in read(folder/"e9931.json")]==[
                (r["g"],r["records"]) for r in read(ref/"e9931.json")]
            sample[tag]={k:z[k] for k in ("displays","six_intervals","interval911","clocks","ms","rgb_matches","firmware_sha256")}
            sample[tag]["matched_map_packets"]=len(map_payloads(folder))
            sample[tag]["shortfall_same_cost_ms"]=milliseconds(
                z["clocks"]["SEAL"][0]-deadline(folder,911)["latest_load_same_cost"])
    for tag in ("976hint","976equal"):
        same_trace(directory(a.temp,1,tag+"count","cold"),directory(a.temp,1,tag,"cold"))
        result["candidate_profile"][tag]=read(a.temp/f"nes-{tag}-counts.json")
        result["guards"][tag]={}
        for fault,last in FAULTS.items():
            folder=a.temp/f"nes-{tag}-{fault}"
            r=read(folder/"result.json")
            assert r["passed"] and r["commits"]==6 and r["last_status"]==last
            assert sha(folder/"frame-910.rgb")==sha(directory(a.temp,1,tag,"cold")/"frame-910.rgb")
            result["guards"][tag][fault]=dict(commits=r["commits"],status=last)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
