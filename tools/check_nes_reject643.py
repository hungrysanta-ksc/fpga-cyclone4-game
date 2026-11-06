"""Exercise the MMC642 exporter/lease overlap with the two captured boundary identities."""
import argparse
from pathlib import Path
import shutil
import subprocess
from check_nes_fault641 import digest, evidence, MODULES, ROOT
from nes_status495 import once


def fix(export, joint):
    export = once(export, "enable,start_permitted,", "enable,start_permitted,discard_permitted,")
    export = once(export, "begin release_frame<=1;state<=DRAIN;error<=2;end", """begin
      // The rejected collector belongs to the next input. Wait for the
      // preceding display to retire before requesting its collector release.
      if(discard_permitted)begin release_frame<=1;state<=DRAIN;error<=2;end
     end""")
    joint = once(joint, ".start_permitted(export_permitted204||reader_drained204),",
                 ".start_permitted(export_permitted204||reader_drained204),.discard_permitted(export_permitted204),")
    return export, joint


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("board", "out", "bin"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    assert digest(a.board / "output_files/board.sof") == evidence("witness642-package.json")["board"]["SHA"]["board.sof"]
    a.out.mkdir(parents=True, exist_ok=False)
    source = (a.board / "nes_native_export203.sv").read_text()
    joint = (a.board / "nes_live_joint.sv").read_text()
    assert ".enable((export_permitted204||(lease204&&plan_closed204))&&!direct_nes_fault204)" in joint
    fixed, fixed_joint = fix(source, joint)
    for mode in ("baseline", "defer"):
        folder = a.out / mode
        folder.mkdir()
        sources = ["nes_" + m + ".sv" for m in MODULES]
        for f in sources:
            shutil.copyfile(a.board / f, folder / f)
        exporter = "nes_native_export203.sv"
        (folder / exporter).write_text(source if mode == "baseline" else fixed, newline="\n")
        (folder / "nes_live_joint.sv").write_text(joint if mode == "baseline" else fixed_joint, newline="\n")
        tests = ROOT / "tests/nes-functional"
        for f in ("spi200_bus.svh", "fault641_tb.sv", "reject643.svh"):
            shutil.copyfile(tests / f, folder / f)
        commands = [("vlib", "lib", ["work"]),
                    ("vlog", "compile", ["-sv", "+define+WITNESS642+REJECT643" +
                     ("+DEFER643" if mode == "defer" else ""), *sources, exporter, "fault641_tb.sv"])]
        for gen in (32, 97):
            for phase in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
                commands.append(("vsim", f"g{gen}-p{phase}", ["-c", "fault641_tb", f"-gGEN643={gen}",
                                 f"-gHOST_PHASE={phase}", "-gNES_HALF=23.281", "-gSPI_HALF=190.476",
                                 "-do", "onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"]))
        for program, label, args in commands:
            log = folder / (label + ".log")
            with log.open("wb") as output:
                subprocess.run([a.bin / (program + ".exe"), *args], cwd=folder, check=True,
                               stdout=output, stderr=subprocess.STDOUT, timeout=120)
            if program == "vsim":
                assert "PASS643" in log.read_text()


if __name__ == "__main__":
    main()
