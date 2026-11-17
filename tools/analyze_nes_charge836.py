"""Compare 2576 recovery with 2580's following VBlank on the same timeline."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_group835 import read
from analyze_nes_map830 import point, window
from analyze_nes_repeat833 import inspect
from analyze_nes_seal831 import contents, measure
from nes_charge836 import OUT, PROBES
from nes_raw506 import sha
from replay_nes_repeat833 import verify_rejection


TAGS = (
    "832base", "835progresswarmfixed", "836v2chargefixed", "836v2rawfixed",
    "836v2bothfixed", "836v2bothdirectfixed", "836v2bothearlyfixed",
    "836v2bankearlyfixed", "836v2banksplitfixed", "836v2bothdirect",
    "836v2bankearly", "836v2banksplit",
)


def phase_results(temp, phase):
    prefix = f"nes-tile821-demoB-jointmirror-p{phase}-"
    reference = temp / (prefix + TAGS[0])
    baseline = measure(reference, reference)
    expected, _ = inspect(reference)
    report = {}
    for tag in TAGS:
        folder = temp / (prefix + tag)
        data = read(folder, reference, baseline)
        image, commands = inspect(folder)
        assert image == expected
        raw = [c for c in commands if 1121 <= c[0] < 1505]
        if tag != "832base":
            assert len(raw) == 1 and raw[0][1] == 9
        rows = [r for r in window(folder) if r["g"] == 910]
        raw_head = next((r for r in rows if r["event"] == "load" and r["op"] == 9), None)
        tail = {
            "last_OBJ_return": point(next(r for r in reversed(rows) if r["event"] == "ack" and r["op"] == 7 and r["section"] == 1)),
            "palette_head": point(next(r for r in rows if r["event"] == "load" and r["section"] == 3)),
            "SEAL_head": point(next(r for r in rows if r["event"] == "load" and r["op"] == 3)),
            "upload": point(next(r for r in rows if r["event"] == "upload165_entry")),
            "reveal": point(next(r for r in rows if r["event"] == "reveal")),
        }
        if raw_head:
            tail["raw_head"] = point(raw_head)
        report[tag] = {k: data[k] for k in (
            "intervals", "last_ACK", "delta_ACK", "delta2572", "reveal2576", "palette", "OAM",
            "raw_B", "raw_complete", "map2580", "map4_ack", "map5_load", "E0_between_map_E1", "gate",
        )}
        report[tag].update(tail2580=tail, raw_transactions=len(raw), raw_wire_B=sum(c[2] for c in raw))
        if tag in ("836v2banksplitfixed", "836v2banksplit"):
            live = [list(map(int, line.split())) for line in (folder / "totals836.txt").read_text().splitlines()]
            assert [r[0] for r in live] == list(range(909 if tag.endswith("fixed") else 905, 911))
            assert live[-2:] == [[909, 1712, 72], [910, 1472, 32]]
            report[tag]["checked_live_bytes_and_descriptor_span"] = live
    return report


def opening_results(temp, phase):
    prefix = f"nes-tile821-earlyB-jointmirror-p{phase}-"
    ref, candidate = (temp / (prefix + tag) for tag in ("823826", "836v2banksplit"))
    assert contents(ref) == contents(candidate)
    for generation in range(905, 911):
        name = f"frame-{generation}.rgb"
        assert (candidate / name).read_bytes() == (ref / name).read_bytes()
    results = []
    for folder in (ref, candidate):
        run = json.loads((folder / "joint.json").read_bytes())
        assert run["passed"] and run["commits"] == 6 and run["last_status"] == 1
        visible = [r["frame"] for r in window(folder) if r["event"] == "reveal"]
        assert len(visible) == 6
        with (folder / "seal528.csv").open() as f:
            latch = [r for r in csv.DictReader(f) if r["g"] == "908" and r["event"] == "latch"][-1]
        results.append(dict(intervals=[b-a for a,b in zip(visible[1:],visible[2:])],
                            final_latch_908=[int(latch[k]) for k in ("line", "h")],
                            last_ACK=run["frames"][-1]["ACK_masterclock"]))
    return dict(MMC826=results[0], candidate=results[1],
                delta_ACK=results[1]["last_ACK"]-results[0]["last_ACK"])


def checks(temp):
    prefix = "nes-tile821-demoB-jointmirror-p1-836v2banksplitfixed"
    for fault, status in (("stop", 228), ("coverage", 224)):
        folder = temp / (prefix + "guard" + fault)
        rows = window(folder)
        assert [r["g"] for r in rows if r["event"] == "reveal"] == list(range(905, 909))
        assert [(r["g"], r["op"], r["value"]) for r in rows if r["event"] == "ack" and r["value"] >= 224] == [(909, 3, status)]
        if fault == "stop":
            stop = int((folder / "injected835.txt").read_text())
            assert not any(r["event"] in ("ppu_dma", "ppu_last") and r["clock"] >= stop for r in rows)
    verify_rejection(temp / (prefix + "damage"), "damage")
    images = {}
    for mode in ("direct", "early", "split"):
        image = PROBES / f"nes-output823/link-836{mode}/src/obj-nes-100/firmware.stm"
        menu = json.loads((OUT / f"menu-{mode}.json").read_bytes())
        base = json.loads((OUT / f"base-{mode}/result.json").read_bytes())
        assert menu["firmware"] == base["firmware_sha256"] == sha(image)
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        images[mode] = dict(ARM_SHA256=sha(image), flash_B=image.stat().st_size, menu_release=True, base_return=True)
    for mode in ("charge", "raw", "both", "bank"):
        folder = OUT / ("final-" + mode)
        build = json.loads((folder / "build.json").read_bytes())
        images[mode] = dict(ROM_SHA256=sha(folder / "sink165.sfc"), physical_B=build["physical_ROM_B"], free_B=build["physical_free_B"])
    return dict(images=images, stop_clock=stop, STOP=228, coverage_error=224, WRAM_damage_error=224)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("temp", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    result = dict(phases={p: phase_results(args.temp, p) for p in (1, 2)},
                  opening={p: opening_results(args.temp, p) for p in (1, 2)}, checks=checks(args.temp))
    args.out.write_text(json.dumps(result, indent=2) + "\n")
