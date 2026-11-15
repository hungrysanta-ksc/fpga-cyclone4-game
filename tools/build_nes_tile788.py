# SPDX-License-Identifier: MIT
"""Let an already selected <=32B tile use the checked late VBlank grant."""
import argparse
import json
from pathlib import Path

from build_nes_trace_replay import Code
from nes_raw506 import sha
from prepare_nes_complete685 import edit as edit685
from prepare_nes_progress680 import ORIGIN, client


def build(base635, base685, out):
    pinned = json.loads((base685 / "build.json").read_text())
    def edit(body, labels):
        body, labels = edit685(body, labels)
        assert bytes(body) == (base685 / "body.bin").read_bytes()
        body = bytearray(body)
        end = labels["map_beam_ok526"] - ORIGIN
        spare = end - 13
        assert body[spare:end] == bytes([0xea]) * 13
        fallback = bytes([0x4c]) + (labels["late_map680"] & 65535).to_bytes(2, "little")
        site = body.index(fallback, labels["selected526"] - ORIGIN, spare)
        # Selected non-map descriptor only, after the existing 225..252 latch.
        # X/Y retain the actual checked descriptor and DMA length.
        code = Code(ORIGIN + spare)
        code.labels.update(labels)
        code.emit(0xc0,33,0)
        code.branch(0x90, "map_beam_ok526")
        code.jump("late_map680")
        patch = code.finish()
        body[spare:spare + len(patch)] = patch
        body[site:site + 3] = bytes([0x4c]) + ((ORIGIN + spare) & 65535).to_bytes(2, "little")
        assert len(body) == pinned["body_bytes"]
        return body, labels
    result = client(base635, out, extra_edit=edit)
    result.update(candidate="small_tile788", reference=sha(base685 / "sink165.sfc"),
                  body_sha256=sha(out / "body.bin"), tile_bytes=32, last_latch_line=252)
    (out / "build.json").write_text(json.dumps(result, indent=2) + "\n", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("base635", "base685", "out"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    build(args.base635, args.base685, args.out)
