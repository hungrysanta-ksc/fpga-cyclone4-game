# SPDX-License-Identifier: MIT
"""Run self-contained original NES memory RTL tests with installed Questa.

No upstream core, game ROM, historical raw evidence, or license file is loaded.
Use the already authorized local license workflow before invoking this driver.
Raw logs and source copies remain in a fresh output directory, outside Git.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "local_memory": (["nes_local_memory"], [],
                     "PASS LOCAL MEMORY checks=153604 complete_scrubs=3 interrupted_scrubs=1 bytes=12288"),
    "rom_early": (["nes_rom_early"], [],
                  "PASS ROM EARLY checks=4168 requests=525 cache_pairs=256 negative_cases=6"),
    "rom_boot": (["nes_rom_physical", "nes_rom_loader", "nes_rom_boot"], ["rom_boot_model"],
                 "PASS BOOT checks=360505 read_bytes=180226 negative_cases=8 images=2"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_suite(questa, out):
    out.mkdir()  # Never replace a previous experiment.
    result = {"suite": "NES-PUBLIC-UNITS-053", "scope": "original standalone RTL only",
              "hardware_test": False, "cases": {}}
    suffix = ".exe" if os.name == "nt" else ""
    for name, (rtl, models, marker) in CASES.items():
        folder = out / name
        folder.mkdir()
        files = [ROOT / "src/nes" / (n + ".sv") for n in rtl]
        files += [ROOT / "tests/nes-functional" / (n + ".sv")
                  for n in [*models, name + "_tb"]]
        hashes = {}
        for source in files:
            shutil.copyfile(source, folder / source.name)
            hashes[source.relative_to(ROOT).as_posix()] = sha(source)
        steps = [("vlib", ["work"]), ("vlog", ["-sv", *[p.name for p in files]]),
                 ("vsim", ["-c", name + "_tb", "-do",
                           "onerror {quit -code 1}; run -all; quit -f"])]
        for tool, args in steps:
            log = folder / (tool + ".log")
            with log.open("wb") as stream:
                completed = subprocess.run([str(questa / (tool + suffix)), *args],
                                           cwd=folder, stdout=stream, stderr=subprocess.STDOUT,
                                           timeout=240, check=False)
            content = log.read_text(errors="replace")
            if completed.returncode or re.search(r"\*\* (?:Fatal|Error)(?:\s|:)", content):
                raise RuntimeError(f"{name}/{tool} failed: inspect {log}")
        if marker not in content:
            raise RuntimeError(f"{name}: expected assertion completion missing; inspect {log}")
        result["cases"][name] = {"passed": True, "pass_marker": marker, "sources": hashes,
                                "simulation_log_sha256": sha(log)}
        print(marker, flush=True)
    result["passed"] = True
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questa-bin", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run_suite(args.questa_bin.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()
