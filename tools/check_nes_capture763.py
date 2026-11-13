"""Replay the empty next capture against the 707D board sources used for A/B."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from check_nes_fault641 import MODULES, ROOT, digest


def run(board, out, binaries):
    out.mkdir(parents=True, exist_ok=False)
    names = ["nes_" + m + ".sv" for m in MODULES]
    names += ["nes_native_export203.sv", "nes_geometry_sender653.sv"]
    for name in names:
        shutil.copyfile(board / name, out / name)
    for name in ["fault641_tb.sv", "spi200_bus.svh", "reject643.svh"]:
        shutil.copyfile(ROOT / "tests/nes-functional" / name, out / name)
    # 660 added the high byte of the 16-bit BG memory response. The legacy
    # fixture supplies zero memory data, so connect both bytes of that word.
    tb = out / "fault641_tb.sv"
    source = tb.read_text()
    port = ".mem_data(8'd0)"
    assert source.count(port) == 1
    tb.write_text(source.replace(port, port + ",.bg_word(8'd0)"), newline="\n")
    assert ".discard_permitted(export_permitted204)" in (board / "nes_live_joint.sv").read_text()
    def command(tool, args, label):
        with (out / (label + ".log")).open("wb") as stream:
            subprocess.run([binaries / (tool + ".exe"), *args], cwd=out, stdout=stream,
                           stderr=subprocess.STDOUT, timeout=120, check=True)
    command("vlib", ["work"], "lib")
    command("vlog", ["-sv", "+define+WITNESS642+REJECT643+DEFER643", *names, "fault641_tb.sv"], "compile")
    cases = []
    for gen in (32, 97):
        for phase in range(12):
            label = f"g{gen}-p{phase}"
            command("vsim", ["-c", "fault641_tb", f"-gGEN643={gen}", f"-gHOST_PHASE={phase}",
                             "-gNES_HALF=23.281", "-gSPI_HALF=190.476",
                             "-do", "onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"], label)
            assert f"PASS643 gen={gen} STOP" in (out / (label + ".log")).read_text()
            cases.append(label)
    (out / "result.json").write_text(json.dumps(dict(cases=cases, files={n:digest(out/n) for n in names}), indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("board", "out", "bin"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    run(a.board, a.out, a.bin)
