"""Replay the two-batch FINISH boundary against the MMC639 fitted RTL inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MODULES = """domain_reset124 capture_lease201 direct206 plan_spi200 plan_batch206
native_mailbox206 source_tile192 chr_cache611 obj_capture611 tile205 native_arbiter165
tile_bulk206 bulk_control194 bulk_aperture188 screen_status151""".split()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(name):
    return json.loads((ROOT / "analysis" / name).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("board", "out", "bin"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    package = evidence("trial639-package.json")
    assert digest(args.board / "output_files/board.sof") == package["board"]["SHA"]["board.sof"]
    pins = evidence("trial613-package.json")["inputs"] | evidence("export636-verification.json")["board_changes"]
    sources = ["nes_" + module + ".sv" for module in MODULES]
    for name in sources:
        assert digest(args.board / name) == pins[name], name
        shutil.copyfile(args.board / name, args.out / name)
    benches = ["fault641_tb", "boot641_tb"]
    for name in ["spi200_bus.svh", *(name + ".sv" for name in benches)]:
        shutil.copyfile(ROOT / "tests/nes-functional" / name, args.out / name)
    commands = [("vlib", "vlib", ["work"]),
                ("vlog", "vlog", ["-sv", *sources, *(name + ".sv" for name in benches)])]
    for bench in benches:
        commands.append(("vsim", bench, ["-c", bench, "-gSPI_HALF=190.476", "-do",
                        "onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"]))
    for tool, label, params in commands:
        with (args.out / (label + ".log")).open("wb") as log:
            subprocess.run([args.bin / (tool + ".exe"), *params], cwd=args.out,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=150)
    log = (args.out / "fault641_tb.log").read_text(errors="replace")
    signature = evidence("hardware640-mmc639.json")["runs"][0]["fields"]["plan_reply_hex"]
    assert log.count("reply=" + signature) == 3 and "PASS641" in log
    boot = (args.out / "boot641_tb.log").read_text(errors="replace")
    assert "PASS641 SPI73" in boot
    log += boot
    print("\n".join(line for line in log.splitlines()
                    if any(tag in line for tag in ("FIRST case=", "CANCEL case=", "E8 case=", "BOOT case=", "PASS641"))))


if __name__ == "__main__":
    main()
