"""Verify placement, lookups and two complete schedules against the fixed 654 ELF."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_credit654 import measure
from analyze_nes_direct653 import inputs
from analyze_nes_sender652 import budget
from check_nes_fault641 import digest,evidence
from analyze_nes_output615 import ms,read

MODES=("walk","pair","mask","m9k2")
FILES=("nes_geometry_sender653.sv","nes_native_spi165.sv","nes_native_export203.sv","nes_native_mailbox165.sv")


def counters(folder):
    rows=[list(map(int,r.split())) for r in (folder/"search.txt").read_text().splitlines()]
    assert [r[:2] for r in rows]==[[955,i] for i in range(17)]
    return dict(compare_A=sum(r[2] for r in rows[:7]),compare_B=sum(r[3] for r in rows[:7]),
                search=sum(r[4] for r in rows[:7]),log=digest(folder/"search.txt"))


def analyze(a):
    t=a.traces;old=evidence("credit654-verification.json")
    fw=digest(a.arm/"src/obj-nes-100/firmware.stm")
    assert fw==old["arm"]["combined"]["firmware"]
    baseline=t/"nes-credit654-board01"
    models=read(t/"nes-credit654-rtl01/sender.json")
    assert digest(baseline/"output_files/board.fit.rpt")==old["fit"]["fit_report"]
    result={}
    for mode in MODES:
        brd=t/f"nes-search655-board-{mode}";rtl=t/f"nes-search655-rtl-{mode}"
        guard=t/f"nes-search655-guards-{mode}";direct=t/f"nes-search655-directed-{mode}";pr=t/f"nes-search655-profile-{mode}"
        for name in evidence("trial613-package.json")["inputs"]:
            if name!="nes_native_spi165.sv":assert digest(brd/name)==digest(baseline/name)
        for name in FILES:
            assert all(digest(brd/name)==digest(f/name) for f in (rtl,guard,direct,pr))
        assert all("PASS652" in (f/"vsim.log").read_text() for f in (rtl,guard,direct,pr))
        blocks=read(rtl/"sender.json")
        assert blocks.keys()==models.keys()
        for g,rows in blocks.items():
            assert [r["wire"] for r in rows]==[r["wire"] for r in models[g]]
        assert digest(guard/"blocks.txt")==digest(t/"nes-credit654-guards02/blocks.txt")
        assert (direct/"blocks.txt").read_bytes()==(t/"nes-search655-directed-walk/blocks.txt").read_bytes()
        arm_check=a.probe/f"raw-{mode}.json"
        assert read(arm_check)["firmware"]==fw and read(arm_check)["raw_cold_cells"]==99
        assert [r["wire"] for r in read(pr/"sender.json")["955"]]==[r["wire"] for r in blocks["955"]]
        replay=mode
        if mode=="m9k2" and blocks==read(t/"nes-search655-rtl-mask/sender.json"):replay="mask"
        phases={}
        for n in ("1","2"):
            f=t/f"nes-search655-{replay}{n}"
            m=measure(f,t/f"nes-direct653-owner{n}",t/f"nes-front638-both{n}h",blocks,n,fw)
            ref=old["phases"][n]["serial-combined"]
            m["last_vs_654_ms"]=ms(m["last_ACK"]-ref["last_ACK"])
            m["matches_654_last_ACK"]=m["last_ACK"]==ref["last_ACK"]
            del m["end"]
            phases[n]=m
        rpt=(brd/"output_files/board.fit.rpt").read_text()
        ram=[s for s in rpt.splitlines() if "nes_native_spi165:native_spi|" in s and "|ALTSYNCRAM " in s]
        hierarchy=(brd/"output_files/board.map.rpt").read_text()
        cost=re.search(r"\|nes_geometry_sender653:codec\|\s*;\s*(\d+) \(\d+\)\s*;\s*(\d+) \(",hierarchy)
        assert cost and ram
        result[mode]=dict(fit=budget(brd),codec_map_comb_FF=list(map(int,cost.groups())),
                input=inputs(blocks),search955first7=counters(pr),inferred_RAMs=[r.split(";")[2].strip()+" "+r.split(";")[3].strip() for r in ram],
                phases=phases,replay=replay,rtl={name:digest(brd/name) for name in FILES},sender=digest(rtl/"sender.json"),
                partial_STOP=digest(guard/"vsim.log"),compared_addresses=digest(direct/"vsim.log"),directed_bytes=digest(direct/"blocks.txt"),
                ARM_cold=digest(arm_check))
    guards={}
    for k in ("end","geometry","queue","menu","seal"):
        f=a.probe/(k+".json");assert read(f)["firmware"]==fw;guards[k]=digest(f)
    for k in ("none","program","done","busy","token"):
        f=a.probe/f"base-{k}/result.json";r=read(f)
        assert r["passed"] and r["firmware_sha256"]==fw and r["base_restored"]==r["safe_return"]==int(k=="none")
        guards[k]=digest(f)
    return dict(modes=result,baseline=dict(fit=budget(baseline),src=inputs(models),search955first7=counters(t/"nes-search655-profile-base")),
                firmware=fw,ARM_guards=guards,scope="53 captures, real board SPI/export/CDC with recorded query data, measured block readiness, fixed combined ARM and 65816. Physical FPS is unmeasured.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("traces","probe","arm","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
