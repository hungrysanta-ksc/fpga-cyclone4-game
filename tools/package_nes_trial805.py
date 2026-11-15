"""Build the MMC805/806 hardware handoff from the routed 804 board and linked STOP fix."""
import argparse
from pathlib import Path
from types import SimpleNamespace

from assemble_nes_trial792 import replace_client
from package_nes_trial704 import ROOT, image, read, sha
from package_nes_trial802 import package_pair
from prepare_nes_trial802 import PROBES, rename_edition
from replay_nes_output768 import CONTROL_ELF

WORK = PROBES / "nes-trial805"
PARENT = PROBES / "nes-fortress804"
EDITIONS = ((802, 805), (803, 806))


def board_evidence(board, proof):
    fit = proof["Quartus_Lite"]["nes-fortress804-board"]
    assert all(sha(board/"output_files"/name) == expected for name,expected in fit["files"].items())
    assert sha(board/"rtl/ppu.sv") == fit["ppu"] and min(fit["worst_ns"].values()) >= 0
    return fit


def package(board, temp, proof):
    base = read(ROOT/"analysis/trial802-package.json")
    original = PROBES/"nes-trial802/MMC802-60SEC-MMC803-LONG.zip"
    parents, references, checks = {}, {}, {}
    delivery = temp/"nes-delivery805"
    fit = board_evidence(board, proof)
    assert read(delivery/"routing806.json")["base_SOF"] == fit["files"]["board.sof"]
    for parent,n in EDITIONS:
        parent_link = PARENT/f"link{parent}a"
        expected = proof["ARM"][str(parent)]
        assert sha(parent_link/"src/obj-nes-100/firmware.stm") == expected["firmware"]
        parents[parent] = parent_link, CONTROL_ELF["804T" if n == 805 else "804L"]
        references[parent] = f"nes-804-display-{parent}"
        src = WORK/f"link{n}/src"
        assert sha(src/"nes_run136.inc") == sha(parent_link/"src/nes_run136.inc")
        fw = src/"obj-nes-100/firmware.stm"
        stopped = read(WORK/f"check{n}/stopped.json")
        assert stopped == expected["stopped"] and fw.stat().st_size == expected["bytes"]
        guards = read(WORK/f"check{n}/independent.json")
        assert guards["firmware"] == sha(fw) and guards["ACK"] == expected["independent"]
        report = read(WORK/f"check{n}/report.json")
        assert report["context"]["raw"] == stopped["late"]["context"]
        assert report["file"] == f"/sd2snes/nes-game-last-mmc{n}.txt"
        for phase in (1,2):
            replay = read(temp/f"nes-trial805-{n}-p{phase}/result.json")
            ref = expected["display"][str(phase)]
            assert replay["passed"] and replay["vram_DMA_B"] == ref["DMA"]
            assert [f["ACK_masterclock"] for f in replay["frames"]] == ref["ack"]
        checks[n] = dict(recovered_context=stopped["late"]["context"],
                         recovered_ppu=stopped["late"]["ppu"],
                         context_cases=list(stopped), independent=guards["ACK"], formatted_report=report)
    package_pair(board,temp,delivery,WORK,EDITIONS,parents,base,original,fit,
                 dict(reference_SHA256=sha(ROOT/"analysis/fortress804.json"),linked_checks=checks),
                 reference_runs=references)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("patch","assemble","package"))
    parser.add_argument("temp", type=Path)
    parser.add_argument("--quartus", type=Path)
    args = parser.parse_args()
    board = args.temp/"nes-fortress804-board"
    proof = read(ROOT/"analysis/fortress804.json")
    if args.action == "patch":
        for parent,n in EDITIONS:
            rename_edition(PARENT/f"link{parent}a/src",WORK/f"patch{n}",parent,n)
    elif args.action == "assemble":
        board_evidence(board,proof)
        delivery = args.temp/"nes-delivery805"
        delivery.mkdir()
        image(SimpleNamespace(number="805",board=board,out=delivery/"packed805",quartus=args.quartus))
        replace_client(806,board,delivery,args.quartus,PROBES/"nes-longrun694/client01")
    else:
        package(board,args.temp,proof)
