"""Bind the diagnostic RTL to the board build and decode the actual ARM FINISH log."""
import argparse
from pathlib import Path
import re
from check_nes_fault641 import digest, evidence, MODULES, simulate
from check_nes_fault641_arm import replay
from prepare_nes_witness642 import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "board", "out", "bin", "src"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--prior642", type=Path, help="MMC642 board for the 643 deferred-discard regression")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    derived = args.out / "reference"
    if args.prior642:
        from prepare_nes_reject643 import materialize
        materialize(args.base, args.prior642, derived)
    else:
        prepare(args.base, derived)
    for path in derived.rglob("*"):
        if path.is_file():
            assert digest(path) == digest(args.board / path.relative_to(derived)), path.name
    pins = {"nes_" + m + ".sv": digest(derived / ("nes_" + m + ".sv")) for m in MODULES}
    log, boot = simulate(args, pins, ["+define+WITNESS642"])
    assert "PASS642 FINISH" in log and "PASS641 SPI73" in boot
    pkg = evidence("trial639-package.json")
    assert digest(args.src / "obj-nes-100/sd2snes.elf") == pkg["ELF"]
    assert digest(args.src / "obj-nes-100/firmware.stm") == pkg["firmware_SHA256"]
    fields = evidence("hardware640-mmc639.json")["runs"][0]["fields"]
    for case in range(1, 7):
        raw = re.search(rf"E8 case={case} reply=([0-9a-f]{{40}})", log)[1]
        replay(args.src, fields, bytes.fromhex(raw))
        print(f"ARM retained full fault E8 case={case} reply={raw}")
    print("PASS642 RTL, stage-0 SPI73, linked MMC639 FINISH and EA rejection")


if __name__ == "__main__":
    main()
