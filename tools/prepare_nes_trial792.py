"""Build MMC792/793 inputs from the selected 791R schedule and the 789 screen code."""
import argparse
import ast
import difflib
import json
import re
from pathlib import Path
from unittest.mock import patch

from prepare_nes_report594 import literal
from prepare_nes_trial763 import PROBES, ROOT, digest
from package_nes_window516 import LABELS
from prepare_nes_longrun694 import optimal
import nes_rom636 as codec

BASE = PROBES / "nes-tail791/link-lane_mask_seal/src"
CLIENT = PROBES / "nes-seal789/client"
OUT = PROBES / "nes-trial792"


def port(name):
    reference = PROBES / "nes-trial763"
    before, after = [(reference / edition / "src" / name).read_text().splitlines(True)
                     for edition in ("linked763", "linked764")]
    source = (BASE / name).read_text()
    # Apply each old timed->long hunk to the corresponding unique 791R context.
    for group in difflib.SequenceMatcher(None, before, after, autojunk=False).get_grouped_opcodes(1):
        old = "".join(before[group[0][1]:group[-1][2]])
        new = "".join(after[group[0][3]:group[-1][4]])
        if "int n=nes_report623(" in old:
            # Keep the 791R dictionary and repack the 764 epoch format for it.
            pairs = ast.literal_eval(re.search(r'pairs782\[\] = (".*");', source)[1]).encode("latin1")
            plain = ast.literal_eval(re.search(r'nes_report623\(text,size,0,(".*"),', new)[1]).encode("ascii")
            encoded = plain
            for i in range(0, len(pairs), 2):
                encoded = encoded.replace(pairs[i:i+2], bytes([128+i//2]))
            start = source.index(" int n=nes_report_packed782(text,size,0,")
            end = source.index("  (unsigned long)nes_budget210.displayed_window", start)
            source = (source[:start] + " int n=nes_report_packed782(text,size,0," + literal(encoded)
                      + ",\n  (unsigned long)nes_budget210.epoch693,(unsigned long)nes_budget210.failed_transfers,nes_budget210.open?1u:0u,\n" + source[end:])
            continue
        assert source.count(old) == 1, (name, old)
        source = source.replace(old, new)
    return source


def arm():
    assert digest(BASE / "obj-nes-100/sd2snes.elf") == "a76263cb9fef1f6ab1d9434bc591b00dd9de4311f4b31f3ea120b8ed587fd5fa"
    for n in (792, 793):
        out = OUT / f"patch{n}"
        out.mkdir(parents=True, exist_ok=True)
        for name in LABELS:
            raw = (BASE/name).read_bytes()
            assert b"763" in raw
            (out/name).write_bytes(raw.replace(b"763", str(n).encode()))
        if n == 793:
            for name in ("nes_native_runtime165.c", "nes_runtime_board165.inc", "nes_budget210.c",
                         "nes_native_runtime165.h", "nes_budget210.h"):
                (out/name).write_text(port(name), newline="\n")


def long_client():
    # Carry only the checked L+R+Start+Select service hook into the 789 body.
    old = PROBES / "nes-complete685/client01"
    long = PROBES / "nes-longrun694/client01"
    a, b, c = [(p/"body.bin").read_bytes() for p in (old, long, CLIENT)]
    assert len(c) == len(a) and len(b) == len(a)+36
    merged = bytearray(c)
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            assert c[i] == x
            merged[i] = y
    merged.extend(b[len(a):])
    out = OUT / "client793"
    with patch.object(codec, "pack", optimal):
        codec.build(PROBES/"nes-reuse635/client04", out, edit_body=lambda *_: bytes(merged), allow_extension=True)
    labels = json.loads((CLIENT/"labels.json").read_bytes())
    for k,v in json.loads((long/"labels.json").read_bytes()).items():
        if k.endswith("693"):
            labels[k] = v
    (out/"labels.json").write_text(json.dumps(labels, indent=2)+"\n")
    assert (out/"body.bin").read_bytes() == merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("arm", "long_client"))
    globals()[parser.parse_args().operation]()
