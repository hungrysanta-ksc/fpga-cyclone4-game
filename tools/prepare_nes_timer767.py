"""Gate the timed comparison on its live RUN owner, after native_boot172."""
from argparse import ArgumentParser
from pathlib import Path

from prepare_nes_trial763 import LABELS, PROBES, ROOT, digest
from package_nes_trial704 import read


def prepare(src, out):
    assert digest(src / "obj-nes-100/firmware.stm") == read(ROOT / "analysis/trial763-package.json")["variants"]["765"]["firmware"]
    out.mkdir(parents=True, exist_ok=False)
    for name in LABELS:
        data = (src / name).read_bytes()
        assert b"765" in data and b"767" not in data
        (out / name).write_bytes(data.replace(b"765", b"767"))
    name = "nes_runtime_board165.inc"
    text = (src / name).read_text()
    old = "if((uint32_t)(now-native_runtime165.started)>=6000u)"
    assert text.count(old) == 1 and "native_runtime165.receiver=NULL;" in text
    (out / name).write_text(text.replace(old, "if(native_runtime165.receiver&&(uint32_t)(now-native_runtime165.started)>=6000u)"), newline="\n")


if __name__ == "__main__":
    p = ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    prepare(PROBES / "nes-trial763/timed765/src", p.parse_args().out)
