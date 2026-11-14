"""Materialize the two changed 707D ROM builds and four physical trial ARM patches."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from package_nes_window516 import LABELS

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"
VARIANTS = {
    763: ("nes-trial704/arm704-02", "704", "nes-complete685/client01"),
    764: ("nes-trial704/arm705", "705", "nes-longrun694/client01"),
    765: ("nes-credit753/arm-prefix", "690", "nes-static751/sharedfast"),
    766: ("nes-credit753/arm-prefix", "690", "nes-static751/sharedfast"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boards(source, dest):
    proof = json.loads((ROOT / "analysis/bg707-verification.json").read_bytes())
    assert proof["functional_gate"] and proof["FIT_STA_gate"]
    inputs = proof["inputs"]
    pins = {**inputs["base"], **inputs["changed"]}
    for name, expected in pins.items():
        assert digest(source / name) == expected, name
    for number in (763, 765):
        board = dest / f"board{number}"
        board.mkdir(parents=True, exist_ok=False)
        for name in pins:
            out = board / name
            out.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(source / name, out)
        shutil.copyfile(PROBES / VARIANTS[number][2] / "sink-program.hex", board / "sink-program.hex")
        for name in ("report_nes_oe612.tcl", "report_nes_reader661.tcl", "report_nes_word660.tcl"):
            shutil.copyfile(source / name, board / name)
    assert digest(source / "sink-program.hex") == digest(PROBES / VARIANTS[764][2] / "sink-program.hex")


def patches(dest):
    for number, (source, old, _) in VARIANTS.items():
        src = PROBES / source / "src"
        out = dest / f"patch{number}"
        out.mkdir(parents=True, exist_ok=False)
        for name in LABELS:
            raw = (src / name).read_bytes()
            assert old.encode() in raw
            (out / name).write_bytes(raw.replace(old.encode(), str(number).encode()))
        if number == 765:
            # Use the board service's existing tick read. Keep the hardware
            # fault check ahead of timeout and avoid a second tick read per SPI.
            name = "nes_runtime_board165.inc"
            raw = (src / name).read_text()
            anchor = " uint32_t now=getticks();"
            assert raw.count(anchor) == 1
            raw = raw.replace(anchor, anchor + "\n if((uint32_t)(now-native_runtime165.started)>=6000u){"
                              "\n  native_runtime165.result=NES_RUNTIME165_DEADLINE;return false;\n }")
            old = "if(native_runtime165.result!=NES_RUNTIME693_USER&&!nes_run136.first_error)"
            new = ("if(native_runtime165.result!=NES_RUNTIME693_USER&&"
                   "(native_runtime165.result!=NES_RUNTIME165_DEADLINE||!native_runtime165.frames)"
                   "&&!nes_run136.first_error)")
            assert raw.count(old) == 1
            (out / name).write_text(raw.replace(old, new), newline="\n")
            # Freeze the last statistics bin when an in-flight operation
            # crosses 60s. Long-play builds retain their rolling epochs.
            name = "nes_budget210.c"
            raw = (src / name).read_text()
            a = raw.index(" if((uint32_t)(elapsed-s->epoch693)>=6000u)")
            b = raw.index("s->open=true;", a)
            raw = raw[:a] + " s->frame_start=elapsed;s->bin=elapsed/500<12?elapsed/500:11;" + raw[b:]
            (out / name).write_text(raw, newline="\n")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--patches", type=Path, required=True)
    args = parser.parse_args()
    boards(args.board, args.out)
    patches(args.patches)
