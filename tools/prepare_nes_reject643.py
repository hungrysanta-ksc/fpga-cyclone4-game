"""Materialize the deferred-discard board without modifying the MMC642 trial."""
import argparse
from pathlib import Path
from prepare_nes_witness642 import prepare
from check_nes_reject643 import fix
from check_nes_fault641 import digest, evidence


def materialize(base639, baseline, out):
    assert digest(baseline / "output_files/board.sof") == evidence("witness642-package.json")["board"]["SHA"]["board.sof"]
    prepare(base639, out)
    for f in out.rglob("*"):
        if f.is_file():
            assert digest(f) == digest(baseline / f.relative_to(out)), f.name
    paths = [out / n for n in ("nes_native_export203.sv", "nes_live_joint.sv")]
    for f, updated in zip(paths, fix(*(f.read_text() for f in paths))):
        f.write_text(updated, newline="\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("base639", "baseline", "out"):
        p.add_argument("--" + n, type=Path, required=True)
    a = p.parse_args()
    materialize(a.base639, a.baseline, a.out)
