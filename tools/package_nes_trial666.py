"""Package the pinned 665 board/65816 and relabeled 664-all ARM for MMC662 comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zipfile
import zlib

from analyze_nes_export636 import board as board_result
from check_nes_fault641 import ROOT, digest, evidence
from nes_cf68_pair_preflight import decode, encode
from nes_schedule492 import funcs

PREFIX = "01-MMC666-SD-ROOT/"
MARKER = "NES MMC3 666.nh1"
IMAGE = "sd2snes/fpga_mmc666.bi3"
ROM = "sd2snes/nes/mmc666.nes"
LOGS = [f"sd2snes/nes-{kind}-mmc666.txt" for kind in ("progress", "budget", "game-last")]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def package(a):
    proof = evidence("entry665-verification.json")
    previous = evidence("trial662-package.json")
    old, new = (p / "obj-nes-100" for p in (a.base, a.arm))
    assert digest(old / "firmware.stm") == proof["ARM_SHA256"]
    firmware = (new / "firmware.stm").read_bytes()
    assert (old / "firmware.stm").read_bytes()[32:].replace(b"662", b"666") == firmware[32:]
    functions = funcs(new / "sd2snes.elf")
    assert functions and funcs(old / "sd2snes.elf") == functions
    size, crc, inverse = struct.unpack_from("<III", firmware, 8)
    assert firmware[:4] == b"STM3" and size + 512 == len(firmware) <= 212992
    assert zlib.crc32(firmware[512:]) == crc and crc ^ inverse == 0xffffffff
    for name in [MARKER, *("/" + n for n in (IMAGE, ROM, *LOGS))]:
        assert name.encode() + b"\0" in firmware
        assert name.replace("666", "662").encode() + b"\0" not in firmware
    firmware_sha = digest(new / "firmware.stm")
    a.checks.mkdir(parents=True, exist_ok=False)
    def check(name, script, args):
        with (a.checks / (name + ".log")).open("wb") as log:
            subprocess.run([sys.executable, str(ROOT / "tools" / script), *map(str, args)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    for name, script, extra in (("menu", "check_nes_menu533.py", ["--trial", "666"]),
                               ("windows", "check_nes_windows518.py", ["--layout", "trimmed"])):
        check(name, script, ["--arm", a.arm, "--out", a.checks / (name + ".json"), *extra])
    recovery = {}
    for fault in ("none", "program", "done", "busy", "token"):
        check("base-" + fault, "check_nes_transfer512_recovery.py",
              ["--arm", a.arm, "--out", a.checks / ("base-" + fault), "--trial", "666", "--fault", fault])
        row = read(a.checks / ("base-" + fault) / "result.json")
        assert row["passed"] and row["firmware_sha256"] == firmware_sha
        assert row["safe_return"] == row["base_restored"] == int(fault == "none")
        assert row["config_paths"] == ["/" + IMAGE, "/sd2snes/fpga_base.bi3"]
        recovery[fault] = row
    menu, windows = (read(a.checks / (n + ".json")) for n in ("menu", "windows"))
    assert menu["firmware"] == windows["firmware_SHA256"] == firmware_sha
    assert [(w["start_s"], w["end_s"]) for w in windows["accepted"]] == [(5, 40), (40, 55)]
    assert menu["marker_cases"] == 4
    assert all(v["released"] == v["prepared"] == int(k == "normal") for k, v in menu["rows"].items())
    board = board_result(a.board)
    for name, sha in proof["boards"]["entry665"]["timing"]["pins"].items():
        assert digest(a.board / "output_files" / name) == sha
    assert min(board["minimum_slack_ns"].values()) > 0
    assert min(board["ROM_pin_min_setup_ns"].values()) > 0
    raw, packed = (a.image / "board.rbf").read_bytes(), (a.image / Path(IMAGE).name).read_bytes()
    assert digest(a.image / "board.sof") == board["SHA"]["board.sof"]
    assert encode(raw) == packed and decode(packed) == raw
    assert "was successful" in (a.image / "cpf.log").read_text()
    programmer = read(a.programmer / "result.json")
    assert programmer["passed"] and programmer["image_sha256"] == hashlib.sha256(packed).hexdigest()
    assert programmer["rbf_sha256"] == hashlib.sha256(raw).hexdigest()
    rom = read(a.romcheck / "result.json")
    assert rom["bytes"] == 5120 and rom["client"] == proof["client_SHA256"] == digest(a.client / "sink165.sfc")
    assert rom["program"] == digest(a.board / "sink-program.hex") == digest(a.client / "sink-program.hex")
    assert rom["bus"] == digest(a.board / "nes_sink_bus165.sv") and rom["log"] == digest(a.romcheck / "vsim.log")
    assert digest(a.prior) == previous["ZIP_SHA256"]
    files = {
        PREFIX + MARKER: b"", PREFIX + IMAGE: packed, PREFIX + "sd2snes/firmware.stm": firmware,
        PREFIX + "sd2snes/nes/ROM-NOT-INCLUDED.txt": b"Copy your own mmc662.nes as mmc666.nes. SMB3(J) CRC32 5a04eed7.\n",
        "README-KO.txt": (ROOT / "docs/nes-mmc666-trial.ko.md").read_bytes(),
    }
    with zipfile.ZipFile(a.prior) as prior:
        for name in ("sd2snes/fpga_base.bi3", "sd2snes/m3nu.bin"):
            key = "01-MMC662-SD-ROOT/" + name
            data = prior.read(key)
            assert hashlib.sha256(data).hexdigest() == previous["files"][key]
            files[PREFIX + name] = data
    assert not any("RESTORE" in name.upper() or name.lower().endswith((".nes", ".sav", ".srm", ".rtc")) for name in files)
    result = dict(candidate="MMC666", baseline="MMC662", physical_verified=False, board665=board,
                  firmware_SHA256=firmware_sha, ELF=digest(new / "sd2snes.elf"),
                  identical_functions=len(functions), Flash_B=len(firmware), Flash_free_B=212992-len(firmware),
                  menu=menu, windows=windows, recovery=recovery, programmer=programmer, ROM_read=rom,
                  required_ROM={**previous["required_ROM"], "path": ROM}, logs=LOGS,
                  timing_evidence=digest(ROOT / "analysis/entry665-verification.json"),
                  comparison=dict(reference="MMC662", window_s=[[5,40],[40,55]],
                                  reference_fps=[682/35,316/15],
                                  candidate_fps=None, measured_on_hardware=False),
                  ROM_included=False, RESTORE_included=False,
                  files={name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
    files["manifest.json"] = (json.dumps(result, indent=2) + "\n").encode()
    a.out.mkdir(parents=True, exist_ok=False)
    archive = a.out / "MMC666-TRIAL.zip"
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and sorted(z.namelist()) == sorted(files)
        assert all(z.read(n) == b for n,b in files.items())
    result.update(ZIP_SHA256=digest(archive), ZIP_bytes=archive.stat().st_size)
    a.report.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(str(archive.resolve()), result["ZIP_SHA256"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for key in ("base","arm","board","checks","image","programmer","romcheck","client","prior","out","report"):
        p.add_argument("--" + key, type=Path, required=True)
    package(p.parse_args())
