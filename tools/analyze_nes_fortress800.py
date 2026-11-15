"""Verify the fortress experiment against the two frozen physical fault words."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from probe_nes_fortress800 import compact_reader, preview_ppu


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(line):
    return dict(item.split("=", 1) for item in line.split() if "=" in item)


def analyze(temp):
    physical = Path(__file__).resolve().parents[1] / "analysis/hardware799-results.json"
    fault = json.loads(physical.read_text())["MMC799"]
    signature = (fault["context"]["raw"], fault["ppu_raw"])
    data = {"physical_report_sha256": digest(physical), "physical_signature": signature,
            "phase_ns": [0.5, 3.5, 6.5], "runs": {}, "case8_phase2": {}}
    signatures = {}
    for label in ("b-base", "b-preview", "c-compact", "c-abort"):
        for phase in range(3):
            folder = temp / f"nes-fortress800{label}-p{phase}"
            key = f"{label}-p{phase}"
            sim = folder / "simulation.log"
            result = json.loads((folder / "result.json").read_text())
            lines = sim.read_text().splitlines()
            meta = json.loads((folder / "inputs.json").read_text())
            assert meta["phase"] == data["phase_ns"][phase]
            assert result["returncode"] == 0 and result["completed"]
            assert result["simulation_sha256"] == digest(sim)
            assert any("DONE698" in line for line in lines)
            cases = [fields(line) for line in lines if line.startswith("# CASE699CPU ")]
            assert [int(row["scenario"]) for row in cases] == list(
                range(8, 11) if label == "c-abort" else range(36))
            failures = {int(row["scenario"]): (row["context"], row["ppu"])
                        for row in cases if row["failed"] != "0"}
            target = [n for n, sig in failures.items() if sig == signature]
            others = {n: sig for n, sig in failures.items() if sig != signature}
            if label == "b-base":
                assert len(target) == 9 and len(others) == 3
                signatures[phase] = others
            elif label == "c-abort":
                assert not failures and sum("ABORT800 scenario=" in line for line in lines) == 3
            else:
                assert not target and others == signatures[phase]
            data["runs"][key] = {"cases": len(cases), "matching_fault": target,
                                 "other_first_faults": others, "log_sha256": digest(sim),
                                 "inputs_sha256": digest(folder / "inputs.json")}
            if phase == 2 and label != "c-abort":
                trace = [fields(line) for line in lines if line.startswith("# WRAP800 s=8 ")]
                trace = {int(row["t"]): row for row in trace}
                launch, response = (32, 37) if label == "b-base" else (28, 33)
                assert trace[launch]["mem"] == "1/1/204082"
                assert trace[response]["reply"] == "1/204082"
                assert trace[35]["ce"] == "1" and trace[35]["valid"] == str(int(label != "b-base"))
                data["case8_phase2"][label] = [trace[n] for n in (20, 25, 27, 28, 32, 33, 35, 37)]

    data["regression_controls"] = {}
    for name, count in (("bg707", 12), ("spade699", 8)):
        for phase in range(3):
            folder = temp / f"nes-fortress800-old-{name}-p{phase}"
            lines = (folder / "simulation.log").read_text().splitlines()
            result = json.loads((folder / "result.json").read_text())
            assert result["completed"] and result["returncode"] == 0
            assert result["simulation_sha256"] == digest(folder / "simulation.log")
            rows = [fields(line) for line in lines if line.startswith("# CASE699CPU ")]
            assert len(rows) == count and all(row["failed"] == "0" for row in rows)
            assert any("DONE698" in line for line in lines)
            data["regression_controls"][f"{name}-p{phase}"] = {
                "passed": len(rows), "log_sha256": result["simulation_sha256"]}

    data["boards"] = {}
    base = temp / "nes-trial763/board763"
    for label, folder in (("baseline", base), ("preview", temp / "nes-fortress800-board-a"),
                          ("compact", temp / "nes-fortress800-board-b-bound")):
        files = folder / "output_files"
        path = files / "board.fit.summary"
        rtl = ("rtl/ppu.sv", "nes_rom_service.sv")
        for name, transform in zip(rtl, (preview_ppu, compact_reader)):
            source = (base / name).read_text()
            changed = label != "baseline" and (name == rtl[0] or label == "compact")
            assert (folder / name).read_text() == (transform(source) if changed else source)
        result = {"sources": {name: digest(folder / name) for name in
                              (*rtl, "cdc181.sdc", "cdc576.sdc", "initial576.sdc")},
                  "fit": path.read_text().splitlines(), "reports": {}, "errors": []}
        for name in ("board.map.rpt", "board.fit.rpt", "board.sta.rpt", "board.sta.summary"):
            if (files / name).exists():
                result["reports"][name] = digest(files / name)
        if (files / "board.sta.summary").exists():
            result["sta"] = (files / "board.sta.summary").read_text().splitlines()
            report = (files / "board.sta.rpt").read_text(errors="replace")
            rows = re.findall(r"^;\s+(-\d+\.\d+)\s*;\s*([^;\n]+?)\s*;\s*([^;\n]+?)\s*;[^\n]+$", report, re.M)
            result["failing_paths"] = sorted({(slack, src, dst) for slack, src, dst in rows
                                              if "|" in src and "|" in dst})
        area = (files / "board.fit.rpt").read_text(errors="replace")
        labs = re.search(r"Total LABs:  partially or completely used\s*;\s*(\d+) / (\d+)", area)
        if labs:
            result["labs_used_total"] = [int(x) for x in labs.groups()]
        if label != "baseline":
            errors = (folder / "compile.log").read_text(errors="replace").splitlines()
            result["errors"] = [line for line in errors if re.match(r"Error \(\d+\):", line)]
        data["boards"][label] = result
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.temp), indent=2) + "\n", encoding="utf-8")
