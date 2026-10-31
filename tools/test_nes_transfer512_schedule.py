# SPDX-License-Identifier: MIT
"""Use the same 509 ROM calendar, ARM cost assumptions and actual 65816 for each arm."""
import argparse
import json
from pathlib import Path
from test_nes_service509_schedule import Calendar
import test_nes_raw506_joint as joint
from nes_transfer512 import input_packets, legacy_packets

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--variant", choices=("original","map","input","both"), required=True)
    for name in ("arm","data","fixture","plans","client","mesen","out","calendar","driver503"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--board-packets",action="store_true", help="Use the verified original FPGA block boundaries")
    a = p.parse_args()
    a.out = a.out.resolve()
    a.candidate = a.capture_gate = True
    a.frames, a.cpi, a.spi_us, a.rom_stride, a.rom_phase, a.start = 12, 2, 0, 48, 0, 3000000
    from nes_transfer512_rpc import PipeLink
    joint.Link = PipeLink
    if a.variant in ("input", "both"):
        joint.encode = input_packets
    elif getattr(a,"board_packets",False):
        joint.encode = legacy_packets
    joint.run(a)
    result = json.loads((a.out / "joint.json").read_text())
    result["variant"] = a.variant
    result["parameters"]["ROM_calendar"] = Calendar(a.calendar).summary
    (a.out / "joint.json").write_text(json.dumps(result, indent=2) + "\n")
