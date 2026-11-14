# SPDX-License-Identifier: MIT
"""Extend the linked 763/767 schedule through the workload-matched capture 969."""
import argparse
import json
import runpy
import shutil
import sys
from contextlib import ExitStack
from itertools import groupby
from pathlib import Path
from unittest.mock import patch

from analyze_nes_scroll229 import FETCH, records
from check_nes_record657 import bench, encode, prepare as sender
from check_nes_snoop601 import pin, read, samples, sha
from prepare_nes_dense519 import ROM_SHA, tiles
from test_nes_schedule496 import prepare

LAST = 970
ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"


def inputs(out, game):
    pin(game, ROM_SHA)
    out.mkdir(parents=True, exist_ok=False)
    original = PROBES / "nes-output489/audit01"
    fixture = out / "fixture"
    fixture.mkdir()
    prepare(argparse.Namespace(rom=game, frames=LAST-904, compact=original, row_counts=None), fixture, True)
    assert tiles(fixture, 957) == tiles(PROBES / "nes-dense519/fixture02", 957)
    for g in range(905, LAST+1):
        prior = PROBES / "nes-seal538/plans01" if g <= 957 else original
        dst = out / "plans" / f"frame{g}"
        dst.mkdir(parents=True)
        shutil.copyfile(prior / dst.name / "plans.json", dst / "plans.json")
        assert (original / dst.name / "expected-hdma.bin").read_bytes() == (fixture / f"expected-{g}.bin").read_bytes()
    geometry = PROBES / "nes-geometry230"
    fetch = geometry / "capture02/ppu-fetch.bin"
    stim = geometry / "stim05"
    pins = read(stim / "result.json")
    pin(stim / "result.json", read(ROOT / "analysis/geometry230-verification.json")["stimulus_result_sha256"])
    pin(fetch, pins["inputs"][fetch.name])
    by_frame = {r["frame"]: r for r in pins["frames"]}
    chr_rom = game.read_bytes()[0x40010:]
    cache = {}
    for gen, rows in groupby(records(fetch, FETCH), key=lambda r:r[0]):
        if not 958 <= gen <= LAST:
            continue
        raw = stim / f"frame{gen}.hex"
        pin(raw, by_frame[gen]["stimulus_sha256"])
        writes, _ = samples(rows, raw, chr_rom)
        lines = {}
        for kind, addr, value in writes:
            if kind:
                tag = addr // 16
                key = tag % 128
                if key not in lines or lines[key][0] != tag:
                    lines[key] = [tag, {}]
                lines[key][1][addr % 16] = value
        cache[gen] = lines
    assert list(cache) == list(range(958, LAST+1))
    (out / "obj-cache.json").write_text(json.dumps(cache), encoding="utf8")


def replay(variant, extras, remaining, omit_wait):
    import test_nes_obj609 as obj
    import test_nes_tile532 as tile

    original_capture = obj.capture
    original_schedule = tile.run_schedule
    def capture(path):
        frames = original_capture(path)
        for g, lines in read(extras / "obj-cache.json").items():
            frames[int(g)] = {int(k):(tag, {int(addr):v for addr,v in data.items()}) for k,(tag,data) in lines.items()}
        return frames
    def schedule(args, instrument, link, frames):
        assert frames == 53
        def extended_oracle(source, options):
            source = instrument(source, options)
            for gen in range(958, LAST+1):
                directory = args.capture / f"frame{gen}"
                expected = (directory / "expected-cgram.bin").read_bytes() + (directory / "expected-oam.bin").read_bytes()
                assert len(expected) == 1056
                (args.out / f"colors636-{gen}.bin").write_bytes(expected)
            return source
        return original_schedule(args, extended_oracle, link, frames=LAST-904)
    # Counterfactual only on 969. Execute the existing no-wait branch without
    # modifying the linked code, E0 validation, packet admission or final ACK.
    from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_PC
    from test_nes_raw506_joint import Runtime
    base_init = Runtime.__init__
    def hook(cpu, args, link):
        base_init(cpu, args, link)
        assert variant == "767"
        pc, resume = 0x0801eb08, 0x0801eb26
        assert bytes(cpu.u.mem_read(pc, 2)) == bytes.fromhex("2368")
        def omit(u, address, size, unused):
            if cpu.generation == 969 and not cpu.irq:
                cpu.events.append(dict(event="omit_optional_wait768", generation=969, clock=cpu.clock))
                u.reg_write(UC_ARM_REG_PC, resume | 1)
        cpu.u.hook_add(UC_HOOK_CODE, omit, begin=pc, end=pc)
    pin_path = Path(remaining[remaining.index("--arm")+1]) / "obj-nes-100/sd2snes.elf"
    manifest = read(ROOT / f"analysis/trial{variant}-package.json")
    expected = manifest["variants"]["763"]["ELF"] if variant == "763" else manifest["ELF"]
    pin(pin_path, expected)
    sys.argv[1:] = remaining
    with ExitStack() as stack:
        stack.enter_context(patch.object(obj, "capture", capture))
        stack.enter_context(patch.object(tile, "run_schedule", schedule))
        if omit_wait:
            stack.enter_context(patch.object(Runtime, "__init__", hook))
        runpy.run_module("test_nes_status689" if variant == "763" else "test_nes_static751",run_name="__main__")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("inputs")
    p.add_argument("out", type=Path)
    p.add_argument("game", type=Path)
    p = sub.add_parser("sender")
    for arg in ("out", "board", "bin", "prefix"):
        p.add_argument(arg, type=Path)
    p = sub.add_parser("run", add_help=False)
    p.add_argument("variant", choices=("763","767"))
    p.add_argument("extras", type=Path)
    p.add_argument("--omit-wait969", action="store_true")
    a, rest = parser.parse_known_args()
    if a.action == "inputs":
        assert not rest
        inputs(a.out,a.game)
    elif a.action == "sender":
        assert not rest
        a.data = PROBES / "nes-delta231/test07"
        a.guards = False
        sender(a, encoder=encode, codec="nes_geometry_sender653.sv",
               bench=lambda s:bench(s,False,False,True,False,False), generations=range(957,LAST+1))
        prefix, tail = read(a.prefix), read(a.out / "sender.json")
        assert [r["wire"] for r in tail["957"]] == [r["wire"] for r in prefix["957"]]
        (a.out / "joint-sender.json").write_text(json.dumps({**tail,**prefix}),encoding="utf8")
    else:
        replay(a.variant,a.extras,rest,a.omit_wait969)
