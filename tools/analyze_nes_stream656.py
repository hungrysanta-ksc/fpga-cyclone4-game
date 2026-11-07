"""Reconcile serialized D1 data, recoveries, full placement and timed CPU schedules."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_credit654 import measure
from analyze_nes_direct653 import inputs
from analyze_nes_sender652 import budget
from analyze_nes_output615 import read,ms
from check_nes_fault641 import evidence,digest

MODES=("stream","ingress","owner","fused","late","header")

def analyze(a):
    old=evidence("search655-verification.json")["modes"]["walk"]
    fw=digest(a.arm/"src/obj-nes-100/firmware.stm")
    assert fw==evidence("credit654-verification.json")["arm"]["combined"]["firmware"]
    t=a.traces;base=t/"nes-search655-board-walk"
    assert digest(base/"output_files/board.fit.rpt")==old["fit"]["fit_report"]
    baseline=read(t/"nes-search655-rtl-walk/sender.json")
    result={}
    for mode in MODES:
        board=t/f"nes-stream656-board-{mode}";rtl=t/f"nes-stream656-rtl-{mode}"
        guard=t/f"nes-stream656-directed-{mode}"
        for name in ("nes_geometry_sender653.sv","nes_native_spi165.sv","nes_native_export203.sv","nes_native_mailbox165.sv"):
            assert digest(rtl/name)==digest(guard/name)==digest(board/name)
        changed={"nes_native_spi165.sv"}
        if mode=="fused":changed.update(["nes_live_joint.sv","nes_native_mailbox165.sv"])
        for name in evidence("trial613-package.json")["inputs"]:
            if name not in changed:assert digest(board/name)==digest(base/name)
        assert all("PASS652" in (f/"vsim.log").read_text() for f in (rtl,guard))
        blocks=read(rtl/"sender.json")
        assert blocks.keys()==baseline.keys()
        for g in blocks:
            assert [r["wire"] for r in blocks[g]]==[r["wire"] for r in baseline[g]]
        assert digest(guard/"blocks.txt")==digest(t/"nes-stream656-directed-stream/blocks.txt")
        ac=a.probe/("raw-"+mode+".json");assert read(ac)["firmware"]==fw and read(ac)["raw_cold_cells"]==99
        phase={}
        for n in ("1","2"):
            p=t/f"nes-stream656-{mode}{n}"
            v=measure(p,t/f"nes-direct653-owner{n}",t/f"nes-front638-both{n}h",blocks,n,fw)
            prior=old["phases"][n]
            v["ACK_vs_655_ms"]=ms(v["last_ACK"]-prior["last_ACK"])
            v["unchanged_655_ACK"]=v["last_ACK"]==prior["last_ACK"]
            v["timing_pass"]=all(v["checks"].values()) and v["last_ACK"]<=prior["last_ACK"]
            del v["end"]
            phase[n]=v
        rpt=(board/"output_files/board.fit.rpt").read_text()
        ram=[r.split(";")[2].strip()+" "+r.split(";")[3].strip() for r in rpt.splitlines()
             if "nes_native_spi165:native_spi|" in r and "|ALTSYNCRAM " in r]
        assert ram==["M9K Simple Dual Port"],ram
        mapping=(board/"output_files/board.map.rpt").read_text()
        costs={}
        for node in ("nes_native_spi165:native_spi","nes_geometry_sender653:codec","nes_native_mailbox165:native_records"):
            m=re.search(r"\|"+node+r"\|\s*;\s*(\d+) \((\d+)\)\s*;\s*(\d+) \((\d+)\)",mapping)
            assert m,node
            costs[node]=list(map(int,m.groups()))
        result[mode]=dict(fit=budget(board),MAP_comb_inclusive_local_FF_inclusive_local=costs,
            phases=phase,input=inputs(blocks),cell_RAM=ram,rtl={f:digest(board/f) for f in changed|{"nes_geometry_sender653.sv"}},
            D1=digest(rtl/"blocks.txt"),ready=digest(rtl/"sender.json"),directed=digest(guard/"blocks.txt"),
            STOP_log=digest(guard/"vsim.log"),ARM_recovery=digest(ac))
    guards={}
    for k in ("end","queue","geometry","menu","seal"):
        f=a.probe/(k+".json");assert read(f)["firmware"]==fw;guards[k]=digest(f)
    for k in ("none","token","program","done","busy"):
        f=a.probe/f"base-{k}/result.json";r=read(f)
        assert r["passed"] and r["firmware_sha256"]==fw and r["safe_return"]==r["base_restored"]==int(k=="none")
        guards[k]=digest(f)
    return dict(modes=result,baseline=dict(fit=budget(base),input=inputs(baseline)),firmware=fw,guards=guards,
        scope="Board RTL and measured sender clocks, fixed 654 combined ARM and 65816, shared SPI/IRQ and ROM calendar; no physical candidate.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("arm","probe","traces","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
