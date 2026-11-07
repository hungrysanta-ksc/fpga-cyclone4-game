"""Check firmware, RTL packet timings, complete-fit outcome and both continuous schedules."""
import argparse
import json
import re
from pathlib import Path
from collections import Counter,defaultdict
from check_nes_game478 import Machine
from check_nes_fault641 import digest,evidence
from analyze_nes_end651 import canonical
from analyze_nes_export636 import run as verify
from analyze_nes_output615 import csv_groups,ms,one,read


def crc32_cost(src,base):
    costs=[]
    for directory in (base,src):
        m=Machine(directory,bytes(128))
        samples=[]
        for byte in range(256):
            for state in (0,0xffffffff,0x12345678^byte):
                x=state^byte
                for _ in range(8):x=(x>>1)^(0xedb88320 if x&1 else 0)
                before=m.instructions
                assert m.call("crc32_update",[state,byte])==x
                samples.append(m.instructions-before)
        costs.append([min(samples),max(samples)])
    return dict(calls_per_ELF=len(samples),instructions=costs)


def budget(board):
    path=board/"output_files"
    summary=(path/"board.fit.summary").read_text()
    report=(path/"board.fit.rpt").read_text()
    def use(label,text):
        m=re.search(label+r"\s*[:;]\s*([\d,]+)\s*/\s*([\d,]+)",text)
        return [int(n.replace(",","")) for n in m.groups()]
    labs=re.search(r"Fitter requires (\d+) LABs.*contains only (\d+) LABs",report)
    return dict(LE=use("Total logic elements",summary),M9K=use("M9Ks",report),
        comb=use("Total combinational functions",summary),FF=use("Dedicated logic registers",summary),
        RAM_bits=use("Total memory bits",summary),LAB_error=[int(s) for s in labs.groups()] if labs else None,
        fit=summary.splitlines()[0],STA=(path/"board.sta.rpt").exists(),SOF=(path/"board.sof").exists(),
        fit_report=digest(path/"board.fit.rpt"),spi=digest(board/"nes_native_spi165.sv"))


