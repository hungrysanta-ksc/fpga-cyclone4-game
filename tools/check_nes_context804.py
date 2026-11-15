"""Feed the stopped 801I observer's SPI bytes to the linked ARM fault exit."""
import argparse
import json
import re
from pathlib import Path

from check_nes_reset796 import replay


def check(src, log):
    tokens = re.findall(r"PAGE804 cmd=(\w{2}) reply=(\w{14})", log.read_text())
    assert len(tokens) == 12
    pages = {int(op, 16): bytes.fromhex(reply) for op, reply in tokens}
    assert set(pages) == {0x71, 0x72, 0x74, 0x75}
    assert all(pages[int(op, 16)].hex() == reply for op, reply in tokens)
    context = (pages[0x71][2:] + pages[0x72][2:5]).hex()
    assert (pages[0x74][2:] + pages[0x75][2:5]).hex() == "50d3ce0000a08001"
    # A distinct pre-existing word proves that an earlier capture is preserved.
    saved = 0xfedcba9876543210
    malformed = dict(pages)
    malformed[0x72] = pages[0x72][:-1] + b"\x02"
    cases = {}
    for tag, data, previous, expected in (("late", pages, None, context),
                                          ("bad_revision", malformed, None, "0"*16),
                                          ("already_saved", pages, saved, f"{saved:016x}")):
        r = replay(src, 2, stopped_pages=data, retained_context=previous)
        assert r["context"] == expected and r["status"] == [4, 3, int(tag != "bad_revision")]
        assert r["ppu"] == "50d3ce0000a08001" and r["ppu_valid"] == 1
        cases[tag] = r
    cases["clean"] = replay(src, 2)
    return cases


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("src", "log", "out"):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    a.out.write_text(json.dumps(check(a.src, a.log), indent=2) + "\n")
