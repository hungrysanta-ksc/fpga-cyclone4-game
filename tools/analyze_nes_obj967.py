"""Compare the complete selected physical captures and the ten directed ROM-window runs."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from read_nes_supply905 import MS, decode


ROOT = Path(__file__).resolve().parents[1]
DIGESTS = {
    955: "1722e64899b5633062d8c2a89768d9ddb519ffe2664bfc416edba232c8ae029e",
    966: "c223944a88f83ee8cc6736de3817ee7c98061a1328047d4b0a2e386776104d9a",
}


def capture(directory, edition):
    path = directory / f"nes-frame-mmc{edition}.bin"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != DIGESTS[edition]:
        raise ValueError(f"unexpected MMC{edition} recording")
    trace = decode(path, edition)
    if any(trace["dropped"]) or any("invalid" in row for row in trace["rows"]):
        raise ValueError(f"incomplete MMC{edition} trace")
    row, = (r for r in trace["rows"] if "detail" in r)
    return dict(sha256=digest, valid_summaries=len(trace["rows"]), selected=row)


def read_run(directory, phase, mode):
    log = (directory / f"p{phase}-{mode}.log").read_bytes().decode("utf-8", errors="replace")
    pattern = rf"^# PASS967 mode={mode} phase={phase} ((?:\w+=-?\d+ *)+)\s*$"
    matches = re.findall(pattern, log, re.MULTILINE)
    if len(matches) != 1 or "# Errors: 0," not in log or "** Fatal:" in log:
        raise ValueError(f"incomplete RTL run for {phase}/{mode}")
    fields = dict(field.split("=") for field in matches[0].split())
    return {key: int(value) for key, value in fields.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path)
    parser.add_argument("rtl_logs", type=Path)
    parser.add_argument("board_sof", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package = json.loads((ROOT / "analysis/trial966-package.json").read_text())
    board_digest = hashlib.sha256(args.board_sof.read_bytes()).hexdigest()
    if board_digest != package["image"]["SOF"]:
        raise ValueError("routed board differs from the MMC966 package")
    captures = {n: capture(args.captures, n) for n in DIGESTS}
    guards = (args.rtl_logs / "guards.log").read_bytes().decode("utf-8", errors="replace")
    if "PASS963 SPI" not in guards or "# Errors: 0," not in guards:
        raise ValueError("page acceptance / STOP guard failure")
    schedules = {}
    for phase in (1, 2):
        runs = {mode: read_run(args.rtl_logs, phase, mode)
                for mode in ("control", "early", "eight", "late", "other")}
        base = runs["control"]
        if any(run["E9"] != base["E9"] for run in runs.values()):
            raise ValueError("E9 launch time changed")
        if not (runs["late"]["done"] == runs["other"]["done"] == base["done"]
                and runs["early"]["done"] == runs["eight"]["done"] < base["done"]):
            raise ValueError("directed ROM-window controls disagree")
        schedules[phase] = dict(
            runs=runs, eight_grant_gain_ms=round((base["done"] - runs["eight"]["done"]) * 46.56e-6, 6)
        )
    result = dict(board_sof_sha256=board_digest, capture_bin_ms=MS, page_guards_passed=True, captures=captures,
                  synthetic_rom_windows=schedules)
    args.output.write_bytes((json.dumps(result, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
