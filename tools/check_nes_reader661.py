"""Compare both candidate timing implementations to the 660 pin/CDC waveform."""
import argparse
import subprocess
from pathlib import Path


def run(a):
    a.out.mkdir(parents=True, exist_ok=False)
    for source, name in ((a.base, "baseline"), (a.counter, "counter_reader"), (a.pipe, "pipe_reader")):
        s = (source / "nes_rom_physical.sv").read_text().replace("module nes_rom_physical #", f"module {name} #", 1)
        (a.out / (name + ".sv")).write_text(s, newline="\n")
    tb = Path(__file__).with_name("nes_reader661_tb.sv")
    for exe, args in (("vlib", ["work"]), ("vlog", ["-sv", "baseline.sv", "counter_reader.sv", "pipe_reader.sv", str(tb.resolve())]),
                      ("vsim", ["-c", "reader661_tb", "-do", "onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"])):
        with (a.out / (exe + ".log")).open("wb") as log:
            subprocess.run([a.bin / (exe + ".exe"), *args], cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert (a.out / "vsim.log").read_text().count("PASS661") == 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for k in ("base", "counter", "pipe", "out", "bin"):
        parser.add_argument("--" + k, type=Path, required=True)
    run(parser.parse_args())
