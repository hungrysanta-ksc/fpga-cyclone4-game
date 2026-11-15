"""Verify the terminal signature, reader schedule, independent checks and board fit."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from nes_raw506 import sha


def read_json(p):
    return json.loads(p.read_bytes())


def run(temp, work):
    physical = read_json(Path(__file__).resolve().parents[1] / "analysis/hardware803-results.json")["MMC803"]
    target = physical["ppu_raw"]
    assert target == "50d3ce0000a08001" and physical["physical_request"] is None
    board = temp / "nes-fortress804-board"
    old = temp / "nes-fortress801-i"
    runs, examples = {}, {}
    for phase in range(3):
        failures = {}
        for mode in ("control","cold","observer","fixed-warm","fixed-cold","nonzero","stop-low","wrap","abort"):
            root = temp / f"nes-804-{mode}-p{phase}"
            path = root / "simulation.log"
            log = path.read_text()
            result = read_json(root / "result.json")
            assert result["completed"] and result["returncode"] == 0 and "** Fatal:" not in log
            source = read_json(root / "inputs.json")["sources"]
            selected = old if mode in ("control","cold","observer") else board
            for rel in ("rtl/ppu.sv","nes_rom_service.sv","nes_native_arbiter165.sv","nes_rom_physical.sv"):
                assert source[rel] == sha(selected / rel)
            cases = re.findall(r"^# CASE699CPU scenario=(\d+) failed=(\d) error=(\d+).*? context=(\w+) ppu=(\w+)$", log, re.M)
            expected = 1 if mode == "stop-low" else 3 if mode == "abort" else 36
            assert len(cases) == len({r[0] for r in cases}) == expected
            faults = {int(n):(err,ctx,ppu) for n,bad,err,ctx,ppu in cases if bad == "1"}
            failures[mode] = faults
            runs[f"{mode}-p{phase}"] = dict(log=sha(path), cases=expected,
                fault_signatures=dict(Counter(row[2] for row in faults.values())))
            if mode in ("wrap","abort"):
                ref = "full" if mode=="wrap" else "abort"
                refpath = temp / f"nes-fortress801-guards-{ref}-p{phase}/simulation.log"
                def events(text):
                    return [s for s in text.splitlines() if s.startswith(("# WRAP800 ","# CASE699CPU ","# ABORT800 ","# DONE698"))]
                assert events(log) == events(refpath.read_text())
                runs[f"{mode}-p{phase}"]["identical_reference_events"] = len(events(log))
            if mode == "stop-low":
                assert "# STOP804 accepted=204020 step=16" in log
            if mode == "observer":
                assert log.count("# PAGE804 cmd=") == 12
            if mode in ("cold","fixed-cold","nonzero"):
                trace = [line for line in log.splitlines() if line.startswith("# TRACE804 s=9 ")]
                events = {}
                low, tail = ("202020","2020fe") if mode=="nonzero" else ("204020","204000")
                for name, marker in (("low_accept",f"mem=1/1/{low}"),("low_response",f"reply=1/{low}"),
                                     ("tail_accept",f"mem=1/1/{tail}"),("tail_response",f"reply=1/{tail}"),
                                     ("sample","dot=335 ce=1 pipe=10")):
                    line = next(x for x in trace if marker in x)
                    events[name] = int(re.search(r" t=(\d+)",line)[1])
                    if name=="sample":
                        assert f"mapped={tail} valid={int(mode!='cold')}" in line
                examples[f"{mode}-p{phase}"] = events
        assert not failures["control"] and not failures["fixed-warm"]
        assert failures["cold"] == failures["observer"]
        assert {n for n,(_,_,ppu) in failures["cold"].items() if ppu==target} == {9,17,25}
        assert set(failures["fixed-cold"]) == {34,35}
        assert all(failures["cold"][n]==v for n,v in failures["fixed-cold"].items())
    arms = {}
    for n in ("802","803"):
        check = work/f"check{n}"
        fw = work/f"link{n}a/src/obj-nes-100/firmware.stm"
        independent = read_json(check/"independent.json")
        assert independent["firmware"] == sha(fw) and independent["ACK"]["corrupt_bits"] == 152
        previous = work.parent/f"nes-trial802/link{n}/src/obj-nes-100/firmware.stm"
        arm = dict(firmware=sha(fw),bytes=fw.stat().st_size,delta_bytes=fw.stat().st_size-previous.stat().st_size,
                   flash_free=212992-fw.stat().st_size,independent=independent["ACK"],
                   stopped=read_json(check/"stopped.json"),tests={f.relative_to(check).as_posix():sha(f)
                      for f in sorted(check.rglob("*.json"))},display={})
        for i in (1,2):
            r = read_json(temp/f"nes-804-display-{n}-p{i}/result.json")
            before = read_json(temp/f"nes-trial802-{n}-p{i}/result.json")
            assert r["passed"] and r["commits"]==2 and r["last_status"]==1 and r["vram_DMA_B"]==before["vram_DMA_B"]
            assert [x["generation"] for x in r["frames"]]==[905,906]
            arm["display"][i] = dict(ack=[x["ACK_masterclock"] for x in r["frames"]],
                   reference_ack=[x["ACK_masterclock"] for x in before["frames"]],DMA=r["vram_DMA_B"])
        arms[n] = arm
    fit = {}
    for b in (old,board):
        root=b/"output_files"
        sta=(root/"board.sta.summary").read_text()
        text=(root/"board.fit.summary").read_text()
        worst = {k:min(float(s) for s in re.findall(r"Type *: .*? "+k+r" .*?\nSlack : ([-.\d]+)",sta))
                 for k in ("Setup","Hold","Recovery","Removal")}
        assert "Successful" in text and min(worst.values())>=0 and "Slack : -" not in sta
        fit[b.name] = dict(worst_ns=worst,LE=re.search(r"Total logic elements : ([\d,]+)",text)[1],
             LAB=re.search(r"Total LABs:  partially or completely used\s*; (\d+)",(root/"board.fit.rpt").read_text(encoding="latin1"))[1],
             files={name:sha(root/name) for name in ("board.fit.rpt","board.sta.rpt","board.sof")},
             ppu=sha(b/"rtl/ppu.sv"))
    assert sha(board/"board.sdc")==sha(old/"board.sdc")
    changed = []
    for top in (Path("."),Path("rtl"),Path("sys")):
        files = (old/top).glob("*") if top == Path(".") else (old/top).rglob("*")
        for src in files:
            if src.is_file() and src.suffix.lower() in (".vhd",".sv",".v",".qsf",".hex"):
                rel = src.relative_to(old)
                if sha(src)!=sha(board/rel):
                    changed.append(rel.as_posix())
    assert changed==["rtl/ppu.sv"]
    related = {}
    for path,count,key in (("paths801.tsv",12,"slack_ns"),("io612.tsv",9,"slack")):
        with (board/path).open() as f:
            rows = list(csv.DictReader(f,delimiter="\t"))
        assert len(rows)==count and min(float(r[key]) for r in rows)>=0
        related[path]=rows
    return dict(physical_PPU=target,physical_request_unknown=True,runs=runs,
                example_NES_source_clocks=examples,ARM=arms,Quartus_Lite=fit,
                changed_board_sources=changed,related_STA=related)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("temp","work","out"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.temp,a.work),indent=2)+"\n",newline="\n")