def check(a):
    t=a.traces
    src=a.arm/"src"
    flash=src/"obj-nes-100/firmware.stm";fw=digest(flash)
    old=evidence("end651-verification.json")
    size=flash.stat().st_size
    assert size<=old["flash_limit_B"] and old["guards"]["grant"]["flash_B"]-size>=324
    guards={}
    for name in ("end","menu","queue","seal","geometry"):
        path=a.arm/(name+".json");assert read(path)["firmware"]==fw;guards[name]=digest(path)
    for reason in ("none","token","program","done","busy"):
        path=a.arm/f"base-{reason}/result.json";v=read(path)
        assert v["passed"] and v["base_restored"]==v["safe_return"]==int(reason=="none") and v["firmware_sha256"]==fw
        guards[reason]=digest(path)
    blocks=read(a.rtl/"sender.json")
    assert list(map(int,blocks))==list(range(905,958))
    ownership=evidence("receive649-verification.json")["RTL"]
    for name,signature in ownership["rtl"].items():
        assert digest(a.board/name)==signature
    for name in evidence("trial613-package.json")["inputs"]:
        if name not in ("nes_native_spi165.sv","board.qsf"):
            assert digest(a.board/name)==digest(a.base_board/name)
    for name in ("nes_geometry_sender652.sv","nes_native_spi165.sv","nes_native_export203.sv","nes_native_mailbox165.sv"):
        assert digest(a.rtl/name)==digest(a.board/name)
    name="nes_geometry_sender652.sv"
    assert Path(__file__).with_name(name).read_text()==(a.board/name).read_text()
    assert "PASS652" in (a.rtl/"vsim.log").read_text()
    timings={}
    limit=evidence("geometry650-verification.json")
    for n in (1,2):
        prior=old["phases"][str(n)]["grant"];mmc=old["MMC643"][str(n)]
        golden=t/f"nes-front638-both{n}h"
        control=t/f"nes-end651-grant{n}";base=canonical(control)
        ref=limit["phases"][str(n)]["cases"]["base"]["cost"]
        cases={}
        for mode in ("control","rtl","owner"):
            f=t/f"nes-sender652-{mode}{n}";v=verify(f,golden);rows=v["rows"]
            assert canonical(f)==base and v["measured"]["firmware_SHA256"]==fw
            assert all(v["measured"][k]==read(control/"joint.json")[k] for k in ("client_SHA256","parameters"))
            events=read(f/"events.json")
            seal,=[e["start"] for e in events if e["generation"]==954 and e.get("packet_opcode")==3]
            cpu=csv_groups(f/"window.csv")
            previous=one(cpu[953],"reveal")["clock"]
            if mode!="control":
                ds=[r for r in events if r["event"]=="sender652_ready"]
                assert len(ds)==sum(map(len,blocks.values()))
                reads=defaultdict(list)
                for event in events:
                    if event.get("opcode")=="0xd1":reads[event["input_generation"]].append(event)
                for r in ds:
                    b=blocks[str(r["input_generation"])][r["index"]]
                    assert abs(ms(r["ready"]-r["origin"])-b["ready_cycles"]/84000)<1e-8
                    actual=reads[r["input_generation"]][r["index"]]
                    assert actual["start"]>=r["ready"] and actual["bytes"]==len(bytes.fromhex(b["wire"]))+3
                assert len({(r["input_generation"],r["index"]) for r in ds})==len(ds)
            waits=Counter(r["input_generation"] for r in events if r["event"]=="sender652_busy")
            first_margin={}
            if mode!="control":
                for r in ds:
                    if r["index"]!=0:continue
                    g=r["input_generation"]
                    first=next(e for e in events if e.get("opcode")=="0xd0" and
                               e.get("input_generation")==g and e["start"]>=r["origin"]-3)
                    first_margin[g]=ms(first["start"]-r["ready"])+7.5*1000/2625000
            indices=Counter(r["index"] for r in events if r["event"]=="sender652_busy")
            index955=[r for r in events if r.get("input_generation")==955 and r.get("opcode")=="0xd2"]
            old_ack=one([r for r in cpu[954] if r["op"]==3],"ack")["clock"]
            confirmed=sum(next(e["clock"] for e in events if e.get("input_generation")==955
                               and e.get("opcode")=="0xd0" and e["start"]>=r["clock"])<=old_ack for r in index955[:7])
            spans=[rows[g]["interval_VB"] for g in range(951,956)]
            margins=[ms(ref["SEAL_start"]-seal),ref["SEAL_from_953_ms"]-ms(seal-previous)]
            checks=dict(SEAL=min(margins)>=0,both3=spans[3:]==[3,3],line951=rows[951]["line"]<=246,
                        wait957=rows[957]["final_waits"]==0,dense=v["dense_mean_ms"]<mmc["dense_ms"] and v["dense_VB"]<mmc["dense_VB"],
                        ACK=v["last_ACK"]<mmc["last_ACK"])
            cases[mode]=dict(intervals=spans,SEAL_margin_absolute_relative_ms=margins,dense_ms=v["dense_mean_ms"],
                dense_VB=v["dense_VB"],line951=rows[951]["line"],wait957=rows[957]["final_waits"],
                last_ACK=v["last_ACK"],last_vs_MMC643_ms=ms(v["last_ACK"]-mmc["last_ACK"]),
                last_vs_grant_ms=ms(v["last_ACK"]-prior["last_ACK"]),busy_observations=sum(waits.values()),
                busy_by_generation=waits,busy_by_block=indices,first_D0_slack_955_ms=first_margin.get(955),confirmed_955_before_954_ACK=confirmed,checks=checks,trace={file:digest(f/file) for file in
                ("joint.json","events.json","packets.jsonl","window.csv","obj-phases.json")})
        timings[n]=cases
    guard_log=a.rtl_guards/"vsim.log"
    assert "PASS652" in guard_log.read_text() and digest(a.rtl_guards/"nes_geometry_sender652.sv")==digest(a.board/"nes_geometry_sender652.sv")
    return dict(firmware=fw,flash_B=size,flash_saved_B=old["guards"]["grant"]["flash_B"]-size,guards=guards,rtl_guards=digest(guard_log),
        CRC32=crc32_cost(src,a.base_arm/"src"),baseline_fit=budget(a.base_board),candidate_fit=budget(a.board),
        encoder=digest(a.board/"nes_geometry_sender652.sv"),sender_trace=digest(a.rtl/"blocks.txt"),
        board_owner_witness=ownership["witness"],
        blocks=sum(map(len,blocks.values())),first7_955=[{k:v for k,v in b.items() if k!="wire"}|{"payload":len(bytes.fromhex(b["wire"]))} for b in blocks["955"][:7]],
        phases=timings,scope="Linked ARM and 65816, recorded immutable query data with one-edge response, real exporter and mailboxes, SPI-owner RAM timing replay. Modeled IRQ, shared SPI and ROM calendar. No placed STA or physical candidate.")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("arm","base-arm","board","base-board","rtl","rtl-guards","traces","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(check(a),indent=2)+"\n",newline="\n")
