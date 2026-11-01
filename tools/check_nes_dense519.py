# SPDX-License-Identifier: MIT
"""Exercise a zero/OBJ-only generation on the linked MCU, including cancellation."""
import argparse
import json
from pathlib import Path

from check_nes_supply485_arm import ARM, sha


def run(arm, candidate, mode):
    m = ARM(arm, mode)
    m.setup()
    before = len(m.endpoint.calls)
    assert m.emit(2, 0, 0) and len(m.endpoint.calls) == before
    ok = bool(m.emit(1, 0, 3))
    first = m.endpoint.accepted
    if mode != "bad_E8_CRC":
        assert ok and first == int(candidate)
    if ok:
        ok = bool(m.emit(1, 1, 6))
    if ok:
        ok = bool(m.call("nes_plan200_end", [m.p]) and m.call("nes_plan200_progress", [m.p, 1]))
    assert ok == (mode == "normal"), mode
    assert not m.get(m.s, "nes_native_sink165", "displayed") and not m.endpoint.rearmed
    before = len(m.endpoint.calls)
    if not ok:
        assert not m.call("nes_plan200_end", [m.p])
    assert not m.call("nes_plan200_retire", [m.p])
    assert len(m.endpoint.calls) == before and not m.endpoint.rearmed
    return dict(mode=mode, first_obj_accepted_batches=first, finish=ok)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    result = {}
    for name in ("baseline", "candidate"):
        src = getattr(args, name)
        blob = src / "obj-nes-100/firmware.stm"
        text, data, bss = map(int, (src.parent / "size.log").read_text().splitlines()[-1].split()[:3])
        result[name] = dict(sha256=sha(blob), firmware_bytes=blob.stat().st_size, text_bytes=text,
                            data_bytes=data, bss_bytes=bss,
                            cases=[run(src, name == "candidate", mode) for mode in
                                   ("normal", "bad_E8_CRC", "STOP_after_E9", "STOP_after_bulk", "wrong_generation", "bad_accepted", "bad_ACK")])
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
