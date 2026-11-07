"""Attribute END latency without double-counting concurrent ROM, queue and SPI work."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from analyze_nes_direct653 import inputs
from analyze_nes_end651 import canonical,profile
from analyze_nes_export636 import run as verify
from analyze_nes_output615 import csv_groups,ms,one,read
from analyze_nes_sender652 import budget
from check_nes_fault641 import digest,evidence


def measure(folder,baseline,golden,blocks,phase,fw):
    stats=verify(folder,golden);rows=stats["rows"]
    assert stats["measured"]["firmware_SHA256"]==fw
    assert canonical(folder)==canonical(baseline)
    j=read(baseline/"joint.json")
    assert all(stats["measured"][k]==j[k] for k in ("parameters","client_SHA256"))
    events=read(folder/"events.json");cpu=csv_groups(folder/"window.csv")
    ds=defaultdict(list);ready=defaultdict(list)
    for r in events:
        if r.get("opcode")=="0xd1":ds[r["input_generation"]].append(r)
        if r["event"]=="sender652_ready":ready[r["input_generation"]].append(r)
    for g in range(905,958):
        for i,(d,r,b) in enumerate(zip(ds[g],ready[g],blocks[str(g)],strict=True)):
            assert i==r["index"] and d["start"]>=r["ready"] and d["bytes"]==len(bytes.fromhex(b["wire"]))+3
            assert abs(ms(r["ready"]-r["origin"])-b["ready_cycles"]/84000)<1e-8
    p=profile(folder);end=p["END"]
    p["ROM_first_grant"]=p["BG_grants"][0];p["ROM_last_grant"]=p["BG_grants"][-1]
    del p["BG_grants"]
    for row in p["tiles"]:
        for k in ("start","push","load","ack","ARM_credit"):row[k]=ms(row[k]-end)
    assert abs(sum(p["END_to_output_ms_by_owner"].values())-p["END_to_output_ms"])<1e-8
    mmc=evidence("end651-verification.json")["MMC643"][phase]
    ref=evidence("geometry650-verification.json")["phases"][phase]["cases"]["base"]["cost"]
    seal,=[r["start"] for r in events if r["generation"]==954 and r.get("packet_opcode")==3]
    margin=ref["SEAL_from_953_ms"]-ms(seal-one(cpu[953],"reveal")["clock"])
    intervals=[rows[g]["interval_VB"] for g in range(951,956)]
    last=ms(stats["last_ACK"]-mmc["last_ACK"])
    gates=dict(SEAL=seal<=ref["SEAL_start"] and margin>=0,margin11=margin>=0.011,
               both3=intervals[-2:]==[3,3],line951=rows[951]["line"]<=246,wait957=rows[957]["final_waits"]==0,
               dense=stats["dense_mean_ms"]<mmc["dense_ms"] and stats["dense_VB"]<mmc["dense_VB"],
               ACK=last<0,ACK653=stats["last_ACK"]<=j["frames"][-1]["ACK_masterclock"])
    p["end_enter_after_954_ms"]=ms(end-one(cpu[954],"reveal")["clock"])
    return dict(end=p,intervals=intervals,margin954_ms=margin,absolute_margin_ms=ms(ref["SEAL_start"]-seal),
                line951=rows[951]["line"],wait957=rows[957]["final_waits"],dense_ms=stats["dense_mean_ms"],
                last_ACK=stats["last_ACK"],last_vs_MMC643_ms=last,
                last_vs_653_ms=ms(stats["last_ACK"]-j["frames"][-1]["ACK_masterclock"]),checks=gates,
                firmware=fw,pins={k:digest(folder/k) for k in ("events.json","window.csv","joint.json","packets.jsonl","obj-phases.json")})


def analyze(a):
    base_blocks=read(a.base_rtl/"sender.json");serial=read(a.rtl/"sender.json")
    for g in range(905,958):
        assert [b["wire"] for b in base_blocks[str(g)]]==[b["wire"] for b in serial[str(g)]]
    for name in ("nes_geometry_sender653.sv","nes_native_spi165.sv","nes_native_export203.sv","nes_native_mailbox165.sv"):
        assert digest(a.board/name)==digest(a.rtl/name)==digest(a.guards/name)
    for name in evidence("trial613-package.json")["inputs"]:
        if name!="nes_native_spi165.sv":assert digest(a.board/name)==digest(a.base_board/name)
    assert "PASS652" in (a.guards/"vsim.log").read_text()
    cases={}
    for phase in ("1","2"):
        base=a.traces/f"nes-direct653-owner{phase}";gold=a.traces/f"nes-front638-both{phase}h"
        fw=read(base/"joint.json")["firmware_SHA256"]
        cases[phase]={"653":measure(base,base,gold,base_blocks,phase,fw)}
        for mode in a.modes:
            is_serial=mode.startswith("serial-")
            arm=mode.removeprefix("serial-")
            binary=fw if arm=="baseline" else digest(a.probe/arm/"src/obj-nes-100/firmware.stm")
            folder=a.traces/f"nes-credit654-{mode}{phase}"
            cases[phase][mode]=measure(folder,base,gold,serial if is_serial else base_blocks,phase,binary)
    arm_cost={}
    for mode in sorted({v.removeprefix("serial-") for v in a.modes}-{"baseline"}):
        folder=a.probe/mode
        binary=folder/"src/obj-nes-100/firmware.stm";fw=digest(binary)
        pins={}
        for k in ("end","queue","seal","raw","menu","geometry"):
            f=folder/(k+".json");assert read(f)["firmware"]==fw;pins[k]=digest(f)
        for k in ("none","busy","program","done","token"):
            f=folder/f"base-{k}/result.json";r=read(f)
            assert r["passed"] and r["firmware_sha256"]==fw
            assert r["safe_return"]==r["base_restored"]==int(k=="none")
            pins[k]=digest(f)
        arm_cost[mode]=dict(firmware=fw,flash_B=binary.stat().st_size,guards=pins)
    return dict(phases=cases,arm=arm_cost,base_fit=budget(a.base_board),fit=budget(a.board),base_input=inputs(base_blocks),
                serial_input=inputs(serial),testbench=digest(a.guards/"tb.sv"),guards_log=digest(a.guards/"vsim.log"),
                cold_bytes=digest(a.guards/"blocks.txt"),RTL_D1=digest(a.rtl/"blocks.txt"))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("board","base-board","rtl","base-rtl","guards","probe","traces","out"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--modes",nargs="+",required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
