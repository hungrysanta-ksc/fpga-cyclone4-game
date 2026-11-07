"""Reconcile direct map capture, byte-exact fallback, display and whole-board fit."""
import argparse
import json
from collections import Counter,defaultdict
from pathlib import Path
from analyze_nes_end651 import canonical
from analyze_nes_export636 import run as verify
from analyze_nes_output615 import csv_groups,ms,one,read
from analyze_nes_sender652 import budget
from check_nes_fault641 import digest,evidence


def inputs(blocks):
    return dict(packets=sum(map(len,blocks.values())),
        payload_B=sum(len(bytes.fromhex(b["wire"])) for p in blocks.values() for b in p),
        first7_955_B=sum(len(bytes.fromhex(b["wire"])) for b in blocks["955"][:7]),
        first7_955_us=sum(b["ready_cycles"] for b in blocks["955"][:7])/84,
        encoder7_955_us=sum(b["codec_cycles"] for b in blocks["955"][:7])/84,
        frame955_B=sum(len(bytes.fromhex(b["wire"])) for b in blocks["955"]),
        frame955_packets=len(blocks["955"]))


def analyze(a):
    old=evidence("sender652-verification.json");mmc=evidence("end651-verification.json")["MMC643"]
    fw=digest(a.arm/"src/obj-nes-100/firmware.stm")
    assert fw==old["firmware"]==read(a.probe/"arm-guards.json")["firmware"]
    # Menu/base and final-ACK guards run on the same ELF used in both replays.
    guards={}
    for name in ("end","geometry","seal","queue","menu"):
        path=a.probe/(name+".json");assert read(path)["firmware"]==fw;guards[name]=digest(path)
    for fault in ("none","program","token","done","busy"):
        path=a.probe/f"base-{fault}/result.json";r=read(path)
        assert r["firmware_sha256"]==fw and r["passed"] and r["base_restored"]==r["safe_return"]==int(fault=="none")
        guards[fault]=digest(path)
    shared=("nes_native_export203.sv","nes_native_mailbox165.sv","nes_native_spi165.sv","nes_geometry_sender653.sv")
    for name in shared:
        assert digest(a.board/name)==digest(a.rtl/name)==digest(a.guards/name)
    assert (a.board/shared[-1]).read_text()==Path(__file__).with_name(shared[-1]).read_text()
    assert all("PASS652" in (d/"vsim.log").read_text() for d in (a.rtl,a.guards))
    for name in evidence("trial613-package.json")["inputs"]:
        if name not in ("board.qsf","nes_native_spi165.sv","nes_native_export203.sv"):
            assert digest(a.board/name)==digest(a.base_board/name)
    blocks=read(a.rtl/"sender.json");baseline=read(a.base_rtl/"sender.json")
    assert digest(a.rtl/"sender.json")==digest(a.replay_rtl/"sender.json")
    assert list(map(int,blocks))==list(range(905,958))
    report={}
    for phase in (1,2):
        n=str(phase);p=a.traces/f"nes-direct653-owner{n}";base=a.traces/f"nes-sender652-owner{n}"
        v=verify(p,a.traces/f"nes-front638-both{n}h");rows=v["rows"];prior=old["phases"][n]["owner"]
        assert canonical(base)==canonical(p) and v["measured"]["firmware_SHA256"]==fw
        assert all(v["measured"][k]==read(base/"joint.json")[k] for k in ("client_SHA256","parameters"))
        ref=evidence("geometry650-verification.json")["phases"][n]["cases"]["base"]["cost"]
        events=read(p/"events.json");cpu=csv_groups(p/"window.csv")
        reads=defaultdict(list);ready=defaultdict(list)
        for e in events:
            if e.get("opcode")=="0xd1":reads[e["input_generation"]].append(e)
            if e["event"]=="sender652_ready":ready[e["input_generation"]].append(e)
        for g in range(905,958):
            for i,(d,r,b) in enumerate(zip(reads[g],ready[g],blocks[str(g)],strict=True)):
                assert r["index"]==i and d["start"]>=r["ready"] and d["bytes"]==len(bytes.fromhex(b["wire"]))+3
                assert abs(ms(r["ready"]-r["origin"])-b["ready_cycles"]/84000)<1e-8
        seal,=[e["start"] for e in events if e["generation"]==954 and e.get("packet_opcode")==3]
        margin=ref["SEAL_from_953_ms"]-ms(seal-one(cpu[953],"reveal")["clock"])
        intervals=[rows[g]["interval_VB"] for g in range(951,956)]
        ack=ms(v["last_ACK"]-mmc[n]["last_ACK"])
        checks=dict(SEAL=margin>=0 and seal<=ref["SEAL_start"],margin11=margin>=.011,
            both3=intervals[-2:]==[3,3],line951=rows[951]["line"]<=246,wait957=rows[957]["final_waits"]==0,
            dense=v["dense_mean_ms"]<mmc[n]["dense_ms"] and v["dense_VB"]<mmc[n]["dense_VB"],ACK=ack<0)
        report[n]=dict(intervals=intervals,dense_ms=v["dense_mean_ms"],dense_VB=v["dense_VB"],
            SEAL_margin_absolute_relative_ms=[ms(ref["SEAL_start"]-seal),margin],line951=rows[951]["line"],
            wait957=rows[957]["final_waits"],last_ACK=v["last_ACK"],last_vs_MMC643_ms=ack,
            last_vs_652_ms=ms(v["last_ACK"]-prior["last_ACK"]),checks=checks,
            source_SPI_B=sum(e["bytes"] for e in events if e.get("opcode") in ("0xd0","0xd1","0xd2","0xd3")),
            source_SPI_652_B=sum(e["bytes"] for e in read(base/"events.json") if e.get("opcode") in ("0xd0","0xd1","0xd2","0xd3")),
            busy=Counter(e["input_generation"] for e in events if e["event"]=="sender652_busy"),
            pins={f:digest(p/f) for f in ("joint.json","events.json","window.csv","packets.jsonl","seal528.csv")})
    return dict(phases=report,guards=guards,arm_negative=read(a.probe/"arm-guards.json"),firmware=fw,
        baseline=inputs(baseline),direct=inputs(blocks),fit=budget(a.board),fit652=budget(a.base_board),
        RTL={name:digest(a.board/name) for name in shared},transactions=digest(a.rtl/"blocks.txt"),
        replay_input=digest(a.replay_rtl/"sender.json"),cold_fallback=digest(a.guards/"blocks.txt"),
        abort_STOP_log=digest(a.guards/"vsim.log"),scope="RTL export/CDC/shared M9K/SPI timing replay with ARM CPI2, IRQ, ROM calendar and actual 65816. No physical FPS.")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("board","base-board","rtl","replay-rtl","base-rtl","guards","arm","probe","traces","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
